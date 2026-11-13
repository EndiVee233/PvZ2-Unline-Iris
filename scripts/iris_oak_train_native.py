"""Register the aiming game after the existing Dark adapters, preserving chains."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_oak_train_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    ph = struct.unpack_from('<I', data, 28)[0]
    stride, count = struct.unpack_from('<HH', data, 42)
    headers = [h for h in range(ph, ph + stride * count, stride)
               if struct.unpack_from('<I', data, h)[0] == 1]
    rw, = [h for h in headers if struct.unpack_from('<I', data, h + 8)[0] == 0xf80000]
    if struct.unpack_from('<II', data, rw + 16) not in ((0, 4096), (0, 8192)):
        raise ValueError('Unexpected Dark writable metadata segment')
    struct.pack_into('<I', data, rw + 20, 8192)
    h, = [h for h in headers if struct.unpack_from('<I', data, h + 24)[0] == 5
          and sum(struct.unpack_from('<I', data, h + o)[0] for o in (4, 16)) == len(data)]
    _, off, va, _, size, mem, _, _ = struct.unpack_from('<8I', data, h)
    assert size == mem
    pad = -(va + size) % 4
    data.extend(bytes(pad)); size += pad
    start = va + size; tramp = start + 45 * 40; entry = tramp + 36
    hooks = [(0x619fc0, 0, 'IRIS_OAK_TRAIN_REGISTER'),
             (0x69ecd8, 36, 'IRIS_OAK_TRAIN_WINCON'),
             (0x187614, 37, 'IRIS_OAK_TRAIN_UPDATE')]
    def branch(pc, target, thumb=False):
        delta = target - pc - 8
        if delta % (2 if thumb else 4) or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('OakTrain branch out of range')
        return ((0xfa000000 | ((delta & 2) << 23)) if thumb else 0xea000000) | ((delta >> 2) & 0xffffff)
    targets = []
    for address, _, _ in hooks:
        old = struct.unpack_from('<I', data, address)[0]
        if old & 0xff000000 != 0xea000000:
            raise ValueError(f'OakTrain requires the existing hook chain: {address:x}')
        delta = (old & 0xffffff) << 2
        if delta & 0x2000000: delta -= 0x4000000
        targets.append(address + 8 + delta)
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-oak-train' + s) for s in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) }} }}')
    defines = {'IRIS_DARK_TRACE': int(trace), 'IRIS_OAK_TRAIN_STUB': start,
               'IRIS_OAK_TRAIN_DAMAGE': 0x5e0b74}
    for i, (_, _, name) in enumerate(hooks): defines[name] = tramp + i * 12
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti',
                    '-fno-math-errno', '-fno-jump-tables', '-fno-unwind-tables',
                    '-fno-asynchronous-unwind-tables', *[f'-D{k}={v}' for k, v in defines.items()],
                    '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(45):
        pc = start + len(code)
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch(pc + 20, entry, True),
                    0xe28dd010, 0xe8bd8010, 0xe320f000, (-(pc + 24)) & 0xffffffff))
    for i, ((address, mode, _), target) in enumerate(zip(hooks, targets)):
        code.extend(struct.pack('<3I', branch(tramp + i * 12, target), 0xe320f000, 0xe320f000))
        struct.pack_into('<I', data, address, branch(address, start + mode * 40))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if va + size + len(code) > 0xf7f000:
        raise ValueError('OakTrain overlaps writable state')
    data.extend(code)
    struct.pack_into('<II', data, h + 16, size + len(code), size + len(code))
    path.write_bytes(data)
