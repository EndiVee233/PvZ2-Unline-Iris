"""Exercise compiled module registration, save fields and clipped illumination."""
import argparse
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data = path.read_bytes(); u = Uc(UC_ARCH_ARM, UC_MODE_ARM); u.mem_map(0, 0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2, 0xf << 20); u.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
    ph, = struct.unpack_from('<I', data, 28); step, count = struct.unpack_from('<HH', data, 42)
    for q in range(ph, ph + step * count, step):
        kind, off, va, _, size, _, flags, _ = struct.unpack_from('<8I', data, q)
        if kind == 1:
            assert flags != 7; u.mem_write(va, data[off:off + size])
    op, = struct.unpack_from('<I', data, 0x2d8160)
    displacement = (op & 0xffffff) << 2
    if displacement & 0x2000000: displacement -= 0x4000000
    entry = 0x2d8160 + 8 + displacement
    def word(p, v): u.mem_write(p, struct.pack('<I', v))
    def read(p): return struct.unpack('<I', u.mem_read(p, 4))[0]
    def floating(p, v): u.mem_write(p, struct.pack('<f', v))
    def string(p): return bytes(u.mem_read(p, 100)).split(b'\0')[0].decode()
    registry, reflect, ptype, descriptor, stop, stack = (0xf40000, 0xf41000, 0xf42000, 0xf43000, 0xf70000, 0xfff000)
    word(registry, 0xf44000); word(0xf4400c, 0xf50000)
    word(reflect, 0xf45000)
    for slot, fn in ((0x24, 0xf50010), (0x28, 0xf50020), (0x14, 0xf50030), (0x2c, 0xf50040)):
        word(0xf45000 + slot, fn)
    word(ptype, 0xf46000); word(0xf46034, 0xf50050)
    env = dict(alloc=0xf00000, allocated=[], names=[], fields=[], base=0, clips=[], draws=0, destructor=0)
    textslot = 0xf60000
    app, board, clock, plant, fw, typ, vec = (0xf8000, 0xf9000, 0xfa000, 0xfb000, 0xfc000, 0xfd000, 0xfe000)
    props = module = 0
    word(0xd00838, 0xff000); word(0xff000, app); word(app + 0x6c0, board)
    word(0xd4ed90, clock); word(board + 0xa8, 5)
    word(board + 0x590, 0)
    word(plant + 0x30, fw); word(plant + 0xb8, 2); word(plant + 0x58, 2); word(plant + 0x5c, 4)
    word(plant + 8, 1); word(plant + 12, 1); word(fw + 4, plant)
    u.mem_write(0x555500, bytes(0x100))
    floating(app + 0x6a0, 1); floating(0x555510, 1); floating(0x555514, 1)
    word(0x555500 + 0x6c, 0x556500); word(0x556500, 0x557500); word(0x55754c, 0xf50060)
    word(0x444428, 257); word(0x44442c, 296)
    u.mem_write(plant + 0x60, b'\1'); word(typ + 0x10, 0xff100)
    u.mem_write(0xff100, b'POPANIM_PLANT_STREETLAMP\0'); word(vec, plant)

    def ret(v=0): u.reg_write(UC_ARM_REG_R0, v); u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
    def hook(cpu, pc, size, _):
        r0, r1, r2, r3 = [u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
        if pc == entry + 560: env['base'] += 1; ret()
        elif pc == entry + 572: ret(55)
        elif pc == 0x537e38: ret(456)
        elif pc == 0xb363dc:
            assert r0 in (40, 0x44, 0x180, 0x2c)
            p = env['alloc']; env['alloc'] += 0x200; env['allocated'].append((p, r0)); ret(p)
        elif pc in (0x894ca0, 0xb76c4c, 0xe8c10): ret()
        elif pc in (0x134100, 0x1341d8): ret(0x111100 if pc == 0x134100 else 0x111200)
        elif pc == 0x895608:
            env['names'].append(string(r1)); assert r2 in (0x111100, 0x111200); ret()
        elif pc == 0x851728: ret(0x222200)
        elif pc == 0x851920: assert r0 == 0x222200; ret(registry)
        elif pc == 0xb75560:
            u.mem_write(textslot, string(r1).encode() + b'\0'); word(textslot - 4, 100); word(r0, textslot); ret()
        elif pc == 0xf50000: assert r3 in (0x2c, 0x180); ret()
        elif pc == 0xf50010: assert string(read(r1)) in ('LevelModule', 'LevelModuleProperties'); ret(ptype)
        elif pc == 0xf50020: assert (r0, r1, r2, r3) == (reflect, descriptor, 123, 0); ret()
        elif pc == 0xf50030: assert r1 in (6, 8); ret(r1)
        elif pc == 0xf50040: env['fields'].append((string(read(r2)), r3, read(u.reg_read(UC_ARM_REG_SP)))); ret()
        elif pc == 0xf50050: ret(123)
        elif pc == 0x8821a8: ret(0x333300)
        elif pc == 0x8890c4: word(r0, read(r2)); word(r0 + 4, read(r2 + 4)); ret()
        elif pc == 0x888b8c: ret(0x333400)
        elif pc == 0x884378: ret(props if read(r1) == 1 else typ if read(r1) == 2 else 0)
        elif pc == 0x13dea0: word(r0, r2); word(r0 + 4, r3); ret()
        elif pc == 0x248120: assert r1 == 1; word(r0, vec); word(r0 + 4, vec + 4); ret()
        elif pc in (0xb36928, 0x7d2810, 0x7d2940, 0x7d2aa8, 0x7d2de4, 0x7d27f0): ret()
        elif pc == 0x1524d8: assert string(read(r0 + 12)).startswith('IMAGE_UI_MISTY_'); ret(0x444400)
        elif pc == 0x7d2e14: env['clips'].append((r1, r2, r3, read(u.reg_read(UC_ARM_REG_SP)))); ret()
        elif pc == 0x7d53cc: env['draws'] += 1; ret()
        elif pc == 0xf50060:
            assert r1 == 0x444400
            dest = struct.unpack('<4i', u.mem_read(r2, 16)); source = struct.unpack('<4i', u.mem_read(r3, 16))
            x, y, w, h = dest; sx, sy, sw, sh = source
            assert 200 <= x < x + w <= 776 and 84 <= y < y + h <= 616, dest
            assert 0 <= sx < sx + sw <= 257 and 0 <= sy < sy + sh <= 296
            env['clips'].append((x, y, w, h)); env['draws'] += 1; ret()
        elif pc in (0x141444, 0x14148c): env['destructor'] += 1; ret()
        elif pc == stop: u.emu_stop()
    u.hook_add(UC_HOOK_CODE, hook)
    def run(mode, args=(0, 0, 0, 0)):
        u.reg_write(UC_ARM_REG_SP, stack); u.reg_write(UC_ARM_REG_LR, stop)
        for reg, v in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args): u.reg_write(reg, v)
        u.emu_start(entry + mode * 40, stop, count=300000)
        assert u.reg_read(UC_ARM_REG_PC) == stop and u.reg_read(UC_ARM_REG_SP) == stack
        return u.reg_read(UC_ARM_REG_R0)
    run(0); run(0)
    assert env['names'] == ['WarMistProperties', 'WarMistModule'] and env['base'] == 2
    props = run(1); module = run(2); assert run(7) == run(4)
    assert read(props) == read(0xf80108) and read(module) == read(0xf8010c)
    word(module + 0x10, 1); word(props + 0x28, 3)
    items, countp = 0xe80000, 0xe70000
    word(items + 3 * 36 + 8, 0x11223344)
    word(countp, 3); assert run(13, (items, countp, 0, 0)) == 456
    item = items + 3 * 36
    assert (read(countp), read(item), read(item + 4), read(item + 8), read(item + 12), read(item + 0x1c)) == (4, 14, 599999, 0x11223344, board, entry + 480)
    word(countp, 4096); run(13, (items, countp, 0, 0)); assert read(countp) == 4096
    run(5, (reflect, descriptor, 0, 0)); run(6, (reflect, descriptor, 0, 0))
    assert env['fields'] == [('m_iNormValX', 0x20, 8), ('m_iBloverEffectInterval', 0x24, 8),
                              ('m_iInitMistPosX', 0x28, 6), ('iris_started', 0x18, 8),
                              ('iris_previous', 0x1c, 8), ('iris_offset', 0x20, 8), ('iris_blow_end', 0x24, 8),
                              ('iris_blover_uid_low', 0x28, 6), ('iris_blover_uid_high', 0x2c, 6)]
    floating(clock + 0x1c, 10); floating(module + 0x1c, 9.9); floating(module + 0x20, -384)
    for i in range(63): floating(module + 0x80 + i * 4, 1)
    # Set lamps' fade to its settled state. The native footprint is 19 cells.
    for y in range(5):
        for x in range(9):
            ax, ay = abs(x - 4), abs(y - 2)
            if ay <= 2 and ax <= 3 and (ax == 0 if ay == 2 else ax + ay != 4): floating(module + 0x80 + ((y + 1) * 9 + x) * 4, 0)
    # Simulate the engine moving the item while retaining the destination's
    # fixed vtable. The callable's board pointer must move with its payload.
    moved = items + 20 * 36; word(moved + 8, 0x55667788)
    for offset in (0, 4, 12, 16, 20, 24, 28, 32): word(moved + offset, read(item + offset))
    run(12, (moved + 8, 0x555500, 0, 0)); assert env['draws'] > 0
    cells = {((x - 200) // 64, (y - 160) // 76) for x, y, _, _ in env['clips']}
    # Thirteen unlit cells are left of the initial fog boundary; thirty-one are
    # actually covered. Clipping must not manufacture fog in the clear area.
    assert len(cells) == 31 and all(x >= 2 for x, _ in cells), cells
    assert all(w <= 64 and h <= 76 for _, _, w, h in env['clips'])
    floating(fw + 0x10, 40)
    for i in range(63): floating(module + 0x80 + i * 4, 0)
    env['clips'].clear(); run(10, (board, 0x555500, 0, 0)); assert not env['clips']
    assert run(11, (fw, 0, 0, 0)) == 55
    assert struct.unpack('<f', u.mem_read(module + 0x24, 4))[0] == 25
    floating(clock + 0x1c, 12); run(11, (fw, 0, 0, 0))
    assert struct.unpack('<f', u.mem_read(module + 0x24, 4))[0] == 25
    word(plant + 8, 2); run(11, (fw, 0, 0, 0))
    assert struct.unpack('<f', u.mem_read(module + 0x24, 4))[0] == 27
    run(9, (module, 0, 0, 0)); assert read(0xf80110) == 0 and env['destructor'] == 1
    print('PASS: own module metadata, inherited schemas, typed properties, 19-cell lighting, whole-board food, clipped fog and destruction')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('library', type=Path); check(parser.parse_args().library)
