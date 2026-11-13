"""Install WarMist's own LevelModule classes without borrowing class layouts."""
import struct
import subprocess
from native_payload import require_position_independent


HOOK = 0x2d8160
STUBS = 14


def patch_mist_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    expected = (0xe92d48f0, 0xe24dd020)
    if struct.unpack_from('<2I', data, HOOK) != expected:
        raise ValueError('Unexpected LevelModule registration prologue')
    if struct.unpack_from('<2I', data, 0x3d2654) != (0xe92d4ff0, 0xed2d8b04):
        raise ValueError('Unexpected Blover action prologue')
    if struct.unpack_from('<I', data, 0x1891ec)[0] != 0xeb0ebb11:
        raise ValueError('Unexpected board render-item collector call')
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    segments = [q for q in range(phoff, phoff + stride * count, stride)
                if struct.unpack_from('<I', data, q)[0] == 1]
    if not any(struct.unpack_from('<I', data, q + 8)[0] == 0xf80000 for q in segments):
        raise ValueError('Dark framework RW state must be installed first')
    q, = [q for q in segments if struct.unpack_from('<I', data, q + 24)[0] == 5
           and sum(struct.unpack_from('<I', data, q + o)[0] for o in (4, 16)) == len(data)]
    _, off, va, _, size, mem, _, _ = struct.unpack_from('<8I', data, q)
    assert size == mem
    pad = -(va + size) % 4
    data.extend(bytes(pad)); size += pad
    start = va + size
    trampoline = start + STUBS * 40
    entry = trampoline + 24

    def branch(pc, target, thumb=False):
        delta = target - pc - 8
        if delta % (2 if thumb else 4) or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Mist ARM branch out of range')
        return ((0xfa000000 | ((delta & 2) << 23)) if thumb else 0xea000000) | ((delta >> 2) & 0xffffff)

    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-mist' + e) for e in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-fno-math-errno', '-fno-jump-tables',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    f'-DIRIS_DARK_TRACE={int(trace)}', f'-DIRIS_MIST_STUB={start}',
                    f'-DIRIS_MIST_REGISTER_ORIGINAL={trampoline}', '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(STUBS):
        pc = start + len(code)
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch(pc + 20, entry, True),
                    0xe28dd010, 0xe8bd8010, 0xe320f000, (-(pc + 24)) & 0xffffffff))
    code.extend(data[HOOK:HOOK + 8])
    code.extend(struct.pack('<I', branch(trampoline + 8, HOOK + 8)))
    code.extend(data[0x3d2654:0x3d265c])
    code.extend(struct.pack('<I', branch(trampoline + 20, 0x3d265c)))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if size + len(code) > 0x10000:
        raise ValueError('Native patch segment capacity exceeded')
    struct.pack_into('<I', data, HOOK, branch(HOOK, start))
    struct.pack_into('<I', data, 0x3d2654, branch(0x3d2654, start + 11 * 40))
    struct.pack_into('<I', data, 0x1891ec, branch(0x1891ec, start + 13 * 40) | 0x01000000)
    data.extend(code)
    struct.pack_into('<II', data, q + 16, size + len(code), size + len(code))
    path.write_bytes(data)
