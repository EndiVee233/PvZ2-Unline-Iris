"""Recover from the old engine's single-page glyph-atlas exhaustion."""
import struct
import subprocess


def patch_font_cache(path, source, ndk, out):
    data = bytearray(path.read_bytes())
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    for header in range(phoff, phoff + stride * count, stride):
        kind, offset, address, _, size, mem, flags, _ = struct.unpack_from('<8I', data, header)
        if kind == 1 and flags == 5 and size == mem and offset + size == len(data):
            break
    else:
        raise ValueError('Missing executable patch segment')
    expected = {0xA301C8: 0xEB000050, 0xA30684: 0xEEF0DA4A}
    if any(struct.unpack_from('<I', data, pc)[0] != opcode for pc, opcode in expected.items()):
        raise ValueError('Unexpected PrimeGlyphMesh layout')
    start = address + size
    toolchain = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, payload = out / 'iris-font-cache.o', out / 'iris-font-cache.bin'
    subprocess.run([toolchain / 'clang.exe', '--target=armv7a-linux-androideabi21',
                    '-c', source, '-o', obj], check=True)
    symbols = {'iris_build_glyph_part': 0xA30310, 'iris_get_font_manager': 0xA311FC,
               'iris_clear_glyph_cache': 0xA31E78, 'iris_log_write': 0xE89C4}
    subprocess.run([toolchain / 'ld.lld.exe', f'-Ttext={start:#x}', '--oformat=binary',
                    *(f'--defsym={name}={value:#x}' for name, value in symbols.items()),
                    '-o', payload, obj], check=True)
    code = payload.read_bytes()
    if size % 4 or size + len(code) > 8192:
        raise ValueError('Glyph cache patch exceeds reserved executable pages')

    def branch(pc, target, link=False):
        delta = target - pc - 8
        assert delta % 4 == 0 and -0x2000000 <= delta < 0x2000000
        return (0xEB000000 if link else 0xEA000000) | (delta // 4 & 0xFFFFFF)

    struct.pack_into('<I', data, 0xA301C8, branch(0xA301C8, start, True))
    # BuildPart logs allocation failure but used to continue with uninitialized
    # glyph/image pointers. Return false via its existing failure epilogue.
    struct.pack_into('<I', data, 0xA30684, branch(0xA30684, 0xA30930))
    data.extend(code)
    struct.pack_into('<II', data, header + 16, size + len(code), mem + len(code))
    path.write_bytes(data)
