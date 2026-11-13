"""Scoped Peanut extension of the original Repeater allocation and callbacks."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_peanut_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    slots = {0xce529c: 0x3fc8b4, 0xce52ec: 0x3fc43c, 0xce52f0: 0x3fc59c,
             0xce5308: 0x13f310, 0xce52c0: 0x13f290}
    def branch(pc, target, *, link=False, thumb=False):
        delta = target - pc - 8
        if delta % (2 if thumb else 4) or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Peanut ARM branch out of range')
        return ((0xfa000000 | ((delta & 2) << 23)) if thumb else
                0xeb000000 if link else 0xea000000) | ((delta >> 2) & 0xffffff)
    expected = slots | {0xce5278: 0x3b963c, 0x3fc170: branch(0x3fc170, 0xb363dc, link=True),
                        0xce52c4: 0x3fc524, 0xce530c: 0x3ba4f4,
                        0x3fc214: 0xe3a03020, 0x3fc270: 0xe92d47f0,
                        0x3fc274: 0xe24dd040, 0x3a53ec: branch(0x3a53ec, 0x44d13c, link=True)}
    if any(struct.unpack_from('<I', data, p)[0] != v for p, v in expected.items()):
        raise ValueError('Unexpected original Repeater or animation bridge')
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    for header in range(phoff, phoff + stride * count, stride):
        kind, offset, address, _, size, mem, flags, _ = struct.unpack_from('<8I', data, header)
        if kind == 1 and flags == 5 and size == mem and offset + size == len(data):
            break
    else:
        raise ValueError('Missing native patch segment')
    pad = -(address + size) % 4
    data.extend(bytes(pad)); size += pad
    start, trampoline, entry = address + size, address + size + 440, address + size + 452
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-peanut' + e) for e in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    f'-DIRIS_DARK_TRACE={int(trace)}', f'-DIRIS_PEANUT_REFLECT_ORIGINAL={trampoline}',
                    '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(11):
        pc = start + len(code)
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch(pc + 20, entry, thumb=True),
                    0xe28dd010, 0xe8bd8010, 0xe320f000, (-(pc + 24)) & 0xffffffff))
    code.extend(data[0x3fc270:0x3fc278])
    code.extend(struct.pack('<I', branch(trampoline + 8, 0x3fc278)))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if size + len(code) > 0x10000:
        raise ValueError('Native patch segment capacity exceeded')
    for mode, slot in enumerate(slots): struct.pack_into('<I', data, slot, start + mode * 40)
    struct.pack_into('<I', data, 0xce5278, start + 320)
    struct.pack_into('<I', data, 0xce52c4, start + 360)
    struct.pack_into('<I', data, 0xce530c, start + 400)
    struct.pack_into('<I', data, 0x3fc170, branch(0x3fc170, start + 200, link=True))
    struct.pack_into('<I', data, 0x3fc214, 0xe3a03028)
    struct.pack_into('<I', data, 0x3fc270, branch(0x3fc270, start + 240))
    struct.pack_into('<I', data, 0x3a53ec, branch(0x3a53ec, start + 280, link=True))
    data.extend(code)
    struct.pack_into('<II', data, header + 16, size + len(code), size + len(code))
    path.write_bytes(data)
