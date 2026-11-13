"""Aster Ice/Fire-shroom growth art and unranked stage data.

Each stage has its own authored PAM view. The native adapter changes the
existing Plant through Iris's Sun-shroom mutation path, retaining its UID.
Hidden stage types cannot become additional seed packets or rank upgrades.
"""
from contextlib import closing
from copy import deepcopy
from io import StringIO
import json
from zipfile import ZipFile

from index_texture_prefetch import ResourceZip
from iris_cn_scaredy import rename_main_label
from iris_dark_ages import Importer
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from rsb_local import ResourceBundle


class GrowthAssets:
    def __init__(self, source, decoder):
        self.source = source
        self.doc = deepcopy(source.manifest(decoder))
        self.views = {}
        for group in self.doc['groups']:
            for resource in list(group.get('resources', [])):
                if resource['id'] == 'POPANIM_EFFECTS_FIRESHROOM_BULLET':
                    clone = deepcopy(resource)
                    original = '\\'.join(resource['path']).upper()
                    clone['id'] = 'POPANIM_EFFECTS_IRIS_FIRE_STONE'
                    clone['path'][-1] = 'iris_fire_stone.pam'
                    self.views['\\'.join(clone['path']).upper()] = (original, 'STONE', 0)
                    group['resources'].append(clone)
                for species in ('ICE', 'FIRE'):
                    if resource['id'] != f'POPANIM_PLANT_{species}SHROOM':
                        continue
                    path = '\\'.join(resource['path']).upper()
                    self.views[path] = (path, species, 1)
                    for stage in (2, 3):
                        clone = deepcopy(resource)
                        clone['id'] += f'_IRIS_STAGE{stage}'
                        clone['path'][-1] = f'iris_{species.lower()}shroom_stage{stage}.pam'
                        self.views['\\'.join(clone['path']).upper()] = (path, species, stage)
                        group['resources'].append(clone)

    def manifest(self, decoder):
        return deepcopy(self.doc)

    def group_for(self, path):
        return self.source.group_for(self.views.get(path, (path,))[0])

    def texture(self, group, path):
        return self.source.texture(group, path)

    def read(self, group, path):
        original, species, stage = self.views.get(path, (path, None, None))
        raw = self.source.read(group, original)
        if species == 'STONE':
            return stone_animation(raw)
        if species:
            idle = 'idle3' if species == 'ICE' and stage == 2 else 'idle'
            raw = rename_main_label(raw, f'{idle}_stage{stage}', 'idle')
            raw = rename_main_label(raw, f'attack_stage{stage}', 'attack')
            if species == 'ICE':
                raw = rename_main_label(raw, f'plantfood_stage{stage}', 'plantfood')
            raw = action_commands(raw)
        return raw


def action_commands(raw):
    """Map Aster's rig-specific stage commands to the selected Iris action.

    In Iris use_action2/3 directly accesses other Action entries. Keeping
    them causes an out-of-range read after growth; the framework already
    selects the proper projectile from this hidden stage's property sheet.
    """
    import struct
    from pam_transform_index import PamIndex
    edits = []
    for sprite in PamIndex(raw).sprites:
        for frame in sprite['frames']:
            for command in ('use_action2', 'use_action3'):
                count = sum(c == command for c, _ in frame['commands'])
                if not count:
                    continue
                marker = struct.pack('<H', len(command)) + command.encode()
                fragment = raw[frame['start']:frame['end']]
                if fragment.count(marker) != count:
                    raise ValueError('Ambiguous growth attack command')
                at = 0
                for _ in range(count):
                    at = fragment.index(marker, at)
                    edits.append((frame['start']+at, len(marker)))
                    at += len(marker)
    replacement = struct.pack('<H', len('use_action')) + b'use_action'
    for at, size in sorted(edits, reverse=True):
        raw = raw[:at]+replacement+raw[at+size:]
    parsed = PamIndex(raw)
    if any(c in ('use_action2', 'use_action3') for s in parsed.sprites
           for f in s['frames'] for c, _ in f['commands']):
        raise ValueError('Unconverted growth attack command')
    return raw


def stone_animation(raw):
    """Join the authored ten-frame fall and 27-frame impact into one clip."""
    import struct
    from pam_transform_index import PamIndex
    raw = rename_main_label(raw, 'anim_stage4_in', 'iris_fire_stone')
    frames = PamIndex(raw).sprites[-1]['frames']
    if frames[75]['label'] != 'iris_fire_stone' or frames[85]['label'] != 'anim_stage4':
        raise ValueError('Fire-stone animation timing changed')
    value = bytearray(raw)
    if not value[frames[84]['start']] & 16:
        raise ValueError('Missing authored fall stop')
    value[frames[84]['start']] &= ~16
    frame = frames[85]
    marker = struct.pack('<H', len('anim_stage4')) + b'anim_stage4'
    fragment = bytes(value[frame['start']:frame['end']])
    if fragment.count(marker) != 1:
        raise ValueError('Ambiguous impact animation label')
    value[frame['start']] &= ~8
    at = frame['start'] + fragment.index(marker)
    del value[at:at+len(marker)]
    result = bytes(value)
    parsed = PamIndex(result)
    if len(parsed.sprites[-1]['frames']) != 112:
        raise ValueError('Fire-stone frame commands changed')
    return result


def stage_data(species, source_type, source_props):
    """Select explicit tier-one values; never copy level or rank tables."""
    types, sheets = [], []
    for stage, growth in enumerate(source_props['GrowthStages'], 1):
        alias = species if stage == 1 else f'iris_{species}_stage{stage}'
        sheet = f'Iris{species.title()}Stage{stage}'
        kind = {k: deepcopy(source_type[k]) for k in
                ('PlantAudioGroups', 'PopAnim', 'HomeWorld')}
        # v163 still names the later Chinese global freezing group, which
        # is absent from its actual init bundle. Iris owns condition visuals
        # in its native zombie rigs; requesting this nonexistent group blocks
        # the entire asynchronous level loader.
        kind['PlantAudioGroups'] = [g for g in kind['PlantAudioGroups'] if g != 'FreezonEffectGroup']
        if species == 'iceshroom':
            # Zombie::OnConditionAdded(freeze) dereferences this native Iris
            # effect immediately. The group must be loaded even when no
            # Iceberg Lettuce packet happens to be in the player's seed bank.
            kind['PlantAudioGroups'].append('PlantIceburg')
        kind.update(TypeName=alias, PlantFramework='PlantIrisDark',
                    AnimRigClass='PlantAnimRig', Properties=f'RTID({sheet}@PropertySheets)')
        kind['PlantAudioGroups'].insert(0, 'PlantIceShroom' if species == 'iceshroom' else 'PlantFireShroom')
        if stage > 1:
            kind['Enabled'] = False
            kind['PopAnim'] += f'_IRIS_STAGE{stage}'
        props = {k: deepcopy(source_props[k]) for k in
                 ('Cost', 'Hitpoints', 'PacketCooldown', 'StartingCooldown',
                  'PlantGridType', 'ArtCenter', 'PlantStats')}
        action = deepcopy(source_props['Actions'][0])
        action['Projectile'] = growth['Projectile']
        action['SpawnOffset'] = deepcopy(growth['SpawnOffset'])
        # Native Board::SpawnProjectile consumes height separately. The
        # framework callback supplies the audited -0.32 * authored height.
        actions = [action]
        if species == 'iceshroom':
            actions.extend({'Type': 'special', 'Projectile': source_props[key]}
                           for key in ('SplitOneProjectile', 'SplitTwoProjectile'))
        else:
            actions.append({'Type': 'special', 'Projectile': 'RTID(IrisFireStone@ProjectileTypes)'})
        props.update(Actions=actions, PlantFoodDurationSeconds=1,
                     PlantFoodPlayCount=1)
        types.append({'objclass': 'PlantType', 'aliases': [alias], 'objdata': kind})
        sheets.append({'objclass': 'PlantPropertySheet', 'aliases': [sheet], 'objdata': props})
    return types, sheets


def restore_growth_shrooms(raw, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    original = ResourceBundle(raw, read_index, write_index)
    importer = Importer(raw, read_index, write_index, decoder)
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        donor = GrowthAssets(bundle('plant2'), decoder)
        for root in ('PlantIceShroom', 'PlantFireShroom'):
            importer.root(donor, root, decoder)
        importer.images(original, bundle('uiactive'), 'UIImages_Dynamic', 'UIImages',
                        ['IMAGE_UI_PACKETS_ICESHROOM', 'IMAGE_UI_PACKETS_FIRESHROOM'], decoder,
                        reference='IMAGE_UI_PACKETS_SUNSHROOM', etc1tool=etc1tool)
        dynamic = bundle('dynamic')
        source_types = aster_properties(dynamic, r'PACKAGES\PLANTTYPES.RTON', decoder)
        source_props = aster_properties(dynamic, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
        source_shots = aster_properties(dynamic, r'PACKAGES\PROJECTILETYPES.RTON', decoder)
    result = ResourceBundle(importer.finish(), read_index, write_index)
    groups = {g['id'] for g in result.manifest(decoder)['groups']}
    paths = [r'PACKAGES\PLANTTYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON', r'PACKAGES\PROJECTILETYPES.RTON', r'PACKAGES\GRIDITEMTYPES.RTON']
    types, sheets, shots, grids = [read_rton(result, p, decoder) for p in paths]
    for species, sheet in (('iceshroom', 'IceShroom'), ('fireshroom', 'FireShroom')):
        if any(species in o.get('aliases', []) for o in types['objects']):
            raise ValueError(f'{species} already defined')
        kind = next(o['objdata'] for o in source_types['objects'] if species in o.get('aliases', []))
        props = next(o['objdata'] for o in source_props['objects'] if sheet in o.get('aliases', []))
        new_types, new_sheets = stage_data(species, kind, props)
        for kind in new_types:
            missing = set(kind['objdata']['PlantAudioGroups']) - groups
            if missing:
                raise ValueError(f'Unresolved growth-plant resource groups: {missing}')
        types['objects'].extend(new_types)
        sheets['objects'].extend(new_sheets)
    allowed = {k for o in shots['objects'] if o.get('objclass') == 'ProjectilePropertySheet'
               for k in o['objdata']}
    flags = {v for o in shots['objects'] for v in o.get('objdata', {}).get('CollisionFlags', [])}
    for obj in source_shots['objects']:
        if not any(a.startswith(('IceShroom', 'FireShroom')) for a in obj.get('aliases', [])):
            continue
        shot = deepcopy(obj)
        shot.pop('uid', None)
        source = shot['objdata']
        data = {k: deepcopy(v) for k, v in source.items() if k in allowed}
        shot['objdata'] = data
        # Aster's derived projectile classes have incompatible native ABIs.
        # Iris-specific collision behavior is selected by the private art
        # identity in the native adapter, leaving all stock projectiles alone.
        data['ClassName'] = 'Projectile'
        data['BaseDamage'] = source['BaseDamage']
        if 'InitialVelocity' in data:
            data['InitialVelocity'][1:] = [{'Min': 0.0, 'Max': 0.0}, {'Min': 0.0, 'Max': 0.0}]
        data['CollisionFlags'] = [v for v in source.get('CollisionFlags', []) if v in flags]
        for key in ('DamageType', 'ProjectileType', 'PlantLevelStats'):
            data.pop(key, None)
        shots['objects'].append(shot)
    zero = [{'Min': 0.0, 'Max': 0.0} for _ in range(3)]
    shots['objects'].append({'objclass': 'ProjectilePropertySheet', 'aliases': ['IrisFireStone'],
        'objdata': {'ClassName': 'IrisFireStone', 'BaseDamage': 75, 'SplashDamage': 37,
                    'DamageFlags': ['fire'], 'CollisionFlags': [], 'DiesOnImpact': False,
                    'HasShadow': False, 'InitialVelocity': deepcopy(zero),
                    'InitialAcceleration': deepcopy(zero),
                    'AttachedPAM': 'POPANIM_EFFECTS_IRIS_FIRE_STONE',
                    'AttachedPAMAnimationToPlay': 'iris_fire_stone'}})
    for alias, cls, root in (('iris_ice_hole', 'IrisIceHole', 'PlantIceShroom'),
                             ('iris_fire_wall', 'IrisFireWall', 'PlantFireShroom')):
        if any(alias in o.get('aliases', []) for o in grids['objects']):
            raise ValueError('Growth ground effect already defined')
        grids['objects'].append({'objclass': 'GridItemType', 'aliases': [alias], 'objdata': {
            'TypeName': alias, 'GridItemClass': cls,
            'Properties': 'RTID(IrisGrowthGround@PropertySheets)', 'ResourceGroups': [root]}})
    sheets['objects'].append({'objclass': 'GridItemPropertySheet', 'aliases': ['IrisGrowthGround'],
        'objdata': {'Hitpoints': 1000, 'HitRectOffsetX': -15, 'HitRectOffsetWidth': 30}})
    changes = {}
    for path, doc in zip(paths, (types, sheets, shots, grids)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes, set())
