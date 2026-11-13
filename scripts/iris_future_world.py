"""Restore the Far Future prototype with resources from two original ROW builds."""

from copy import deepcopy
from contextlib import closing
from io import BytesIO, StringIO
import json
import struct
from zipfile import ZipFile

from iris_future_art import polish_art
from iris_future_audio import CITRON_IMPACT, polish_audio
from iris_future_gargantuar import (
    GARGANTUAR_ATLAS, GARGANTUAR_GROUP, aster_properties, mech_assets, mech_layout, mech_manifest,
    patch_mech_beam, patch_mech_laser_state, update_mech_properties,
)
from prepare_baseline import sha256
from rsb_local import ResourceBundle


DONOR_HASHES = (
    'd2ce330a5a22c8b92bdda24df760b8e6b3ece4ff22002e5e046d0e01b1d925e3',  # 1.4.244592
    '7050cc5ebdd961776bd7b29a99b0633bdbac3fee4395ef7d8fbaaddf78c02211',  # 2.1.1
)
GROUPS = (
    'WorldExists_future', 'WorldPackages_future', 'WorldMap_Future', 'WorldMap_Future_NonPVR',
    'DelayLoad_Background_Future', 'Dirt_Spawn_Future', 'FutureMowerGroup', 'FutureNoteGroup',
    'Future_Gravestone', 'Railcart_Future_Group', 'EMPeachEffects', 'SunBombChallengeModule',
    'PlantBlover', 'PlantCitron', 'PlantEMPea', 'PlantHolonut', 'PlantLaserBean',
    'PlantMagnifyingGrass', 'PlantPowerPlant',
    'ZombieFutureBasicGroup', 'ZombieFutureGargantuarGroup', 'ZombieFutureImpGroup',
    'ZombieFutureJetpackGroup', 'ZombieFutureMechConeGroup', 'ZombieFutureMechDiscoGroup',
    'ZombieFutureMechFootballGroup', 'ZombieFutureProtectorGroup',
    'AudioFuture', 'FutureGroansAudio', 'Music_MainPath_Future', 'Music_MiniGame_A_Future',
    'Music_MiniGame_B_Future', 'PlantBloverAudio', 'PlantCitronAudio', 'PlantEMPeachAudio',
    'PlantInfinutAudio', 'PlantLaserBeanAudio', 'PlantMagnifyingGrassAudio',
    'ZombieFutureGargantuarAudio', 'ZombieFutureJetpackAudio', 'ZombieFutureMechConeAudio',
    'ZombieFutureMechDiscoAudio', 'ZombieFutureMechFootballAudio', 'ZombieFutureProtectorAudio',
    'ZombieFutureSpiderBotAudio',
)
WORLD_MAP = r'PACKAGES\WORLDS\FUTURE\WORLDMAP.RTON'
WORLD_MAP_ID = 'RESFILE_PACKAGES_WORLDS_FUTURE_WORLDMAP'
PROPERTY_SHEETS = r'PACKAGES\PROPERTYSHEETS.RTON'
AUDIO_POOL = 'ZombieCowboyPonchoAudio'
FUTURE_BLACKLIST_INSERT = 0x50B954
# ROW 2 supplies the finished Citron rig and all three mech atlas containers.
FINISHED_GROUPS = {'PlantCitron', 'ZombieFutureGargantuarGroup'}


def enable_future_in_engine(path, beam_source, ndk, out):
    data = bytearray(path.read_bytes())
    if struct.unpack_from('<I', data, FUTURE_BLACKLIST_INSERT)[0] != 0xEBF4E6FF:
        raise ValueError('Unexpected Iris world blacklist initializer')
    # Skip only the insertion of "future". Keep the other worlds and the string cleanup.
    struct.pack_into('<I', data, FUTURE_BLACKLIST_INSERT, 0xE320F000)
    patch_mech_beam(data, beam_source, ndk, out)
    patch_mech_laser_state(data, beam_source.with_name('mech_state.S'), ndk, out)
    path.write_bytes(data)


def read_rton(bundle, path, decoder):
    raw = bundle.read(bundle.group_for(path), path)
    if raw[:4] != b'RTON':
        raise ValueError(f'Expected RTON at {path}')
    stream = BytesIO(raw[4:])
    stream.name = path
    return json.loads(decoder(repairFiles=False).parse_root_object(stream))


def update_packages(bundle, aster_sheets, decoder, encoder):
    def encode(data):
        return encoder().encode_root_object(StringIO(json.dumps(data)))

    path = r'PACKAGES\WORLDMAPLIST.RTON'
    world_list = read_rton(bundle, path, decoder)
    future, = (world for world in world_list['objects'][0]['objdata']['MapList']
               if world['MapName'] == 'future')
    if not future['ComingSoon'] or future['LastLevel']:
        raise ValueError('Unexpected Far Future prototype world definition')
    future.update(ComingSoon=False, LastLevel='future10')

    world_map = read_rton(bundle, WORLD_MAP, decoder)
    endless, = (event for event in world_map['objects'][0]['objdata']['m_eventList']
                if event['m_name'] == 'future_level_danger_room')
    endless['m_autoVisible'] = True

    zombie_path = r'PACKAGES\ZOMBIETYPES.RTON'
    zombie_types = read_rton(bundle, zombie_path, decoder)
    flag, = (zombie for zombie in zombie_types['objects'] if 'future_flag' in zombie.get('aliases', []))
    flag['objdata']['PopAnim'] = 'POPANIM_ZOMBIE_ZOMBIE_FUTURE_FLAG'

    property_sheets = read_rton(bundle, PROPERTY_SHEETS, decoder)
    update_mech_properties(property_sheets, aster_sheets)

    plant_path = r'PACKAGES\PLANTTYPES.RTON'
    plants = read_rton(bundle, plant_path, decoder)
    citron, = (plant['objdata'] for plant in plants['objects'] if 'citron' in plant.get('aliases', []))
    citron['PlantAudioGroups'] = ['PlantCitronAudio']

    projectile_path = r'PACKAGES\PROJECTILETYPES.RTON'
    projectiles = read_rton(bundle, projectile_path, decoder)
    impacts = {'PlasmaBall': CITRON_IMPACT, 'GiantPlasmaBall': ''}
    for projectile in projectiles['objects']:
        for alias in projectile.get('aliases', []):
            if alias in impacts:
                projectile['objdata']['ImpactSoundEvent'] = impacts.pop(alias)
    if impacts:
        raise ValueError('Missing Far Future Citron projectiles')

    last_path = r'PACKAGES\LEVELS\FUTURE10.RTON'
    last_level = read_rton(bundle, last_path, decoder)
    belt, = (obj['objdata'] for obj in last_level['objects']
             if obj['objclass'] == 'ConveyorSeedBankProperties')
    if [plant['PlantType'] for plant in belt['InitialPlantList']] != ['empea']:
        raise ValueError('Unexpected Far Future final-day conveyor')
    # The prototype only supplies EMPeach, which cannot clear normal zombies.
    belt['InitialPlantList'] += [
        {'PlantType': 'laser_bean', 'Weight': 40},
        {'PlantType': 'citron', 'Weight': 25},
        {'PlantType': 'holonut', 'MaxCount': 3, 'Weight': 10},
        {'PlantType': 'blover', 'MaxCount': 2, 'Weight': 15},
    ]
    belt['DropDelayConditions'] = [
        {'Delay': delay, 'MaxPackets': count} for delay, count in ((3, 0), (6, 2), (9, 5), (12, 9))
    ]
    return {'Packages': {path: encode(world_list), zombie_path: encode(zombie_types), last_path: encode(last_level),
                         plant_path: encode(plants), projectile_path: encode(projectiles),
                         PROPERTY_SHEETS: encode(property_sheets)},
            'WorldPackages_future': {WORLD_MAP: encode(world_map)}}


def restore_future(source, donor_paths, aster_apk, etc1tool, read_index, write_index, decoder, encoder):
    from index_texture_prefetch import ResourceZip
    from merge_legacy_pvp_resources import Bundle

    if tuple(map(sha256, donor_paths)) != DONOR_HASHES:
        raise ValueError('Far Future requires the original ROW 1.4.244592 and 2.1.1 OBBs, in that order')
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def aster_group(name):
            entry, = (path for path in archive.namelist() if path.endswith('/' + name + '.rsb.smf'))
            return ResourceBundle(archive.read(entry), read_index, write_index)

        future, zombies, plants = map(aster_group, ('future', 'zombie2', 'plant1'))
        aster_sheets = aster_properties(aster_group('dynamic'), PROPERTY_SHEETS, decoder)
    mech_groups = {group['id']: group.get('resources', []) for group in zombies.manifest(decoder)['groups']
                   if group['id'].startswith(GARGANTUAR_GROUP)}
    mech_atlas = mech_groups[GARGANTUAR_ATLAS]
    layout = mech_layout(mech_atlas)
    base = Bundle(source)
    manifest_index, manifest_path, manifest = base.manifest()
    original = ResourceBundle(source, read_index, write_index)
    updates = update_packages(original, aster_sheets, decoder, encoder)
    slot = manifest['slot_count']
    slots = {r['id']: r['slot'] for group in manifest['groups'] for r in group.get('resources', [])}
    audio_pool, = (group for group in manifest['groups'] if group['id'] == AUDIO_POOL)
    audio_slots = {r['id']: r['slot'] for r in audio_pool['resources']}
    packages, = (group for group in manifest['groups'] if group['id'] == 'Packages')
    packages['resources'] = [r for r in packages['resources'] if r['id'] != WORLD_MAP_ID]
    new_slots = {}
    moved_audio = set()
    moved_audio_ids = set()

    pending = set(GROUPS)
    for version, path in enumerate(donor_paths):
        raw = path.read_bytes()
        donor = Bundle(raw)
        _, _, donor_manifest = donor.manifest()
        groups = {group['id']: group for group in donor_manifest['groups']}
        roots = [name for name in GROUPS if name in pending and name in groups
                 and (version or name not in FINISHED_GROUPS)]
        pending.difference_update(roots)
        selected = set(roots)
        for root in roots:
            selected.update(group['id'] for group in groups[root].get('subgroups', []))
        remap = {}
        for old, group in enumerate(donor.groups):
            name = group['ID']
            if name not in selected:
                continue
            index = len(base.groups)
            remap[old] = index
            base.groups.append(group)
            base.infos.append(bytearray(donor.infos[old]))
            base.pools.append(bytearray(donor.pools[old]))
            base.payloads.append(donor.payloads[old])
            count, first = struct.unpack_from('<II', base.infos[index], 196)
            struct.pack_into('<I', base.infos[index], 200, len(base.textures))
            base.textures.extend(donor.textures[first:first + count])
            base.sync_info(index)
            for entry, _ in donor.files(old):
                if entry not in original.files or entry == WORLD_MAP:
                    continue
                if original.files[entry] != [AUDIO_POOL] or not entry.endswith('.BNK'):
                    raise ValueError(f'Unexpected Far Future resource collision at {entry}')
                moved_audio.add(entry)
                sound = original.read(AUDIO_POOL, entry)
                if len(sound) > 32:
                    updates.setdefault(name, {})[entry] = sound
        imported = {donor.groups[index]['ID'] for index in remap}
        if any(name not in imported for name in selected if groups[name]['type'] == 'simple'):
            raise ValueError('Incomplete Far Future group directory')
        for composite in donor.composites:
            count = struct.unpack_from('<I', composite, 1152)[0]
            indices = [struct.unpack_from('<I', composite, 128 + 16 * i)[0] for i in range(count)]
            if not indices or any(index not in remap for index in indices):
                continue
            record = bytearray(composite)
            for index, old in enumerate(indices):
                struct.pack_into('<I', record, 128 + 16 * index, remap[old])
            base.composites.append(record)
        for group in donor_manifest['groups']:
            if group['id'] not in selected:
                continue
            group = deepcopy(group)
            if group['id'] in {f'{GARGANTUAR_GROUP}_{size}' for size in (384, 768, 1536)}:
                mech_manifest(group, mech_atlas, layout)
            for resource in group.get('resources', []):
                resource_id = resource['id']
                if resource_id == WORLD_MAP_ID:
                    resource['slot'] = slots[resource_id]
                    continue
                if resource_id in audio_slots:
                    moved_audio_ids.add(resource_id)
                    resource['slot'] = audio_slots[resource_id]
                    continue
                if resource_id in slots:
                    raise ValueError(f'Unexpected Far Future resource ID collision at {resource_id}')
                if resource_id not in new_slots:
                    new_slots[resource_id] = slot
                    slot += 1
                resource['slot'] = new_slots[resource_id]
            manifest['groups'].append(group)

    if pending:
        raise ValueError(f'Missing Far Future resource groups: {sorted(pending)}')
    audio_pool['resources'] = [resource for resource in audio_pool['resources']
                               if resource['id'] not in moved_audio_ids]
    manifest['slot_count'] = slot
    for group, removed in (('Packages', {WORLD_MAP}), (AUDIO_POOL, moved_audio)):
        index = original.groups[group][0]
        old_files = dict(base.files(index))
        if not removed <= old_files.keys():
            raise ValueError(f'Cannot move entries from {group}')
        table = write_index([(name, entry) for name, entry in old_files.items() if name not in removed], 1)
        payload = base.payloads[index]
        size, start = struct.unpack_from('<II', payload, 72)
        if len(table) > size:
            raise ValueError(f'Rebuilt resource index exceeds the original {group} index')
        payload[start:start + size] = table.ljust(size, b'\0')
        struct.pack_into('<I', payload, 72, len(table))
    base.replace_manifest(manifest_index, manifest_path, manifest)
    assembled = ResourceBundle(base.build(), read_index, write_index)
    if assembled.manifest(decoder) != manifest or any(len(groups) != 1 for groups in assembled.files.values()):
        raise ValueError('Far Future resource index failed verification')
    result = assembled.replace(updates, set())
    assembled = ResourceBundle(result, read_index, write_index)
    if any(assembled.read(group, entry) != data
           for group, entries in updates.items() for entry, data in entries.items()):
        raise ValueError('Far Future resource update failed verification')
    row = ResourceBundle(raw, read_index, write_index)
    citron_path = r'PLANT1_SOUNDBANKS\PLANT_CITRON.BNK'
    mech_path = r'ZOMBIE2_SOUNDBANKS\ZOMBIE_FUTURE_GARGANTUAR.BNK'
    aster_citron = plants.read(plants.group_for(citron_path), citron_path)
    aster_mech = zombies.read(zombies.group_for(mech_path), mech_path)
    art = polish_art(assembled, future, decoder, etc1tool)
    mech_art = mech_assets(assembled, zombies, mech_groups, decoder, etc1tool)
    audio = polish_audio(assembled, row, aster_citron, aster_mech)
    presentation = {}
    for entry, data in (art | mech_art | audio).items():
        presentation.setdefault(assembled.group_for(entry), {})[entry] = data
    result = assembled.replace(presentation, set(), preserve_compression=set(presentation))
    verified = ResourceBundle(result, read_index, write_index)
    if any(verified.read(group, entry) != data
           for group, entries in presentation.items() for entry, data in entries.items()):
        raise ValueError('Far Future presentation failed verification')
    print(f'Far Future: restored {len(verified.groups) - len(original.groups)} resource groups')
    return result
