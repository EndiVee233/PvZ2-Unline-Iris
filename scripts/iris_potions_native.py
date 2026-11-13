"""Register potion grids and preserve native condition/damage fallback paths."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_potions_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    if struct.unpack_from('<I', data, 0x282388)[0] & 0xff000000 != 0xea000000:
        raise ValueError('Potions require the ground registration chain')
    hooks = [(0x5e0b74, 16, (0xe92d4ff0, 0xe24dd09c)),
             (0x62c1e8, 17, (0xe5d01010, 0xe3510000)),
             (0x62c2c4, 18, (0xe5d01010, 0xe3510000)),
             (0x187614, 26, (0xe92d4ff0, 0xe24dd05c))]
    for address, _, expected in hooks:
        if struct.unpack_from('<2I', data, address) != expected:
            raise ValueError(f'Unexpected potion hook prologue at {address:x}')
    ph = struct.unpack_from('<I', data, 28)[0]
    stride, count = struct.unpack_from('<HH', data, 42)
    h, = [h for h in range(ph, ph + stride * count, stride)
          if struct.unpack_from('<I', data, h)[0] == 1
          and struct.unpack_from('<I', data, h + 24)[0] == 5
          and sum(struct.unpack_from('<I', data, h + o)[0] for o in (4, 16)) == len(data)]
    _, off, va, _, size, mem, _, _ = struct.unpack_from('<8I', data, h)
    assert size == mem
    pad = -(va + size) % 4
    data.extend(bytes(pad)); size += pad
    start = va + size
    tramp = start + 33 * 40
    entry = tramp + 60

    def branch(pc, target, thumb=False):
        delta = target - pc - 8
        if delta % (2 if thumb else 4) or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Potion branch out of range')
        return ((0xfa000000 | ((delta & 2) << 23)) if thumb else 0xea000000) | ((delta >> 2) & 0xffffff)

    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-potions' + s) for s in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) }} }}')
    defines = {'IRIS_DARK_TRACE': int(trace), 'IRIS_POTION_STUB': start,
               'IRIS_POTION_REGISTER': tramp, 'IRIS_POTION_ZOMBIE_DAMAGE': tramp + 12,
               'IRIS_POTION_SPEED': tramp + 24, 'IRIS_POTION_ANIM_SPEED': tramp + 36,
               'IRIS_POTION_BOARD_UPDATE': tramp + 48}
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti',
                    '-fno-math-errno', '-fno-jump-tables', '-fno-unwind-tables',
                    '-fno-asynchronous-unwind-tables', *[f'-D{k}={v}' for k, v in defines.items()],
                    '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(33):
        pc = start + len(code)
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch(pc + 20, entry, True),
                    0xe28dd010, 0xe8bd8010, 0xe320f000, (-(pc + 24)) & 0xffffffff))
    old = struct.unpack_from('<I', data, 0x282388)[0]
    delta = (old & 0xffffff) << 2
    if delta & 0x2000000: delta -= 0x4000000
    code.extend(struct.pack('<3I', branch(tramp, 0x282390 + delta), 0xe320f000, 0xe320f000))
    struct.pack_into('<I', data, 0x282388, branch(0x282388, start))
    for i, (address, mode, _) in enumerate(hooks, 1):
        code.extend(data[address:address + 8])
        code.extend(struct.pack('<I', branch(tramp + i * 12 + 8, address + 8)))
        struct.pack_into('<I', data, address, branch(address, start + mode * 40))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if va + size + len(code) > 0xf7f000:
        raise ValueError('Potion payload would overlap writable state')
    data.extend(code)
    struct.pack_into('<II', data, h + 16, size + len(code), size + len(code))
    path.write_bytes(data)
