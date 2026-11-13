"""Append the private ground-effect classes to Iris's RX patch segment."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_jester_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    if struct.unpack_from('<I',data,0x619fc0)[0]&0xff000000!=0xea000000:
        raise ValueError('Rogue registration must precede Jester')
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    headers = [h for h in range(phoff, phoff + stride * count, stride)
               if struct.unpack_from('<I', data, h)[0] == 1]
    h, = [h for h in headers if struct.unpack_from('<I', data, h+24)[0] == 5
          and sum(struct.unpack_from('<I', data, h+o)[0] for o in (4, 16)) == len(data)]
    _, off, va, _, size, mem, _, _ = struct.unpack_from('<8I', data, h)
    assert size == mem
    pad = -(va + size) % 4
    data.extend(bytes(pad)); size += pad
    start = va + size
    trampoline, projectile, props, entry = start+520, start+532, start+544, start+556
    def branch(pc, target, thumb=True):
        delta = target-pc-8
        if delta % 2 or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Growth projectile branch out of range')
        return ((0xfa000000 | ((delta & 2) << 23)) if thumb else 0xea000000) | ((delta >> 2) & 0xffffff)
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-jester'+suffix) for suffix in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
    subprocess.run([tools/'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-fno-math-errno',
                    '-fno-jump-tables', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    f'-DIRIS_DARK_TRACE={int(trace)}', f'-DIRIS_JESTER_STUB={start}',
                    f'-DIRIS_JESTER_REGISTER={trampoline}',f'-DIRIS_JESTER_PROJECTILE_UPDATE={projectile}',f'-DIRIS_JESTER_PROPS_REGISTER={props}', '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools/'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(13):
        pc = start + len(code)
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch(pc+20, entry),
                    0xe28dd010, 0xe8bd8010, 0xe320f000, (-(pc+24)) & 0xffffffff))
    previous=struct.unpack_from('<I',data,0x619fc0)[0];delta=(previous&0xffffff)<<2
    if delta&0x2000000:delta-=0x4000000
    old=0x619fc0+8+delta
    code.extend(struct.pack('<3I',branch(trampoline,old,False),0xe320f000,0xe320f000))
    for address,where,mode,expected in ((0x488e0c,projectile,8,(0xe92d4070,0xed2d8b02)),(0x48b51c,props,9,(0xe92d48f0,0xe24ddd06))):
        actual=struct.unpack_from('<2I',data,address)
        if actual!=expected:raise ValueError(f'Unexpected Jester hook {address:x}: {actual}')
        code.extend(data[address:address+8]);code.extend(struct.pack('<I',branch(where+8,address+8,False)))
        struct.pack_into('<I',data,address,branch(address,start+mode*40,False))
    struct.pack_into('<I',data,0x619fc0,branch(0x619fc0,start,False))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if size + len(code) > 0x10000:
        raise ValueError('Native patch segment capacity exceeded')
    data.extend(code)
    struct.pack_into('<II', data, h+16, size+len(code), size+len(code))
    path.write_bytes(data)
