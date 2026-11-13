"""Translate the authored Dark Dragon actions to Iris-owned property fields.

This is a boss action configuration, not a plant/zombie rank table. All three
authored health phases survive; the source phase's Level member is excluded.
"""
from copy import deepcopy
from contextlib import closing
from io import StringIO
from pathlib import Path
from zipfile import ZipFile
import json
import math
import re
import struct

SPAWN_TYPES = ('dark', 'dark_armor1', 'dark_armor2', 'dark_armor3',
               'dark_imp', 'dark_wizard', 'dark_juggler', 'dark_archmage',
               'dark_gargantuar')
ACTION_NAMES = ('Walk', 'Spawn', 'FireBreath', 'Fireballs')
ACTION_CLASSES = ('ZombossDarkWalkActionDefinition', 'ZombossDarkSpawnActionDefinition',
                  'ZombossDarkFireBreathActionDefinition', 'ZombossDarkLobFireballsActionDefinition')
STAGE_FIELDS = ('HitPoints', 'AnimRateModifier', 'DamageIndexFull', 'DamageIndexHalf',
                'ChilledDurationFromFrozen', 'StunTime', 'StunDamageScale',
                'StunStaggerBackMovement', 'StunStaggerBackTime')
ACTION_FIELDS = (
    ('Weight', 'RepeatMin', 'RepeatMax', 'WalkVerticalChance', 'WalkPreferSquashChance'),
    ('Weight', 'RepeatMin', 'RepeatMax', 'SpawnStartTime', 'SpawnEndTime', 'SpawnDistanceVariance'),
    ('Weight', 'RepeatMin', 'RepeatMax', 'Cdtime', 'FlameDuration', 'FlameFillRowTime', 'PlantfoodDamageToInterrupt'),
    ('Weight', 'RepeatMin', 'RepeatMax', 'LobbedFlameDuration', 'PlantfoodDamageToInterrupt',
     'MinColumn', 'TargetMagnetshroomChance', 'LobbedFlameDelay'))
ACTION_RANGES = ((), ('SpawnZombieWavePointRange', 'SpawnWavesBetweenPlantFood'), (),
                 ('LobbedFlameCount', 'DragonImpCount'))


def dragon_settings(sheet, sheets, replacements):
    aliases = {a: o for o in sheets['objects'] for a in o.get('aliases', [])}
    if len(sheet['Stages']) != 3:
        raise ValueError('Changed Dark Dragon phase count')
    result = {'MagnetStunDuration': sheet['MagnetStunDuration'],
              'PowerUpDamageModifier': sheet['PowerUpDamageModifier'],
              'MinColumn': sheet['MinColumn'], 'MaxColumn': sheet['MaxColumn']}
    for stage_index, stage in enumerate(sheet['Stages']):
        prefix = 'Phase' + str(stage_index)
        if set(stage) - set(STAGE_FIELDS) - {'Level', 'Actions', 'IdleTime', 'RetreatAction', 'StunDamageColorFlash'}:
            raise ValueError('Unreviewed Dark Dragon phase fields')
        for key in STAGE_FIELDS:
            value = stage[key]
            if not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError('Invalid boss field ' + key)
            result[prefix + key] = value
        for edge in ('Min', 'Max'):
            result[prefix + 'Idle' + edge] = stage['IdleTime'][edge]
        for channel in ('mRed', 'mGreen', 'mBlue', 'mAlpha'):
            result[prefix + 'Stun' + channel[1:]] = stage['StunDamageColorFlash'][channel]
        retreat = re.fullmatch(r'RTID\(([^@]+)@\.\)', stage['RetreatAction'])
        if not retreat or aliases[retreat[1]]['objclass'] != ACTION_CLASSES[0]:
            raise ValueError('Unreviewed dragon retreat behavior')
        enabled = set()
        for reference in stage['Actions']:
            match = re.fullmatch(r'RTID\(([^@]+)@\.\)', reference)
            if not match:
                raise ValueError('Unresolved dragon action ' + reference)
            obj = aliases[match[1]]
            kind = ACTION_CLASSES.index(obj['objclass'])
            if kind in enabled:
                raise ValueError('Duplicate dragon phase action')
            enabled.add(kind)
            data = deepcopy(obj['objdata'])
            allowed = set(ACTION_FIELDS[kind]) | set(ACTION_RANGES[kind])
            if kind == 1:
                allowed.add('SpawnZombieTypes')
            if set(data) - allowed:
                raise ValueError('Unreviewed dragon action fields: ' + repr(set(data) - allowed))
            action = prefix + ACTION_NAMES[kind]
            for key in ACTION_FIELDS[kind]:
                # Aster factory 0xbc40a8 writes 0x40000000 at +0x34:
                # LobbedFlameDelay defaults to two seconds.
                # It must not inherit arbitrary bytes from an absent field.
                if key not in data and key != 'LobbedFlameDelay':
                    raise ValueError('Missing dragon action field ' + key)
                result[action + key] = data.get(key, 2)
            for key in ACTION_RANGES[kind]:
                for edge in ('Min', 'Max'):
                    result[action + key + edge] = data[key][edge]
            if kind == 1:
                names = [replacements.get(name, name) for name in data['SpawnZombieTypes']]
                if not names or len(names) > 8 or any(n not in SPAWN_TYPES for n in names):
                    raise ValueError('Unported dragon summon pool')
                result[action + 'Count'] = len(names)
                for i, name in enumerate(names):
                    result[action + 'Type' + str(i)] = SPAWN_TYPES.index(name)
        result[prefix + 'ActionMask'] = sum(1 << i for i in enabled)
    return result


def restore_dragon(raw, aster_apk, read_index, write_index, decoder, encoder):
    from index_texture_prefetch import ResourceZip
    from iris_dark_ages import Importer
    from iris_future_gargantuar import aster_properties
    from iris_future_world import read_rton
    from iris_future_audio import chunks, media
    from iris_scaredy_audio import convert_plant_bank
    from rsb_local import ResourceBundle
    original = ResourceBundle(raw, read_index, write_index)
    importer = Importer(raw, read_index, write_index, decoder)
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        art = bundle('zombie3')
        for group in ('ZombieDarkZombossGroup', 'ZombieDarkZombossEffectsGroup', 'ZombieDarkImpDragonGroup'):
            importer.root(art, group, decoder)
        audio = deepcopy(next(g for g in art.manifest(decoder)['groups'] if g['id'] == 'ZombossDarkAgesAudio'))
        resource, = audio['resources']
        path = '\\'.join(resource['path']).upper()
        bank = art.read(art.group_for(path), path)
        recipe = json.loads((Path(__file__).resolve().parents[1] / 'src/dark/dragon-audio-v88.json').read_text())
        samples = media(chunks(bank))
        required = {r['media'] for r in recipe['nodes'].values() if 'media' in r}
        # Aster v163 embeds complete Vorbis files even for sources whose
        # historical StreamType says prefetch/stream. Its loose WEM copies
        # are different encodings and must not replace the embedded audio.
        if required - samples.keys() or any(v[:4] != b'RIFF' or struct.unpack_from('<I', v, 4)[0] + 8 != len(v)
                                          for v in samples.values()):
            raise ValueError('Dark Dragon audio is no longer fully embedded')
        global_path = r'SOUNDBANKS\GLOBAL_DATA.BNK'
        legacy = original.read(original.group_for(global_path), global_path)
        importer.simple(audio, {path: convert_plant_bank(legacy, bank, recipe)}, {})
        dynamic = bundle('dynamic')
        donor_types = aster_properties(dynamic, r'PACKAGES\ZOMBIETYPES.RTON', decoder)
        donor_sheets = aster_properties(dynamic, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
    result = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\ZOMBIETYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON']
    types, sheets = [read_rton(result, p, decoder) for p in paths]
    def find(doc, alias):
        obj, = [o for o in doc['objects'] if alias in o.get('aliases', [])]
        return obj['objdata']
    if any('zombossmech_dark' in o.get('aliases', []) for o in types['objects']):
        raise ValueError('Dark Dragon already registered')
    allowed = {key for o in sheets['objects'] if o.get('objclass') == 'ZombiePropertySheet'
               for key in o['objdata'] if not key.startswith('#')}
    policy = json.loads((Path(__file__).resolve().parents[1] / 'src/dark/port-policy.json').read_text())
    used = {o.get('uid') for o in types['objects']}
    for alias, source_sheet, class_name, uid in (
            ('zombossmech_dark', 'ZombieZombossMechDark', 'ZombieIrisDragon', '1.2200.1'),
            ('dark_imp_dragon', 'ZombieDarkImpDragonDefault', 'ZombieIrisDragonImp', '1.2201.1')):
        if uid in used:
            raise ValueError('Dragon identity collision')
        source = find(donor_sheets, source_sheet)
        data = {k: deepcopy(v) for k, v in source.items() if k in allowed}
        if alias == 'zombossmech_dark':
            data.update(dragon_settings(source, donor_sheets, policy['zombie_replacements']))
            data['Hitpoints'] = sum(stage['HitPoints'] for stage in source['Stages'])
            for i, name in enumerate(SPAWN_TYPES):
                data['SummonType' + str(i)] = 'RTID(' + name + '@ZombieTypes)'
            data['EatDPS'] = 0
        prop_alias = 'IrisDragon' if alias == 'zombossmech_dark' else 'IrisDragonImp'
        sheets['objects'].append({'objclass': 'IrisDragonProperties' if alias == 'zombossmech_dark' else 'ZombiePropertySheet',
                                  'aliases': [prop_alias], 'objdata': data})
        actor = deepcopy(find(donor_types, alias))
        actor.update(ZombieClass=class_name, AnimRigClass='ZombieAnimRig',
                     Properties='RTID(' + prop_alias + '@PropertySheets)', AudioGroups=['ZombossDarkAgesAudio'],
                     ResourceGroups=['ZombieDarkZombossGroup', 'ZombieDarkZombossEffectsGroup', 'ZombieDarkImpDragonGroup'])
        # Reuse an existing Iris statistics enum, while retaining unique
        # registry keys and UIDs for the actual boss and dragon imp.
        actor['TypeName'] = 'zombossmech_future' if alias == 'zombossmech_dark' else 'dark_imp'
        types['objects'].append({'objclass': 'ZombieType', 'aliases': [alias], 'uid': uid, 'objdata': actor})
    changes = {}
    for path, doc in zip(paths, (types, sheets)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes, set())
