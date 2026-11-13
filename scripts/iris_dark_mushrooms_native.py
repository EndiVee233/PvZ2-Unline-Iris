"""Attach the Sun-shroom growth/PF adapter to Iris's appended native code."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_mushrooms_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    for header in range(phoff, phoff + stride * count, stride):
        kind, offset, address, _, size, mem, flags, _ = struct.unpack_from('<8I', data, header)
        if kind == 1 and flags == 5 and size == mem and offset + size == len(data):
            break
    else:
        raise ValueError('Missing executable Iris patch segment')
    if (struct.unpack_from('<II', data, 0x410054) != (0xe92d4bf0, 0xe24dd040)
            or struct.unpack_from('<I', data, 0xce5f10)[0] != 0x4103b0):
        raise ValueError('Unexpected Sun-shroom native methods')
    puff_expected = {0x3fa1e8: 0xe3a00024, 0x3fa290: 0xe3a03024,
                     0xce5074: 0x3fa5ac, 0xce50ec: 0x3fa644, 0xce50c0: 0x3fa754}
    if any(struct.unpack_from('<I', data, at)[0] != value for at, value in puff_expected.items()):
        raise ValueError('Unexpected Puff-shroom framework layout')
    # Prior Thumb payloads may end in an unaligned string literal.
    padding = -(address + size) % 4
    data.extend(bytes(padding))
    size += padding
    start = address + size
    trampoline = start + 240
    entry = start + 252
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, payload, linker = [out / ('iris-mushrooms' + ext) for ext in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-fno-math-errno',
                    f'-DIRIS_DARK_TRACE={int(trace)}',
                    f'-DIRIS_SUNSPAWN_ORIGINAL={trampoline}', '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', payload, obj], check=True)

    def branch(pc, target, thumb=False):
        delta = target - pc - 8
        if delta % (2 if thumb else 4) or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Mushroom adapter exceeds ARM branch range')
        return ((0xfa000000 | ((delta & 2) << 23)) if thumb else 0xea000000) | ((delta >> 2) & 0xffffff)

    code = bytearray()
    for mode in range(6):
        pc = start + len(code)
        # Preserve both arguments to the shared sunflower spawn callback.
        # r0 is replaced by the mapped library base, r1 by their stack block.
        words = [0xe92d4013, 0xe1a0100d if mode == 0 else 0xe1a01000,
                 0xe3a02000 | mode, 0xe59f0010, 0xe08f0000,
                 branch(pc + 20, entry, True), 0xe8bd8013,
                 0xe320f000, 0xe320f000, (-(pc + 24)) & 0xffffffff]
        code.extend(struct.pack('<10I', *words))
    code.extend(data[0x410054:0x41005c])
    code.extend(struct.pack('<I', branch(trampoline + 8, 0x41005c)))
    code.extend(payload.read_bytes())
    code.extend(bytes(-len(code) % 4))
    if size % 4 or not payload.stat().st_size or size + len(code) > 0x10000:
        raise ValueError('Unexpected mushroom adapter size')
    struct.pack_into('<I', data, 0x410054, branch(0x410054, start))
    # Existing R_ARM_RELATIVE relocation supplies the load address.
    struct.pack_into('<I', data, 0xce5f10, start + 40)
    if struct.unpack_from('<I', data, 0xce5f0c)[0] != 0x410324:
        raise ValueError('Unexpected Sun-shroom plant-food start')
    struct.pack_into('<I', data, 0xce5f0c, start + 200)
    # Fully grown Sun-shroom uses PlantSunflower rather than PlantSunshroom.
    if (struct.unpack_from('<I', data, 0xce5e0c)[0] != 0x410324
            or struct.unpack_from('<I', data, 0xce5e10)[0] != 0x4103b0):
        raise ValueError('Unexpected mature Sun-shroom inherited callbacks')
    struct.pack_into('<I', data, 0xce5e0c, start + 200)
    struct.pack_into('<I', data, 0xce5e10, start + 40)
    struct.pack_into('<I', data, 0xce5074, start + 80)
    struct.pack_into('<I', data, 0xce50ec, start + 120)
    struct.pack_into('<I', data, 0xce50c0, start + 160)
    struct.pack_into('<I', data, 0x3fa1e8, 0xe3a00030)
    struct.pack_into('<I', data, 0x3fa290, 0xe3a03030)
    data.extend(code)
    struct.pack_into('<II', data, header + 16, size + len(code), size + len(code))
    path.write_bytes(data)
