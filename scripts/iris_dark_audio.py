"""Port Aster's Dark Ages music tree to Iris's Wwise 88 engine."""
import hashlib
import json
import struct
from pathlib import Path

from iris_future_audio import chunks, objects, pack_chunks, pack_objects, add_media, GLOBAL

DARK_MUSIC = r'SOUNDBANKS\IRIS_DARK_MUSIC.BNK'
BANK_ID = 0xf16963f7  # Wwise FNV-1("iris_dark_music")
WORLD_SELECTOR = 144683016
DARK_ROOT = 556668047
DARK_SWITCH = 155171117  # Wwise FNV-1("darkages")


def port_dark_music(legacy_raw, aster_raw, stream):
    recipe = json.loads((Path(__file__).resolve().parents[1] / 'src/dark/music-v88.json').read_text())
    legacy, donor = chunks(legacy_raw), chunks(aster_raw)
    if (struct.unpack_from('<I', legacy[b'BKHD'])[0], struct.unpack_from('<I', donor[b'BKHD'])[0]) != (88, 112):
        raise ValueError('Unexpected Dark Ages Wwise versions')
    original, source = objects(legacy), objects(donor)
    media_ids = {sound: 0x71041000 + i for i, sound in enumerate(sorted({
        r['media'] for r in recipe['nodes'].values() if 'media' in r}))}
    header = bytearray(legacy[b'BKHD'])
    struct.pack_into('<I', header, 4, BANK_ID)
    music = {b'BKHD': bytes(header)}
    locations = add_media(music, {media_ids[sound]: stream(sound) for sound in media_ids})
    additions = {}
    for name, record in recipe['nodes'].items():
        node = int(name)
        kind, body = source[node]
        if kind != record['kind'] or hashlib.sha256(body).hexdigest() != record['sha256'] or node in original:
            raise ValueError(f'Unexpected Aster music object {node}')
        edits = [(at, size, bytes.fromhex(value)) for at, size, value in record['edits']]
        if 'media' in record:
            sound = media_ids[record['media']]
            offset, size = record['source']
            # Embedded Vorbis source, with the v88 32-bit storage field and
            # explicit bank/offset/size. No loose streaming path is required.
            edits.append((offset, size, struct.pack('<6IB', 0x40001, 0, sound,
                                                    BANK_ID, *locations[sound], 0)))
            edits.append((record['clip_source'], 4, struct.pack('<I', sound)))
        last = len(body)
        for at, size, value in sorted(edits, reverse=True):
            if at < 0 or at + size > last:
                raise ValueError('Overlapping Dark Ages music conversion')
            body = body[:at] + value + body[at + size:]
            last = at
        additions[node] = kind, body

    # Add only the Dark Ages world selection; all existing world mappings,
    # gameplay events and their stop/pause behavior remain original.
    kind, body = original[WORLD_SELECTOR]
    switch = recipe['world_switch']
    if kind != 12 or hashlib.sha256(body).hexdigest() != switch['sha256']:
        raise ValueError('Unexpected Iris world music selector')
    count_at, size_at, tree_at = (switch[n] for n in ('ulNumChilds', 'uTreeDataSize', 'key'))
    count, = struct.unpack_from('<I', body, count_at)
    tree_size, = struct.unpack_from('<I', body, size_at)
    tree = bytearray(body[tree_at:tree_at + tree_size])
    if len(tree) != tree_size or struct.unpack_from('<HH', tree, 4) != (1, count):
        raise ValueError('Unexpected Iris world music decision tree')
    leaves = [bytes(tree[i:i + 12]) for i in range(12, len(tree), 12)]
    leaves.append(struct.pack('<IIHH', DARK_SWITCH, DARK_ROOT, 50, 100))
    leaves.sort(key=lambda leaf: struct.unpack_from('<I', leaf)[0])
    struct.pack_into('<H', tree, 6, count + 1)
    tree = bytes(tree[:12]) + b''.join(leaves)
    edits = [(tree_at, tree_size, tree), (size_at, 4, struct.pack('<I', len(tree))),
             (count_at + 4 + count * 4, 0, struct.pack('<I', DARK_ROOT)),
             (count_at, 4, struct.pack('<I', count + 1))]
    for at, size, value in sorted(edits, reverse=True):
        body = body[:at] + value + body[at + size:]
    ordered = {}
    for node, value in original.items():
        if node == WORLD_SELECTOR:
            ordered.update(additions)
            value = kind, body
        ordered[node] = value
    if any(ordered[n] != v for n, v in original.items() if n != WORLD_SELECTOR):
        raise ValueError('Dark Ages changed unrelated audio')
    legacy[b'HIRC'] = pack_objects(ordered)
    return pack_chunks(legacy), pack_chunks(music)
