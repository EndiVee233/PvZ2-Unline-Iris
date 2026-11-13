"""Exercise the compiled ARM/Thumb cower adapter against mocked engine calls."""
import argparse
from pathlib import Path
import struct

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data = path.read_bytes()
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0, 0x1000000)
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    for at in range(phoff, phoff + stride * count, stride):
        kind, off, va, _, size, _, _, _ = struct.unpack_from('<8I', data, at)
        if kind == 1:
            uc.mem_write(va, data[off:off + size])
    uc.reg_write(UC_ARM_REG_C1_C0_2, 0xf << 20)
    uc.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
    framework, plant, rig, table = 0xf00000, 0xf01000, 0xf02000, 0xf03000
    app_slot, app, board, clock = 0xf04000, 0xf05000, 0xf06000, 0xf07000
    string, stack, stop = 0xf08000, 0xfff000, 0xf09000
    def word(at, value): uc.mem_write(at, struct.pack('<I', value))
    def read(at): return struct.unpack('<I', uc.mem_read(at, 4))[0]
    def seconds(value): uc.mem_write(clock + 0x1c, struct.pack('<f', value))
    word(framework + 4, plant)
    word(plant, table)
    word(table + 0x70, 0xf0a000)
    word(rig, table + 0x200)
    word(table + 0x200 + 0x8c, 0xf0a010)
    word(0xd00838, app_slot)
    word(app_slot, app)
    word(app + 0x6c0, board)
    word(0xd4ed90, clock)
    env = {'danger': False, 'playing': False, 'paused': False}
    animations = []
    properties, actions = 0xf0d000, 0xf10000
    projectile, projectile_props, victim = 0xf11000, 0xf12000, 0xf13000
    victim_table, victim_type, parent_type = 0xf14000, 0xf15000, 0xf15100
    class_name, parent_name, projectile_label, manager = 0xf16000, 0xf16100, 0xf17000, 0xf18000
    food_calls, impacts, pushes, starts, freed = [], [], [], [], []
    query_memory = 0xf19000
    neighbor, neighbor_fw = 0xf1a000, 0xf1b000
    already_active, active_fw = 0xf1c000, 0xf1d000
    def return_value(value=0):
        uc.reg_write(UC_ARM_REG_R0, value)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    def hook(cpu, address, size, _):
        if address == 0xe8c10: return_value()
        elif address == 0x248120:
            output, mask, rect = [uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
            assert struct.unpack('<4i', uc.mem_read(rect, 16)) == (3, 1, 3, 3)
            assert mask in (1, 2)
            values = [victim] if mask == 2 else [plant, neighbor, already_active]
            pos = query_memory + (0x100 if mask == 2 else 0)
            uc.mem_write(pos, struct.pack('<'+'I'*len(values), *values))
            uc.mem_write(output, struct.pack('<3I', pos, pos + len(values)*4, pos + len(values)*4))
            return_value()
        elif address == 0xb36928:
            freed.append(uc.reg_read(UC_ARM_REG_R0)); return_value()
        elif address == 0x3fecc8:
            fw = uc.reg_read(UC_ARM_REG_R0)
            starts.append(fw); word(read(fw + 4) + 0x48, 5); return_value()
        elif address == 0xf0a030:
            return_value(int(uc.reg_read(UC_ARM_REG_R0) == already_active))
        elif address == 0x1872a8: return_value(int(env['paused']))
        elif address == 0x3feea4: return_value(int(env['danger']))
        elif address == 0x44da38: return_value(int(env['playing']))
        elif address == 0xf0a000: return_value(rig)
        elif address == 0xf0a010:
            animations.append(('idle', True)); return_value()
        elif address == 0xb363dc:
            assert uc.reg_read(UC_ARM_REG_R0) == 0x28
            return_value(framework)
        elif address == 0xb75560:
            target = uc.reg_read(UC_ARM_REG_R0)
            source = uc.reg_read(UC_ARM_REG_R1)
            raw = bytes(uc.mem_read(source, 32)).split(b'\0', 1)[0]
            word(target, string)
            word(string - 4, 0)
            uc.mem_write(string, raw + b'\0')
            return_value()
        elif address in (0x44d0b0, 0x44d220):
            text = read(uc.reg_read(UC_ARM_REG_R1))
            name = bytes(uc.mem_read(text, 32)).split(b'\0', 1)[0].decode()
            animations.append((name, address == 0x44d220)); return_value(1)
        elif address == 0xb76c4c: return_value()
        elif address == 0x13f310:
            target = uc.reg_read(UC_ARM_REG_R0)
            source = uc.reg_read(UC_ARM_REG_R2)
            uc.mem_write(target, bytes(uc.mem_read(source, 24)))
            return_value(target)
        elif address == 0x39e838:
            assert uc.reg_read(UC_ARM_REG_R1) == plant
            word(uc.reg_read(UC_ARM_REG_R0), 1)
            word(uc.reg_read(UC_ARM_REG_R0) + 4, 2)
            return_value()
        elif address == 0x13f3c4: return_value(properties)
        elif address == 0x13dea0:
            uc.mem_write(uc.reg_read(UC_ARM_REG_R0), bytes(8))
            return_value()
        elif address == 0x3cdf88:
            assert uc.reg_read(UC_ARM_REG_R0) == framework + 8
            assert uc.reg_read(UC_ARM_REG_R1) == plant
            point = uc.reg_read(UC_ARM_REG_R2)
            assert struct.unpack('<3f', uc.mem_read(point, 12)) == (200.0, 300.0, 0.0)
            assert uc.reg_read(UC_ARM_REG_R3) == 2
            assert read(uc.reg_read(UC_ARM_REG_SP)) == actions + 0x60
            food_calls.append(1)
            return_value()
        elif address == 0x413bbc: return_value(projectile_props)
        elif address == 0xf0a020: return_value(victim_type)
        elif address == 0x28b850:
            assert uc.reg_read(UC_ARM_REG_R0) == board
            return_value(manager)
        elif address == 0x67a3d8:
            assert uc.reg_read(UC_ARM_REG_R0) == manager
            assert uc.reg_read(UC_ARM_REG_R1) == victim
            point = uc.reg_read(UC_ARM_REG_R2)
            area = bool(starts)
            assert struct.unpack('<3f', uc.mem_read(point, 12)) == ((500.0 if area else 528.0), 300.0, 0.0)
            assert uc.reg_read(UC_ARM_REG_R3) == struct.unpack('<I', struct.pack('<f', 50.0 if area else 5.0))[0]
            native_stack = uc.reg_read(UC_ARM_REG_SP)
            duration = struct.unpack('<f', uc.mem_read(native_stack, 4))[0]
            assert abs(duration - (0.5 if area else 0.1)) < 1e-7
            context = read(native_stack + 4)
            assert bytes(uc.mem_read(context, 8)) == bytes(8)
            assert bytes(uc.mem_read(read(context + 8), 1)) == b'\0'
            assert read(context + 12) == 0xccbfd8
            assert bytes(uc.mem_read(context + 16, 24)) == bytes(24)
            assert read(native_stack + 8) == 1
            pushes.append(1)
            return_value()
        elif address == 0x489930:
            assert uc.reg_read(UC_ARM_REG_R0) == projectile
            assert uc.reg_read(UC_ARM_REG_R1) == victim
            impacts.append(1)
            return_value(1)
    uc.hook_add(UC_HOOK_CODE, hook)
    preserved = [UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11]
    def run(pc, arg=framework):
        uc.reg_write(UC_ARM_REG_SP, stack)
        uc.reg_write(UC_ARM_REG_LR, stop)
        uc.reg_write(UC_ARM_REG_R0, arg)
        for register in preserved: uc.reg_write(register, 0x12340000 + register)
        uc.emu_start(pc, stop, count=5000)
        assert uc.reg_read(UC_ARM_REG_PC) == stop
        assert uc.reg_read(UC_ARM_REG_SP) == stack
        assert all(uc.reg_read(register) == 0x12340000 + register for register in preserved)
    # Enter the actual factory call site, then stop where it would continue.
    branch = read(0x3fe9fc)
    delta = (branch & 0xffffff) << 2
    if delta & 0x2000000: delta -= 0x4000000
    allocator = 0x3fe9fc + 8 + delta
    run(allocator, 0x20)
    assert read(framework + 0x20) == read(framework + 0x24) == 0
    assert read(0x3feaa0) == 0xe3a03028
    word(plant + 0x48, 4)
    seconds(10)
    run(0x3fedd8)
    assert not animations
    env['danger'] = True
    run(0x3fedd8)
    assert animations[-1] == ('hide', False) and read(plant + 0x48) == 6
    env['playing'] = True
    run(0x3fedd8)
    assert len(animations) == 1
    env['playing'] = False
    run(0x3fedd8)
    assert animations[-1] == ('hide_idle', True)
    env['danger'] = False
    seconds(10.9)
    run(0x3fedd8)
    assert len(animations) == 2
    env['paused'] = True
    seconds(20)
    run(0x3fedd8)
    assert len(animations) == 2
    env['paused'] = False
    seconds(11.1)
    run(0x3fedd8)
    assert animations[-1] == ('hide_end', False) and read(plant + 0x48) == 6
    env['playing'] = True
    run(0x3fedd8)
    assert read(plant + 0x48) == 6
    env['playing'] = False
    run(0x3fedd8)
    assert animations[-1] == ('idle', True) and read(plant + 0x48) == 4
    # New danger interrupts rising, while native special states are preserved.
    env['danger'] = True
    run(0x3fedd8)
    run(0x3fedd8)
    env['danger'] = False
    seconds(13)
    run(0x3fedd8)
    assert animations[-1] == ('hide_end', False)
    env['danger'] = True
    run(0x3fedd8)
    assert animations[-1] == ('hide', False)
    word(plant + 0x48, 7)
    run(0x3fedd8)
    assert read(plant + 0x48) == 7 and read(framework + 0x24) == 0
    # An existing cowering save has no transient phase yet.
    word(plant + 0x48, 6)
    run(0x3fedd8)
    assert animations[-1] == ('hide_idle', True)
    damage_stub = read(0xce6508)
    source, target = 0xf0b000, 0xf0c000
    for state, phase, flags, damage, expected in [
        (4, 0, 0, 100.0, 100.0), (6, 1, 0, 100.0, 100.0),
        (6, 2, 0, 100.0, 90.0), (6, 3, 0, 100.0, 90.0),
        (6, 2, 2, 100.0, 100.0), (7, 2, 0, 100.0, 100.0),
        (6, 2, 0, -50.0, -50.0),
    ]:
        word(plant + 0x48, state)
        word(framework + 0x24, phase)
        packet = struct.pack('<If4I', 0x12345, damage, flags, 0x56789, 0x56791, 0x56791)
        uc.mem_write(source, packet)
        uc.reg_write(UC_ARM_REG_R1, framework)
        uc.reg_write(UC_ARM_REG_R2, source)
        run(damage_stub, target)
        assert struct.unpack('<f', uc.mem_read(target + 4, 4))[0] == expected
        assert bytes(uc.mem_read(source, 24)) == packet
        assert bytes(uc.mem_read(target, 4)) == packet[:4]
        assert bytes(uc.mem_read(target + 8, 16)) == packet[8:]
    uc.mem_write(plant + 0x10, struct.pack('<2f', 200, 300))
    word(plant + 0x44, 2)
    word(properties + 0x30, actions)
    word(properties + 0x34, actions + 2 * 0x60)
    run(0x3ff0fc)
    assert food_calls == [1]
    word(properties + 0x34, actions + 0x60)
    run(0x3ff0fc)
    assert food_calls == [1]  # missing action never falls back to ordinary spores
    word(projectile + 0x10, projectile_props)
    word(projectile_props + 0x80, projectile_label)
    uc.mem_write(projectile_label, b'iris_scaredy_plantfood\0')
    word(victim, victim_table)
    word(victim_table, 0xf0a020)
    word(victim_type + 4, class_name)
    word(victim_type + 8, parent_type)
    word(parent_type + 4, parent_name)
    word(parent_type + 8, 0)
    uc.mem_write(class_name, b'ZombieBasic\0')
    uc.mem_write(parent_name, b'Zombie\0')
    uc.mem_write(victim + 0x10, struct.pack('<2f', 400, 300))
    impact_stub = read(0xce8984)
    def hit():
        uc.reg_write(UC_ARM_REG_R1, victim)
        run(impact_stub, projectile)
        assert uc.reg_read(UC_ARM_REG_R0) == 1
    hit()
    assert len(pushes) == len(impacts) == 1
    uc.mem_write(class_name, b'ZombieGargantuarMech\0')
    hit()
    assert len(pushes) == 1 and len(impacts) == 2
    uc.mem_write(class_name, b'GridItem\0')
    word(victim_type + 8, 0)
    hit()
    assert len(pushes) == 1 and len(impacts) == 3
    uc.mem_write(class_name, b'ZombieBasic\0')
    word(victim_type + 8, parent_type)
    uc.mem_write(projectile_label, b'animation\0')
    hit()
    assert len(pushes) == 1 and len(impacts) == 4
    uc.mem_write(projectile_label, b'iris_scaredy_plantfood\0')
    word(projectile + 0x10, 0)
    hit()
    assert len(pushes) == 2 and len(impacts) == 5
    assert read(projectile + 0x10) == projectile_props
    word(plant + 0x58, 2); word(plant + 0x5c, 4); word(plant + 0x48, 6)
    word(table + 0x74, 0xf0a030)
    for obj, fw in ((neighbor, neighbor_fw), (already_active, active_fw)):
        word(obj, table); word(obj + 0x30, fw); word(obj + 0x60, 1)
        word(obj + 0x48, 4); word(fw, 0xce6458); word(fw + 4, obj)
    run(read(0xce64ec))
    assert starts == [framework, neighbor_fw]
    assert len(pushes) == 3 and len(freed) == 2
    assert read(plant + 0x48) == read(neighbor + 0x48) == 5
    assert read(already_active + 0x48) == 4
    print('PASS: cower/damage, separate PF action, projectile knockback, giant/grid exclusion, native collision return, ARM ABI')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('library', type=Path)
    check(parser.parse_args().library)
