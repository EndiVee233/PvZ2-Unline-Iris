"""Exercise compiled Magnet callbacks, typed pieces, timing and stock fallback."""
import argparse
from pathlib import Path
import struct
from native_payload import registration_payload
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data = path.read_bytes()
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(0, 0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2, 0xf << 20)
    u.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
    ph = struct.unpack_from('<I', data, 28)[0]
    step, count = struct.unpack_from('<HH', data, 42)
    for q in range(ph, ph + step * count, step):
        kind, off, va, _, size, _, _, _ = struct.unpack_from('<8I', data, q)
        if kind == 1:
            u.mem_write(va, data[off:off + size])
    fw, plant, ptype, name, zombie, zmeta, zname, rig, pieces, vec, appslot, app, board, clock = [0xf00000 + i * 0x1000 for i in range(14)]
    textslot, stop, stack = 0xf20000, 0xf30000, 0xfff000
    def word(p, v): u.mem_write(p, struct.pack('<I', v))
    def read(p): return struct.unpack('<I', u.mem_read(p, 4))[0]
    def floating(p, v): u.mem_write(p, struct.pack('<f', v))
    def number(p): return struct.unpack('<f', u.mem_read(p, 4))[0]
    def text(p): return bytes(u.mem_read(p, 110)).split(b'\0')[0].decode()
    word(fw + 4, plant)
    word(ptype + 0x10, name)
    u.mem_write(name, b'POPANIM_PLANT_MAGNETSHROOM\0')
    word(plant + 0xb8, 7)
    word(plant + 0x58, 2); word(plant + 0x5c, 3); word(plant + 0x48, 4)
    floating(plant + 0x10, 500); floating(plant + 0x14, 250)
    word(zombie, 0xf40000); word(0xf40000, 0xf50000); word(0xf4003c, 0xf50010); word(0xf40034, 0xf50020)
    word(zombie + 8, 77); word(zombie + 0xc, 1); word(zombie + 0x40, 88)
    floating(zombie + 0x10, 750); floating(zombie + 0x14, 250)
    word(zmeta + 4, zname); u.mem_write(zname, b'Zombie\0')
    word(plant, 0xf41000); word(0xf41070, 0xf50030)
    word(rig, 0xf42000)
    for off, fn in ((0x114, 0xf50040), (0xf0, 0xf50050), (0xe4, 0xf50060), (0xf4, 0xf50060)):
        word(0xf42000 + off, fn)
    word(0xd00838, appslot); word(appslot, app); word(app + 0x6c0, board)
    word(0xd4ed90, clock); word(board + 0xa8, 5)
    entry = registration_payload(data, 0x3b9478, 'PlantIrisDark')
    env = {'pause': False, 'parts': [], 'removed': [], 'damage': [], 'labels': [], 'stock': 0}
    def ret(v=0): u.reg_write(UC_ARM_REG_R0, v); u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
    def hook(cpu, pc, size, _):
        r0, r1, r2, r3 = [u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
        if pc == 0x8821a8: ret(0xf60000)
        elif pc == 0x8890c4: word(r0, read(r2)); word(r0 + 4, read(r2 + 4)); ret()
        elif pc == 0x888b8c: ret(0xf61000)
        elif pc == 0x884378:
            key = read(r1)
            obj = ptype if key == 7 else zombie if key == 77 else rig if key == 88 else next((p for p in env['parts'] if read(p + 8) == key and p not in env['removed']), 0)
            ret(obj)
        elif pc == 0x13dea0: word(r0, r2); word(r0 + 4, r3); ret()
        elif pc == 0xf50000: ret(zmeta)
        elif pc == 0xf50010: assert r1 in (1,3); ret(1)
        elif pc == 0xf50020: env['damage'].append(number(r1 + 4)); ret()
        elif pc == 0xf50030: ret(rig)
        elif pc == 0xf50040: assert r1 in (2, 6, 9); ret(pieces)
        elif pc == 0xf50050: word(r0, textslot); word(textslot - 4, 100); ret()
        elif pc == 0xf50060: ret()
        elif pc == 0x453994: ret(0xf62000)
        elif pc == 0x7a3e90: assert r0>=1; ret(0)
        elif pc == 0x270400:
            assert (r0, r1) == (0xf62000, 0x1c)
            part = 0xf70000 + len(env['parts']) * 0x100
            env['parts'].append(part); word(part + 8, 100 + len(env['parts'])); word(part + 12, 1)
            word(part, 0xf43000); word(0xf43070, 0xf50070); word(0xf43074, 0xf50080); word(0xf43058, 0xf50090)
            floating(part + 0x10, 750); floating(part + 0x14, 250); floating(part + 0x18, 50); ret(part)
        elif pc == 0xf50070:
            assert (r1, r2) == (zombie, pieces)
            assert number(u.reg_read(UC_ARM_REG_SP)) == 0.75; ret()
        elif pc == 0xf50080: assert r1 == zombie; ret()
        elif pc == 0xf50090: u.mem_write(r0 + 0x10, bytes(u.mem_read(r1, 12))); ret()
        elif pc == 0x2708b4: env['removed'].append(r0); ret()
        elif pc == 0x248120:
            assert r1 == 2
            word(vec, zombie); word(r0, vec); word(r0 + 4, vec + 4); word(r0 + 8, vec + 4); ret()
        elif pc == 0x1872a8: ret(int(env['pause']))
        elif pc == 0xb75560:
            u.mem_write(textslot, text(r1).encode() + b'\0'); word(textslot - 4, 100); word(r0, textslot); ret()
        elif pc in (0xb76c4c, 0xb36928, 0xe8c10, 0x1a4280, 0x3ba164, 0x3ba2c0): ret()
        elif pc == 0x44cd0c: assert text(read(r1))=='Magnet_Item' and r2==0; ret()
        elif pc in (0x44d220, 0x44d0b0): env['labels'].append(text(read(r1))); ret()
        elif pc == 0x64c468: env['stock'] += 1; ret(55)
        elif pc == stop: u.emu_stop()
    u.hook_add(UC_HOOK_CODE, hook)
    preserved = [UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11]
    def run(mode, pointer=fw):
        u.reg_write(UC_ARM_REG_SP, stack); u.reg_write(UC_ARM_REG_LR, stop)
        u.reg_write(UC_ARM_REG_R0, pointer)
        for reg in preserved: u.reg_write(reg, 0x76540000 + reg)
        u.emu_start(entry + mode * 40, stop, count=200000)
        assert u.reg_read(UC_ARM_REG_PC) == stop and u.reg_read(UC_ARM_REG_SP) == stack
        assert all(u.reg_read(reg) == 0x76540000 + reg for reg in preserved)
        return u.reg_read(UC_ARM_REG_R0)
    def tick(t): floating(clock + 0x1c, t); run(8)
    word(zombie + 0x30, 1); floating(zombie + 0x34, 1000); tick(1)
    assert not env['parts']  # Plastic cone is not magnetic.
    word(zombie + 0x30, 2); tick(2)
    assert len(env['parts']) == 1 and read(zombie + 0x30) == 0 and number(zombie + 0x34) == 0
    part = env['parts'][0]
    assert read(fw + 0x48) == 1 and read(part + 0x48) == 0x49524953
    env['pause'] = True; tick(3); assert number(part + 0x10) == 750
    env['pause'] = False
    for i in range(20): tick(3 + i * 0.1)
    assert read(fw + 0x48) == 2 and abs(number(part + 0x10) - 500) < 0.01
    assert run(12, part) == 0 and env['stock'] == 0
    tick(18); assert part in env['removed'] and read(fw + 0xc) == 0
    word(zombie + 0x30, 9); floating(zombie + 0x34, 1000); floating(clock + 0x1c, 20)
    run(5); assert read(plant + 0x48) == 5
    tick(20.5); assert len(env['parts']) == 2 and read(fw + 0xc) == 3
    for i in range(14): tick(20.6 + i * 0.1)
    tick(22.1); assert read(fw + 0x48) == 6
    for i in range(20): tick(22.2 + i * 0.05)
    assert env['damage'] == [300.0] and env['parts'][1] in env['removed']
    run(7); assert read(plant + 0x48) == 4
    word(part + 0x48, 0); assert run(12, part) == 55 and env['stock'] == 1
    assert 'special' in env['labels'] and 'busy' in env['labels'] and 'plantfood_collection' in env['labels']
    print('PASS: nonmetal exclusion, native helmet detach/particle ABI, acceleration/hold/expiry, pause, PF collection/300 damage, scoped physics and ARM ABI')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('library', type=Path); check(p.parse_args().library)
