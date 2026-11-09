"""Compare the recovered touch reader with the NA ARM dispatcher in Unicorn."""

import argparse
import math
import random
import struct
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_FPEXC, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

from prepare_baseline import NATIVE, ROOT, SOURCE, SOURCE_SHA256, sha256


ENTRY = 0x009F0298
TRANSFORM = 0x009D9390
DIVIDE = 0x00B8C290
BOARD_TRANSFORM = 0x001841FC
FLOORF_PLT = 0x000E8700
CALLBACKS = {0x009F036C: 0, 0x009E8208: 1, 0x009E8378: 2,
             0x009E8528: 3, 0x009E8828: 4}
DATA = 0x02000000
PACKET = DATA + 0x100
OBJECT = DATA + 0x200
STOP = DATA + 0x400
STACK = DATA + 0xF00


def machine():
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    cpu.mem_map(DATA, 0x1000)
    cpu.reg_write(UC_ARM_REG_SP, STACK)
    cpu.reg_write(UC_ARM_REG_LR, STOP)
    cpu.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
    return cpu


def prepare(cpu, packet):
    cpu.mem_write(DATA, struct.pack('<I', PACKET))
    cpu.mem_write(PACKET, packet)
    cpu.mem_write(OBJECT, bytes([0xA5]) * 48)


def original(native, packet):
    cpu = machine()
    for page in {address & ~0xFFF for address in (ENTRY, *CALLBACKS)}:
        cpu.mem_map(page, 0x1000)
        # All selected functions reside in the first file-backed PT_LOAD.
        cpu.mem_write(page, native[page:page + 0x1000])
    prepare(cpu, packet)
    cpu.reg_write(UC_ARM_REG_R1, DATA)
    result = []

    def stop_at_handler(cpu, address, size, _):
        if address in CALLBACKS:
            stack = cpu.reg_read(UC_ARM_REG_SP)
            result.extend((CALLBACKS[address], bytes(cpu.mem_read(stack, 44))))
            cpu.emu_stop()

    cpu.hook_add(UC_HOOK_CODE, stop_at_handler)
    cpu.emu_start(ENTRY, STOP, count=128)
    route, fields = result
    return route, fields, struct.unpack('<I', cpu.mem_read(DATA, 4))[0]


def load_probe(binary, symbol):
    cpu = machine()
    with binary.open('rb') as stream:
        elf = ELFFile(stream)
        # The tiny probe is statically linked. Load its code and constants.
        segments = [segment for segment in elf.iter_segments()
                    if segment['p_type'] == 'PT_LOAD' and segment['p_vaddr'] != 0]
        start = min(segment['p_vaddr'] for segment in segments) & ~0xFFF
        end = max(segment['p_vaddr'] + segment['p_memsz'] for segment in segments)
        cpu.mem_map(start, ((end + 0xFFF) & ~0xFFF) - start)
        for segment in segments:
            cpu.mem_write(segment['p_vaddr'], segment.data())
        entry = elf.get_section_by_name('.symtab').get_symbol_by_name(symbol)[0]['st_value']
    return cpu, entry


def recovered(binary, packet, remaining=48):
    cpu, entry = load_probe(binary, 'recover_touch')
    prepare(cpu, packet)
    cpu.reg_write(UC_ARM_REG_R0, DATA)
    cpu.reg_write(UC_ARM_REG_R1, remaining)
    cpu.reg_write(UC_ARM_REG_R2, OBJECT)
    cpu.emu_start(entry, STOP, count=1024)
    assert cpu.reg_read(UC_ARM_REG_R0) <= 0xFF
    return (cpu.reg_read(UC_ARM_REG_R0), bytes(cpu.mem_read(OBJECT, 44)),
            struct.unpack('<I', cpu.mem_read(DATA, 4))[0])


def transformed(native, binary, fields, point, alias=False):
    expected = machine()
    for address in (TRANSFORM, DIVIDE):
        page = address & ~0xFFF
        expected.mem_map(page, 0x2000)
        expected.mem_write(page, native[page:page + 0x2000])
    actual, entry = load_probe(binary, 'recover_coordinates')

    x = DATA + 4
    y = x if alias else DATA + 8
    for cpu, pc, offset in ((expected, TRANSFORM, 0xB0), (actual, entry, 0)):
        cpu.mem_write(OBJECT + offset, struct.pack('<8i', *fields))
        cpu.mem_write(x, struct.pack('<2i', *point))
        cpu.reg_write(UC_ARM_REG_R0, OBJECT)
        cpu.reg_write(UC_ARM_REG_R1, x)
        cpu.reg_write(UC_ARM_REG_R2, y)
        cpu.emu_start(pc, STOP, count=1024)
    return bytes(expected.mem_read(x, 8)), bytes(actual.mem_read(x, 8))


def board_transformed(native, binary, fields, point):
    expected = machine()
    for address in (BOARD_TRANSFORM, FLOORF_PLT):
        page = address & ~0xFFF
        expected.mem_map(page, 0x1000)
        expected.mem_write(page, native[page:page + 0x1000])
    actual, entry = load_probe(binary, 'recover_board_point')
    with binary.open('rb') as stream:
        symbols = ELFFile(stream).get_section_by_name('.symtab')
        floor = symbols.get_symbol_by_name('floorf')[0]['st_value']

    def emulate_floor(cpu, address, size, _):
        # This is libm floorf's ARM soft-float boundary, shared by both runs.
        value = struct.unpack('<f', struct.pack('<I', cpu.reg_read(UC_ARM_REG_R0)))[0]
        rounded = math.floor(value) if math.isfinite(value) and value != 0.0 else value
        cpu.reg_write(UC_ARM_REG_R0, struct.unpack('<I', struct.pack('<f', rounded))[0])
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    expected.hook_add(UC_HOOK_CODE, emulate_floor, begin=FLOORF_PLT, end=FLOORF_PLT)
    actual.hook_add(UC_HOOK_CODE, emulate_floor, begin=floor, end=floor)
    expected.mem_write(OBJECT + 0x28, struct.pack('<ii', *fields[:2]))
    expected.mem_write(OBJECT + 0x678, struct.pack('<fff', *fields[2:]))
    actual.mem_write(OBJECT, struct.pack('<iifff', *fields))
    for cpu, pc in ((expected, BOARD_TRANSFORM), (actual, entry)):
        cpu.mem_write(DATA, struct.pack('<ii', *point))
        cpu.reg_write(UC_ARM_REG_R0, OBJECT)
        cpu.reg_write(UC_ARM_REG_R1, DATA)
        cpu.emu_start(pc, STOP, count=1024)
        assert cpu.reg_read(UC_ARM_REG_PC) == STOP
    return bytes(expected.mem_read(DATA, 8)), bytes(actual.mem_read(DATA, 8))


def build_probe(ndk, out):
    toolchain = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    source = ROOT / 'src/recovered/native'
    wrapper = out / 'probe.cpp'
    wrapper.write_text(
        '#include "touch_event.hpp"\n'
        'using namespace iris::recovered;\n'
        'extern "C" unsigned recover_touch(const std::uint8_t** cursor, std::size_t size, TouchEvent* event) {\n'
        '    if (!readTouchEvent(*cursor, size, *event)) return 0xff;\n'
        '    return static_cast<unsigned>(originalTouchRoute(event->phase));\n'
        '}\n'
        'extern "C" void recover_coordinates(const TouchCoordinateTransform* transform, std::int32_t* x, std::int32_t* y) {\n'
        '    transformTouchCoordinates(*transform, *x, *y);\n'
        '}\n'
        'extern "C" void recover_board_point(const BoardTouchTransform* transform, std::int32_t* point) {\n'
        '    transformBoardTouch(*transform, point[0], point[1]);\n'
        '}\n'
        'extern "C" float floorf(float value) {\n'
        '    return value; // Intercepted by the emulator.\n'
        '}\n',
        encoding='ascii',
    )
    objects = []
    for unit in (source / 'touch_event.cpp', wrapper):
        obj = out / (unit.stem + '.o')
        subprocess.run([toolchain / 'clang++.exe', '--target=armv7a-linux-androideabi21',
                        '-marm', '-std=c++17', '-O2', '-fno-stack-protector', '-I', source,
                        '-c', unit, '-o', obj], check=True)
        objects.append(obj)
    binary = out / 'recovered.elf'
    builtins = subprocess.check_output(
        [toolchain / 'clang++.exe', '--target=armv7a-linux-androideabi21', '-print-libgcc-file-name'],
        text=True,
    ).strip()
    subprocess.run([toolchain / 'ld.lld.exe', '-Ttext=0x100000', '-e', 'recover_touch',
                    '-o', binary, *objects, builtins], check=True)
    return binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ndk', required=True, type=Path)
    args = parser.parse_args()
    if sha256(SOURCE) != SOURCE_SHA256:
        parser.error('Unexpected NA input APK hash')
    with ZipFile(SOURCE) as apk:
        native = apk.read(NATIVE)
    with TemporaryDirectory() as temp:
        binary = build_probe(args.ndk, Path(temp))
        cases = 0
        for phase in (0, 1, 2, 3, 4, 5, 6, 7, 0xFFFFFFFF):
            for timestamp in (0, 0x401A000000000000, 0x7FF8000000000123):
                packet = struct.pack('<IIiiiiiQIII', 0, 0x7FFFFFFE, -113, 2048, 6, -9,
                                     1, timestamp, phase, 0xDEADBEEF, 0xDEADBEEF)
                old_route, old_fields, old_cursor = original(native, packet)
                new_route, new_fields, new_cursor = recovered(binary, packet)
                # The original stack leaves alignment bytes 28..31 unspecified.
                assert (old_route, old_cursor) == (new_route, new_cursor), phase
                assert old_fields[:28] == new_fields[:28], phase
                assert old_fields[32:] == new_fields[32:], phase
                cases += 1
        for size in range(48):
            assert recovered(binary, packet, size) == (0xFF, bytes([0xA5]) * 44, PACKET), size
        transforms = [
            ((0, 0, 640, 480, 0, 0, 1280, 960), (641, 477), False),
            ((9, -19, 3, 2, 100, 100, -2, 3), (97, 96), False),
            ((9, -19, 3, 2, 100, 100, -2, 3), (97, 96), True),
            ((9, -19, 3, 2, 100, 100, 0, 3), (97, 96), False),
            ((9, -19, 3, 2, 100, 100, 2, 0), (97, 96), False),
            ((0, 0, 1, 1, 0, 0, -1, -1), (-2**31, -2**31), False),
        ]
        rng = random.Random(0x9D9390)
        for _ in range(64):
            values = tuple(rng.randrange(-2**31, 2**31) for _ in range(10))
            transforms.append((values[:8], values[8:], False))
        for fields, point, alias in transforms:
            before, after = transformed(native, binary, fields, point, alias)
            assert before == after, (fields, point, before.hex(), after.hex())
        board_transforms = [
            ((0, 0, 1.0, 0.0, 0.0), (0, 100)),
            ((20, -5, 2.5, 3.75, -6.25), (-4, 8)),
            ((20, -5, -2.5, 3.75, -6.25), (-4, 8)),
            ((0, 0, 0.0, 0.0, 0.0), (0, -1)),
            ((0, 0, -0.0, 0.0, 0.0), (1, -1)),
            ((20, -5, float('nan'), 3.75, -6.25), (-4, 8)),
            ((0, 0, 0.001, 0.0, 0.0), (-2**31, 2**31 - 1)),
        ]
        for _ in range(64):
            fields = (rng.randint(-400, 400), rng.randint(-400, 400),
                      rng.uniform(0.1, 8), rng.uniform(-80, 80), rng.uniform(-80, 80))
            board_transforms.append((fields, (rng.randint(-400, 1400), rng.randint(-400, 1400))))
        for fields, point in board_transforms:
            before, after = board_transformed(native, binary, fields, point)
            assert before == after, (fields, point, before.hex(), after.hex())
    print(f'{cases} dispatcher comparisons, 48 truncated packets, {len(transforms)} coordinate comparisons, '
          f'and {len(board_transforms)} board-point comparisons passed')


if __name__ == '__main__':
    main()
