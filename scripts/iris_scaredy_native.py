"""Append the bounded Scaredy transition adapter to the Iris executable segment."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_scaredy_native(path, source, ndk, out, *, trace=False):
    data = bytearray(path.read_bytes())
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    for header in range(phoff, phoff + stride * count, stride):
        kind, offset, address, _, size, mem, flags, _ = struct.unpack_from('<8I', data, header)
        if kind == 1 and flags == 5 and size == mem and offset + size == len(data):
            break
    else:
        raise ValueError('Missing executable Iris patch segment')
    expected = {0x3fe9fc: 0xeb1cde76, 0x3fedd8: 0xe92d4830,
                0x3feaa0: 0xe3a03020, 0xce5508: 0x13f310,
                0x3ff0fc: 0xe92d48f0, 0xce7984: 0x489930}
    if any(struct.unpack_from('<I', data, pc)[0] != op for pc, op in expected.items()):
        raise ValueError('Unexpected native Scaredy-shroom framework')
    start = address + size
    entry = start + 0xf0
    tools = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, payload, linker = out / 'iris-scaredy.o', out / 'iris-scaredy.bin', out / 'iris-scaredy.ld'
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }')
    subprocess.run([tools / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    f'-DIRIS_DARK_TRACE={int(trace)}', '-c', source, '-o', obj], check=True)
    require_position_independent(obj)
    subprocess.run([tools / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', payload, obj], check=True)

    def branch(pc, target, *, link=False, thumb=False):
        delta = target - pc - 8
        if delta % (2 if thumb else 4) or not -0x2000000 <= delta < 0x2000000:
            raise ValueError('Scaredy adapter branch exceeds ARM range')
        if thumb:
            return 0xfa000000 | ((delta >> 2) & 0xffffff) | ((delta & 2) << 23)
        return (0xeb000000 if link else 0xea000000) | ((delta >> 2) & 0xffffff)

    # r0 is the allocation size at the first hook; r0 is the framework at the
    # second. Each stub supplies the mapped ELF base without relocations.
    stubs = bytearray()
    for index in range(2):
        pc = start + len(stubs)
        words = [0xe92d4010, 0xe1a01000, 0xe3a02000 | index,
                 0xe59f0010, 0xe08f0000,
                 branch(pc + 20, entry, thumb=True), 0xe8bd8010,
                 0xe320f000, 0xe320f000, (-(pc + 24)) & 0xffffffff]
        stubs.extend(struct.pack('<10I', *words))
    pc = start + len(stubs)
    damage = [0xe92d4007, 0xe1a0100d, 0xe3a02002,
              0xe59f0010, 0xe08f0000,
              branch(pc + 20, entry, thumb=True), 0xe8bd8007,
              0xe320f000, 0xe320f000, (-(pc + 24)) & 0xffffffff]
    stubs.extend(struct.pack('<10I', *damage))
    pc = start + len(stubs)
    food = [0xe92d4010, 0xe1a01000, 0xe3a02003,
            0xe59f0010, 0xe08f0000,
            branch(pc + 20, entry, thumb=True), 0xe8bd8010,
            0xe320f000, 0xe320f000, (-(pc + 24)) & 0xffffffff]
    stubs.extend(struct.pack('<10I', *food))
    pc = start + len(stubs)
    impact = [0xe92d4013, 0xe1a0100d, 0xe3a02004,
              0xe59f0010, 0xe08f0000,
              branch(pc + 20, entry, thumb=True), 0xe28dd008, 0xe8bd8010,
              0xe320f000, (-(pc + 24)) & 0xffffffff]
    stubs.extend(struct.pack('<10I', *impact))
    pc = start + len(stubs)
    begin_food = [0xe92d4010, 0xe1a01000, 0xe3a02005,
                  0xe59f0010, 0xe08f0000,
                  branch(pc + 20, entry, thumb=True), 0xe8bd8010,
                  0xe320f000, 0xe320f000, (-(pc + 24)) & 0xffffffff]
    stubs.extend(struct.pack('<10I', *begin_food))
    code = bytes(stubs) + payload.read_bytes()
    if not payload.read_bytes() or size % 4 or size + len(code) > 0x10000:
        raise ValueError('Unexpected Scaredy adapter size')
    struct.pack_into('<I', data, 0x3fe9fc, branch(0x3fe9fc, start, link=True))
    struct.pack_into('<I', data, 0x3fedd8, branch(0x3fedd8, start + 40))
    struct.pack_into('<I', data, 0x3feaa0, 0xe3a03028)
    # This vtable word already has an R_ARM_RELATIVE relocation. The loader
    # adds the mapped ELF base to the new ARM stub just as for the old method.
    struct.pack_into('<I', data, 0xce5508, start + 80)
    struct.pack_into('<I', data, 0x3ff0fc, branch(0x3ff0fc, start + 120))
    struct.pack_into('<I', data, 0xce7984, start + 160)
    if struct.unpack_from('<I', data, 0xce54ec)[0] != 0x3fecc8:
        raise ValueError('Unexpected Scaredy-shroom PF start')
    struct.pack_into('<I', data, 0xce54ec, start + 200)
    data.extend(code)
    struct.pack_into('<II', data, header + 16, size + len(code), mem + len(code))
    path.write_bytes(data)
