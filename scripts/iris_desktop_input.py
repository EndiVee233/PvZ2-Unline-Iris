"""Route desktop-only events through Iris's existing touch queue."""
import struct
import subprocess


HOOK = 0x9F0310
CAVE = 0xCCAB14
CAVE_LIMIT = 0xCCAF90


def patch_native(path, source, ndk, out):
    """Link a position-independent event handler into unused RX alignment space."""
    bin_dir = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj = out / 'iris-input.o'
    linker = out / 'iris-input.ld'
    payload = out / 'iris-input.bin'
    linker.write_text('SECTIONS { . = 0xCCAB64; .text : { *(.text.entry) *(.text*) *(.rodata*) } '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }', encoding='ascii')
    subprocess.run([bin_dir / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-c', source, '-o', obj], check=True)
    subprocess.run([bin_dir / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', payload, obj], check=True)

    data = bytearray(path.read_bytes())
    # Preserve the original phase 0..4 jump table and out-of-range return.
    def branch(origin, target, link=False, condition=14):
        displacement = target - origin - 8
        assert displacement % 4 == 0 and -0x2000000 <= displacement < 0x2000000
        return (condition << 28) | (0x0B000000 if link else 0x0A000000) | (displacement // 4 & 0xFFFFFF)

    entry = CAVE + 0x50
    stub = [
        branch(CAVE, HOOK + 4, condition=9),  # bls original switch
        0xE3530005,                         # cmp r3, #5
        0x13530006,                         # cmpne r3, #6
        branch(CAVE + 12, 0x9F036C, condition=1),
        0xE1A01000,                         # mov r1, r0 (driver)
        0xE1A0200D,                         # mov r2, sp (deserialized touch)
        0xE24F0008,                         # adr r0, this instruction
        0xE59FC008,                         # ldr ip, base-offset literal
        0xE040000C,                         # sub r0, r0, ip (ELF base)
        0xFA000000 | ((entry - (CAVE + 36) - 8) // 4 & 0xFFFFFF),  # blx Thumb handler
        branch(CAVE + 40, 0x9F036C),
        CAVE + 24,
    ]
    code = payload.read_bytes()
    end = entry + len(code)
    if (end > CAVE_LIMIT or any(data[CAVE:end]) or
            struct.unpack_from('<I', data, HOOK)[0] != 0x8A000015 or
            struct.unpack_from('<II', data, 0x84)[0] != CAVE or
            struct.unpack_from('<II', data, 0x84)[1] != CAVE):
        raise ValueError('Unexpected Iris native layout or input handler is too large')
    struct.pack_into('<II', data, 0x84, end, end)
    struct.pack_into('<I', data, HOOK, branch(HOOK, CAVE))
    struct.pack_into(f'<{len(stub)}I', data, CAVE, *stub)
    data[entry:end] = code
    path.write_bytes(data)
