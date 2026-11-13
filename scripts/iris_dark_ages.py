"""Restore audited Dark Ages campaign levels using Aster artwork.

The remaining Aster campaign requires new native implementations. This module
does not replace their behavior with unrelated plants or zombies.
"""
from contextlib import closing
from copy import deepcopy
from io import StringIO
from pathlib import Path
import json
import struct
import zlib
from tempfile import TemporaryDirectory
from math import ceil
from zipfile import ZipFile

from PIL import Image
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from prepare_localized_resources import atlas_image, atlas_path
from rsb_local import ResourceBundle, align
from iris_dark_audio import port_dark_music, DARK_MUSIC, GLOBAL
from iris_dark_levels import selected_levels, validate_levels, resize_world_nav, connect_map

ROOTS = {
    'dark': ('DelayLoad_Background_Dark', 'DarkMowerGroup', 'Tombstone_Dark_Effects',
             'Tombstone_Dark_Special', 'Tombstone_Dark_Sun', 'WorldMap_Dark', 'WorldMap_Dark_NonPVR'),
    'plant2': ('PlantSunshroom', 'PlantPuffshroom'),
    'zombie3': ('ZombieDarkBasicGroup',),
}


def donor_sprite(image, sprite, root):
    # Most Aster atlases use literal pixel rectangles. Its replacement dark
    # basic zombie, oak and ice-shroom atlases retain 128% logical sizes with
    # physical offsets. Whole-atlas/crop inspection is required: timestamp
    # presence and image-name dimensions do not describe this convention.
    ratio = 25 / 32 if root in {'ZombieDarkBasicGroup', 'ZombieDarkWizardGroup', 'ZombieRogueGroup', 'ZombieDarkJesterGroup', 'ZombieArchmageGroup', 'ZombieDarkKingGroup', 'ZombieDarkGargantuarGroup', 'ZombieDarkImpGroup', 'ZombieTargetGroup', 'ZombieWolfFireGroup', 'ZombieWolfImpGroup', 'ZombieWolfBossGroup', 'ZombieDarkZombossGroup', 'ZombieDarkZombossEffectsGroup', 'ZombieDarkImpDragonGroup', 'PlantOakshooter', 'PlantIceShroom'} else 1
    x, y, w, h = (sprite[k] for k in ('ax', 'ay', 'aw', 'ah'))
    right, bottom = x + round(w * ratio), y + round(h * ratio)
    border = 3 if sprite['id'] == 'IMAGE_BACKGROUNDS_THEATRE_DARK_TEXTURE' else 2
    # Aster's shared 69x71 jalapeno glow contains only a 3x4 visible spot
    # at (34,34). Its authored transparent bottom margin extends 12 pixels
    # beyond this atlas, unlike ordinary two-pixel packing borders. Retain
    # that attachment canvas rather than moving or stretching the glow.
    if sprite['id'] == 'IMAGE_EFFECTS_ZOMBOSS_DARK_FIREBALL_ZOMBOSS_DARK_FIREBALL_69X71':
        if (x, y, w, h, image.size) != (373, 453, 88, 91, (1024, 512)):
            raise ValueError('Changed Dark Dragon glow packing')
        if image.crop((x, y, right, bottom)).getbbox() != (34, 34, 37, 38):
            raise ValueError('Changed Dark Dragon glow pixels')
        border = 12
    if right > image.width + border or bottom > image.height + border:
        raise ValueError(f'Donor rectangle exceeds atlas: {sprite["id"]}')
    # A few stock rectangles include up to two transparent border pixels
    # outside the packed texture; PIL supplies that padding without stretching.
    return image.crop((x, y, right, bottom)).resize((w, h), Image.Resampling.LANCZOS)


def enable_dark_in_engine(path):
    data = bytearray(path.read_bytes())
    at = 0x50b9c0
    expected = 0xeb000000 | (((0x245558 - at - 8) // 4) & 0xffffff)
    if struct.unpack_from('<I', data, at)[0] != expected:
        raise ValueError('Unexpected dark world blacklist instruction')
    struct.pack_into('<I', data, at, 0xe320f000)
    path.write_bytes(data)


def stage_labels(raw, stage):
    """Expose one authored growth stage to Iris's original generic anim rig."""
    from pam_transform_index import PamIndex
    edits = []
    for frame in PamIndex(raw).sprites[-1]['frames']:
        label = frame['label']
        if label and label.endswith(f'_stage{stage}'):
            name = label.rsplit('_stage', 1)[0]
            before = struct.pack('<H', len(label)) + label.encode()
            after = struct.pack('<H', len(name)) + name.encode()
            fragment = raw[frame['start']:frame['end']]
            if fragment.count(before) != 1:
                raise ValueError('Ambiguous PAM label')
            offset = frame['start'] + fragment.index(before)
            edits.append((offset, len(before), after))
    for offset, length, replacement in reversed(edits):
        raw = raw[:offset] + replacement + raw[offset + length:]
    PamIndex(raw)
    return raw


class Importer:
    def __init__(self, source, read_index, write_index, decoder):
        from merge_legacy_pvp_resources import Bundle
        self.base = Bundle(source)
        self.mi, self.mn, self.manifest = self.base.manifest()
        self.write_index = write_index
        self.slots = {r['id']: r['slot'] for g in self.manifest['groups'] for r in g.get('resources', [])}
        self.next_slot = self.manifest['slot_count']
        self.names = {g['id'] for g in self.manifest['groups']}

    def simple(self, group, files, textures, replace=False):
        base = self.base
        name = group['id']
        if name in self.names and not replace:
            raise ValueError(f'Duplicate imported group {name}')
        self.names.add(name)
        index = next(i for i,g in enumerate(base.groups) if g['ID']==name) if replace else len(base.groups)
        # In particular, UIImages must retain the original compressed RSG
        # texture section used by Iris's HUD loader and speed-art patcher.
        flags = struct.unpack_from('<I', base.payloads[index], 16)[0] if replace else 0
        sections = [bytearray(), bytearray()]
        entries, rows = [], []
        # Keep physical textures and PTX indices in the same lexical order as
        # the filename trie; added atlases can sort before the existing atlas.
        for path, raw in sorted(files.items()):
            kind = int(path in textures)
            offset = len(sections[kind])
            sections[kind].extend(align(raw))
            entry = (kind, offset, len(raw))
            if kind:
                width, height, pitch, fmt = textures[path] if len(textures[path]) == 4 else (*textures[path], textures[path][0] * 4, 0)
                entry += (len(rows), 0, 0, width, height)
                row = bytearray(base.h['ptxInfo_EachLength'])
                struct.pack_into('<4I', row, 0, width, height, pitch, fmt)
                rows.append(row)
            entries.append((path, entry))
        table = self.write_index(entries, 1)
        head = bytearray(align(bytes(92) + table))
        plain = align(zlib.compress(sections[0])) if sections[0] and flags & 2 else sections[0]
        pixels = align(zlib.compress(sections[1])) if sections[1] and flags & 1 else sections[1]
        struct.pack_into('<4sI', head, 0, b'pgsr', 4)
        struct.pack_into('<5I', head, 16, flags, len(head), len(head), len(plain), len(sections[0]))
        struct.pack_into('<3I', head, 40, len(head) + len(plain), len(pixels), len(sections[1]))
        struct.pack_into('<II', head, 72, len(table), 92)
        info, pool = bytearray(204), bytearray(152)
        # The pool's third word is its slot capacity. Zero makes native
        # GetGroupForFile reject every allocation, even for valid RSG data.
        struct.pack_into('<I', pool, 136, 1)
        info[:len(name)] = name.encode()
        pool[:len(name)] = name.encode()
        struct.pack_into('<II', info, 196, len(rows), len(base.textures))
        if replace:
            base.infos[index], base.pools[index], base.payloads[index] = info, pool, head + plain + pixels
        else:
            base.groups.append({'ID': name})
            base.infos.append(info)
            base.pools.append(pool)
            base.payloads.append(head + plain + pixels)
        base.textures.extend(rows)
        base.sync_info(index)
        for resource in group.get('resources', []):
            rid = resource['id']
            if rid not in self.slots:
                self.slots[rid] = self.next_slot
                self.next_slot += 1
            resource['slot'] = self.slots[rid]
        if replace:
            at = next(i for i,g in enumerate(self.manifest['groups']) if g['id']==name)
            self.manifest['groups'][at] = group
        else:
            self.manifest['groups'].append(group)
        return index

    def root(self, donor, root, decoder):
        groups = {g['id']: g for g in donor.manifest(decoder)['groups']}
        composite = deepcopy(groups[root])
        # Iris loads this list in order. Every selectable image resolution
        # must precede Common, whose PAMs resolve their images immediately.
        subgroups = list(composite['subgroups'])
        composite['subgroups'] = []
        imported = []
        for subgroup in sorted(subgroups, key=lambda item: not bool(item.get('res'))):
            group = deepcopy(groups[subgroup['id']])
            files, textures = {}, {}
            resources = group.get('resources', [])
            for atlas in [r for r in resources if r.get('atlas')]:
                path = atlas_path(atlas)
                image = atlas_image(donor, donor.group_for(path), path)
                sprites = [r for r in resources if r.get('parent') == atlas['id']]
                # Align cells to all three resolutions and keep each authored
                # rectangle whole. Cropping all sprites to 25/32 cut off map
                # islands and enlarged the battlefield grid.
                width = 4096 if root.startswith('WorldMap') or root == 'DelayLoad_Background_Theatre_Dark' else 2048
                x = y = row_height = 0
                placements = []
                for sprite in sorted(sprites, key=lambda s: s['ah'], reverse=True):
                    w, h = sprite['aw'], sprite['ah']
                    if w + 2 > width:
                        width = 4096
                    if x + w + 2 > width:
                        x, y, row_height = 0, y + row_height, 0
                    placements.append((x, y, donor_sprite(image, sprite, root)))
                    sprite.update(ax=x, ay=y)
                    x += ceil((w + 4) / 4) * 4
                    row_height = max(row_height, ceil((h + 4) / 4) * 4)
                height = (y + row_height + 3) // 4 * 4
                if height > 8192:
                    raise ValueError(f'Atlas too large: {path}')
                canvas = Image.new('RGBA', (width, height))
                for x, y, sprite in placements:
                    canvas.paste(sprite, (x, y))
                atlas.update(width=width, height=height)
                # Iris PTX format 0 consumes RGBA bytes. BGRA here swaps red
                # and blue across maps, plants, zombies and UI icons.
                files[path] = canvas.tobytes('raw', 'RGBA')
                textures[path] = (width, height)
            for resource in list(resources):
                if resource['type'] != 'PopAnim':
                    continue
                path = '\\'.join(resource['path']).upper()
                raw = donor.read(donor.group_for(path), path)
                if resource['id'] == 'POPANIM_PLANT_SUNSHROOM':
                    for stage, suffix in enumerate(('SMALL', 'GROWN', 'STAGE3'), 1):
                        clone = deepcopy(resource)
                        clone['id'] += '_' + suffix
                        clone['path'][-1] = f'iris_sunshroom_{stage}.pam'
                        files['\\'.join(clone['path']).upper()] = stage_labels(raw, stage)
                        resources.append(clone)
                elif resource['id'] == 'POPANIM_PLANT_PUFFSHROOM':
                    raw = stage_labels(raw, 1)
                files[path] = raw
            imported.append((self.simple(group, files, textures), int(group.get('res', 0))))
            composite['subgroups'].append(deepcopy(subgroup))
            if group.get('res') == '1536':
                for size in (768, 384):
                    scale = size / 1536
                    small = deepcopy(group)
                    small['id'] = group['id'].replace('_1536', '_' + str(size))
                    small['res'] = str(size)
                    smaller_files, smaller_textures = {}, {}
                    for resource in small['resources']:
                        if resource.get('atlas'):
                            old_path = atlas_path(resource)
                            w, h = textures[old_path]
                            resource['id'] = resource['id'].replace('_1536', '_' + str(size))
                            resource['path'] = [p.replace('_1536', '_' + str(size)) for p in resource['path']]
                            resource.update(width=round(w*scale), height=max(1,round(h*scale)))
                            source_image = Image.frombytes('RGBA',(w,h),files[old_path],'raw','RGBA')
                            pic = Image.new('RGBA', (resource['width'], resource['height']))
                            for sprite in group['resources']:
                                if sprite.get('parent') != resource['id'].replace('_' + str(size), '_1536'):
                                    continue
                                x, y, sw, sh = (sprite[k] for k in ('ax', 'ay', 'aw', 'ah'))
                                crop = source_image.crop((x, y, x + sw, y + sh))
                                crop = crop.resize((ceil(sw * scale), ceil(sh * scale)), Image.Resampling.LANCZOS)
                                pic.paste(crop, (round(x * scale), round(y * scale)))
                            new_path = atlas_path(resource)
                            smaller_files[new_path] = pic.tobytes('raw','RGBA')
                            smaller_textures[new_path] = pic.size
                        elif 'parent' in resource:
                            resource['parent'] = resource['parent'].replace('_1536', '_' + str(size))
                            resource['path'] = [str(size) if p=='1536' else p for p in resource['path']]
                            for field in ('ax','ay','aw','ah'):
                                resource[field] = (ceil if field in ('aw', 'ah') else round)(resource[field]*scale)
                    imported.append((self.simple(small,smaller_files,smaller_textures),size))
                    composite['subgroups'].append({'id':small['id'],'res':str(size)})
        self.validate_animation_dependencies(composite)
        record = bytearray(1156)
        record[:len(root)] = root.encode()
        for i, (index, res) in enumerate(imported):
            struct.pack_into('<II', record, 128 + i * 16, index, res)
        struct.pack_into('<I', record, 1152, len(imported))
        self.base.composites.append(record)
        self.manifest['groups'].append(composite)

    def validate_animation_dependencies(self, composite):
        """Resolve PAM images in Iris load order at each supported resolution."""
        from pam_transform_index import PamIndex
        groups = {g['id']: g for g in self.manifest['groups']}
        for size in ('1536', '768', '384'):
            available = set()
            for subgroup in composite['subgroups']:
                if subgroup.get('res', size) != size:
                    continue
                group = groups[subgroup['id']]
                index = next(i for i, g in enumerate(self.base.groups) if g['ID'] == group['id'])
                for resource in group.get('resources', []):
                    if resource['type'] == 'Image':
                        available.add(resource['id'])
                    elif resource['type'] == 'PopAnim':
                        path = '\\'.join(resource['path']).upper()
                        # Read from the authored files rather than assuming
                        # an ID existing elsewhere means it is already loaded.
                        entry = dict(self.base.files(index))[path]
                        payload = self.base.payloads[index]
                        section = ResourceBundle.section(payload, entry[0])
                        raw = section[entry[1]:entry[1] + entry[2]]
                        missing = [image['name'] for image in PamIndex(raw).images
                                   if image['name'].split('|')[-1] not in available]
                        if missing:
                            raise ValueError(f'{composite["id"]}/{size}: {resource["id"]} loads before images {missing}')

    def images(self, original, donor, donor_root, target_root, ids, decoder, reference=None, aliases=None, etc1tool=None):
        """Import images, keeping seed portraits inside the original HUD atlas."""
        donor_group = next(g for g in donor.manifest(decoder)['groups'] if g['id'] == donor_root + '_1536')
        entries = {r['id']: r for r in donor_group['resources']}
        icons = [entries[rid] for rid in ids]
        scale, dx, dy = 1, 0, 0
        if reference:
            target_group = next(g for g in self.manifest['groups'] if g['id'] == target_root + '_1536')
            old = next(r for r in target_group['resources'] if r['id'] == reference)
            new = entries[reference]
            scale = old['ah'] / new['ah']
            dx = old.get('x', 0) - new.get('x', 0) * scale
            dy = old.get('y', 0) - new.get('y', 0) * scale
        for size in (384, 768, 1536):
            group = deepcopy(next(g for g in self.manifest['groups'] if g['id'] == f'{target_root}_{size}'))
            files = {p: original.read(group['id'], p) for p in original.groups[group['id']][3]}
            textures = {p: original.texture(group['id'], p) for p in files if p.endswith('.PTX')}
            if target_root == 'UIImages':
                # Standalone portraits resolve but render corrupted in Iris.
                # Match the stock packets' single HUD atlas and UV convention.
                from iris_speed_art import paste_etc1, free_atlas_region
                hud = next(r for r in group['resources'] if r.get('atlas'))
                hud_path = atlas_path(hud)
                width, height, _, fmt = textures[hud_path]
                if fmt != 147:
                    raise ValueError('Expected original ETC1/A8 seed atlas')
                texture = bytearray(files[hud_path])
            for index, icon in enumerate(icons):
                source_path = atlas_path(entries[icon['parent']])
                atlas_image_source = atlas_image(donor, donor.group_for(source_path), source_path)
                pic = donor_sprite(atlas_image_source, icon, donor_root)
                pic = pic.resize((max(1, ceil(pic.width * scale * size / 1536)),
                                  max(1, ceil(pic.height * scale * size / 1536))), Image.Resampling.LANCZOS)
                rid = f'ATLASIMAGE_IRIS_DARK_{target_root.upper()}_{size}_{index}'
                atlas = {'type': 'Image', 'id': rid, 'path': ['atlases', rid.lower()],
                         'atlas': True, 'width': pic.width, 'height': pic.height}
                target = deepcopy(icon)
                target.update(parent=rid, ax=0, ay=0, aw=pic.width, ah=pic.height)
                if target_root == 'UIImages':
                    side = (max(pic.size) + 3) & -4
                    packet_x, packet_y = free_atlas_region(group['resources'], hud['id'], width, height, side, side)
                    padded = Image.new('RGBA', (side, side))
                    padded.paste(pic)
                    with TemporaryDirectory(prefix='iris-packet-') as temp:
                        paste_etc1(texture, width, height, packet_x, packet_y, padded, etc1tool, Path(temp))
                    target.update(parent=hud['id'], ax=packet_x, ay=packet_y)
                if reference:
                    target.update(x=round(icon.get('x', 0) * scale + dx),
                                  y=round(icon.get('y', 0) * scale + dy))
                target['path'] = [str(size) if p == '1536' else p for p in target['path']]
                group['resources'] = [r for r in group['resources'] if r['id'] != target['id']]
                group['resources'] += [target] if target_root == 'UIImages' else [atlas, target]
                for alias in (aliases or {}).get(icon['id'], ()):
                    clone = deepcopy(target)
                    clone['id'] = alias
                    clone['path'][-1] = alias.lower()
                    group['resources'].append(clone)
                path = atlas_path(atlas)
                if target_root == 'UIImages':
                    files[hud_path] = bytes(texture)
                else:
                    files[path], textures[path] = pic.tobytes('raw', 'RGBA'), pic.size
            self.simple(group, files, textures, replace=True)

    def finish(self):
        invalid = [g['ID'] for g, pool in zip(self.base.groups, self.base.pools)
                   if struct.unpack_from('<I', pool, 136)[0] == 0]
        if invalid:
            raise ValueError(f'Native resource pools have no allocation slots: {invalid}')
        self.manifest['slot_count'] = self.next_slot
        self.base.replace_manifest(self.mi, self.mn, self.manifest)
        return self.base.build()


def restore_dark(source, aster_apk, read_index, write_index, decoder, encoder, ui_apk=None, *, etc1tool=None):
    from index_texture_prefetch import ResourceZip
    imported = Importer(source, read_index, write_index, decoder)
    original = ResourceBundle(source, read_index, write_index)
    if ui_apk is None:
        ui_apk = Path(__file__).resolve().parents[2] / 'MuMu_PvZ2C_1.7.5_arm64_fixed.apk'
    with ZipFile(ui_apk) as ui_archive:
        for part, roots in [('uicommon', ('UI_Universe',)), ('uiactive', ('UI_WorldMap', 'UI_WorldPreview'))]:
            ui = ResourceBundle(ui_archive.read(f'assets/pvz2tool/version/base/smf/{part}.rsb.smf'), read_index, write_index)
            donor_groups = {g['id']: g for g in ui.manifest(decoder)['groups']}
            for root in roots:
                donor = donor_groups[root + '_1536']
                ids = [r['id'] for r in donor['resources'] if 'DARK' in r['id'] and 'parent' in r]
                imported.images(original, ui, root, root, ids, decoder,
                                'IMAGE_UI_UNIVERSE_WORLDS_FUTURE' if root == 'UI_Universe' else None)
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = (n for n in archive.namelist() if n.endswith('/' + name + '.rsb.smf'))
            return ResourceBundle(archive.read(path), read_index, write_index)
        for name, roots in ROOTS.items():
            donor = bundle(name)
            for root in roots:
                imported.root(donor, root, decoder)
        imported.images(original, bundle('uiactive'), 'UIImages_Dynamic', 'UIImages',
                        ['IMAGE_UI_PACKETS_SUNSHROOM', 'IMAGE_UI_PACKETS_PUFFSHROOM'], decoder,
                        aliases={'IMAGE_UI_PACKETS_SUNSHROOM': [
                            'IMAGE_UI_PACKETS_SUNSHROOM_' + stage for stage in ('SMALL', 'GROWN', 'STAGE3')]},
                        etc1tool=etc1tool)
        dynamic = bundle('dynamic')
        world = aster_properties(dynamic, r'PACKAGES\WORLDS\DARK.RTON', decoder)
        levels = selected_levels(dynamic, decoder, aster_properties)
        init = bundle('init')
        audio_global, audio_dark = port_dark_music(
            original.read(original.group_for(GLOBAL), GLOBAL),
            init.read(init.group_for(r'INIT_SOUNDBANKS\GLOBAL_DATA3.BNK'), r'INIT_SOUNDBANKS\GLOBAL_DATA3.BNK'),
            lambda sound: init.read(init.group_for(f'INIT_STREAMINGWAVES\\GLOBAL_DATA3\\{sound}.WEM'),
                                    f'INIT_STREAMINGWAVES\\GLOBAL_DATA3\\{sound}.WEM'))
        imported.simple({'type': 'simple', 'id': 'Music_MainPath_DarkAges', 'resources': [
            {'type': 'SoundBank', 'id': 'SOUNDBANK_IRIS_DARK_MUSIC', 'path': ['soundbanks', 'iris_dark_music.bnk']}
        ]}, {DARK_MUSIC: audio_dark}, {})
        # The converted shared Dark Ages tree contains Music_MainPath,
        # Music_MiniGame_A and Music_MiniGame_B (world switch 556668047).
        # The stage always loads MainPath; these dependency names must also
        # exist or the native module loader waits forever before battle.
        for name in ('Music_MiniGame_A_DarkAges', 'Music_MiniGame_B_DarkAges'):
            # The native completion ratio divides loaded bytes by total
            # bytes. An empty group produces NaN and never becomes ready.
            marker = 'iris_' + name.lower() + '.txt'
            imported.simple({'type': 'simple', 'id': name, 'resources': [
                {'type': 'File', 'id': 'RESFILE_' + name.upper(),
                 'path': ['properties', marker]}]},
                {'PROPERTIES\\' + marker.upper(): b'Uses the shared Iris Dark Ages music bank\n'}, {})
    result = ResourceBundle(imported.finish(), read_index, write_index)
    changes = {}
    changes.setdefault(result.group_for(GLOBAL), {})[GLOBAL] = audio_global
    def update(path, obj):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(obj)))
    for path in result.files:
        if path.startswith('LOCALES\\') and path.endswith('\\PROPERTIES\\LAWNSTRINGS.TXT'):
            text = result.read(result.group_for(path),path).decode('utf-16')
            additions = {'DARK':'Dark Ages', 'WORLD_NAME_DARK':'Dark Ages',
                         'WORLD_PREVIEW_DESCRIPTION_DARK':'Explore the Dark Ages at night.',
                         'WORLD_PREVIEW_LOCKED_DARK':'Complete the previous world to unlock.',
                         'IRIS_DARK_MINIGAME_PLACEHOLDER':'Minigame placeholder: this empty level will finish automatically.',
                         'IRIS_DARK_LEVEL_PENDING':'This level is still being ported and is not available yet.'}
            for key,value in additions.items():
                if '['+key+']' not in text:
                    text += '\r\n['+key+']\r\n'+value+'\r\n'
            changes.setdefault(result.group_for(path),{})[path] = text.encode('utf-16')
    path = r'PACKAGES\WORLDMAPLIST.RTON'
    worlds = read_rton(result, path, decoder)
    dark, = (w for w in worlds['objects'][0]['objdata']['MapList'] if w['MapName'] == 'dark')
    dark.update(Hidden=False, ComingSoon=False, EntryPoint='dark_level_91', LastLevel='dark30', RevealedFrom='tutorial4')
    update(path, worlds)
    for profile in ('ANDROID', 'IPAD', 'IPHONE', 'IPHONE5'):
        path = f'PACKAGES\\UI_{profile}.RTON'
        ui = read_rton(result, path, decoder)
        resize_world_nav(ui, worlds['objects'][0]['objdata']['MapList'])
        update(path, ui)
    data = world['objects'][0]['objdata']
    # World IDs persist in PlayerInfo.wm and are not resource-group indices.
    # Native level completion writes Dark Ages to world 7; prototype world 5
    # collides with Far Future and causes the next node to relock on reload.
    data.update(m_worldId=7, m_resGroupID=dark['WorldResources']['ID'])
    connect_map(data, levels)
    update(r'PACKAGES\WORLDS\DARK\WORLDMAP.RTON', world)
    path = r'PACKAGES\LEVELMODULES.RTON'
    modules = read_rton(result, path, decoder)
    stage = next(o['objdata'] for o in modules['objects'] if 'DarkStage' in o.get('aliases', []))
    stage['ResourceGroupNames'] = ['DelayLoad_Background_Dark', 'Dirt_Spawn_Egypt', 'ZombieDarkBasicGroup',
        'AudioEgypt', 'Tombstone_Dark_Effects', 'Tombstone_Dark_Special', 'Tombstone_Dark_Sun']
    stage['GravestoneDefaultTypeName'] = 'gravestone_dark'
    stage['MusicSuffix'] = 'DarkAges'
    update(path, modules)
    path = r'PACKAGES\GRIDITEMTYPES.RTON'
    grids = read_rton(result, path, decoder)
    for obj in grids['objects']:
        d = obj.get('objdata', {})
        if d.get('TypeName') == 'gravestone_dark': d['ResourceGroups'] = ['Tombstone_Dark_Special']
        if d.get('TypeName') == 'gravestoneSunOnDestruction': d['ResourceGroups'] = ['Tombstone_Dark_Sun']
    update(path, grids)
    path = r'PACKAGES\PROPERTYSHEETS.RTON'
    sheets = read_rton(result, path, decoder)
    for obj in sheets['objects']:
        if 'GridItemGravestoneSunOnDestruction' in obj.get('aliases', []):
            obj['objdata']['PopAnim'] = 'POPANIM_GRAVESTONES_DARK_SUN'
        if 'GridItemGravestonePlantfoodOnDestruction' in obj.get('aliases', []):
            obj['objdata']['PopAnim'] = 'POPANIM_GRAVESTONES_DARK_PLANTFOOD'
    update(path, sheets)
    path = r'PACKAGES\PLANTTYPES.RTON'
    plants = read_rton(result, path, decoder)
    for obj in plants['objects']:
        d = obj.get('objdata', {})
        if d.get('TypeName') == 'puffshroom': d['PlantAudioGroups'] = ['PlantPuffshroom']
    update(path, plants)
    path = r'PACKAGES\PROJECTILETYPES.RTON'
    projectiles = read_rton(result, path, decoder)
    spore = next(o['objdata'] for o in projectiles['objects'] if 'PuffSporeDefault' in o.get('aliases', []))
    spore.pop('RenderImage')
    spore.update(AttachedPAM='POPANIM_EFFECTS_PUFFSHROOM_PROJECTILE',
                 AttachedPAMOffset={'x': -90, 'y': -105}, AttachedPAMAnimationToPlay='animation',
                 ImpactPAM='POPANIM_EFFECTS_PUFFSHROOM_HIT')
    update(path, projectiles)
    # Keep checking the accepted prototype's plant resources even though
    # campaign levels now use the chooser rather than a forced preset bank.
    preset = ['sunshroom', 'puffshroom', 'peashooter', 'wallnut', 'cabbagepult', 'potatomine']
    plant_types = {o['objdata']['TypeName']: o['objdata'] for o in plants['objects']
                   if o.get('objclass') == 'PlantType'}
    property_aliases = {a for o in sheets['objects'] for a in o.get('aliases', [])}
    resource_ids = {r['id'] for g in imported.manifest['groups'] for r in g.get('resources', [])}
    for name in preset:
        plant = plant_types[name]
        if plant['Properties'] not in {f'RTID({a}@PropertySheets)' for a in property_aliases}:
            raise ValueError(f'Missing preset plant properties: {name}')
        if plant['PopAnim'] not in resource_ids:
            raise ValueError(f'Missing preset plant animation: {name}')
    if 'POPANIM_GRAVESTONES_DARK_PLANTFOOD' not in resource_ids:
        raise ValueError('Missing plant food gravestone animation')
    validate_levels(levels, {'LevelModules': modules, 'PlantTypes': plants,
                            'ZombieTypes': read_rton(result, r'PACKAGES\ZOMBIETYPES.RTON', decoder),
                            'PropertySheets': sheets})
    added_levels = {}
    for path, level in levels.items():
        if path in result.files:
            update(path, level)
        else:
            added_levels[path] = encoder().encode_root_object(StringIO(json.dumps(level)))
    raw = result.replace(changes, set())
    final = Importer(raw, read_index, write_index, decoder)
    final.simple({'type': 'simple', 'id': 'WorldExists_dark', 'resources': []}, {}, {})
    # The asynchronous world loader expects the map resource in this group,
    # not an empty group with the map left in the eagerly loaded Packages.
    check = ResourceBundle(raw,read_index,write_index)
    map_path = r'PACKAGES\WORLDS\DARK\WORLDMAP.RTON'
    package_group = deepcopy(next(g for g in final.manifest['groups'] if g['id']=='Packages'))
    map_resource, = [r for r in package_group['resources'] if r['id']=='RESFILE_PACKAGES_WORLDS_DARK_WORLDMAP']
    package_group['resources'].remove(map_resource)
    package_files = {p:check.read('Packages',p) for p in check.groups['Packages'][3] if p!=map_path}
    package_files.update(added_levels)
    for path in added_levels:
        package_group['resources'].append({
            'type': 'File', 'id': 'RESFILE_' + path[:-5].replace('\\', '_'),
            'path': path.lower().split('\\')})
    final.simple(package_group,package_files,{},replace=True)
    final.simple({'type':'simple','id':'WorldPackages_dark','resources':[map_resource]},
                 {map_path:check.read('Packages',map_path)}, {})
    return final.finish()
