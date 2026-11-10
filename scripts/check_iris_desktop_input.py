"""Exercise the installed Iris ARM input and board-clear hooks in Unicorn."""

import argparse
from io import BytesIO
import math
import struct
from zipfile import ZipFile

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_FPEXC, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R9, UC_ARM_REG_R11,
    UC_ARM_REG_SP,
)

from iris_desktop_input import (
    BOARD_CLEAR, COIN_DRAW_EXIT, COIN_DRAW_HOOK, COIN_PLUS_READS, COIN_SELECTION_PENDING,
    PAYLOAD_VADDR, POWERUP_ACTIVATE, POWERUP_SELECT_HOOK, SPEED_DRAW_HOOK, SPEED_STATE, SPRITE_HOOK,
    TIME_CONFIG,
)
from prepare_baseline import NATIVE


DRIVER, APP, BOARD, MANAGER, CONFIG, HOLDER, BUTTON, TYPE, BUCKET, CURSOR = (
    0x3000000 + n * 0x1000 for n in range(10)
)
PACKET, POINTER, STOP, STACK = 0x3010000, 0x3010100, 0x3010200, 0x3020000
COLLECTABLE = BUCKET + 0x500


def check(image, base):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    cpu.mem_map(DRIVER, 0x30000)
    cpu.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
    with BytesIO(image) as stream:
        segments = [s for s in ELFFile(stream).iter_segments() if s['p_type'] == 'PT_LOAD']
        assert len(segments) == 3 and segments[-1]['p_flags'] == 5
        assert segments[-1]['p_vaddr'] == PAYLOAD_VADDR
        for segment in segments:
            start = segment['p_vaddr'] & -0x1000
            end = (segment['p_vaddr'] + segment['p_memsz'] + 0xFFF) & -0x1000
            cpu.mem_map(base + start, end - start)
            cpu.mem_write(base + segment['p_vaddr'], segment.data())

    def read(address):
        return struct.unpack('<I', cpu.mem_read(address, 4))[0]

    def write(address, *values):
        cpu.mem_write(address, struct.pack(f'<{len(values)}I', *values))

    assert all(read(base + address) == 0xE3A00000 for address in COIN_PLUS_READS)

    def string(address):
        return bytes(cpu.mem_read(address, 48)).split(b'\0')[0]

    def make_string(out, name, *_):
        text = PACKET + 0x500
        write(text - 4, 2)
        cpu.mem_write(text, string(name) + b'\0')
        write(out, text)

    def floorf(bits, *_):
        value = struct.unpack('<f', struct.pack('<I', bits))[0]
        return struct.unpack('<I', struct.pack('<f', math.floor(value)))[0]

    def run(pc, stop=STOP):
        cpu.reg_write(UC_ARM_REG_LR, STOP)
        cpu.reg_write(UC_ARM_REG_SP, STACK)
        cpu.emu_start(base + pc, stop, count=50000)
        assert cpu.reg_read(UC_ARM_REG_PC) == stop

    def send(phase, x, y=0, px=-1, py=-1, ident=0x7FFFFFFE):
        cpu.mem_write(PACKET, struct.pack('<IIiiiiiQIII', 0, ident, x, y, px, py, 1, 0, phase, 0, 0))
        write(POINTER, PACKET)
        cpu.reg_write(UC_ARM_REG_R0, DRIVER)
        cpu.reg_write(UC_ARM_REG_R1, POINTER)
        run(0x9F0298)
        assert read(POINTER) == PACKET + 48

    calls = []
    coin_clock = 0
    coin_graphics = HOLDER + 0x600
    graphics_color = coin_graphics + 0x4C

    def clock_gettime(clock, stamp, *_):
        assert clock == 1
        write(stamp, coin_clock // 1000, coin_clock % 1000 * 1000000)
        return 0

    app_table = base + 0xCDD258
    native = {
        0xB75560: make_string,
        0x536398: lambda out, *_: {b'UIPowerupHolder': HOLDER}.get(string(read(out)), 0),
        0x537FFC: lambda *_: 1,
        0x5385C0: lambda out, *_: write(out, 123, 456),
        0x537174: lambda x, *_: BUTTON if x == 123 else BOARD,
        0x8821A8: lambda *_: HOLDER,
        0x888B8C: lambda *_: BUCKET,
        0x8890C4: lambda out, _, handle, *a: write(out, read(handle), read(handle + 4)),
        0x884378: lambda _, handle, *a: {1: BUTTON, 2: TYPE, 3: COLLECTABLE}.get(read(handle), 0),
        0x13DEA0: lambda out, _, first, second: write(out, first, second),
        0x45D9B4: lambda *_: 1,
        0x1331EC: lambda *_: 2,
        0x160C64: lambda *_: 3,
        0x169510: lambda *_: 4,
        0x169194: lambda *_: 5,
        0x1693C4: lambda *_: 6,
        0x365EC4: lambda out, ui, bucket, _: (
            write(out + 8, HOLDER + 0x200, HOLDER + 0x208)
            if (ui, bucket) == (MANAGER, 0x18) else 0),
        0x881B84: lambda *_: None,
        0x1EB238: lambda *_: BUTTON,
        0x3761EC: lambda _, value, *a: write(CONFIG + 0x28, value),
        POWERUP_ACTIVATE: lambda powerup, *a: calls.append(('activate power-up', powerup)),
        0x2BD798: lambda *_: calls.append('close pause menu'),
        0x17D1BC: lambda _, paused, *a: calls.append(('set paused', paused)),
        0x192A1C: lambda *_: calls.append('cancel'),
        0x9E8340: lambda *_: None,
        0x1841FC: lambda *_: None,
        0xE8700: floorf,
        0xE8E5C: clock_gettime,
        0x7D2810: lambda graphics, *a: calls.append('coin push state') if graphics == coin_graphics else None,
        0x7D2940: lambda *_: None,
        0x7D2AA8: lambda _, color, *a: calls.append(('color', *struct.unpack('<4I', cpu.mem_read(color, 16)))),
        0x7D2BB4: lambda *_: graphics_color,
        0x7D2BBC: lambda *_: calls.append('push color'),
        0x7D2DE4: lambda _, enabled, *a: calls.append(('colorize', enabled)),
        0x534F5C: lambda out, *_: write(out, 600, 8, 64, 64),
        0x1524D8: lambda ref, *_: {b'IMAGE_UI_HUD_INGAME_SPEED': BUTTON,
                                   b'IMAGE_UI_HUD_INGAME_SPEED_DOWN': TYPE}[string(read(ref + 12))],
        0x7D53CC: lambda graphics, image, x, _: calls.append(('speed draw', image, x)),
        0x18D628: lambda board, graphics, column, row: calls.append(('cross', column, row)),
        0x462BD0: lambda powerup, point, span, scale: calls.append(
            ('pinch', powerup, read(point), read(point + 4), span, scale)),
    }
    callbacks = {base + address: fn for address, fn in native.items()}

    def virtual(table, slot, fn):
        address = STOP + 4 + len(callbacks) * 4
        callbacks[address] = fn
        write(table + slot, address)

    def emulate(_, address, size, data):
        if address in callbacks:
            args = [cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
            value = callbacks[address](*args)
            if value is not None:
                cpu.reg_write(UC_ARM_REG_R0, value)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    cpu.hook_add(UC_HOOK_CODE, emulate)
    write(DRIVER + 0x44, APP)
    write(APP, app_table)
    write(APP + 0x6C0, BOARD)
    write(APP + 0x2B8, MANAGER)
    write(base + 0xD00838, MANAGER + 0x300)
    write(MANAGER + 0x300, APP)
    write(APP + 0x6A0, 0x3F800000)
    write(MANAGER + 0xAC, MANAGER + 0xA8)
    write(BOARD + 0xA8, 5)
    write(BOARD, BOARD + 0x400)
    virtual(BOARD + 0x400, 0x60, lambda out, *_: write(out, 20, 30))
    write(BOARD + 0x9C, 9, 5)
    cpu.mem_write(BOARD + 0xC4, bytes([1]))
    write(base + TIME_CONFIG, CONFIG)
    write(base + 0xD4E964, MANAGER)
    for slot, label in ((0x1B0, 'down'), (0x1B4, 'up')):
        virtual(app_table, slot, lambda _, touch, *a, tag=label: calls.append((tag, read(touch + 8))))
    for phase, entry in ((0, 0x9E8208), (1, 0x9E8378), (3, 0x9E8528), (4, 0x9E8828)):
        callbacks[base + entry] = lambda *a, tag=phase: calls.append(tag)
        send(phase, 0)
        assert calls.pop() == phase
    send(2, 0)
    send(7, 0)
    assert not calls

    write(HOLDER + 0x40, HOLDER + 0x200, HOLDER + 0x208)
    write(HOLDER + 0x200, 1, 0x400000)
    write(BUTTON, BUTTON + 0x400)
    write(BUTTON + 0xF0, 2, 0x400000)
    write(TYPE, TYPE + 0x400)
    write(TYPE + 8, TYPE + 0x200)
    virtual(BUTTON + 0x400, 0x10, lambda _, kind, *a: int(kind == 1))
    virtual(TYPE + 0x400, 0x10, lambda _, kind, *a: int(kind == 2))
    for key, name in ((30, b'PowerupPinchZombie'), (42, b'PowerupFlickZombie'), (41, b'PowerupWizardFinger')):
        cpu.mem_write(TYPE + 0x200, name + b'\0')
        send(6, key)
        assert calls == [('down', 123), ('up', 123)], (key, calls)
        calls.clear()
    send(6, 30)
    assert not calls
    send(6, 8)
    assert calls == [('down', 123), ('up', 123)]
    calls.clear()

    write(BOARD + 0x640, CURSOR)
    write(CURSOR, CURSOR + 0x400)
    virtual(CURSOR + 0x400, 0x10, lambda _, kind, *a: int(kind in (4, 5)))
    virtual(CURSOR + 0x400, 0x2C, lambda *_: 1)
    virtual(CURSOR + 0x400, 0x30, lambda out, *_: write(out, 3, 2))
    virtual(CURSOR + 0x400, 0x20, lambda *_: calls.append('sprite'))
    virtual(CURSOR + 0x400, 0x24, lambda _, touch, *a: calls.append(
        ('cursor move', read(touch + 8), read(touch + 12))))
    send(6, 100)
    assert calls.pop() == 'cancel'
    send(6, 101, px=95, py=100)
    assert not calls
    send(6, 101, px=250, py=220)
    assert calls == [('down', 250), ('up', 250)]
    calls.clear()
    write(COLLECTABLE, COLLECTABLE + 0x200)
    virtual(COLLECTABLE + 0x200, 0x10, lambda _, kind, *a: int(kind == 3))
    virtual(COLLECTABLE + 0x200, 0x98, lambda _, touch, *a: calls.append(('collect', read(touch + 8))))
    virtual(COLLECTABLE + 0x200, 0x4C, lambda out, *_: write(out, 100, 200, 20, 20))
    write(COLLECTABLE + 8, 3, 0x400000)
    write(BUCKET + 4, BUCKET + 0x200, 1)
    write(BUCKET + 0x208, COLLECTABLE)
    send(5, 120, 210)
    assert calls.pop() == ('collect', 100)
    assert calls.pop() == ('cursor move', 100, 180)
    cpu.reg_write(UC_ARM_REG_R0, BOARD)
    cpu.reg_write(UC_ARM_REG_R1, HOLDER)
    run(0x18A2C4)
    assert calls.pop() == ('cross', 3, 2)
    cpu.reg_write(UC_ARM_REG_R4, HOLDER)
    cpu.reg_write(UC_ARM_REG_R5, BOARD)
    run(SPRITE_HOOK, base + SPRITE_HOOK + 4)
    assert calls.pop() == 'sprite'
    assert read(BOARD + 0x634) == read(BOARD + 0x638) == 0
    send(6, 29)
    assert calls.pop() == ('collect', 110)

    for tool, cursor_type in (('shovel', 6), ('plant food', 4)):
        virtual(CURSOR + 0x400, 0x10, lambda _, kind, *a: int(kind == cursor_type))
        assert cpu.mem_read(CURSOR + 0x12, 1) == b'\0'
        for x, y, expected in ((250, 230, [('cross', 0, 0)]), (120, 210, [])):
            send(5, x, y)
            assert calls.pop() == ('collect', x - 20)
            cpu.reg_write(UC_ARM_REG_R0, BOARD)
            cpu.reg_write(UC_ARM_REG_R1, HOLDER)
            run(0x18A2C4)
            assert calls == expected, (tool, x, y, calls)
            calls.clear()
        assert cpu.mem_read(CURSOR + 0x12, 1) == b'\0'

    # The native callback checks its rectangle in unzoomed board coordinates.
    callbacks[base + 0x1841FC] = lambda _, point, *a: write(
        point, read(point) - 25, read(point + 4) - 30)

    def collect_if_hit(_, touch, *args):
        x, y = read(touch + 8), read(touch + 12)
        if 100 <= x < 120 and 200 <= y < 220:
            calls.append(('picked up', x, y))

    virtual(COLLECTABLE + 0x200, 0x98, collect_if_hit)
    send(5, 155, 270)
    assert calls == [('picked up', 110, 210)], calls
    calls.clear()
    send(5, 135, 270)
    assert not calls

    input_dispatch = BOARD + 0x800
    delegate = input_dispatch + 0x100
    powerup = input_dispatch + 0x200
    write(BOARD + 0x630, input_dispatch)
    write(input_dispatch + 0xc, delegate, delegate + 24)
    write(delegate + 4, base + 0x462BD0, 0, powerup, 1, base + 0x463510)
    write(app_table + 0x1c4, base + 0x9C7498)
    write(BOARD + 0x400 + 0x134, base + 0x1847CC)
    write(BOARD + 0x678, 0x3FA00000, 0x43C80000, 0x43480000)  # zoom 1.25, anchor (400, 200)
    def viewport(_, x, y, *args):
        write(x, read(x) + 5)
        write(y, read(y) + 10)

    callbacks[base + 0x9D9390] = viewport
    callbacks[base + 0x9D7CCC] = lambda _, x, *a: BOARD if x > 400 else BUTTON
    virtual(BUTTON + 0x400, 0x134, lambda *_: None)
    send(0, 520, 300)
    send(3, 520, 300)
    assert calls == [0, 3]
    calls.clear()
    write(powerup + 0x24, 1)
    send(0, 120, 300)
    send(3, 123, 300)  # The original widget manager routes this click to UI.
    assert calls == [0, 3]
    calls.clear()
    cpu.mem_write(DRIVER + 0xdc, b'\1')
    send(0, 511, 300)
    send(1, 517, 300)
    send(3, 520, 300)
    assert calls == [0, 1, ('pinch', powerup, 500, 288, 0, 0xBF800000), 3], calls
    calls.clear()
    send(0, 520, 300)
    send(1, 570, 300)
    send(3, 520, 300)
    assert calls == [0, 1, 3]
    calls.clear()
    send(0, 520, 300)
    send(0, 521, 300, ident=2)
    send(3, 520, 300)
    send(3, 521, 300, ident=2)
    assert calls == [0, 0, 3, 3]
    calls.clear()

    cpu.mem_write(BOARD + 0x671, bytes([1]))
    send(6, 62)
    assert not calls
    write(APP + 0xBC4, BUTTON)
    write(MANAGER + 0xAC, MANAGER + 0x200)
    write(MANAGER + 0x208, BUTTON)
    send(6, 62)
    assert calls == ['close pause menu', ('set paused', 0)]
    calls.clear()
    cpu.mem_write(BOARD + 0x671, bytes([0]))
    write(MANAGER + 0xAC, MANAGER + 0xA8)

    write(CONFIG + 0x28, 0x3F800000)
    feedback = base + SPEED_STATE + 0x74
    def draw_speed():
        cpu.reg_write(UC_ARM_REG_R4, HOLDER)
        cpu.reg_write(UC_ARM_REG_R5, BUTTON)
        run(SPEED_DRAW_HOOK, base + SPEED_DRAW_HOOK + 4)

    def check_paused_speed_draw(image):
        draw_speed()
        assert calls == [('color', 128, 128, 128, 255), ('colorize', 1),
                         ('speed draw', image, -72 & 0xFFFFFFFF)]
        calls.clear()

    draw_speed()
    assert calls.pop() == ('speed draw', BUTTON, -72 & 0xFFFFFFFF)
    cpu.mem_write(BOARD + 0x671, bytes([1]))
    write(MANAGER + 0xAC, MANAGER + 0x200)
    write(MANAGER + 0x208, BUTTON)
    check_paused_speed_draw(BUTTON)
    send(6, 50)
    send(0, 555, 32)
    send(3, 555, 32)
    assert calls == [0, 3] and read(CONFIG + 0x28) == 0x3F800000 and read(feedback) == 0
    calls.clear()
    write(MANAGER + 0x208, TYPE)
    draw_speed()
    assert not calls
    cpu.mem_write(BOARD + 0x671, bytes([0]))
    write(MANAGER + 0xAC, MANAGER + 0xA8)
    npc = HOLDER + 0x800
    write(APP + 0xbb0, npc)
    write(npc + 0x124, 2)  # The Day 6 dialogue uses this state, without a widget-manager modal.
    send(6, 50)
    send(0, 555, 32)
    draw_speed()
    assert calls == [('speed draw', BUTTON, -72 & 0xFFFFFFFF)]
    calls.clear()
    send(3, 555, 32)
    assert read(CONFIG + 0x28) == 0x3F800000 and not calls
    send(0, 555, 32)
    write(npc + 0x124, 7)  # Dialogue ends before the disabled press is released.
    send(3, 555, 32)
    assert read(CONFIG + 0x28) == 0x3F800000 and not calls
    send(0, 555, 32)
    write(npc + 0x124, 2)
    draw_speed()
    assert calls.pop() == ('speed draw', BUTTON, -72 & 0xFFFFFFFF)
    write(npc + 0x124, 7)
    send(3, 555, 32)
    assert read(CONFIG + 0x28) == 0x3F800000 and not calls
    assert read(feedback) == 0

    send(0, 555, 32)
    draw_speed()
    assert calls.pop() == ('speed draw', TYPE, -72 & 0xFFFFFFFF)
    send(3, 800, 32)
    assert read(CONFIG + 0x28) == 0x3F800000 and not calls
    send(0, 555, 32)
    send(3, 555, 32)
    assert read(CONFIG + 0x28) == 0x40000000 and not calls
    assert read(feedback) == 2
    write(feedback, 0)
    draw_speed()
    assert calls.pop() == ('speed draw', TYPE, -72 & 0xFFFFFFFF)
    cpu.mem_write(BOARD + 0x671, bytes([1]))
    write(MANAGER + 0xAC, MANAGER + 0x200)
    write(MANAGER + 0x208, BUTTON)
    check_paused_speed_draw(TYPE)
    cpu.mem_write(BOARD + 0x671, bytes([0]))
    write(MANAGER + 0xAC, MANAGER + 0xA8)
    write(npc + 0x124, 2)
    send(6, 50)
    send(0, 555, 32)
    send(3, 555, 32)
    assert read(CONFIG + 0x28) == 0x40000000 and not calls
    assert read(feedback) == 0
    write(npc + 0x124, 7)
    send(6, 50)
    assert read(CONFIG + 0x28) == 0x3F800000 and read(feedback) == 1

    send(6, 50)
    assert read(CONFIG + 0x28) == 0x40000000
    send(6, 50)
    assert read(CONFIG + 0x28) == 0x3F800000
    send(6, 50)

    def check_coin_draw(time, alpha):
        nonlocal coin_clock
        coin_clock = time
        cpu.reg_write(UC_ARM_REG_R4, coin_graphics)
        cpu.reg_write(UC_ARM_REG_R9, BUTTON)
        stop = COIN_DRAW_HOOK + 4 if alpha else COIN_DRAW_EXIT
        run(COIN_DRAW_HOOK, base + stop)
        expected = ['coin push state'] if alpha else []
        if 0 < alpha < 255:
            expected += [('color', 255, 255, 255, alpha), 'push color',
                         ('color', 255, 255, 255, 255), ('colorize', 1)]
        assert calls == expected, (time, calls)
        calls.clear()

    write(graphics_color, 255, 255, 255, 255)
    write(BUTTON + 0xEC, 2290, 0xFFFFFFFF)
    write(BOARD + 0xA8, 3)
    check_coin_draw(5000, 255)
    write(BOARD + 0xA8, 4)
    check_coin_draw(10000, 255)
    check_coin_draw(12048, 255)
    check_coin_draw(13072, 127)
    check_coin_draw(14096, 0)
    write(BUTTON + 0xEC, 2300)
    check_coin_draw(14100, 0)
    check_coin_draw(14164, 127)
    check_coin_draw(14228, 255)
    check_coin_draw(17300, 127)
    write(BUTTON + 0xEC, 1500)
    check_coin_draw(17300, 127)
    check_coin_draw(17364, 255)
    check_coin_draw(21460, 0)
    write(BUTTON + 0xF0, 2500)  # Native temporary balance target.
    check_coin_draw(21500, 0)
    check_coin_draw(21628, 255)
    check_coin_draw(25724, 0)

    selection = base + COIN_SELECTION_PENDING
    cpu.reg_write(UC_ARM_REG_R0, powerup)
    run(POWERUP_SELECT_HOOK, base + POWERUP_SELECT_HOOK + 4)
    assert calls == [('activate power-up', powerup)] and read(selection) == 1
    calls.clear()
    check_coin_draw(26000, 0)
    assert read(selection) == 0 and read(BUTTON + 0xEC) == 1500
    check_coin_draw(26064, 127)
    check_coin_draw(26128, 255)
    check_coin_draw(30224, 0)
    cpu.reg_write(UC_ARM_REG_R0, powerup)
    run(POWERUP_SELECT_HOOK, base + POWERUP_SELECT_HOOK + 4)
    assert calls == [('activate power-up', powerup)] and read(selection) == 1
    calls.clear()

    cpu.reg_write(UC_ARM_REG_R0, 0)
    cpu.reg_write(UC_ARM_REG_R11, APP)
    run(BOARD_CLEAR, base + BOARD_CLEAR + 4)
    assert read(APP + 0x6C0) == 0
    assert read(base + SPEED_STATE + 4) == 0
    assert read(base + SPEED_STATE + 12) == 0
    assert read(base + SPEED_STATE + 20) == 0
    assert read(base + SPEED_STATE + 48) == 0
    assert read(feedback) == 0
    assert read(base + SPEED_STATE + 0x78) == 0
    assert read(selection) == 0
    assert read(CONFIG + 0x28) == 0x3F800000


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk')
    with ZipFile(parser.parse_args().apk) as apk:
        image = apk.read(NATIVE)
    for load_base in (0, 0x20000000):
        check(image, load_base)
    print('Installed Iris ARM desktop hooks passed at two load bases')
