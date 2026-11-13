"""Emulate success, atlas exhaustion/retry, and an unrenderable glyph."""
import argparse
from pathlib import Path
import struct

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC


def check(path):
    data = path.read_bytes()
    pc = 0xA301C8
    word, = struct.unpack_from('<I', data, pc)
    displacement = (word & 0xFFFFFF) << 2
    if displacement & 0x2000000:
        displacement -= 0x4000000
    entry = pc + 8 + displacement
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    regs = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
    preserved = [UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8]
    for outcomes in ([1], [0, 1], [0, 0]):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0, 0x1000000)
        for h in range(phoff, phoff + count * stride, stride):
            kind, off, va, _, size, _, _, _ = struct.unpack_from('<8I', data, h)
            if kind == 1:
                uc.mem_write(va, data[off:off + size])
        mesh, manager, stop, stack = 0xF00000, 0xF01000, 0xF02000, 0xFFF000
        args = [mesh, 0x3F800000, 0, 0xFFFFFFFF]
        for r, v in zip(regs, args):
            uc.reg_write(r, v)
        for r in preserved:
            uc.reg_write(r, 0x12340000 + r)
        uc.reg_write(UC_ARM_REG_SP, stack)
        uc.reg_write(UC_ARM_REG_LR, stop)
        uc.mem_write(mesh + 0x30, struct.pack('<3I', 9, 0xF03000, 0xF0300C))
        calls, resets, logs = [], [], []

        def hook(cpu, address, size, _):
            if address == 0xA30310:
                assert [cpu.reg_read(r) for r in regs] == args
                if calls:
                    assert struct.unpack('<3I', cpu.mem_read(mesh + 0x30, 12)) == (0, 0xF03000, 0xF03000)
                value = outcomes[len(calls)]
                calls.append(value)
                cpu.mem_write(mesh + 0x30, struct.pack('<3I', 9, 0xF03000, 0xF0300C))
                cpu.reg_write(UC_ARM_REG_R0, value)
            elif address == 0xA311FC:
                cpu.reg_write(UC_ARM_REG_R0, manager)
            elif address == 0xA31E78:
                assert cpu.reg_read(UC_ARM_REG_R0) == manager
                resets.append(1)
            elif address == 0xE89C4:
                logs.append(1)
            else:
                return
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        uc.hook_add(UC_HOOK_CODE, hook)
        uc.emu_start(entry, stop, count=1000)
        assert calls == outcomes and len(resets) == len(outcomes) - 1
        assert len(logs) == len(outcomes) - 1
        assert uc.reg_read(UC_ARM_REG_SP) == stack
        assert all(uc.reg_read(r) == 0x12340000 + r for r in preserved)
        assert uc.reg_read(UC_ARM_REG_R0) == outcomes[-1]
        if outcomes[-1] == 0:
            assert struct.unpack('<3I', uc.mem_read(mesh + 0x30, 12)) == (0, 0xF03000, 0xF03000)
    # The allocation failure now reaches the existing false-return epilogue.
    assert struct.unpack_from('<I', data, 0xA30684)[0] == 0xEA0000A9
    print('PASS: normal layout, cache-reset retry, bounded failure, preserved ARM registers')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('library', type=Path)
    check(parser.parse_args().library)
