"""Port Aster's two speed-button sprites into Iris's existing ETC1/A8 HUD atlases."""

from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from PIL import Image

from prepare_localized_resources import atlas_image, atlas_path, box
from rsb_local import ResourceBundle


SPEED = 'IMAGE_UI_HUD_INGAME_SPEED'
SPEED_IMAGES = (SPEED, SPEED + '_DOWN')
PAUSE = 'IMAGE_UI_HUD_INGAME_PAUSE_BUTTON'
HUD_ATLASES = tuple(f'UIImages_{resolution}' for resolution in (384, 768, 1536))


def aster_icons(apk, read_index, write_index, decoder):
    from index_texture_prefetch import ResourceZip

    stream = ResourceZip(apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        path, = (name for name in archive.namelist() if name.endswith('/uicommon.rsb.smf'))
        donor = ResourceBundle(archive.read(path), read_index, write_index)
    group, = (group for group in donor.manifest(decoder)['groups'] if group['id'] == 'UIImages_1536')
    resources = {resource['id']: resource for resource in group['resources']}
    sprites = [resources[name] for name in SPEED_IMAGES]
    parent, = {sprite['parent'] for sprite in sprites}
    path = atlas_path(resources[parent])
    image = atlas_image(donor, donor.group_for(path), path)
    return [image.crop(box(sprite)) for sprite in sprites]


def paste_etc1(texture, width, height, x, y, sprite, tool, scratch):
    size = (sprite.width + 3) & -4
    padded = Image.new('RGBA', (size, size))
    padded.paste(sprite)
    source = scratch / 'speed.png'
    target = scratch / 'speed.etc1'
    padded.convert('RGB').save(source)
    subprocess.run([tool, source, '--encodeNoHeader', '-o', target], check=True)
    rgb = target.read_bytes()
    if len(rgb) != size * size // 2:
        raise ValueError('Unexpected speed-button ETC1 size')
    stride = width * 2
    row_length = size * 2
    for row in range(size // 4):
        start = (y // 4 + row) * stride + x * 2
        texture[start:start + row_length] = rgb[row * row_length:(row + 1) * row_length]
    alpha = padded.getchannel('A').tobytes()
    for row in range(size):
        start = width * height // 2 + (y + row) * width + x
        texture[start:start + size] = alpha[row * size:(row + 1) * size]


def append_manifest_sprites(raw, decoder, encoder, additions, slot):
    """Keep original RTON tokens and string-cache indices byte-for-byte."""
    class LiteralEncoder(encoder):
        def encode_cached_string(self, string, cached_strings):
            value = string.encode('utf-8')
            return b'\x81' + self.encode_number(len(value)) + value

    class LocateAtlasArrays(decoder):
        def __init__(self):
            super().__init__(repairFiles=False)
            self.value_mappings = {**self.value_mappings, b'\x86': LocateAtlasArrays.parse_list}
            self.locations = {}

        def parse_list(self, stream, *args):
            start = stream.tell() + 1  # just after the array's FD marker
            decoded = super().parse_list(stream, *args)
            for parent in additions:
                if parent.encode('ascii') not in decoded:
                    continue
                entries = json.loads(decoded)
                if any(isinstance(entry, dict) and entry.get('id') == parent for entry in entries):
                    self.locations[parent] = (start, stream.tell() - 1, len(entries))
            return decoded

    parser = LocateAtlasArrays()
    stream = BytesIO(raw)
    stream.name = 'resource manifest'
    stream.seek(4)
    parser.parse_root_object(stream)
    literal = LiteralEncoder()
    marker = b'\x90\x0aslot_count\x24'
    count = literal.encode_number(slot)
    offset = raw.index(marker + count) + len(marker)
    edits = [(offset, offset + len(count), literal.encode_number(slot + len(SPEED_IMAGES)))]
    for parent, sprites in additions.items():
        start, end, count = parser.locations[parent]
        before = literal.encode_number(count)
        if raw[start:start + len(before)] != before:
            raise ValueError(f'Unexpected array count for {parent}')
        items = json.loads(json.dumps(sprites), object_pairs_hook=literal.encode_object_pairs)
        edits.extend(((start, start + len(before), literal.encode_number(count + len(sprites))),
                      (end, end, b''.join(literal.encode_object(item, {}) for item in items))))
    for start, end, replacement in sorted(edits, reverse=True):
        raw = raw[:start] + replacement + raw[end:]
    return raw


def port_speed_art(bundle, decoder, encoder, icons, etc1tool, updates):
    manifest = bundle.manifest(decoder)
    slot = manifest['slot_count']
    groups = {group['id']: group for group in manifest['groups']}
    additions = {}
    with TemporaryDirectory(prefix='iris-speed-') as temp:
        for atlas_group in HUD_ATLASES:
            resources = groups[atlas_group]['resources']
            pause, = (sprite for sprite in resources if sprite['id'] == PAUSE)
            parent = pause['parent']
            atlas, = (sprite for sprite in resources if sprite['id'] == parent)
            path = atlas_path(atlas)
            group = bundle.group_for(path)
            width, height, _, fmt = bundle.texture(group, path)
            texture = bytearray(bundle.read(group, path))
            size = pause['aw']
            padded = (size + 3) & -4
            bottom = max(box(item)[3] for item in resources if item.get('parent') == parent)
            y = ((bottom + 3) & -4) + 4
            if (fmt != 147 or len(texture) != width * height * 3 // 2
                    or pause['ah'] != size or 2 * padded + 12 > width or y + padded > height):
                raise ValueError(f'No ETC1/A8 space for speed buttons in {path}')
            sprites = []
            for index, (name, icon) in enumerate(zip(SPEED_IMAGES, icons, strict=True)):
                x = 4 + index * (padded + 4)
                sprite = icon.resize((size, size), Image.Resampling.LANCZOS)
                paste_etc1(texture, width, height, x, y, sprite, etc1tool, Path(temp))
                sprites.append({
                    **pause, 'id': name, 'slot': slot + index, 'ax': x, 'ay': y,
                    'path': pause['path'][:-1] + ['speed' if index == 0 else 'speed_down'],
                })
            additions[parent] = sprites
            resources.extend(sprites)
            updates.setdefault(group, {})[path] = texture
    manifest['slot_count'] += len(SPEED_IMAGES)
    path, = (name for name in bundle.files if name.startswith('PROPERTIES\\RESOURCES') and name.endswith('.RTON'))
    group = bundle.group_for(path)
    data = append_manifest_sprites(bundle.read(group, path), decoder, encoder, additions, slot)
    stream = BytesIO(data[4:])
    stream.name = path
    if json.loads(decoder(repairFiles=False).parse_root_object(stream)) != manifest:
        raise ValueError('Speed-button resource manifest failed round-trip')
    updates.setdefault(group, {})[path] = data
