"""Compare an Iris recovery build against the pre-recovery Iris APK."""

import argparse
from io import BytesIO
from pathlib import Path
import sys
from zipfile import ZipFile

from prepare_baseline import NATIVE, ROOT
from recovery_compile import RECOVERED_JAVA, ROUND_THREE, recovered_descriptors


DEX_FILES = ('classes.dex', 'classes2.dex')


def classes(apk, dex_reader):
    result = {}
    for entry in DEX_FILES:
        for definition in dex_reader(apk.read(entry)).classes():
            name = definition['name']
            if name in result:
                raise ValueError(f'Duplicate DEX class {name}')
            result[name] = (entry, definition)
    return result


def declarations(definition, kind):
    excluded = 0x1000  # compiler-generated synthetic members
    if kind == 'fields':
        excluded |= 0x0002  # recovery may rename private constants
    # Includes visibility, static, abstract, native and declared-synchronized.
    flags_mask = 0x20FFF
    return {member: flags & flags_mask for member, flags, *_ in definition[kind]
            if not flags & excluded and member[1] != '<clinit>'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('previous', type=Path)
    parser.add_argument('rebuilt', type=Path)
    parser.add_argument('--aster', type=Path, default=ROOT.parent / 'PvZ2-Unline-Aster')
    parser.add_argument('--round', choices=(1, 2, 3), default=3, type=int, help='recovery round of the rebuilt APK')
    args = parser.parse_args()
    sys.path.insert(0, str(args.aster.resolve() / 'src/recovered/tools'))
    from build_dex_reference_jar import Dex

    with ZipFile(args.previous) as previous, ZipFile(args.rebuilt) as rebuilt:
        old, new = classes(previous, Dex), classes(rebuilt, Dex)
        assert old.keys() == new.keys(), 'DEX class inventory changed'
        moved = {name for name in old if old[name][0] != new[name][0]}
        families = {
            1: {'AndroidUIEventManager'},
            2: RECOVERED_JAVA.keys() - ROUND_THREE,
            3: RECOVERED_JAVA.keys(),
        }
        family = recovered_descriptors(families[args.round])
        assert moved == family, (moved - family, family - moved)
        for name in family:
            old_dex, before = old[name]
            new_dex, after = new[name]
            assert (old_dex, new_dex) == DEX_FILES, name
            for key in ('super', 'interfaces', 'flags'):
                assert before[key] == after[key], (name, key)
            for kind in ('fields', 'methods'):
                changed = declarations(before, kind).items() - declarations(after, kind).items()
                assert not changed, (name, kind, changed)

        assert previous.read(NATIVE) == rebuilt.read(NATIVE), 'Native library changed'
        with (ZipFile(BytesIO(previous.read('assets/extobb.save'))) as old_assets,
              ZipFile(BytesIO(rebuilt.read('assets/extobb.save'))) as new_assets):
            assert old_assets.namelist() == new_assets.namelist(), 'Expansion member list changed'
            for name in old_assets.namelist():
                assert old_assets.read(name) == new_assets.read(name), name
    print(f'{len(new)} DEX classes, {len(family)} rebuilt from Java. '
          'Declarations, native library, and expansion payloads checked.')


if __name__ == '__main__':
    main()
