"""Verify and unpack the local PvZ2 NA 1.6.257161 input for analysis."""

import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Plants+Vs+Zombies+2_1.6.257161na.apk'
SOURCE_SHA256 = '51af5cf9cca41b2e3ebba8b12d33156dbe7160311f1c5885d0acde8b2e62258c'
OBB = 'main.7.com.ea.game.pvz2_na.obb'
NATIVE = 'lib/armeabi-v7a/libPVZ2.so'


def sha256(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def run_log(path, *command):
    with path.open('wb') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)


def extract(archive, entry, path):
    with archive.open(entry) as source, path.open('xb') as output:
        shutil.copyfileobj(source, output)


def read_groups(path):
    with path.open('rb') as resource:
        header = struct.unpack('<28I', resource.read(112))
        if header[:2] != (int.from_bytes(b'1bsr', 'little'), 4):
            raise ValueError('Unexpected OBB header')
        count, offset, stride = header[10:13]
        if stride != 204 or offset < 112 or offset + count * stride > header[3] or header[3] > path.stat().st_size:
            raise ValueError('Invalid RSB group directory')
        resource.seek(offset)
        groups = [resource.read(stride)[:128].split(b'\0', 1)[0].decode('ascii') for _ in range(count)]
    if '' in groups or len(set(groups)) != count:
        raise ValueError('Invalid RSB group names')
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, default=SOURCE)
    parser.add_argument('--apktool', type=Path, default=ROOT / 'tools/apktool.jar')
    parser.add_argument('--build-tools', type=Path, required=True,
                        help='Android SDK Build Tools version directory containing aapt and apksigner')
    parser.add_argument('--output', type=Path, default=ROOT / 'work/baseline',
                        help='new output directory; existing analysis is never overwritten')
    args = parser.parse_args()
    apk, apktool, output = args.apk.resolve(), args.apktool.resolve(), args.output.resolve()
    sdk = args.build_tools.resolve()
    aapt = sdk / ('aapt.exe' if os.name == 'nt' else 'aapt')
    apksigner = sdk / 'lib/apksigner.jar'
    for path in (apk, apktool, aapt, apksigner):
        if not path.is_file():
            parser.error(f'File not found: {path}')
    digest = sha256(apk)
    if digest != SOURCE_SHA256:
        parser.error(f'Unexpected APK SHA-256: {digest}')
    if output.exists():
        parser.error(f'Output already exists: {output}. Specify a new --output directory.')
    output.mkdir(parents=True)
    run_log(output / 'signature.txt', 'java', '-jar', apksigner, 'verify', '--verbose', '--print-certs', apk)
    run_log(output / 'badging.txt', aapt, 'dump', 'badging', apk)

    obb = output / OBB
    database = output / 'DownloadsDB'
    with ZipFile(apk) as package:
        # Use the decoder's extracted native library below. The expansion file
        # and downloader DB live in separate ZIP containers inside the APK.
        with ZipFile(BytesIO(package.read('assets/extobb.save'))) as expansion:
            extract(expansion, OBB, obb)
        with ZipFile(BytesIO(package.read('assets/data.save'))) as data:
            extract(data, 'databases/DownloadsDB', database)

    groups = read_groups(obb)
    (output / 'rsb-groups.txt').write_text('\n'.join(groups) + '\n', encoding='utf-8')
    with sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('Invalid bundled downloader database')
        row = db.execute('SELECT FN, TOTALBYTES, STATUS FROM DownloadColumns WHERE FILEIDX = 0').fetchone()
        if row is None or row[0] != OBB:
            raise ValueError('Downloader database does not identify the bundled OBB')
    expansion_info = {'rsb_version': 4, 'groups': len(groups), 'database_expected_bytes': row[1],
                      'bundled_bytes': obb.stat().st_size, 'database_status': row[2]}
    (output / 'expansion.json').write_text(json.dumps(expansion_info, indent=2) + '\n', encoding='utf-8')
    run_log(output / 'decode.log', 'java', '-jar', apktool, 'd', '-p', output / 'framework',
            '-o', output / 'decoded', apk)
    native = output / 'decoded' / NATIVE
    files = {apk.name: apk, OBB: obb, 'DownloadsDB': database, NATIVE: native}
    inventory = {name: {'bytes': path.stat().st_size, 'sha256': sha256(path)} for name, path in files.items()}
    (output / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
