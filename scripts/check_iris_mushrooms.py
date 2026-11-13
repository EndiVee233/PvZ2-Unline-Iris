"""Exercise the compiled Sun-shroom callbacks and their native ABI."""
import argparse
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data = path.read_bytes()
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0, 0x1000000)
    uc.reg_write(UC_ARM_REG_C1_C0_2, 0xf << 20)
    uc.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    for at in range(phoff, phoff + stride * count, stride):
        kind, off, va, _, size, _, _, _ = struct.unpack_from('<8I', data, at)
        if kind == 1:
            uc.mem_write(va, data[off:off + size])
    framework, plant, props, types, node = [0xf00000 + n * 0x1000 for n in range(5)]
    name, temporary, stack, stop = 0xf05000, 0xf06000, 0xfff000, 0xf07000
    clock, app_slot, app, board = 0xf08000, 0xf09000, 0xf0a000, 0xf0b000
    bucket, slots, table, plant_type, type_name = [0xf0c000 + i * 0x1000 for i in range(5)]
    def word(at, value): uc.mem_write(at, struct.pack('<I', value))
    def read(at): return struct.unpack('<I', uc.mem_read(at, 4))[0]
    def text(at): return bytes(uc.mem_read(at, 80)).split(b'\0')[0].decode()
    word(framework + 4, plant)
    word(0xd4ec98, types)
    word(node + 0x18, 42)
    word(node + 0x1c, 2)
    word(props + 0x8c, name)
    word(0xd4ed90, clock)
    word(0xd00838, app_slot); word(app_slot, app); word(app + 0x6c0, board)
    word(board + 0xa8, 5)
    word(bucket + 4, slots); word(bucket + 8, 0)
    word(table, 0xf30000); word(table + 0x74, 0xf30010)
    word(plant_type + 4, type_name)
    uc.mem_write(type_name, b'Plant\0')
    uc.mem_write(name, b'iris_dark_sun\0')
    start, = struct.unpack_from('<I', data, 0xce5f10)
    start -= 40
    original = start + 240
    env = {'found': True, 'paused': False, 'active': set()}
    spawns, mutations, ends, frees, bursts, updates = [], [], [], [], [], []
    def result(value=0):
        uc.reg_write(UC_ARM_REG_R0, value)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    def hook(cpu, address, size, _):
        r0, r1, r2, r3 = [uc.reg_read(r) for r in
                          (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
        if address == 0x39e838:
            assert r1 == plant
            word(r0, 1); word(r0 + 4, 2); result()
        elif address == 0x13f3c4: result(props)
        elif address == 0x13dea0:
            word(r0, r2); word(r0 + 4, r3); result()
        elif address == 0xb75560:
            value = text(r1).encode() + b'\0'
            word(r0, temporary); word(temporary - 4, 0)
            uc.mem_write(temporary, value); result()
        elif address == 0xb76c4c: frees.append(r0); result()
        elif address == original:
            assert r0 == framework and r1 == 0x1234
            spawns.append(text(read(props + 0x8c))); result()
        elif address == 0x3ba2c0:
            assert r0 == framework
            ends.append(framework); result()
        elif address == 0x195248:
            assert r0 == types and text(read(r1)) == 'sunshroom_stage3'
            result(node if env['found'] else types + 4)
        elif address == 0x1a3ee4: result(2)
        elif address == 0x1a3eb4: result(7)
        elif address == 0x39df1c:
            mutations.append((r0, r1, r2, read(r3), read(r3 + 4)))
            result()
        elif address == 0x8821a8: result(0xf31000)
        elif address == 0x888b8c:
            assert r0 == 0xf31000 and r1 == 0x1f
            result(bucket)
        elif address == 0xf30000: result(plant_type)
        elif address == 0xf30010: result(int(r0 in env['active']))
        elif address == 0x3fa644: bursts.append(r0); result()
        elif address == 0x3fa754: updates.append(r0); result()
        elif address == 0x1872a8: result(int(env['paused']))
        elif address == 0xe8c10: result()
        elif address == 0x410324:
            word(framework + 8, 3); result()
        elif address == stop: uc.emu_stop()
    uc.hook_add(UC_HOOK_CODE, hook)
    def run(entry, target=framework):
        uc.reg_write(UC_ARM_REG_SP, stack)
        uc.reg_write(UC_ARM_REG_LR, stop)
        uc.reg_write(UC_ARM_REG_R0, target)
        uc.reg_write(UC_ARM_REG_R1, 0x1234)
        uc.reg_write(UC_ARM_REG_R4, 0x76543210)
        uc.emu_start(entry, stop, count=20000)
        assert uc.reg_read(UC_ARM_REG_PC) == stop
        assert uc.reg_read(UC_ARM_REG_SP) == stack
        assert uc.reg_read(UC_ARM_REG_R4) == 0x76543210
    word(plant + 0x48, 4)
    run(0x410054)
    assert spawns.pop() == 'iris_dark_sun' and not frees
    word(plant + 0x48, 5)
    run(start + 200)
    assert read(framework + 8) == 1
    run(0x410054)
    assert spawns == ['iris_dark_sun_large'] * 3
    spawns.clear()
    assert read(props + 0x8c) == name and len(frees) == 1
    uc.mem_write(name, b'sun\0')
    run(start + 200)
    assert read(framework + 8) == 3
    run(0x410054)
    assert spawns.pop() == 'sun' and len(frees) == 1
    uc.mem_write(name, b'iris_dark_sun_medium\0')
    run(start + 40)
    assert read(plant + 0x48) == 4
    assert mutations.pop() == (plant, 2, 7, 42, 2)
    env['found'] = False
    run(start + 40)
    assert not mutations
    uc.mem_write(name, b'sun\0')
    run(start + 40)
    assert len(ends) == 3 and not mutations
    # Two other puffs, an unrelated framework, an unplaced preview, and a
    # dying plant share the object registry. Only the placed, live puffs join.
    auxiliaries = [0xf18000 + n * 0x1000 for n in range(5)]
    frameworks = [0xf20000 + n * 0x1000 for n in range(5)]
    word(plant, table); word(plant + 0x60, 1)
    word(plant + 0x58, 1); word(plant + 0x5c, 1)
    word(bucket + 8, 5)
    for i, (obj, fw) in enumerate(zip(auxiliaries, frameworks)):
        word(slots + i * 32 + 8, obj)
        word(obj, table); word(obj + 0x30, fw); word(fw + 4, obj)
        word(fw, 0xce6058 if i != 2 else 0x1234)
        word(obj + 0x60, int(i != 3)); word(obj + 0x48, 3 if i == 4 else 4)
        word(obj + 0x58, i + 2); word(obj + 0x5c, 1)
        run(start + 80, fw)
    uc.mem_write(clock + 0x1c, struct.pack('<f', 10))
    run(start + 120)
    assert bursts == [framework]
    for i, fw in enumerate(frameworks):
        assert read(fw + 0x28) == int(i < 2)
    assert abs(struct.unpack('<f', uc.mem_read(frameworks[0] + 0x24, 4))[0] - 10.3) < 1e-5
    assert abs(struct.unpack('<f', uc.mem_read(frameworks[1] + 0x24, 4))[0] - 10.5) < 1e-5
    run(start + 160, frameworks[0])
    assert bursts == [framework]
    uc.mem_write(clock + 0x1c, struct.pack('<f', 11))
    env['paused'] = True
    run(start + 160, frameworks[0])
    assert bursts == [framework] and read(frameworks[0] + 0x28) == 1
    env['paused'] = False
    run(start + 160, frameworks[0]); run(start + 160, frameworks[0])
    assert bursts == [framework, frameworks[0]]
    assert read(frameworks[1] + 0x28) == 1  # no propagated fan-out
    run(start + 160, frameworks[1])
    assert bursts == [framework, frameworks[0], frameworks[1]]
    assert len(updates) == 4
    print('PASS: sun PF yield/maturation; puff delayed chain, decay reset, pause, exclusions, no fan-out; native ABI')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('library', type=Path)
    check(parser.parse_args().library)
