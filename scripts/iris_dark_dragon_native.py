"""Append Dark Dragon's private framework/controller after existing adapters."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_dark_dragon_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    ph = struct.unpack_from('<I', data, 28)[0]
    stride, count = struct.unpack_from('<HH', data, 42)
    heads = [h for h in range(ph, ph + stride * count, stride)
             if struct.unpack_from('<I', data, h)[0] == 1]
    rw, = [h for h in heads if struct.unpack_from('<I', data, h + 8)[0] == 0xf80000]
    if struct.unpack_from('<II', data, rw + 16) != (0, 8192):
        raise ValueError('Dark Dragon needs the existing Dark two-page state mapping')
    h, = [h for h in heads if struct.unpack_from('<I', data, h + 24)[0] == 5
          and sum(struct.unpack_from('<I', data, h + o)[0] for o in (4, 16)) == len(data)]
    _, _, va, _, size, mem, _, _ = struct.unpack_from('<8I', data, h)
    assert size == mem
    pad = -(va + size) % 4
    data.extend(bytes(pad)); size += pad
    start = va + size; tramp = start + 24 * 40; entry = tramp + 12
    hooks = [(0x619fc0, 0, 'REGISTER')]

    def branch(pc, target, thumb=False):
        d = target - pc - 8
        if d % (2 if thumb else 4) or not -0x2000000 <= d < 0x2000000:
            raise ValueError('Dark Dragon ARM branch out of range')
        return ((0xfa000000 | ((d & 2) << 23)) if thumb else 0xea000000) | ((d >> 2) & 0xffffff)

    targets = []
    for address, _, _ in hooks:
        old = struct.unpack_from('<I', data, address)[0]
        if old >> 24 != 0xea:
            raise ValueError(f'Dark Dragon expected previous hook chain at {address:x}')
        delta = (old & 0xffffff) << 2
        if delta & 0x2000000: delta -= 0x4000000
        targets.append(address + 8 + delta)
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, blob, linker = [out / ('iris-dragon' + s) for s in ('.o', '.bin', '.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) }} }}')
    defines = {'IRIS_DARK_TRACE': int(trace), 'IRIS_DRAGON_STUB': start}
    defines.update({'IRIS_DRAGON_' + name: tramp + 12 * i for i, (_, _, name) in enumerate(hooks)})
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb', '-Oz', '-fPIC',
                    '-ffreestanding', '-fno-exceptions', '-fno-rtti', '-fno-math-errno', '-fno-jump-tables',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    *[f'-D{k}={v}' for k, v in defines.items()], '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', blob, obj], check=True)
    code = bytearray()
    for mode in range(24):
        pc = start + len(code)
        code.extend(struct.pack('<10I', 0xe92d401f, 0xe1a0100d, 0xe3a02000 | mode,
                    0xe59f0010, 0xe08f0000, branch(pc + 20, entry, True),
                    0xe28dd010, 0xe8bd8010, 0xe320f000, (-(pc + 24)) & 0xffffffff))
    for i, ((address, mode, _), target) in enumerate(zip(hooks, targets)):
        code.extend(struct.pack('<3I', branch(tramp + 12 * i, target), 0xe320f000, 0xe320f000))
        struct.pack_into('<I', data, address, branch(address, start + mode * 40))
    code.extend(blob.read_bytes()); code.extend(bytes(-len(code) % 4))
    if va + size + len(code) > 0xf7f000:
        raise ValueError('Dark Dragon code overlaps writable metadata')
    data.extend(code)
    struct.pack_into('<II', data, h + 16, size + len(code), size + len(code))
    path.write_bytes(data)
