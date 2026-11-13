"""Exercise the actual ARM potion factories, saved stacks and native hooks."""
import argparse
from pathlib import Path
import struct
from native_payload import registration_payload
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    raw = path.read_bytes(); u = Uc(UC_ARCH_ARM, UC_MODE_ARM); u.mem_map(0, 0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2, 0xf << 20); u.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
    ph = struct.unpack_from('<I', raw, 28)[0]; stride, count = struct.unpack_from('<HH', raw, 42)
    for h in range(ph, ph + stride * count, stride):
        kind, off, va, _, size, _, _, _ = struct.unpack_from('<8I', raw, h)
        if kind == 1: u.mem_write(va, raw[off:off + size])
    entry = registration_payload(raw, 0x282388, 'IrisSpeedPotion')
    def file_offset(va):
        for h in range(ph, ph + stride * count, stride):
            kind, off, start, _, size, _, _, _ = struct.unpack_from('<8I', raw, h)
            if kind == 1 and start <= va < start + size: return off + va - start
        raise ValueError(hex(va))
    modes = 0
    while struct.unpack_from('<I', raw, file_offset(entry + modes * 40))[0] == 0xe92d401f: modes += 1
    trampoline = entry + modes * 40
    def word(p, v): u.mem_write(p, struct.pack('<I', v))
    def read(p): return struct.unpack('<I', u.mem_read(p, 4))[0]
    def fl(p, v): u.mem_write(p, struct.pack('<f', v))
    def num(p): return struct.unpack('<f', u.mem_read(p, 4))[0]
    def txt(p): return bytes(u.mem_read(p, 100)).split(b'\0')[0].decode()
    parent, registry, reflect, ptype, desc, textslot, stop = [0xf00000 + i * 0x1000 for i in range(7)]
    appslot, app, board, clock, zombie, hit, vec, rig = [0xf10000 + i * 0x1000 for i in range(8)]
    word(registry, 0xf30000); word(0xf3000c, 0xf40000); word(reflect, 0xf31000)
    for o, fn in ((0x24, 0xf40010), (0x28, 0xf40020), (0x14, 0xf40030), (0x2c, 0xf40040), (0x20, 0xf40050)):
        word(0xf31000 + o, fn)
    word(ptype, 0xf32000); word(0xf32034, 0xf40060)
    word(0xd00838, appslot); word(appslot, app); word(app + 0x6c0, board); word(board + 0xa8, 5)
    word(0xd4ed90, clock); word(0xd008bc, appslot + 0x100); word(appslot + 0x100, 0)
    word(zombie, 0xf34000); word(0xf34000, 0xf40080)
    word(parent + 4, parent + 0x100); u.mem_write(parent + 0x100, b'Zombie\0')
    word(zombie + 8, 77); word(zombie + 12, 1); word(zombie + 0x40, 79); word(zombie + 0x44, 1)
    word(hit, zombie); fl(hit + 4, 50)
    env = {'heap': 0xf50000, 'registered': [], 'fields': [], 'owner': 0, 'damage': [],
           'removed': [], 'paused': False, 'rig_scale': [], 'objects': {77: zombie, 79: rig}, 'jars': [], 'rng_bounds': [], 'sounds': [], 'module': 0, 'updates': 0}
    def alloc(size):
        p = env['heap']; env['heap'] += 0x400; u.mem_write(p, bytes(size)); return p
    def ret(value=0): u.reg_write(UC_ARM_REG_R0, value); u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
    def hook(cpu, pc, size, data):
        r0, r1, r2, r3 = [u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
        if pc == trampoline: ret()
        elif pc == trampoline + 12:
            env['damage'].append(num(r1 + 4)); env['last_damage_bytes'] = bytes(u.mem_read(r1, 24)).hex(); ret(123)
        elif pc in (trampoline + 24, trampoline + 36): ret(0x3f800000)
        elif pc == trampoline + 48: env['updates'] += 1; ret()
        elif pc == 0x2d8f48: raise AssertionError('unsafe native module lookup')
        elif pc == 0xf40090: ret(r0 == env['module'])
        elif pc == 0xb363dc: ret(alloc(r0))
        elif pc in (0x894ca0, 0xb76c4c, 0xb36928, 0xe8c10, 0x282b78): ret()
        elif pc in (0x283394, 0x134100, 0x1341d8): ret(parent)
        elif pc == 0x895608: assert txt(r1) in ('IrisSpeedPotion', 'IrisToughnessPotion', 'IrisPotionBuff', 'ZombiePotionModuleProperties', 'ZombiePotionModule'); ret()
        elif pc == 0x851728: ret(0xf35000)
        elif pc == 0x851920: ret(registry)
        elif pc == 0xb75560:
            u.mem_write(textslot, txt(r1).encode() + b'\0'); word(textslot - 4, 100); word(r0, textslot); ret()
        elif pc == 0xf40000: env['registered'].append((txt(read(r1)), r3)); ret()
        elif pc == 0xf40010: assert txt(read(r1)) in ('GridItem', 'Zombie', 'Effect_PopAnim', 'LevelModule', 'LevelModuleProperties'); ret(ptype)
        elif pc == 0xf40060: ret(123)
        elif pc == 0xf40020: assert r2 == 123; ret()
        elif pc == 0xf40030: assert r1 in (6, 8); ret(r1)
        elif pc == 0xf40040: env['fields'].append((txt(read(r2)), r3)); ret()
        elif pc == 0xf40050: ret(456)
        elif pc == 0x282ae4: word(r0 + 8, r0); word(r0 + 12, 1); ret(r0)
        elif pc == 0xf40080: ret(parent)
        elif pc == 0x248120:
            assert r1 in (4, 5)
            items = ([env['owner']] if env['owner'] else []) + (env['jars'] if r1 == 5 else [])
            word(r0, vec); word(r0 + 4, vec + 4 * len(items))
            for i, p in enumerate(items): word(vec + 4 * i, p)
            ret()
        elif pc == 0x17a8c4:
            kind = txt(read(r1)); p = alloc(0x74)
            if kind == 'iris_potion_buff': word(p, read(0xf80e98)); word(p + 0x50, 3); env['owner'] = p
            else:
                assert kind in ('zombiepotion_speed', 'zombiepotion_toughness')
                number = 1 if kind.endswith('speed') else 2; word(p, read(0xf80e90 + 4 * (number - 1)))
                word(p + 0x50, number); word(p + 0x44, r2); word(p + 0x48, r3); env['jars'].append(p)
            ret(p)
        elif pc == 0x7a3e90: assert r0 > 0; env['rng_bounds'].append(r0); ret(0)
        elif pc == 0x13dea0: word(r0, r2); word(r0 + 4, r3); ret()
        elif pc == 0x8821a8: ret(0xf36000)
        elif pc == 0x8890c4: word(r0, read(r2)); word(r0 + 4, read(r2 + 4)); ret()
        elif pc == 0x888b8c: ret(0xf37000)
        elif pc == 0x884378: ret(env['objects'].get(read(r1), 0))
        elif pc == 0x5ee918: env['rig_scale'].append(struct.unpack('<f', struct.pack('<I', r1))[0]); ret()
        elif pc == 0x1a4280: env['sounds'].append(txt(read(r1))); ret()
        elif pc == 0x1872a8: ret(env['paused'])
        elif pc == 0x2708b4: env['removed'].append(r0); ret()
        elif pc == stop: u.emu_stop()
    u.hook_add(UC_HOOK_CODE, hook)
    def run(mode, *args):
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), list(args) + [0] * 4): u.reg_write(reg, value)
        u.reg_write(UC_ARM_REG_SP, 0xfff000); u.reg_write(UC_ARM_REG_LR, stop); u.reg_write(UC_ARM_REG_R4, 0x12345678)
        u.emu_start(entry + mode * 40, stop, count=150000)
        assert u.reg_read(UC_ARM_REG_PC) == stop and u.reg_read(UC_ARM_REG_SP) == 0xfff000 and u.reg_read(UC_ARM_REG_R4) == 0x12345678
        return u.reg_read(UC_ARM_REG_R0)
    run(0); run(0); assert len(env['registered']) == (5 if modes == 33 else 3)
    assert all(size == 0x74 for _, size in env['registered'][:3])
    for mode in (7, 8, 9): run(mode, reflect, desc)
    assert len(env['fields']) == 21
    speed = run(1); run(10, speed); assert num(speed + 0x40) == 50 and read(speed + 0x38) == 3
    fl(hit + 4, 20); run(12, speed, hit); assert num(speed + 0x40) == 30 and not env['owner']
    fl(hit + 4, 30); run(12, speed, hit); owner = env['owner']; assert owner and read(owner + 0x68) == 1
    assert run(17, zombie + 0x150) == 0x3fc00000 and read(zombie + 0x150) == 0
    run(12, speed, hit); assert read(owner + 0x68) == 1  # Already consumed jars cannot fire twice.
    for level in (2, 3, 3):
        p = run(1); run(10, p); fl(hit + 4, 50); run(12, p, hit); assert read(owner + 0x68) == level
    assert run(18, zombie + 0x150) == 0x40200000
    word(zombie + 0x150, 2); assert run(17, zombie + 0x150) == 0; word(zombie + 0x150, 0)
    fl(hit + 4, 100)
    for level, factor in ((1, .85), (2, .70), (3, .55), (3, .55)):
        p = run(2); run(10, p); run(12, p, hit); assert read(owner + 0x6c) == level
        result = run(16, zombie, hit)
        assert result == 123 and abs(env['damage'][-1] - 100 * factor) < .001, (level, result, env['damage'], read(owner + 0x6c), env['last_damage_bytes'])
        assert num(hit + 4) == 100  # Shared caller damage remains untouched.
    word(zombie + 0x48, 4); run(11, owner); assert owner in env['removed']
    env['owner'] = 0; assert run(17, zombie + 0x150) == 0x3f800000
    run(16, zombie, hit); assert env['damage'][-1] == 100
    if modes == 33:
        run(23, reflect, desc); run(24, reflect, desc); assert len(env['fields']) == 28
        props = run(19); module = run(20); env['module'] = module
        manager = board + 0x800; entries = manager + 0x100; word(board + 0x62c, manager)
        word(manager + 4, entries); word(manager + 8, entries + 16)
        word(entries, 999); word(entries + 4, 1); word(entries + 8, 85); word(entries + 12, 1)
        env['objects'][85] = module; word(read(module) + 0x10, 0xf40090)
        env['objects'][84] = props; word(module + 0x10, 84); word(module + 0x14, 1)
        word(props + 0x20, 1); word(props + 0x24, 2); fl(props + 0x28, 2); fl(props + 0x2c, 2)
        fl(clock + 0x1c, 0); run(26, board); assert len(env['jars']) == 1 and read(module + 0x1c) == 1
        run(26, board); assert len(env['jars']) == 1
        fl(clock + 0x1c, 2.1); env['paused'] = True; run(26, board); assert len(env['jars']) == 1
        env['paused'] = False; run(26, board); assert len(env['jars']) == 2
        fl(clock + 0x1c, 5); run(26, board); assert len(env['jars']) == 2
        env['module'] = 0; run(26, board); assert len(env['jars']) == 2 and env['updates'] == 6
        assert (read(env['jars'][0] + 0x44), read(env['jars'][1] + 0x44)) == (8, 7)
        assert read(env['jars'][0] + 0x48) == read(env['jars'][1] + 0x48) == 0
        assert 1800 in env['rng_bounds'] and 1620 in env['rng_bounds']
        print('PASS: potion module ABI/schema, authored initial count, saved timer, pause, cap and weighted right-edge row selection')
    print('PASS: potion native ABI/schema, fatal consumption, independent capped stacks, 1.5/2/2.5 speed, freeze, 0.85/0.70/0.55 pre-armor damage, input ownership and death cleanup')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('library', type=Path); check(parser.parse_args().library)
