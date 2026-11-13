"""Attach scoped Fume-shroom combat to Iris's dormant line-attacker framework."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_fumeshroom_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    slots = {0xce45bc: 0x3e997c, 0xce460c: 0x3e9200,
             0xce45e4: 0x3e9354, 0xce4610: 0x3e991c, 0xce45e0: 0x3e917c}
    expected = slots | {0x3e8ca8: 0xe3a0001c, 0x3e8d4c: 0xe3a0301c}
    if any(struct.unpack_from('<I', data, p)[0] != v for p, v in expected.items()):
        raise ValueError('Unexpected line-attacker framework methods')
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    for header in range(phoff, phoff + stride * count, stride):
        kind, offset, address, _, size, mem, flags, _ = struct.unpack_from('<8I', data, header)
        if kind == 1 and flags == 5 and size == mem and offset + size == len(data):
            break
    else:
        raise ValueError('Missing Iris patch segment')
    pad = -(address + size) % 4
    data.extend(bytes(pad)); size += pad
    start, entry = address + size, address + size + 200
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-fumeshroom' + e) for e in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    f'-DIRIS_DARK_TRACE={int(trace)}', '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(5):
        pc = start + len(code)
        delta = entry - pc - 28
        if delta % 2 or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Fume-shroom stub out of range')
        branch = 0xfa000000 | ((delta & 2) << 23) | ((delta >> 2) & 0xffffff)
        # Preserve the original framework and action arguments on the stack.
        # r0 carries the return value; r4 and the stack remain AAPCS aligned.
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch, 0xe28dd010,
                    0xe8bd8010, 0xe320f000, (-(pc + 24)) & 0xffffffff))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if size + len(code) > 0x10000:
        raise ValueError('Native patch segment capacity exceeded')
    for i, p in enumerate(slots): struct.pack_into('<I', data, p, start + i * 40)
    struct.pack_into('<I', data, 0x3e8ca8, 0xe3a00024)
    struct.pack_into('<I', data, 0x3e8d4c, 0xe3a03024)
    data.extend(code)
    struct.pack_into('<II', data, header + 16, size + len(code), size + len(code))
    path.write_bytes(data)
