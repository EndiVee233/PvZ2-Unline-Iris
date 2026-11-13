"""Convert the audited CN Scaredy-shroom bank to Iris's Wwise 88 layout."""
import hashlib
import json
from pathlib import Path
import struct

from iris_future_audio import chunks, objects, pack_chunks, pack_objects, media, add_media


def convert_plant_bank(legacy_global, donor, recipe, *, external_media=None):
    legacy, source = chunks(legacy_global), chunks(donor)
    if (struct.unpack_from('<I', legacy[b'BKHD'])[0], struct.unpack_from('<I', source[b'BKHD'])[0]) != (88, 112):
        raise ValueError('Unexpected plant Wwise versions')
    if hashlib.sha256(donor).hexdigest() != recipe['sha256']:
        raise ValueError('Plant bank differs from the audited donor')
    source_nodes = objects(source)
    bank_id, = struct.unpack_from('<I', source[b'BKHD'], 4)
    header = bytearray(legacy[b'BKHD'])
    struct.pack_into('<I', header, 4, bank_id)
    result = {b'BKHD': bytes(header)}
    samples = media(source)
    for sound,data in (external_media or {}).items():
        if sound in samples and samples[sound]!=data:
            raise ValueError(f'Conflicting external Wwise media {sound}')
        samples[sound]=data
    target_ids = {sound: recipe.get('media_base', 0x71050000) + i for i, sound in enumerate(sorted(samples))}
    positions = add_media(result, {target_ids[sound]: data for sound, data in samples.items()})
    nodes = {}
    for name, record in recipe['nodes'].items():
        node = int(name)
        kind, body = source_nodes[node]
        if kind != record['kind'] or hashlib.sha256(body).hexdigest() != record['sha256']:
            raise ValueError(f'Unexpected plant sound object {node}')
        edits = [(at, size, bytes.fromhex(value)) for at, size, value in record['edits']]
        if 'media' in record:
            target = target_ids[record['media']]
            edits.append((0, record.get('media_header_size',22), struct.pack('<6IB', record.get('plugin', 0x40001), 0,
                                            target, bank_id, *positions[target], 0)))
        last = len(body)
        for at, size, replacement in sorted(edits, reverse=True):
            if at < 0 or at + size > last:
                raise ValueError('Overlapping plant audio conversion')
            body = body[:at] + replacement + body[at + size:]
            last = at
        nodes[node] = kind, body
    result[b'HIRC'] = pack_objects(nodes)
    return pack_chunks(result)


def port_scaredy_audio(legacy_global, donor):
    recipe = json.loads((Path(__file__).resolve().parents[1] / 'src/dark/scaredy-audio-v88.json').read_text())
    return convert_plant_bank(legacy_global, donor, recipe)
