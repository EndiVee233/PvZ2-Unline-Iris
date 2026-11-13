"""Register the port's own serializable PlantFramework subclass in Iris."""
import struct
import subprocess
from native_payload import require_position_independent


STATE_VA = 0xf80000


def patch_dark_framework(path, source, ndk, out, *, trace=False, smoke=False):
    data = bytearray(path.read_bytes())
    if struct.unpack_from('<2I', data, 0x3b9478) != (0xe92d48f0, 0xe24dd020):
        raise ValueError('Unexpected PlantFramework registration prologue')
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    stack_header = None
    for h in range(phoff, phoff + stride * count, stride):
        kind, offset, address, _, size, mem, flags, _ = struct.unpack_from('<8I', data, h)
        if kind == 0x6474e551:
            stack_header = h
        if kind == 1 and flags == 5 and size == mem and offset + size == len(data):
            header, segment_offset, segment_va, segment_size = h, offset, address, size
    if stack_header is None:
        raise ValueError('Missing reusable GNU_STACK header')
    # Android already uses a non-executable stack by default. Reuse this
    # advisory header for a separate zero-filled RW page, keeping code RX.
    # The page holds relocated runtime pointers, never save or game state.
    struct.pack_into('<8I', data, stack_header, 1, 0, STATE_VA, STATE_VA, 0, 8192, 6, 4096)
    pad = -(segment_va + segment_size) % 4
    data.extend(bytes(pad)); segment_size += pad
    start = segment_va + segment_size
    trampoline, entry = start + 560, start + 572
    def branch(pc, target, *, thumb=False):
        delta = target - pc - 8
        if delta % (2 if thumb else 4) or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Dark framework ARM branch out of range')
        return ((0xfa000000 | ((delta & 2) << 23)) if thumb else 0xea000000) | ((delta >> 2) & 0xffffff)
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-dark-framework' + e) for e in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
    fume_slots = (0xce45bc, 0xce460c, 0xce45e4, 0xce4610, 0xce45e0)
    defines = [f'-DIRIS_FUME_{i}={struct.unpack_from("<I", data, p)[0]}' for i, p in enumerate(fume_slots)]
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-fno-math-errno',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    f'-DIRIS_DARK_TRACE={int(trace)}', f'-DIRIS_DARK_STATE={STATE_VA}',
                    f'-DIRIS_DARK_SMOKE_TEST={int(smoke)}',
                    f'-DIRIS_DARK_STUB={start}', f'-DIRIS_DARK_REGISTER_ORIGINAL={trampoline}',
                    *defines, '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(14):
        pc = start + len(code)
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch(pc + 20, entry, thumb=True),
                    0xe28dd010, 0xe8bd8010, 0xe320f000, (-(pc + 24)) & 0xffffffff))
    code.extend(data[0x3b9478:0x3b9480])
    code.extend(struct.pack('<I', branch(trampoline + 8, 0x3b9480)))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if segment_size + len(code) > 0x10000:
        raise ValueError('Native patch segment capacity exceeded')
    struct.pack_into('<I', data, 0x3b9478, branch(0x3b9478, start))
    if struct.unpack_from('<I', data, 0xcf2a5c)[0] != 0x64c468:
        raise ValueError('Unexpected ZombieParticle update slot')
    struct.pack_into('<I', data, 0xcf2a5c, start + 12 * 40)
    data.extend(code)
    struct.pack_into('<II', data, header + 16, segment_size + len(code), segment_size + len(code))
    path.write_bytes(data)
