"""Back up and verify restoration of Iris saves on the local rooted WSA."""

import argparse
from datetime import datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import tarfile

from prepare_baseline import ROOT


PACKAGE = 'com.ea.game.pvz2_na'
STORE = ROOT / 'work/private-wsa-backups'
ACTIVE = STORE / 'ACTIVE.json'
DEVICE = '127.0.0.1:58526'
DEFAULT_ADB = ROOT.parent / 'PvZ2-Unline-Aster/tools/platform-tools/adb.exe'
TREES = {
    'internal': (f'/data/user/0/{PACKAGE}', ('files', 'databases', 'shared_prefs'), ('files/expansion',)),
    'external': (f'/data/media/0/Android/data/{PACKAGE}', ('files',), ()),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(raw, roots, excludes):
    if not raw:
        return {}
    result = {}
    with tarfile.open(fileobj=BytesIO(raw)) as archive:
        for member in archive:
            name = member.name
            path = PurePosixPath(name)
            if (path.is_absolute() or '..' in path.parts or str(path) != name or name in result
                    or not path.parts or path.parts[0] not in roots
                    or any(name == skip or name.startswith(skip + '/') for skip in excludes)
                    or not (member.isdir() or member.isfile())):
                raise ValueError(f'Unexpected archive entry: {name}')
            result[name] = {
                'type': 'dir' if member.isdir() else 'file',
                'uid': member.uid, 'gid': member.gid, 'mode': member.mode,
                'sha256': digest(archive.extractfile(member).read()) if member.isfile() else None,
            }
    return result


class Wsa:
    def __init__(self, adb):
        self.adb = adb

    def run(self, *args):
        result = subprocess.run([self.adb, '-s', DEVICE, *args], capture_output=True, timeout=120)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace').strip() or 'WSA command failed')
        return result.stdout

    def root(self, command, *, binary=False):
        transport = ('exec-out',) if binary else ('shell', '-T')
        return self.run(*transport, f'su -c {shlex.quote(command)}')

    def stop(self):
        self.run('shell', 'am', 'force-stop', PACKAGE)

    def capture(self, tree):
        base, roots, excludes = TREES[tree]
        selection = ' '.join(shlex.quote(path) for path in roots)
        exclusions = ' '.join(f'--exclude={shlex.quote(path)}' for path in excludes)
        command = (f'if [ -d {base} ]; then cd {base} || exit; '
                   f'set --; for p in {selection}; do if [ -e "$p" ]; then set -- "$@" "$p"; fi; done; '
                   f'if [ "$#" -gt 0 ]; then tar --numeric-owner {exclusions} -cf - "$@"; fi; fi')
        raw = self.root(command, binary=True)
        if raw and (len(raw) % 512 or not raw.endswith(bytes(1024))):
            raise ValueError('Incomplete archive')
        return raw, inventory(raw, roots, excludes)

    def restore_tree(self, tree, archive, expected, current):
        base = TREES[tree][0]
        if archive.stat().st_size:
            remote = f'/data/local/tmp/iris-{tree}-restore-{stamp()}.tar'
            self.run('push', str(archive), remote)
            try:
                self.root(f'mkdir -p {base} && tar --numeric-owner -xf {remote} -C {base}')
            finally:
                self.root(f'rm -f {remote}')
        for name in sorted(current.keys() - expected.keys(), key=lambda value: value.count('/'), reverse=True):
            command = 'rmdir' if current[name]['type'] == 'dir' else 'rm -f'
            self.root(f'{command} -- {shlex.quote(base + "/" + name)}')
        if self.capture(tree)[1] != expected:
            raise ValueError(f'{tree} files differ after restoring')


def stamp():
    return datetime.now().strftime('%Y%m%d-%H%M%S-%f')


def save_state(state):
    temp = ACTIVE.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2), encoding='utf-8')
    temp.replace(ACTIVE)


def verified_backup(state):
    folder = (STORE / state['snapshot']).resolve()
    if folder.parent != STORE.resolve() or state['package'] != PACKAGE:
        raise ValueError('Snapshot location or package mismatch')
    snapshots = {}
    for tree, (_, roots, excludes) in TREES.items():
        archive = folder / f'{tree}.tar'
        raw = archive.read_bytes()
        expected = state['trees'][tree]['entries']
        if digest(raw) != state['trees'][tree]['sha256'] or inventory(raw, roots, excludes) != expected:
            raise ValueError(f'{tree} snapshot failed verification')
        snapshots[tree] = archive, expected
    return folder, snapshots


def backup(wsa, *, current=False):
    STORE.mkdir(parents=True, exist_ok=True)
    state = json.loads(ACTIVE.read_text(encoding='utf-8')) if ACTIVE.exists() else {}
    if current or state.get('status') != 'pending_restore':
        previous = state
        wsa.stop()
        snapshots = {tree: wsa.capture(tree) for tree in TREES}
        if 'files/No_Backup/pp.dat' not in snapshots['internal'][1]:
            raise ValueError('Iris player save missing')
        folder = STORE / (stamp() + '-iris-acceptance')
        folder.mkdir()
        for tree, (raw, _) in snapshots.items():
            (folder / f'{tree}.tar').write_bytes(raw)
        state = {'snapshot': folder.name, 'status': 'pending_restore', 'package': PACKAGE,
                 'trees': {tree: {'sha256': digest(raw), 'entries': entries}
                           for tree, (raw, entries) in snapshots.items()}}
        _, snapshots = verified_backup(state)
        if previous.get('status') == 'pending_restore':
            previous_folder, _ = verified_backup(previous)
            (previous_folder / 'manifest.json').write_text(json.dumps(previous, indent=2), encoding='utf-8')
        save_state(state)
    else:
        _, snapshots = verified_backup(state)
    print(f'Backup verified: {count_files(snapshots)} files ({state["snapshot"]})')


def count_files(snapshots):
    return sum(entry['type'] == 'file' for _, entries in snapshots.values() for entry in entries.values())


def restore(wsa):
    state = json.loads(ACTIVE.read_text(encoding='utf-8'))
    if state.get('status') != 'pending_restore':
        raise ValueError('No pending Iris backup')
    folder, snapshots = verified_backup(state)
    wsa.stop()
    current = {tree: wsa.capture(tree) for tree in TREES}
    suffix = stamp()
    for tree, (raw, _) in current.items():
        (folder / f'{tree}-before-restore-{suffix}.tar').write_bytes(raw)
    for tree, (archive, expected) in snapshots.items():
        wsa.restore_tree(tree, archive, expected, current[tree][1])
    state.update(status='restored', restored_at=stamp())
    save_state(state)
    print(f'Restore verified: {count_files(snapshots)} files; Iris is stopped')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('backup', 'restore'))
    parser.add_argument('--current', action='store_true',
                        help='Back up current progress while retaining the previous snapshot')
    parser.add_argument('--adb', type=Path, default=DEFAULT_ADB)
    args = parser.parse_args()
    if args.current and args.action != 'backup':
        parser.error('--current is only valid for backup')
    wsa = Wsa(args.adb)
    if args.action == 'backup':
        backup(wsa, current=args.current)
    else:
        restore(wsa)
