"""Build a local EN expansion with safe ZH sprite replacements and locale overlays."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import struct
import sys
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageChops, ImageStat
import texture2ddecoder

from prepare_baseline import OBB
from rsb_local import ResourceBundle


ROOT = Path(__file__).resolve().parents[1]
LOCALES = ('de-DE', 'en-US', 'es-ES', 'fr-FR', 'it-IT', 'pt-BR')
PILOT_GROUPS = ('PlantPeashooter', 'PlantSunflower', 'PlantWallnut', 'PlantCabbagepult')
KEY = re.compile(r'^\[([^\]\r\n]+)\][ \t]*\n', re.M)
# Keep printf space flags without reading literal percentages such as "25% of" as arguments.
TOKENS = re.compile(r'\{[^{}\r\n]+\}|%(?! +[A-Za-z]{2})(?:\d+\$)?[-+#0 .\d]*[diuoxXfFeEgGcs%]|</?[A-Za-z][^>\r\n]*>')


def parse_strings(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    keys = list(KEY.finditer(text))
    if not keys:
        raise ValueError('Empty LawnStrings table')
    return text, [(key[1], key.end(), keys[index + 1].start() if index + 1 < len(keys) else len(text))
                  for index, key in enumerate(keys)]


def values_of(text):
    normalized, keys = parse_strings(text)
    return {key: normalized[start:end].rstrip('\n') for key, start, end in keys}


def tokens(value):
    # This label uses literal brackets in the player picker.
    return Counter(token for token in TOKENS.findall(value) if token != '<tap to add player>')


def apply_overlay(original, changes):
    text, keys = parse_strings(original.decode('utf-16'))
    valid = {key for key, _, _ in keys}
    if not isinstance(changes, dict) or not changes.keys() <= valid:
        raise ValueError('Locale overlay contains unknown keys')
    for key, start, end in reversed(keys):
        if key not in changes:
            continue
        before, after = text[start:end].rstrip('\n'), changes[key]
        if not isinstance(after, str) or KEY.search(after + '\n') or '\r' in after or '\0' in after or tokens(before) != tokens(after):
            raise ValueError(f'Unsafe locale override for {key}')
        text = text[:start] + after + text[start + len(before):]
    if b'\r\x00\n\x00' in original:
        text = text.replace('\n', '\r\n')
    return b'\xff\xfe' + text.encode('utf-16-le')


def locale_path(locale):
    return f'LOCALES\\{locale.upper()}\\PROPERTIES\\LAWNSTRINGS.TXT'


def prepare_locales(en, zh, overlays, output, updates):
    tables = output / 'locales'
    tables.mkdir()
    report = {}
    for locale in LOCALES:
        path = locale_path(locale)
        group = en.group_for(path)
        raw = en.read(group, path)
        override = overlays / f'{locale}.json' if overlays else None
        if override and override.is_file():
            raw = apply_overlay(raw, json.loads(override.read_text(encoding='utf-8-sig')))
            updates[group][path] = raw
        values = values_of(raw.decode('utf-16'))
        (tables / f'{locale}.json').write_text(json.dumps(values, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        report[locale] = len(values)
        if locale == 'en-US':
            english = values
    path = 'PROPERTIES\\LAWNSTRINGS.TXT'
    cn_values = values_of(zh.read(zh.group_for(path), path).decode('utf-8-sig'))
    translated = {key: cn_values[key] for key, value in english.items()
                  if cn_values.get(key) and tokens(cn_values[key]) == tokens(value)}
    draft = {**english, **translated}
    (tables / 'zh-CN.draft.json').write_text(json.dumps(draft, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'existing_locales': report, 'zh_draft_matches': len(translated),
            'zh_draft_english_fallback': len(english) - len(translated)}


def atlas_path(atlas):
    path = atlas['path']
    return (path if isinstance(path, str) else '\\'.join(path)).replace('/', '\\').upper() + '.PTX'


def atlas_image(bundle, group, path):
    w, h, pitch, fmt = bundle.texture(group, path)
    data = bundle.read(group, path)
    if fmt == 147 and w % 4 == h % 4 == 0 and len(data) == w * h * 3 // 2:
        split = w * h // 2
        image = Image.frombytes('RGBA', (w, h), texture2ddecoder.decode_etc1(data[:split], w, h), 'raw', 'BGRA')
        image.putalpha(Image.frombytes('L', (w, h), data[split:]))
        return image
    if fmt == 0 and pitch == w * 4 and len(data) == w * h * 4:
        return Image.frombytes('RGBA', (w, h), data)
    block = {152: 4, 161: 5, 162: 6}.get(fmt)
    if block and len(data) == ((w + block - 1) // block) * ((h + block - 1) // block) * 16:
        pixels = texture2ddecoder.decode_astc(data, w, h, block, block)
        return Image.frombytes('RGBA', (w, h), pixels, 'raw', 'BGRA')
    raise ValueError(f'Unsupported atlas format {fmt}: {path}')


def box(resource):
    x, y, w, h = (resource[key] for key in ('ax', 'ay', 'aw', 'ah'))
    return x, y, x + w, y + h


def sprite_crop(image, rect):
    if not (0 <= rect[0] < rect[2] <= image.width and 0 <= rect[1] < rect[3] <= image.height):
        raise ValueError(f'Invalid sprite bounds {rect} for atlas {image.size}')
    return image.crop(rect)


def compatible_sprite(before, after):
    # Compare the silhouette and composited colors independently. A common ID
    # can still refer to a revised costume, animation part, or color palette.
    before = before.resize((32, 32), Image.Resampling.LANCZOS)
    after = after.resize((32, 32), Image.Resampling.LANCZOS)
    alpha = ImageChops.difference(before.getchannel('A'), after.getchannel('A'))
    if ImageStat.Stat(alpha).mean[0] > 18:
        return False
    matte = Image.new('RGBA', before.size, (128, 128, 128, 255))
    difference = ImageChops.difference(Image.alpha_composite(matte, before), Image.alpha_composite(matte, after))
    return max(ImageStat.Stat(difference).mean[:3]) <= 18


def prepare_art(en, donors, decoder, updates, output):
    original = {g['id']: g.get('resources', []) for g in en.manifest(decoder)['groups']}
    donor_manifests = {name: {g['id']: g.get('resources', []) for g in bundle.manifest(decoder)['groups']}
                       for name, bundle in donors.items()}
    report, rgba_paths = {}, set()
    previews = output / 'previews'
    previews.mkdir()
    for plant in PILOT_GROUPS:
        group = plant + '_1536'
        old = original[group]
        candidates = []
        for name, donor in donors.items():
            new = donor_manifests[name].get(group, [])
            if not new or group not in donor.groups:
                continue
            atlases = {entry['id']: atlas_image(donor, group, atlas_path(entry)) for entry in new if entry.get('atlas')}
            sprites = {entry['id']: entry for entry in new if entry.get('parent')}
            candidates.append((name, atlases, sprites))
        changed, retained, sources = [], [], {}
        for atlas in (entry for entry in old if entry.get('atlas')):
            path = atlas_path(atlas)
            image = atlas_image(en, group, path)
            updated = image.copy()
            atlas_changed = False
            sprites = [(item, box(item)) for item in old if item.get('parent') == atlas['id']]
            for sprite, rect in sprites:
                key = sprite['id']
                if any(other is not sprite and rect[0] < area[2] and rect[2] > area[0]
                       and rect[1] < area[3] and rect[3] > area[1] for other, area in sprites):
                    retained.append(key)
                    continue
                dest = sprite_crop(image, rect)
                for name, donor_images, donor_sprites in candidates:
                    match = donor_sprites.get(key)
                    # Preserve trim offsets and reject unrelated uses of the same resource ID.
                    if (not match or any(abs(sprite[k] - match[k]) > 1 for k in ('aw', 'ah'))
                            or any(sprite.get(k, 0) != match.get(k, 0) for k in ('x', 'y'))):
                        continue
                    source = sprite_crop(donor_images[match['parent']], box(match))
                    if not compatible_sprite(dest, source):
                        continue
                    if source.size != dest.size:
                        source = source.resize(dest.size, Image.Resampling.LANCZOS)
                    if source.tobytes() == dest.tobytes():
                        continue
                    updated.paste(source, rect)
                    changed.append(key)
                    sources[key] = name
                    atlas_changed = True
                    break
                else:
                    retained.append(key)
            if atlas_changed:
                image.save(previews / (Path(path.replace('\\', '/')).stem + '-en.png'))
                updated.save(previews / (Path(path.replace('\\', '/')).stem + '-updated.png'))
                updates[group][path] = updated.tobytes()
                rgba_paths.add((group, path))
        report[group] = {'replaced': changed, 'retained': retained, 'sources': sources}
    return report, rgba_paths


def media_format(data):
    if data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        return None
    offset = 12
    while offset + 8 <= len(data):
        chunk, size = struct.unpack_from('<4sI', data, offset)
        if chunk == b'fmt ' and size >= 16 and offset + 8 + size <= len(data):
            codec, channels, rate, bytes_per_second = struct.unpack_from('<HHII', data, offset + 8)
            return {'codec': codec, 'channels': channels, 'sample_rate': rate, 'bytes_per_second': bytes_per_second}
        offset += 8 + size + size % 2
    return None


def audit_music(en, donors):
    old = {name.rsplit('\\', 1)[-1]: name for name in en.files if name.endswith('.WEM')}
    matches = []
    for source, donor in donors.items():
        for path in donor.files:
            leaf = path.rsplit('\\', 1)[-1]
            if leaf not in old or 'MUSIC' not in path:
                continue
            original, cn = old[leaf], path
            before = media_format(en.read(en.group_for(original), original))
            after = media_format(donor.read(donor.group_for(cn), cn))
            matches.append({'en': original, 'zh_bundle': source, 'zh': cn, 'en_format': before, 'zh_format': after})
    return {'embedded_en_banks': sum(name.endswith('.BNK') and 'MUSIC' in name for name in en.files),
            'matched_external_media': matches, 'replaced': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cn-apk', type=Path, required=True)
    parser.add_argument('--cn-workspace', type=Path, default=ROOT.parent / 'pvz2-unline-cn')
    parser.add_argument('--rton-tools', type=Path, default=ROOT / 'tools/pyvz2/OBBEdit/libraries')
    parser.add_argument('--en-obb', type=Path, default=ROOT / 'work/baseline' / OBB)
    parser.add_argument('--row-obb', type=Path, help='optional extracted modern international resource donor')
    parser.add_argument('--overlays', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/localized')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists. Specify a new --output directory.')
    sys.path[:0] = [str(args.rton_tools.resolve()), str((args.cn_workspace / 'scripts').resolve())]
    from index_texture_prefetch import ResourceZip
    from merge_legacy_pvp_resources import trie_read, trie_write
    from pyvz2rton import RTONDecoder

    def bundle(data):
        return ResourceBundle(data, trie_read, trie_write)

    en = bundle(args.en_obb.read_bytes())
    output = args.output
    output.mkdir(parents=True)
    updates = defaultdict(dict)
    stream = ResourceZip(args.cn_apk)
    try:
        with ZipFile(stream) as archive:
            def donor(name):
                path, = (path for path in archive.namelist() if path.endswith('/' + name + '.rsb.smf'))
                return bundle(archive.read(path))

            locale_report = prepare_locales(en, donor('dynamic'), args.overlays, output, updates)
            zh_art = donor('plant1')
            if args.row_obb:
                row_art = bundle(args.row_obb.read_bytes())
                art_report, rgba_paths = prepare_art(en, {'zh': zh_art, 'row': row_art}, RTONDecoder, updates, output)
                del row_art
            else:
                art_report, rgba_paths = prepare_art(en, {'zh': zh_art}, RTONDecoder, updates, output)
            del zh_art
            # Read one CN archive at a time. The Init archive alone is about 410 MiB.
            music_report = audit_music(en, {name: donor(name) for name in ('egypt',)})
            for name in ('init', 'pirate', 'cowboy', 'zombie1', 'zombie2', 'zombie3'):
                music_report['matched_external_media'].extend(audit_music(en, {name: donor(name)})['matched_external_media'])
    finally:
        stream.map.close()
        stream.file.close()
    result = en.replace(updates, rgba_paths)
    verified = bundle(result)
    if en.files != verified.files or en.groups.keys() != verified.groups.keys():
        raise ValueError('Resource index changed unexpectedly')
    for group in en.groups:
        if group not in updates:
            if en.groups[group][2] != verified.groups[group][2]:
                raise ValueError(f'Unrelated RSG changed: {group}')
            continue
        for path in en.groups[group][3]:
            expected = updates[group][path] if path in updates[group] else en.read(group, path)
            if verified.read(group, path) != expected:
                raise ValueError(f'RSG verification failed: {group}/{path}')
    if en.manifest(RTONDecoder) != verified.manifest(RTONDecoder):
        raise ValueError('Resource manifest changed unexpectedly')
    for group, path in rgba_paths:
        width, height, _, _ = en.texture(group, path)
        if verified.texture(group, path) != (width, height, width * 4, 0):
            raise ValueError(f'Invalid RGBA metadata: {group}/{path}')
    obb = output / OBB
    obb.write_bytes(result)
    with ZipFile(output / 'extobb.save', 'x', compression=ZIP_DEFLATED, compresslevel=1) as container:
        container.write(obb, OBB)
    with ZipFile(output / 'extobb.save') as container, container.open(OBB) as wrapped:
        for start in range(0, len(result), 1024 * 1024):
            if wrapped.read(1024 * 1024) != result[start:start + 1024 * 1024]:
                raise ValueError('Packaged expansion does not match generated OBB')
    report = {'locales': locale_report, 'art': art_report, 'music': music_report, 'runtime_verified': False}
    (output / 'resource-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(output.resolve())


if __name__ == '__main__':
    main()
