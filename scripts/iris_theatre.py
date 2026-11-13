"""Translate the authored theatre paths and upgrade trees into owned schemas.

Paths are derived from adjacent authored carpet cells, never screen-space
straight lines. This adapter does not enable a level until its native module
and actor classes have been registered by the build.
"""
from collections import deque
from copy import deepcopy
import math
import re

from iris_dark_levels import adapt_level, without_grades

ROAD_LIMIT = 45
TREE_LIMIT = 4
UPGRADE_LIMIT = 3
THEATRE_TYPES = tuple('zombie_towerdefend_' + s for s in (
    'normal', 'helmet', 'bucket', 'knight', 'jester', 'gargantuar',
    'wizard', 'wolf_fire', 'wolf_imp', 'boss'))
ROAD_IMAGES = tuple('IMAGE_BACKGROUNDS_THEATRE_DARK_RUG_' + s for s in (
    'BOTOOM_LEFT', 'BOTOOM_RIGHT', 'D_TOP', 'LEFT', 'TOP_CENTRE',
    'TOP_LEFT', 'TOP_RIGHT'))
TOWER_PLANTS = (
    'bloomerang', 'bonkchoy', 'citron', 'coconutcannon', 'fumeshroom',
    'laser_bean', 'lightningreed', 'melonpult', 'peanut', 'peashooter',
    'puffshroom', 'repeater', 'snapdragon', 'snowpea', 'splitpea',
    'starfruit', 'threepeater', 'wintermelon')
TOWER_GROUPS = dict(zip(TOWER_PLANTS, (
    'PlantBloomerang', 'PlantBonkchoy', 'PlantCitron', 'PlantCoconutCannon',
    'PlantFumeshroom', 'PlantLaserBean', 'PlantLightningReed', 'PlantMelonpult',
    'PlantPeanut', 'PlantPeashooter', 'PlantPuffshroom', 'PlantRepeater',
    'PlantSnapdragon', 'PlantSnowPea', 'PlantSplitpea', 'PlantStarFruit',
    'PlantThreepeater', 'PlantWinterMelon')))


def spawn_variant(name, sun):
    if name not in THEATRE_TYPES or not isinstance(sun, int) or not 0 <= sun <= 10000:
        raise ValueError('Unreviewed theatre actor/drop')
    return 'iris_theatre_' + name.removeprefix('zombie_towerdefend_') + '_sun_' + str(sun)


def theatre_settings(source):
    settings, = [o['objdata'] for o in source['objects']
                 if o['objclass'] == 'TowerDefendProperties']
    if set(settings) - {'HouseName', 'HousePopAnim',
                        'HitpointsPercentAddPerWave', 'BossSkills', 'Trees', 'Roads'}:
        raise ValueError('Unreviewed theatre properties')
    house = settings.get('HouseName', 'house_1')
    if house not in ('house_1', 'house_2', 'house_3'):
        raise ValueError('Unported theatre house ' + house)
    house_number = int(house[-1])
    art = re.fullmatch(r'POPANIM_TOWERDEFEND_HOUSE_PIG_([123])', settings['HousePopAnim'])
    if not art:
        raise ValueError('Unreviewed theatre house animation')
    growth = settings.get('HitpointsPercentAddPerWave', 0)
    if not math.isfinite(growth) or growth < 0:
        raise ValueError('Invalid authored theatre wave growth')
    skills = settings['BossSkills']
    if not skills or len(skills) > 8 or any(s not in ('intro', 'fire', 'blow') for s in skills):
        raise ValueError('Unreviewed theatre wolf sequence')
    roads = settings['Roads']
    if not 1 <= len(roads) <= ROAD_LIMIT:
        raise ValueError('Invalid theatre road count')
    cells = {}
    for road in roads:
        if set(road) != {'GridX', 'GridY', 'Img'}:
            raise ValueError('Unreviewed theatre road fields')
        x, y = road['GridX'], road['GridY']
        if not isinstance(x, int) or not isinstance(y, int) or not (0 <= x < 9 and 0 <= y < 5):
            raise ValueError('Theatre road outside the lawn')
        if (x, y) in cells:
            raise ValueError('Duplicate theatre road cell')
        if road['Img'] not in ROAD_IMAGES:
            raise ValueError('Unreviewed theatre road image')
        cells[x, y] = road['Img']
    # The original house sits at (1,4), with the exit carpet at (0,4).
    # Orient each cell toward this exit using the shortest adjacent path.
    # This handles the two authored entrances without crossing empty ground.
    goal = (0, 4)
    if goal not in cells:
        raise ValueError('Theatre house has no road connection')
    distances, queue = {goal: 0}, deque([goal])
    while queue:
        x, y = queue.popleft()
        for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if point in cells and point not in distances:
                distances[point] = distances[x, y] + 1
                queue.append(point)
    if len(distances) != len(cells):
        raise ValueError('Disconnected authored theatre carpet')
    trees = settings['Trees']
    if not 1 <= len(trees) <= TREE_LIMIT:
        raise ValueError('Theatre upgrade tree capacity exceeded')
    result = {'HouseKind': int(art[1]), 'HouseHitpoints': house_number + 2,
              'WaveHealthIncrement': growth, 'TreeCount': len(trees),
              'BossSkillCount': len(skills),
              'ResourceGroupNames': ['Tower_Defend_Group',
                                     'DelayLoad_Background_Theatre_Dark']}
    for i, skill in enumerate(skills):
        result['BossSkill' + str(i)] = ('intro', 'fire', 'blow').index(skill)
    for x in range(9):
        for y in range(5):
            index = x * 5 + y
            point = (x, y)
            result[f'Road{index:02}Distance'] = distances.get(point, -1)
            if point in cells:
                result[f'Road{index:02}Image'] = ROAD_IMAGES.index(cells[point])
    plants = set()
    for i, tree in enumerate(trees):
        if set(tree) != {'Infos'} or not 1 <= len(tree['Infos']) <= UPGRADE_LIMIT:
            raise ValueError('Unreviewed theatre upgrade tree')
        result[f'Tree{i}Count'] = len(tree['Infos'])
        for j, info in enumerate(tree['Infos']):
            if set(info) != {'cost', 'launchtimepercent', 'name'}:
                raise ValueError('Unreviewed theatre upgrade fields')
            if not isinstance(info['cost'], int) or info['cost'] < 0:
                raise ValueError('Invalid theatre upgrade cost')
            cooldown = info['launchtimepercent']
            if not math.isfinite(cooldown) or cooldown <= 0:
                raise ValueError('Invalid theatre local attack interval')
            name = info['name']
            if name not in TOWER_PLANTS:
                raise ValueError('Unported theatre plant identity ' + name)
            plants.add(name)
            result[f'Tree{i}Step{j}Plant'] = TOWER_PLANTS.index(name)
            result[f'Tree{i}Step{j}Cost'] = info['cost']
            result[f'Tree{i}Step{j}Interval'] = cooldown
    result['ResourceGroupNames'].extend(TOWER_GROUPS[name] for name in sorted(plants))
    return result, plants


def adapt_theatre_level(source, policy):
    settings, plants = theatre_settings(source)
    source = without_grades(deepcopy(source))
    definition, = [o['objdata'] for o in source['objects']
                   if o['objclass'] == 'LevelDefinition']
    intro_refs = {f'RTID({a}@CurrentLevel)' for o in source['objects']
                  if o['objclass'] == 'TowerDefendIntroProperties'
                  for a in o.get('aliases', [])}
    definition['Modules'] = [r for r in definition['Modules'] if r not in intro_refs]
    definition['Modules'].insert(0, 'RTID(StandardIntro@LevelModules)')
    # The native protection condition owns defeat and serializes the house.
    definition['Modules'].append('RTID(IrisTheatreHouse@CurrentLevel)')
    definition['StageModule'] = 'RTID(IrisTheatreStage@LevelModules)'
    source['objects'] = [o for o in source['objects']
                         if o['objclass'] != 'TowerDefendIntroProperties']
    variants = {}
    for obj in source['objects']:
        if obj['objclass'] == 'TowerDefendProperties':
            obj['objclass'] = 'IrisTheatreProperties'
            obj['objdata'] = settings
        if obj['objclass'] == 'WaveGeneratorProperties':
            # Iris's WaveData has no SunDrop member. Encode that authored
            # per-spawn value in a private type/sheet pair instead of silently
            # dropping it, averaging it, or changing the ordinary zombie type.
            for wave in obj['objdata']['Waves']:
                for spawn in wave.get('Zombies', []):
                    match = re.fullmatch(r'RTID\(([^@]+)@ZombieTypes\)', spawn['Type'])
                    if not match:
                        raise ValueError('Invalid theatre actor reference')
                    name, sun = match[1], spawn.pop('SunDrop', 0)
                    variant = spawn_variant(name, sun)
                    variants[variant] = (name, sun)
                    spawn['Type'] = f'RTID({variant}@ZombieTypes)'
            for entry in obj['objdata'].get('AddToZombiePool', []):
                match = re.fullmatch(r'RTID\(([^@]+)@ZombieTypes\)', entry['Type'])
                if not match:
                    raise ValueError('Invalid theatre pool reference')
                variant = spawn_variant(match[1], 0)
                variants[variant] = (match[1], 0)
                entry['Type'] = f'RTID({variant}@ZombieTypes)'
    source['objects'].append({'objclass': 'ProtectThePlantChallengeProperties',
        'aliases': ['IrisTheatreHouse'], 'objdata': {
            'MustProtectCount': 1, 'Plants': [{
                'PlantType': 'iris_theatre_house_' + str(settings['HouseKind']),
                'GridX': 0, 'GridY': 4}]}})
    adapted = adapt_level(source, policy=policy)
    definition = next(o['objdata'] for o in adapted['objects']
                      if o['objclass'] == 'LevelDefinition')
    definition['Description'] = '[IRIS_THEATRE_DESCRIPTION]'
    generator, = [o['objdata'] for o in adapted['objects']
                   if o['objclass'] == 'WaveGeneratorProperties']
    for wave in generator['Waves']:
        for spawn in wave.get('Zombies', []):
            row = spawn.get('Row', '?')
            if row == '?':
                raise ValueError('Theatre spawn requires an authored entrance')
            row = int(row) - 1
            if not 0 <= row < 5 or settings[f'Road{40 + row:02}Distance'] < 0:
                raise ValueError('Theatre spawn has no carpet entrance')
    bank, = [o['objdata'] for o in adapted['objects']
             if o['objclass'] == 'SeedBankProperties']
    starts = [TOWER_PLANTS[settings[f'Tree{i}Step0Plant']] for i in range(settings['TreeCount'])]
    if sorted(bank.get('PresetPlantList', [])) != sorted(starts):
        raise ValueError('Theatre seed packets differ from upgrade roots')
    return adapted, plants, variants


def restore_theatre_resources(raw, aster_apk, read_index, write_index, decoder, encoder):
    """Install separate theatre art/types; ordinary campaign types are untouched."""
    from contextlib import closing
    from io import StringIO
    from zipfile import ZipFile
    import json
    from index_texture_prefetch import ResourceZip
    from iris_dark_ages import Importer
    from iris_future_gargantuar import aster_properties
    from iris_future_world import read_rton
    from rsb_local import ResourceBundle
    importer = Importer(raw, read_index, write_index, decoder)
    # PlantType::GetResourceGroups requests the framework's own group, in
    # addition to PlantAudioGroups. The generic house uses the native base
    # framework, whose group was trimmed because stock packets use subclasses.
    if 'PlantFramework' not in importer.names:
        path = r'PROPERTIES\IRIS_THEATRE_HOUSE_FRAMEWORK.TXT'
        importer.simple({'type': 'simple', 'id': 'PlantFramework', 'resources': [
            {'type': 'File', 'id': 'RESFILE_IRIS_THEATRE_HOUSE_FRAMEWORK',
             'path': ['properties', 'iris_theatre_house_framework.txt']}]},
            {path: b'Native generic plant framework for the theatre house\n'}, {})
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        cache = {}
        def bundle(name):
            if name not in cache:
                path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
                cache[name] = ResourceBundle(archive.read(path), read_index, write_index)
            return cache[name]
        art = bundle('dark')
        for name in ('DelayLoad_Background_Theatre_Dark', 'Tower_Defend_Group'):
            importer.root(art, name, decoder)
        donor = bundle('dynamic')
        donor_types = aster_properties(donor, r'PACKAGES\ZOMBIETYPES.RTON', decoder)
        donor_sheets = aster_properties(donor, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
        donor_modules = aster_properties(donor, r'PACKAGES\LEVELMODULES.RTON', decoder)
        variants = {}
        for name in ('dark6', *(f'dark_challenge_{side}_{part}'
                     for side in ('sunbombs', 'threepigs') for part in ('a', 'b', 'c'))):
            doc = aster_properties(donor, 'PACKAGES\\LEVELS\\' + name.upper() + '.RTON', decoder)
            policy = {'omitted_modules': [], 'zombie_replacements': {}}
            _, _, entries = adapt_theatre_level(doc, policy)
            variants.update(entries)
        zombie_art = bundle('zombie3')
        for name in ('ZombieWolfFireGroup', 'ZombieWolfImpGroup', 'ZombieWolfBossGroup'):
            importer.root(zombie_art, name, decoder)
        # Iris retains the Starfruit type and framework but trimmed its art.
        # It is reachable as a theatre upgrade, even when absent from seeds.
        plant_art = bundle('plant1')
        star, = [g['id'] for g in plant_art.manifest(decoder)['groups']
                 if g['id'].lower() == 'plantstarfruit']
        if star != TOWER_GROUPS['starfruit']:
            raise ValueError('Review the Starfruit resource spelling: ' + star)
        if star not in importer.names:
            importer.root(plant_art, star, decoder)
        if 'PlantStarfruitAudio' not in importer.names:
            from iris_scaredy_audio import convert_plant_bank
            from pathlib import Path
            original=ResourceBundle(raw,read_index,write_index)
            group=deepcopy(next(g for g in plant_art.manifest(decoder)['groups'] if g['id']=='PlantStarfruitAudio'))
            resource,=group['resources'];path='\\'.join(resource['path']).upper()
            global_path=r'SOUNDBANKS\GLOBAL_DATA.BNK'
            recipe=json.loads((Path(__file__).resolve().parents[1]/'src/dark/starfruit-audio-v88.json').read_text())
            bank=plant_art.read(plant_art.group_for(path),path)
            importer.simple(group,{path:convert_plant_bank(original.read(original.group_for(global_path),global_path),bank,recipe)},{})
        # Ordinary dark actor art has already been imported earlier in the
        # pipeline; effect-only groups are imported from their owning bundle.
        groups = {g['id'] for g in importer.manifest['groups']}
        for name in ('PlantBeFired', 'ZombieSpeedUp'):
            if name not in groups:
                owner = next((bundle(b) for b in ('zombie3', 'dark', 'plant2')
                              if name in {g['id'] for g in bundle(b).manifest(decoder)['groups']}), None)
                if owner is None:
                    raise ValueError('Missing theatre effect group ' + name)
                importer.root(owner, name, decoder)
    result = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\ZOMBIETYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON',
             r'PACKAGES\PLANTTYPES.RTON', r'PACKAGES\LEVELMODULES.RTON']
    types, sheets, plants, modules = [read_rton(result, p, decoder) for p in paths]
    def find(doc, name):
        return next(o for o in doc['objects'] if name in o.get('aliases', []))
    allowed = {key for obj in sheets['objects'] if obj.get('objclass') == 'ZombiePropertySheet'
               for key in obj['objdata'] if not key.startswith('#')}
    used_uids = {o.get('uid') for o in types['objects']}
    # Stable sorting makes the identities deterministic across resource builds.
    for i, (alias, (name, sun)) in enumerate(sorted(variants.items())):
        source = deepcopy(find(donor_types, name)['objdata'])
        sheet_name = source['Properties'].split('(')[1].split('@')[0]
        source_sheet = find(donor_sheets, sheet_name)['objdata']
        props = {k: deepcopy(v) for k, v in source_sheet.items() if k in allowed}
        kind = THEATRE_TYPES.index(name)
        props.update(IrisTheatreKind=kind, IrisTheatreSunDrop=sun,
                     IrisTheatreHouseDamage=source_sheet['EatDPS'],
                     HeadDropFraction=-1, ArmDropFraction=-1, CanSpawnPlantFood=False)
        prop_alias = 'IrisTheatre_' + alias
        sheets['objects'].append({'objclass': 'IrisTheatreZombieProperties',
                                  'aliases': [prop_alias], 'objdata': props})
        # Keep Iris's existing statistics enum while the private kind selects
        # authored theatre behavior, armour and house damage.
        source.update(TypeName='dark', ZombieClass='ZombieIrisTheatre',
                      AnimRigClass='ZombieAnimRig_DarkBasic' if kind < 4 else 'ZombieAnimRig',
                      Properties=f'RTID({prop_alias}@PropertySheets)')
        uid = f'1.{2100 + i}.1'
        if uid in used_uids:
            raise ValueError('Theatre zombie identity collision')
        used_uids.add(uid)
        types['objects'].append({'objclass': 'ZombieType', 'uid': uid,
                                 'aliases': [alias], 'objdata': source})
    wallnut = find(plants, 'wallnut')['objdata']
    base = find(sheets, wallnut['Properties'].split('(')[1].split('@')[0])['objdata']
    for kind in (1, 2, 3):
        alias = 'iris_theatre_house_' + str(kind)
        prop_alias = 'IrisTheatreHouse' + str(kind)
        house = {k: deepcopy(v) for k, v in wallnut.items()
                 if k in ('TypeName', 'HomeWorld')}
        house.update(TypeName=alias, PlantFramework='PlantFramework', AnimRigClass='PlantAnimRig',
                     PopAnim='POPANIM_TOWERDEFEND_HOUSE_PIG_' + str(kind),
                     Properties=f'RTID({prop_alias}@PropertySheets)',
                     PlantAudioGroups=['Tower_Defend_Group'])
        plants['objects'].append({'objclass': 'PlantType', 'aliases': [alias], 'objdata': house})
        props = {k: deepcopy(base[k]) for k in ('PlantGridType', 'ArtCenter') if k in base}
        props.update(Cost=0, Hitpoints=kind + 2, PacketCooldown=0,
                     Actions=[], StartingCooldown=0)
        sheets['objects'].append({'objclass': 'PlantPropertySheet',
                                  'aliases': [prop_alias], 'objdata': props})
    stage = deepcopy(find(donor_modules, 'TheatreDarkStage'))
    stage['aliases'] = ['IrisTheatreStage']
    # Use Iris's retained dark background mapping and only swap the authored
    # theatre images; old ten-row street-cell declarations are not Iris grids.
    native_stage = find(modules, 'DarkStage')['objdata']
    data = deepcopy(native_stage)
    for key in ('BackgroundResourceGroup', 'BackgroundImagePrefix',
                'BackgroundImageLeft', 'BackgroundImageMiddle', 'BackgroundImageRight'):
        data[key] = stage['objdata'][key]
    data['ResourceGroupNames'] = list(dict.fromkeys(
        data.get('ResourceGroupNames', []) + ['DelayLoad_Background_Theatre_Dark', 'Tower_Defend_Group']))
    data['GroupsToUnloadForAds'] = ['DelayLoad_Background_Theatre_Dark']
    stage['objdata'] = data
    modules['objects'].append(stage)
    changes = {}
    for path, doc in zip(paths, (types, sheets, plants, modules)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes, set())
