"""Append the native wizard interval callback to Iris's RX patch segment."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_wizard_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    if struct.unpack_from('<2I', data, 0x6336f8) != (0xe92d48f0, 0xe24dd008):
        raise ValueError('Unexpected wizard update prologue')
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
    trampoline, entry = start+40, start+52
    def branch(pc, target, thumb=True):
        delta = target-pc-8
        if delta % 2 or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Growth projectile branch out of range')
        return ((0xfa000000 | ((delta & 2) << 23)) if thumb else 0xea000000) | ((delta >> 2) & 0xffffff)
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-wizard'+suffix) for suffix in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
    subprocess.run([tools/'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-fno-math-errno',
                    '-fno-jump-tables', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    f'-DIRIS_DARK_TRACE={int(trace)}', f'-DIRIS_WIZARD_STUB={start}',
                    f'-DIRIS_WIZARD_ORIGINAL={trampoline}', '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools/'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(1):
        pc = start + len(code)
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch(pc+20, entry),
                    0xe28dd010, 0xe8bd8010, 0xe320f000, (-(pc+24)) & 0xffffffff))
    code.extend(data[0x6336f8:0x633700])
    code.extend(struct.pack('<I',branch(trampoline+8,0x633700,False)))
    struct.pack_into('<I',data,0x6336f8,branch(0x6336f8,start,False))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if size + len(code) > 0x10000:
        raise ValueError('Native patch segment capacity exceeded')
    data.extend(code)
    struct.pack_into('<II', data, h+16, size+len(code), size+len(code))
    path.write_bytes(data)
