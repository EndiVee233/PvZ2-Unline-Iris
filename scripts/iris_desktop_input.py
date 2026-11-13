"""Route desktop-only events through Iris's existing touch queue."""
import struct
import subprocess


HOOK = 0x9F0310
BOARD_CLEAR = 0x2B8D08
DRAW_HOOK = 0x18A4C4
SPRITE_HOOK = 0x18A648
SPEED_DRAW_HOOK = 0x383070
COIN_DRAW_HOOK = 0x1CCBA0
COIN_DRAW_EXIT = 0x1CCE3C
POWERUP_SELECT_HOOK = 0x45EA7C
POWERUP_ACTIVATE = 0x167220
TRIP_FORMAT = 0x18CE64
CHOOSER_HEADING = 0x4B6224
CHOOSER_PACKET_COPY = 0x4C51AC
CHOOSER_COINS_FORMAT = 0x1CCF9C
PRIME_FONT_INIT = 0xA31500
# Each entry describes the descriptor constructor, font creation, and name-only font read.
DISPLAY_NAME_FONTS = (
    ((0x47B068, 0xEB16D924), (0x47B0A8, 0xEB16D943), (0x30FB40, 0xE5901000)),  # main menu
    ((0x47BD48, 0xEB16D5EC), (0x47BD80, 0xEB16D60D), (0x30D810, 0xE5904000)),  # player list
)
PROFILE_NAME_FONT_READ = 0x33A498
PROFILE_NAME_FONT_OFFSET = 0x33A544
# Three profile modes create and attach the same Facebook widget.
PROFILE_FACEBOOK = {
    0x309B08: (0xE3A000B0, 0xE30046A8),  # preserve r4 = UI scale member offset
    0x30A028: (0xEB20B0EB, 0xE30096A8),  # preserve sb = UI scale member offset
    0x30A26C: (0xEB20B05A, 0xE30096A8),
}
PROFILE_FACEBOOK_SKIPS = {
    0x309B0C: (0xEB20B232, 0x309BBC),
    0x30A02C: (0xE1A05000, 0x30A0DC),
    0x30A208: (0xE59B00A8, 0x30A56C),  # skip enabling the omitted widget
    0x30A270: (0xE1A05000, 0x30A324),
}
TYPEFACE_CALLS = {
    TRIP_FORMAT: 0xEB14748A,
    CHOOSER_HEADING: 0xEB07D384,
    CHOOSER_PACKET_COPY: 0xEB1ACB1D,
    CHOOSER_COINS_FORMAT: 0xEB176A5E,
}
# CoinBank reads m_showPlusButton in Draw, HitTest, and the touch handler.
COIN_PLUS_READS = {0x1CCD50: 0xE5D900F8, 0x1CD4FC: 0xE5D600F8, 0x1CDC48: 0xE5D400F8}
# Board's background and focus-loss listeners both call the pause-menu handler.
AUTO_PAUSE_CALLS = {0x1757F4: 0xEBFFFF7E, 0x176DF0: 0xEBFFF9FF}
ARM_NOP = 0xE320F000
SPEED_STATE = 0xDF9700
TIME_CONFIG = 0xD4ED90
COIN_SELECTION_PENDING = SPEED_STATE + 0x88
DISPLAY_NAME_FONT_STATE = SPEED_STATE + 0x90
STATE_SIZE = 160
PAYLOAD_VADDR = 0xDFA000
RESET_OFFSET = 0x50
DRAW_OFFSET = 0xC4
SPRITE_OFFSET = 0x100
SPEED_DRAW_OFFSET = 0x140
COIN_DRAW_OFFSET = 0x180
POWERUP_SELECT_OFFSET = 0x1C0
TYPEFACE_OFFSET = 0x200
FONT_SIZE_OFFSET = 0x2C0
DISPLAY_NAME_FONT_OFFSET = 0x2E0
ENTRY_OFFSET = 0x3A0
PAGE_SIZE = 0x1000


def patch_native(path, source, ndk, out, *, custom_typefaces=False, dark_minigames=False):
    """Append a read-execute segment without granting execution to game data."""
    bin_dir = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj = out / 'iris-input.o'
    linker = out / 'iris-input.ld'
    payload = out / 'iris-input.bin'
    entry = PAYLOAD_VADDR + ENTRY_OFFSET
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} '
                      '/DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) } }', encoding='ascii')
    subprocess.run([bin_dir / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-mthumb',
                    '-Oz', '-fPIC', '-ffreestanding', '-fno-exceptions', '-fno-rtti',
                    '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                    f'-DIRIS_DARK_INPUT={int(dark_minigames)}', '-c', source, '-o', obj], check=True)
    subprocess.run([bin_dir / 'ld.lld.exe', '-T', linker, '--oformat=binary', '-o', payload, obj], check=True)

    data = bytearray(path.read_bytes())
    program_offset = 0x34
    header_format = '<8I'
    header_size = struct.calcsize(header_format)
    headers = [struct.unpack_from(header_format, data, program_offset + i * header_size) for i in range(8)]
    if (data[:6] != b'\x7fELF\x01\x01'
            or struct.unpack_from('<I', data, 0x1C)[0] != program_offset
            or struct.unpack_from('<HH', data, 0x2A) != (header_size, len(headers))
            or [header[0] for header in headers] != [6, 3, 1, 1, 2, 0x6474E551, 0x70000001, 0x6474E552]
            or headers[3][2] + headers[3][5] != SPEED_STATE
            or SPEED_STATE + STATE_SIZE > PAYLOAD_VADDR
            or struct.unpack_from('<I', data, HOOK)[0] != 0x8A000015
            or struct.unpack_from('<I', data, BOARD_CLEAR)[0] != 0xE58B06C0
            or struct.unpack_from('<I', data, DRAW_HOOK)[0] != 0xE28DD00C
            or struct.unpack_from('<I', data, SPRITE_HOOK)[0] != 0xE59D0008
            or struct.unpack_from('<I', data, SPEED_DRAW_HOOK)[0] != 0xEB113E32
            or struct.unpack_from('<I', data, COIN_DRAW_HOOK)[0] != 0xEB18171A
            or struct.unpack_from('<I', data, POWERUP_SELECT_HOOK)[0] != 0xEBF421E7
            or struct.unpack_from('<I', data, PRIME_FONT_INIT)[0] != 0xE92D48F0
            or any(struct.unpack_from('<I', data, addr)[0] != opcode
                   for hooks in DISPLAY_NAME_FONTS for addr, opcode in hooks)
            or struct.unpack_from('<I', data, PROFILE_NAME_FONT_READ)[0] != 0xE7900006
            or struct.unpack_from('<I', data, PROFILE_NAME_FONT_OFFSET)[0] != 0xFFFFF16C
            or any(struct.unpack_from('<I', data, addr)[0] != original
                   for addr, (original, _) in (PROFILE_FACEBOOK | PROFILE_FACEBOOK_SKIPS).items())
            or any(struct.unpack_from('<I', data, addr)[0] != opcode for addr, opcode in TYPEFACE_CALLS.items())
            or any(struct.unpack_from('<I', data, addr)[0] != opcode for addr, opcode in AUTO_PAUSE_CALLS.items())
            or any(struct.unpack_from('<I', data, addr)[0] != opcode for addr, opcode in COIN_PLUS_READS.items())):
        raise ValueError('Unexpected Iris ELF or input hook layout')
    # Preserve the original phase 0..4 jump table and out-of-range return.
    def branch(origin, target, link=False, condition=14):
        displacement = target - origin - 8
        assert displacement % 4 == 0 and -0x2000000 <= displacement < 0x2000000
        return (condition << 28) | (0x0B000000 if link else 0x0A000000) | (displacement // 4 & 0xFFFFFF)

    base = PAYLOAD_VADDR
    stub = [
        0xE3530006,                         # cmp r3, #6
        branch(base + 4, 0x9F036C, condition=8),
        0xE92D0009,                         # save driver and original phase
        0xE1A01000,                         # mov r1, r0 (driver)
        0xE28D2008,                         # r2 = deserialized touch above saved registers
        0xE3530004,                         # cmp r3, #4
        0x92833010,                         # addls r3, r3, #16 (ordinary touch)
        0xE24F0008,                         # adr r0, this instruction
        0xE59FC01C,                         # ldr ip, base-offset literal
        0xE040000C,                         # sub r0, r0, ip (ELF base)
        0xFA000000 | ((entry - (base + 40) - 8) // 4 & 0xFFFFFF),  # blx Thumb handler
        0xE1A0C000,                         # ip = handled
        0xE8BD0009,
        0xE35C0000,                         # cmp ip, #0
        0x03530004,                         # cmpeq r3, #4
        branch(base + 60, HOOK + 4, condition=9),
        branch(base + 64, 0x9F036C),
        base + 28,
    ]
    code = payload.read_bytes()
    stub_bytes = struct.pack(f'<{len(stub)}I', *stub)
    reset = base + RESET_OFFSET
    restore_speed = [
        0xE58B06C0,  # original: clear app->board
        0xE92D000F,  # push r0-r3
        0xE59F005C,  # load speed state displacement
        0xE08F0000,  # r0 = &speed state
        0xE3A02000,
        0xE580200C,  # clear the remembered pending cursor
        0xE5802014,  # clear the speed button's remembered board
        0xE5802030,  # clear pointer tracking
        0xE5802064,  # clear the pending pinch click
        0xE5802074,  # clear pending speed feedback
        0xE5802078,  # clear the tracked coin widget
        0xE5802088,  # clear pending power-up selection
        0xE5901004,  # load active
        0xE3510000,
        branch(reset + 56, reset + 100, condition=0),
        0xE3A01000,
        0xE5801004,  # clear active
        0xE59F1024,  # load time config displacement from speed state
        0xE7901001,  # load time config object
        0xE3510000,
        branch(reset + 80, reset + 100, condition=0),
        0xE5912028,  # read the current scale
        0xE3520101,  # cmp r2, #0x40000000 (2.0f)
        0x05903000,  # load previous scale if Iris still owns the override
        0x05813028,
        0xE8BD000F,
        branch(reset + 104, BOARD_CLEAR + 4),
        (SPEED_STATE - (reset + 20)) & 0xFFFFFFFF,
        (TIME_CONFIG - SPEED_STATE) & 0xFFFFFFFF,
    ]
    reset_bytes = struct.pack(f'<{len(restore_speed)}I', *restore_speed)
    draw = base + DRAW_OFFSET
    draw_pending = [
        0xE59F0018,  # load displacement to ELF base
        0xE08F0000,  # r0 = ELF base
        0xE1A0100B,  # r1 = board
        0xE1A0200A,  # r2 = graphics
        0xE3A03000,  # r3 = draw mode
        0xFA000000 | ((entry - (draw + 20) - 8) // 4 & 0xFFFFFF),
        0xE28DD00C,  # original epilogue: add sp, sp, #12
        branch(draw + 28, DRAW_HOOK + 4),
        (-(draw + 12)) & 0xFFFFFFFF,
    ]
    draw_bytes = struct.pack(f'<{len(draw_pending)}I', *draw_pending)
    sprite = base + SPRITE_OFFSET
    draw_sprite = [
        0xE92D4010,  # save r4 and return address
        0xE59F001C,  # load displacement to ELF base
        0xE08F0000,  # r0 = ELF base
        0xE1A01005,  # r1 = board
        0xE1A02004,  # r2 = graphics
        0xE3A03001,  # r3 = sprite mode
        0xFA000000 | ((entry - (sprite + 24) - 8) // 4 & 0xFFFFFF),
        0xE8BD4010,
        0xE59D0008,  # original: load the board graphics transform
        0xE12FFF1E,  # bx lr
        (-(sprite + 16)) & 0xFFFFFFFF,
    ]
    speed = base + SPEED_DRAW_OFFSET
    draw_speed = [
        0xE92D4010,
        0xE59F001C,
        0xE08F0000,  # ELF base
        0xE1A01005,  # pause button
        0xE1A02004,  # graphics
        0xE3A03002,  # speed draw mode
        0xFA000000 | ((entry - (speed + 24) - 8) // 4 & 0xFFFFFF),
        0xE8BD4010,
        0xE1A00004,  # restore the graphics argument
        branch(speed + 36, 0x7D2940),  # original Graphics::PopState
        (-(speed + 16)) & 0xFFFFFFFF,
    ]
    coin = base + COIN_DRAW_OFFSET
    draw_coin = [
        0xE92D4010,
        0xE59F0020,
        0xE08F0000,  # ELF base
        0xE1A01009,  # CoinBank
        0xE1A02004,  # graphics
        0xE3A03003,  # coin draw mode
        0xFA000000 | ((entry - (coin + 24) - 8) // 4 & 0xFFFFFF),
        0xE8BD4010,
        0xE3500000,  # transparent: skip to the epilogue without popping state
        branch(coin + 36, COIN_DRAW_EXIT, condition=0),
        0xE12FFF1E,  # visible: return through the original call site
        (-(coin + 16)) & 0xFFFFFFFF,
    ]
    select = base + POWERUP_SELECT_OFFSET
    select_powerup = [
        0xE3500000,  # original selection passed a resolved power-up
        branch(select + 4, select + 32, condition=0),
        0xE92D0003,
        0xE59F0010,
        0xE08F0000,  # address of the pending coin reveal
        0xE3A01001,
        0xE5801000,
        0xE8BD0003,
        branch(select + 32, POWERUP_ACTIVATE),  # continue with the original activation
        (COIN_SELECTION_PENDING - (select + 24)) & 0xFFFFFFFF,
    ]
    def native_call_stub(address, mode):
        # The title formatter takes four original arguments. Pass them as a
        # single stack block. The other text routines take only two.
        if mode == 8:
            setup = [0xE92D401F, 0xE1A0100D, 0xE3A02000]
            pop = 0xE8BD401F
        else:
            setup = [0xE92D4010, 0xE1A02001, 0xE1A01000]
            pop = 0xE8BD4010
        return setup + [
            0xE59F0010,
            0xE08F0000,  # ELF base
            0xE3A03000 | mode,
            0xFA000000 | ((entry - (address + 24) - 8) // 4 & 0xFFFFFF),
            pop,
            0xE12FFF1E,
            (-(address + 24)) & 0xFFFFFFFF,
        ]
    segment = (stub_bytes.ljust(RESET_OFFSET, b'\0') + reset_bytes).ljust(DRAW_OFFSET, b'\0') + draw_bytes
    segment = segment.ljust(SPRITE_OFFSET, b'\0') + struct.pack(f'<{len(draw_sprite)}I', *draw_sprite)
    segment = segment.ljust(SPEED_DRAW_OFFSET, b'\0') + struct.pack(f'<{len(draw_speed)}I', *draw_speed)
    segment = segment.ljust(COIN_DRAW_OFFSET, b'\0') + struct.pack(f'<{len(draw_coin)}I', *draw_coin)
    segment = segment.ljust(POWERUP_SELECT_OFFSET, b'\0') + struct.pack(f'<{len(select_powerup)}I', *select_powerup)
    if custom_typefaces:
        for mode, hook in enumerate(TYPEFACE_CALLS, 8):
            offset = TYPEFACE_OFFSET + (mode - 8) * 0x30
            address = base + offset
            stub = native_call_stub(address, mode)
            segment = segment.ljust(offset, b'\0') + struct.pack(f'<{len(stub)}I', *stub)
            struct.pack_into('<I', data, hook, branch(hook, address, link=True))
    font_size = base + FONT_SIZE_OFFSET
    shrink_font = [
        0xE3530009,  # leave the engine's special small fonts alone
        branch(font_size + 4, font_size + 20, condition=11),
        0xE2433003,  # sub r3, r3, #3
        0xE3530009,
        0xB3A03009,  # clamp normal UI fonts to 9
        0xE92D48F0,  # displaced constructor prologue
        branch(font_size + 24, PRIME_FONT_INIT + 4),
    ]
    segment = segment.ljust(FONT_SIZE_OFFSET, b'\0') + struct.pack('<7I', *shrink_font)
    for index, ((init, _), (create, _), (read, original_read)) in enumerate(DISPLAY_NAME_FONTS):
        offset = DISPLAY_NAME_FONT_OFFSET + index * 0x60
        capture = base + offset
        create_full = capture + 0x10
        read_full = capture + 0x38
        state = DISPLAY_NAME_FONT_STATE + index * 8
        capture_size = [
            0xE59FC004,  # load displacement to the saved size
            0xE78F300C,  # save the unmodified constructor size in r3
            branch(capture + 8, PRIME_FONT_INIT),
            (state - (capture + 12)) & 0xFFFFFFFF,
        ]
        destination = (original_read >> 12) & 0xF
        read_font = [original_read]
        if index == 1:
            # The renderer reserves space for the edit icon only on an existing player row.
            read_font += [0xE3550000, 0x012FFF1E]  # cmp r5, #0; bxeq lr
        address = read_full + 4 * len(read_font)
        read_font += [
            0xE59FC00C,  # load displacement to the full-size font slot
            0xE79FC00C,  # load the full-size font
            0xE35C0000,  # keep the original if the slot is still empty
            0x11A0000C | destination << 12,  # movne destination, ip
            0xE12FFF1E,
            (state + 4 - (address + 12)) & 0xFFFFFFFF,
        ]
        segment = segment.ljust(offset, b'\0') + struct.pack('<4I', *capture_size)
        segment += struct.pack('<10I', *native_call_stub(create_full, 12 + index))
        segment += struct.pack(f'<{len(read_font)}I', *read_font)
        for hook, target in ((init, capture), (create, create_full), (read, read_full)):
            struct.pack_into('<I', data, hook, branch(hook, target, link=True))
    segment = segment.ljust(ENTRY_OFFSET, b'\0') + code
    if not code or len(segment) > 2 * PAGE_SIZE:
        raise ValueError('Unexpected Iris input payload size')
    file_offset = (len(data) + PAGE_SIZE - 1) & -PAGE_SIZE
    # The library is loaded by Android as a shared object. Reuse its PT_INTERP
    # slot, keeping PT_LOAD entries sorted and preserving all original mappings.
    headers.pop(1)
    data_segment = list(headers[2])
    data_segment[5] += STATE_SIZE
    headers[2] = tuple(data_segment)
    headers.insert(3, (1, file_offset, base, base, len(segment), len(segment), 5, PAGE_SIZE))
    for index, header in enumerate(headers):
        struct.pack_into(header_format, data, program_offset + index * header_size, *header)
    struct.pack_into('<I', data, HOOK, branch(HOOK, base))
    struct.pack_into('<I', data, BOARD_CLEAR, branch(BOARD_CLEAR, reset))
    struct.pack_into('<I', data, DRAW_HOOK, branch(DRAW_HOOK, draw))
    struct.pack_into('<I', data, SPRITE_HOOK, branch(SPRITE_HOOK, sprite, link=True))
    struct.pack_into('<I', data, SPEED_DRAW_HOOK, branch(SPEED_DRAW_HOOK, speed, link=True))
    struct.pack_into('<I', data, COIN_DRAW_HOOK, branch(COIN_DRAW_HOOK, coin, link=True))
    struct.pack_into('<I', data, POWERUP_SELECT_HOOK, branch(POWERUP_SELECT_HOOK, select, link=True))
    struct.pack_into('<I', data, PRIME_FONT_INIT, branch(PRIME_FONT_INIT, font_size))
    # The profile field takes the 25-unit Pico slot, which carries FZY4JW in the Chinese expansion.
    struct.pack_into('<I', data, PROFILE_NAME_FONT_READ, 0xE0800006)  # add r0, r0, r6
    struct.pack_into('<I', data, PROFILE_NAME_FONT_OFFSET, 0x5BD60)
    for address, (_, replacement) in PROFILE_FACEBOOK.items():
        struct.pack_into('<I', data, address, replacement)
    for address, (_, target) in PROFILE_FACEBOOK_SKIPS.items():
        struct.pack_into('<I', data, address, branch(address, target))
    for address in COIN_PLUS_READS:
        struct.pack_into('<I', data, address, 0xE3A00000)  # mov r0, #0
    for address in AUTO_PAUSE_CALLS:
        struct.pack_into('<I', data, address, ARM_NOP)
    data.extend(bytes(file_offset - len(data)))
    data.extend(segment)
    path.write_bytes(data)
