"""Append owned hypno framework/controller and preserve all preceding hooks."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_hypno_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    hooks = [(0x282388, 0, 'IRIS_HYPNO_REGISTER'),
             (0x3b9478, 15, 'IRIS_HYPNO_REGISTER_PLANT'),
             (0x5e0b74, 12, 'IRIS_HYPNO_DAMAGE'),
             (0x187614, 13, 'IRIS_HYPNO_UPDATE')]
    for address, _, _ in hooks:
        if struct.unpack_from('<I', data, address)[0] & 0xff000000 != 0xea000000:
            raise ValueError(f'Hypno requires existing registration/damage/update chain: {address:x}')
    expected = struct.unpack_from('<2I', data, 0x69ecd8)
    if expected != (0xe92d4010, 0xe59f007c):
        raise ValueError(f'Unexpected ZombiesDeadWinCon prologue {expected}')
    if struct.unpack_from('<2I', data, 0x179384) != (0xe92d48f0, 0xe24dd020):
        raise ValueError('Unexpected alive-zombie count prologue')
    ph = struct.unpack_from('<I', data, 28)[0]
    stride, count = struct.unpack_from('<HH', data, 42)
    h, = [h for h in range(ph, ph + stride * count, stride)
          if struct.unpack_from('<I', data, h)[0] == 1
          and struct.unpack_from('<I', data, h + 24)[0] == 5
          and sum(struct.unpack_from('<I', data, h + o)[0] for o in (4, 16)) == len(data)]
    _, off, va, _, size, mem, _, _ = struct.unpack_from('<8I', data, h)
    assert size == mem
    pad = -(va + size) % 4; data.extend(bytes(pad)); size += pad
    start = va + size; tramp = start + 30 * 40; entry = tramp + 80
    def branch(pc, target, thumb=False):
        delta = target - pc - 8
        if delta % (2 if thumb else 4) or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Hypno branch out of range')
        return ((0xfa000000 | ((delta & 2) << 23)) if thumb else 0xea000000) | ((delta >> 2) & 0xffffff)
    defines = {'IRIS_DARK_TRACE': int(trace), 'IRIS_HYPNO_STUB': start,
               'IRIS_HYPNO_WINCON': tramp + 48, 'IRIS_HYPNO_COUNT': tramp + 68}
    for i, (_, _, define) in enumerate(hooks): defines[define] = tramp + 12 * i
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-hypno' + s) for s in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) }} }}')
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb', '-Oz', '-fPIC',
                    '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-fno-math-errno', '-fno-jump-tables',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    *[f'-D{k}={v}' for k, v in defines.items()], '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(30):
        pc = start + len(code)
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch(pc + 20, entry, True),
                    0xe28dd010, 0xe8bd8010, 0xe320f000, (-(pc + 24)) & 0xffffffff))
    for i, (address, mode, _) in enumerate(hooks):
        old = struct.unpack_from('<I', data, address)[0]; delta = (old & 0xffffff) << 2
        if delta & 0x2000000: delta -= 0x4000000
        code.extend(struct.pack('<3I', branch(tramp + 12 * i, address + 8 + delta), 0xe320f000, 0xe320f000))
        struct.pack_into('<I', data, address, branch(address, start + mode * 40))
    # This second instruction is PC-relative: relocate its literal instead of
    # copying a load that would read bytes from the appended payload.
    literal = struct.unpack_from('<I', data, 0x69ed60)[0]
    code.extend(struct.pack('<5I', 0xe92d4010, 0xe59f0004,
                            branch(tramp + 56, 0x69ece0), 0xe320f000, literal))
    code.extend(data[0x179384:0x17938c])
    code.extend(struct.pack('<I', branch(tramp + 76, 0x17938c)))
    struct.pack_into('<I', data, 0x69ecd8, branch(0x69ecd8, start + 11 * 40))
    struct.pack_into('<I', data, 0x179384, branch(0x179384, start + 26 * 40))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if va + size + len(code) > 0xf7f000: raise ValueError('Hypno overlaps writable state')
    data.extend(code); struct.pack_into('<II', data, h + 16, size + len(code), size + len(code))
    path.write_bytes(data)
