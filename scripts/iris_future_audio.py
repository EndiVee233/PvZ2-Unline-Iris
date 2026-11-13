"""Rebuild Far Future audio with the Wwise 88 object layout used by Iris."""

import struct


GLOBAL = r'SOUNDBANKS\GLOBAL_DATA.BNK'
MUSIC = r'SOUNDBANKS\FUTURE_MUSIC.BNK'
CITRON = r'SOUNDBANKS\PLANT_CITRON.BNK'
GARGANTUAR = r'SOUNDBANKS\ZOMBIE_FUTURE_GARGANTUAR.BNK'
CITRON_IMPACT = 'Play_Plant_Future_Citron_Impact'

# Descendants of the Far Future music switch (191446208) in both Aster and ROW 2.1.1.
FUTURE_MUSIC_NODES = frozenset((
    2107766, 12242659, 15214101, 16210366, 21869586, 43307336, 87722657, 102054908,
    128449636, 143059153, 191446208, 193001837, 204588385, 228077238, 258844502,
    290992915, 364237837, 411675508, 448694764, 478322970, 492223335, 513677692,
    513862357, 515037617, 520567831, 521677082, 522279922, 540918402, 589190093,
    595598081, 596083692, 611021714, 635736825, 644881747, 673423390, 676578244,
    680867433, 689465511, 706958481, 714543190, 725594292, 751321533, 764306998,
    779639429, 796874455, 811504888, 823067418, 838911545, 859470512, 864273438,
    886436396, 930102709, 937745013, 972531281, 997211339, 1037115027, 1046821695,
    1049714937, 1067395160,
))
# Existing v88 sound objects and their corresponding impact samples in Aster.
CITRON_SAMPLES = {
    77619267: (562199942, 325631480),
    567463436: (964465786, 268314011),
    1044363796: (197808665, 197808665),
}


def chunks(data):
    parts = {}
    offset = 0
    while offset < len(data):
        tag, length = struct.unpack_from('<4sI', data, offset)
        start = offset + 8
        offset = start + length
        if tag in parts or offset > len(data):
            raise ValueError('Invalid Wwise bank chunk')
        parts[tag] = data[start:offset]
    return parts


def pack_chunks(parts):
    return b''.join(struct.pack('<4sI', tag, len(payload)) + payload for tag, payload in parts.items())


def objects(parts):
    hirc = parts[b'HIRC']
    offset = 4
    nodes = {}
    for _ in range(struct.unpack_from('<I', hirc)[0]):
        kind, size, node = struct.unpack_from('<BII', hirc, offset)
        end = offset + 5 + size
        if size < 4 or node in nodes or end > len(hirc):
            raise ValueError('Invalid Wwise HIRC object')
        nodes[node] = kind, hirc[offset + 9:end]
        offset = end
    if offset != len(hirc):
        raise ValueError('Invalid Wwise HIRC size')
    return nodes


def pack_objects(nodes):
    return struct.pack('<I', len(nodes)) + b''.join(
        struct.pack('<BII', kind, len(payload) + 4, node) + payload for node, (kind, payload) in nodes.items()
    )


def media(parts):
    data = parts[b'DATA']
    result = {}
    for sound, offset, size in struct.iter_unpack('<III', parts[b'DIDX']):
        sample = data[offset:offset + size]
        if size < 12 or len(sample) != size or sample[:4] != b'RIFF':
            raise ValueError(f'Invalid Wwise media {sound}')
        result[sound] = sample
    return result


def add_media(parts, additions):
    index = bytearray(parts.get(b'DIDX', b''))
    data = bytearray(parts.get(b'DATA', b''))
    locations = {sound: (offset, size) for sound, offset, size in struct.iter_unpack('<III', index)}
    for sound, sample in additions.items():
        if sound in locations:
            raise ValueError(f'Duplicate Wwise media ID {sound}')
        data.extend(bytes(-len(data) % 16))
        locations[sound] = len(data), len(sample)
        index.extend(struct.pack('<III', sound, *locations[sound]))
        data.extend(sample)
    parts[b'DIDX'] = bytes(index)
    parts[b'DATA'] = bytes(data)
    return locations


def replace_music(legacy, legacy_music, donor, donor_music, stream):
    music = chunks(legacy_music)
    bank_id, = struct.unpack_from('<I', music[b'BKHD'], 4)
    samples = media(chunks(donor_music))
    tracks = {}
    sources = {}
    for node in sorted(FUTURE_MUSIC_NODES):
        kind, body = donor[node]
        # A music track has one media source and one clip in this subtree.
        if kind == 11:
            count, plugin, storage, sound, file_id = struct.unpack_from('<5I', body)
            if count != 1 or plugin != 0x40001 or storage not in (0, 1):
                raise ValueError(f'Unsupported Far Future music track {node}')
            end = 28 if storage == 0 else 20
            clips, _, clip_sound = struct.unpack_from('<III', body, end + 1)
            if clips != 1 or clip_sound != sound:
                raise ValueError(f'Unexpected Far Future music clip {node}')
            if sound not in sources:
                sources[sound] = samples[sound] if sound in samples else stream(sound)
            tracks[node] = (sound, body[:8], bytearray(body[end:]))
        legacy[node] = kind, body

    # Keep the original playback events, switches and transitions. Only the
    # Future subtree is swapped, and its media is local to the Future bank.
    music = {b'BKHD': music[b'BKHD']}
    media_ids = {sound: 0x71020000 + index for index, sound in enumerate(sources)}
    locations = add_media(music, {media_ids[sound]: sample for sound, sample in sources.items()})
    for node, (sound, header, rest) in tracks.items():
        target = media_ids[sound]
        struct.pack_into('<I', rest, 9, target)
        legacy[node] = 11, header + struct.pack('<5I', 0, target, bank_id, *locations[target]) + rest
    return pack_chunks(music)


def replace_citron(legacy, donor, old_audio, aster_audio):
    bank = chunks(old_audio)
    bank_id, = struct.unpack_from('<I', bank[b'BKHD'], 4)
    source = media(chunks(aster_audio))
    # Use new local IDs for all three samples to avoid replacing a sound that
    # the original bank might still reference by its previous ID.
    media_ids = {sound: 0x71010000 + index for index, (_, sound) in enumerate(CITRON_SAMPLES.values())}
    positions = add_media(bank, {target: source[sound] for sound, target in media_ids.items()})
    for node, (old, current) in CITRON_SAMPLES.items():
        kind, body = donor[node]
        plugin, storage, sound, file_id = struct.unpack_from('<4I', body)
        if (kind, plugin, storage, sound, file_id) != (2, 0x20001, 0, old, bank_id):
            raise ValueError(f'Unexpected Citron sound object {node}')
        target = media_ids[current]
        legacy[node] = kind, body[:8] + struct.pack('<4I', target, bank_id, *positions[target]) + body[24:]

    event, action, sequence, mixer = 3524272886, 921216775, 878518310, 919016647
    for node in (event, action, sequence):
        legacy[node] = donor[node]
    kind, body = donor[mixer]
    # Route through the original plant-impact bus. The later Citron-specific
    # bus is absent from Iris's initialization bank.
    if kind != 7 or struct.unpack_from('<I', body, 2)[0] != 2188264548 or struct.unpack_from('<I', body, 41)[0] != 10:
        raise ValueError('Unexpected Citron mixer')
    legacy[mixer] = kind, body[:2] + struct.pack('<I', 2008125593) + body[6:41] + struct.pack('<II', 1, sequence)
    return pack_chunks(bank)


def replace_mech(nodes, reference, legacy_bank, aster_bank):
    bank = chunks(legacy_bank)
    aster = chunks(aster_bank)
    bank_id, = struct.unpack_from('<I', bank[b'BKHD'], 4)
    if struct.unpack_from('<I', aster[b'BKHD'], 4)[0] != bank_id:
        raise ValueError('Unexpected Aster mech bank ID')
    donor = objects(aster)
    samples = media(aster)
    sound_nodes = {node: struct.unpack_from('<I', body, 5)[0]
                   for node, (kind, body) in donor.items() if kind == 2}
    media_ids = {sound: 0x71030000 + index for index, sound in enumerate(sorted(set(sound_nodes.values())))}
    locations = add_media(bank, {target: samples[sound] for sound, target in media_ids.items()})

    # ROW 2 already provides this event tree in the legacy HIRC layout.
    # Retain its v88 mixer settings and point its sound objects at Aster's WEMs.
    parent, mixer = 790059241, 964531660
    kind, body = nodes[parent]
    child_count_offset = 104
    child_count, = struct.unpack_from('<I', body, child_count_offset)
    if kind != 7 or child_count_offset + 4 + child_count * 4 != len(body):
        raise ValueError('Unexpected Iris zombie audio mixer')
    nodes[parent] = kind, (body[:child_count_offset] + struct.pack('<I', child_count + 1)
                           + body[child_count_offset + 4:] + struct.pack('<I', mixer))
    children = {}
    for node, (kind, body) in reference.items():
        if node not in donor or node == parent:
            continue
        if kind != donor[node][0]:
            raise ValueError(f'Mismatched mech sound object {node}')
        if kind == 2:
            plugin, storage, _, legacy_id = struct.unpack_from('<4I', body)
            if (plugin, storage, legacy_id) != (0x20001, 0, bank_id):
                raise ValueError(f'Unexpected legacy mech media reference {node}')
            target = media_ids[sound_nodes[node]]
            body = struct.pack('<6I', 0x40001, 0, target, bank_id, *locations[target]) + body[24:]
        elif node == mixer:
            count, = struct.unpack_from('<I', body, child_count_offset)
            refs = struct.unpack_from(f'<{count}I', body, child_count_offset + 4)
            # Two ROW 2 containers are absent in Aster. Leave them out of
            # the mixer along with their unused ROW 2 events.
            refs = [child for child in refs if child in donor]
            body = body[:child_count_offset] + struct.pack(f'<{len(refs) + 1}I', len(refs), *refs)
        elif kind in (3, 4):
            body = donor[node][1]
        nodes.pop(node, None)
        # The parent mixer resolves its children as it is read by Wwise 88.
        target_nodes = children if kind in (2, 5, 7) else nodes
        target_nodes[node] = kind, body
    ordered = {}
    for node, value in nodes.items():
        if node == parent:
            ordered.update(children)
        ordered[node] = value
    nodes.clear()
    nodes.update(ordered)
    if not donor.keys() <= nodes.keys():
        raise ValueError('Aster mech audio requires missing v88 sound objects')
    return pack_chunks(bank)


def polish_audio(iris, row, aster_citron, aster_mech):
    def get(bundle, path):
        return bundle.read(bundle.group_for(path), path)

    base = chunks(get(iris, GLOBAL))
    reference = chunks(get(row, GLOBAL))
    if any(struct.unpack_from('<I', bank[b'BKHD'])[0] != 88 for bank in (base, reference)):
        raise ValueError('Far Future needs Wwise 88 banks')
    original = objects(base)
    donor = objects(reference)
    revised = dict(original)
    music = replace_music(revised, get(iris, MUSIC), donor, get(row, MUSIC),
                          lambda sound: get(row, f'STREAMINGWAVES\\{sound}.WEM'))
    citron = replace_citron(revised, donor, get(iris, CITRON), aster_citron)
    if any(revised[node] != original[node] for node in original.keys() - FUTURE_MUSIC_NODES):
        raise ValueError('Far Future audio changed an unrelated Wwise object')

    # Wwise 88 resolves some references while reading the bank. Keep the
    # authoring order for the music tree and place actions before their events.
    music_nodes = {node: revised[node] for node in donor if node in FUTURE_MUSIC_NODES}
    ordered = {}
    for node, value in original.items():
        if node not in FUTURE_MUSIC_NODES:
            ordered[node] = value
        elif music_nodes:
            ordered.update(music_nodes)
            music_nodes.clear()
    ordered.update({node: revised[node] for node in donor if node in revised and node not in ordered})
    if ordered != revised:
        raise ValueError('Far Future bank ordering lost a sound object')
    mech = replace_mech(ordered, donor, get(iris, GARGANTUAR), aster_mech)
    base[b'HIRC'] = pack_objects(ordered)
    return {GLOBAL: pack_chunks(base), MUSIC: music, CITRON: citron, GARGANTUAR: mech}
