"""Adapt audited Aster campaign levels to Iris, without ranked actors."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

CATALOG = Path(__file__).resolve().parents[1] / 'src/dark/levels.json'
GRADE_FIELDS = {'Level', 'iLevel'}
POLICY = Path(__file__).resolve().parents[1] / 'src/dark/international-policy.json'
PENDING_LEVEL_COMMENT = 'Iris map metadata only: level implementation pending'
GENERATOR_FIELDS = {'HeroProps', 'Waves', 'ZombiePool', 'FlagWaveInterval', 'WaveCount',
                    'WaveSpendingPointIncrement', 'WaveSpendingPoints', 'SpawnColStart',
                    'SpawnColEnd', 'SpawnCount', 'IgnoreFlagCarriers'}
WAVE_FIELDS = {'DisableRandomSpawns', 'SpawnColStart', 'SpawnColEnd', 'SpawnPlantFoodCount',
               'WavePointStart', 'WavePointIncrement', 'WavePointOverride', 'Event', 'Zombies',
               'AddToZombiePool', 'RemoveFromZombiePool', 'AddToSeedPool', 'RemoveFromSeedPool'}


def validate_wave_schema(generator):
    """Reject silently ignored wave data against the actual Iris reflection."""
    def check(data, fields, context):
        unknown = {k for k in data if not k.startswith('#')} - fields
        if unknown:
            raise ValueError(f'{context}: unsupported Iris fields {sorted(unknown)}')
    check(generator, GENERATOR_FIELDS, 'WaveGeneratorProperties')
    for number, wave in enumerate(generator.get('Waves', []), 1):
        check(wave, WAVE_FIELDS, f'Wave {number}')
        for spawn in wave.get('Zombies', []):
            check(spawn, {'Row', 'HasPlantFood', 'Loot', 'Type'}, f'Wave {number} zombie')
            if not isinstance(spawn.get('Row', '?'), str):
                raise ValueError(f'Wave {number}: Iris zombie Row must be a string')
        for pool in ('AddToZombiePool', 'RemoveFromZombiePool'):
            for entry in wave.get(pool, []):
                check(entry, {'Cost', 'Weight', 'Overridden', 'Type'}, f'Wave {number} {pool}')


def pending_level(source):
    """Supply LevelInfo for star-count/map queries without a playable level."""
    original = next(o['objdata'] for o in source['objects'] if o.get('objclass') == 'LevelDefinition')
    definition = {k: deepcopy(v) for k, v in original.items() if k in ('LevelNumber', 'LevelIndex')}
    definition.update(Name='[DARKAGES_LEVEL_NAME]', Description='[IRIS_DARK_LEVEL_PENDING]',
                      StageModule='RTID(DarkStage@LevelModules)', Modules=[])
    return {'version': 1, '#comment': PENDING_LEVEL_COMMENT,
            'objects': [{'objclass': 'LevelDefinition', 'objdata': definition}]}


def reachable_objects(level):
    """Discard orphaned prototype modules before the engine instantiates them."""
    objects = level['objects']
    selected = [o for o in objects if o.get('objclass') == 'LevelDefinition']
    refs = set(re.findall(r'RTID\(([^@]+)@CurrentLevel\)', json.dumps(selected)))
    seen = set()
    while refs - seen:
        for alias in list(refs - seen):
            seen.add(alias)
            matches = [o for o in objects if alias in o.get('aliases', [])]
            if len(matches) != 1:
                raise ValueError(f'Expected exactly one local object: {alias}')
            obj = matches[0]
            if obj not in selected:
                selected.append(obj)
            refs.update(re.findall(r'RTID\(([^@]+)@CurrentLevel\)', json.dumps(obj)))
    return [o for o in objects if o in selected]


def empty_minigame(source):
    """Keep the node traversable without loading either China-only minigame."""
    source_def = next(o['objdata'] for o in source['objects'] if o.get('objclass') == 'LevelDefinition')
    definition = {k: deepcopy(v) for k, v in source_def.items() if k in ('LevelNumber', 'LevelIndex')}
    definition.update(Name='[DARKAGES_LEVEL_NAME]', Description='[IRIS_DARK_MINIGAME_PLACEHOLDER]',
                      Loot='RTID(DefaultLoot@LevelModules)', StageModule='RTID(DarkStage@LevelModules)',
                      NormalPresentTable='egypt_normal_01', ShinyPresentTable='egypt_shiny_01',
                      Modules=['RTID(StandardIntro@LevelModules)', 'RTID(DarkMowers@LevelModules)',
                               'RTID(ZombiesDeadWinCon@LevelModules)', 'RTID(DefaultZombieWinCondition@LevelModules)',
                               'RTID(SeedBank@CurrentLevel)', 'RTID(Waves@CurrentLevel)'])
    return {'version': 1, 'objects': [
        {'objclass': 'LevelDefinition', 'objdata': definition},
        {'objclass': 'SeedBankProperties', 'aliases': ['SeedBank'],
         'objdata': {'SelectionMethod': 'preset', 'PresetPlantList': ['peashooter']}},
        {'objclass': 'WaveGeneratorProperties', 'aliases': ['Waves'],
         'objdata': {'WaveCount': 1, 'FlagWaveInterval': 1, 'WaveSpendingPoints': 0,
                     'AddToZombiePool': [], 'Waves': [{'DisableRandomSpawns': True, 'Zombies': []}]}}
    ]}


def without_grades(value):
    if isinstance(value, dict):
        return {k: without_grades(v) for k, v in value.items() if k not in GRADE_FIELDS}
    if isinstance(value, list):
        return [without_grades(v) for v in value]
    return value


def source_hash(level):
    return sha256(json.dumps(level, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def adapt_level(source, *, policy=None):
    level = without_grades(deepcopy(source))
    if policy is None:
        policy = json.loads(POLICY.read_text(encoding='utf-8'))
    removed = {f'RTID({a}@CurrentLevel)' for o in level['objects']
               if o.get('objclass') in policy['omitted_modules'] for a in o.get('aliases', [])}
    for o in level['objects']:
        if o.get('objclass') == 'LevelDefinition':
            o['objdata']['Modules'] = [r for r in o['objdata']['Modules'] if r not in removed]
    level['objects'] = reachable_objects(level)
    text = json.dumps(level)
    for old, new in policy['zombie_replacements'].items():
        text = text.replace(f'RTID({old}@ZombieTypes)', f'RTID({new}@ZombieTypes)')
    level = json.loads(text)
    objects = level['objects']
    random_modules = [o for o in objects if o['objclass'] == 'RandZombieProperties']
    random_refs = {f'RTID({a}@CurrentLevel)' for o in random_modules for a in o['aliases']}
    definition, = [o['objdata'] for o in objects if o['objclass'] == 'LevelDefinition']
    definition['Modules'] = [r for r in definition['Modules'] if r not in random_refs]
    definition.update(Name='[DARKAGES_LEVEL_NAME]', Description='[PLAYERS_TRIP_TO_DARKAGES]',
                      NormalPresentTable='egypt_normal_01', ShinyPresentTable='egypt_shiny_01')
    if 'FirstIntroNarrative' in definition:
        narrative = definition['FirstIntroNarrative']
        if narrative == 'DARK_INTRO_SUNSHROOM_CHAT':
            definition['FirstIntroNarrative'] = 'DARKAGES_INTRO_FIRSTLEVEL'
        elif narrative not in policy.get('native_narratives', []):
            raise ValueError('Unreviewed Aster narrative')
    generator, = [o['objdata'] for o in objects if o['objclass'] == 'WaveGeneratorProperties']
    # Iris's initial pool is ZombiePool. AddToZombiePool is only reflected
    # inside a WaveDefinition; the Aster root spelling is silently ignored.
    if 'AddToZombiePool' in generator:
        if 'ZombiePool' in generator:
            raise ValueError('Mixed initial zombie pool formats')
        generator['ZombiePool'] = generator.pop('AddToZombiePool')
    generator.pop('LevelXMLFilename', None)  # not an Iris property
    if generator.get('IsRiseFromGroundMode') is False:
        generator.pop('IsRiseFromGroundMode')
    if len(generator['Waves']) != generator['WaveCount']:
        raise ValueError('Incomplete explicit wave list')
    if random_modules:
        # Iris WaveData reflection (ELF 0x58261c) registers both fields as
        # vector<ZombiePoolData>. Preserve each Aster pool entry's wave range.
        entries = [r for o in random_modules for r in o['objdata']['RandZombieList']]
        generator['ZombiePool'] = []
        previous = set()
        for number, wave in enumerate(generator['Waves'], 1):
            active = {e['Type'] for e in entries if e['FirstWave'] <= number <= e['LastWave']}
            for field, types in [('AddToZombiePool', active - previous),
                                 ('RemoveFromZombiePool', previous - active)]:
                if field in wave:
                    raise ValueError('Unreviewed overlapping pool rules')
                if types:
                    wave[field] = [{'Type': t} for t in sorted(types)]
            previous = active
    level['objects'] = [o for o in objects if o not in random_modules]
    for obj in level['objects']:
        if obj['objclass'] == 'ZombiePotionModuleProperties':
            from iris_potions import adapt_potion_module
            obj['objdata'] = adapt_potion_module(obj['objdata'])
        if obj['objclass'] == 'WarMistProperties':
            groups = obj['objdata'].setdefault('ResourceGroupNames', [])
            if 'War_Misty' not in groups:
                groups.append('War_Misty')
        if obj['objclass'] == 'GravestoneProperties':
            data = obj['objdata']
            if 'Overrides' in data:
                if 'ForceSpawnData' in data:
                    raise ValueError('Mixed gravestone placement formats')
                data['ForceSpawnData'] = [{'GridX': e['mX'], 'GridY': e['mY'], 'TypeName': e['TypeName']}
                                         for e in data.pop('Overrides')]
            for grave in obj['objdata'].get('ForceSpawnData', []):
                if grave.get('TypeName') == 'dark_gravestone':
                    grave['TypeName'] = 'gravestone_dark'
        if obj['objclass'] == 'SeedBankProperties':
            bank = obj['objdata']
            if any(not isinstance(p, str) for p in bank.get('PresetPlantList', [])):
                raise ValueError('Iris seed banks require plain plant names')
    validate_wave_schema(generator)
    return level


def selected_levels(donor, decoder, read_properties):
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    output = {}
    for entry in catalog['levels']:
        if entry['status'] not in ('adapted', 'placeholder') and not entry.get('map_entry'):
            continue
        path = 'PACKAGES\\LEVELS\\' + entry['file'].upper() + '.RTON'
        source = read_properties(donor, path, decoder)
        if source_hash(source) != entry['sha256']:
            raise ValueError(f'Aster level changed since audit: {path}')
        if entry['status'] == 'placeholder':
            output[path] = empty_minigame(source)
        elif entry['status'] == 'adapted':
            output[path] = adapt_level(source)
        else:
            output[path] = pending_level(source)
    return output


def connect_map(data, levels):
    """Preserve the authored route, including locked sites still being ported."""
    available = {path.rsplit('\\', 1)[-1].split('.')[0].lower() for path, doc in levels.items()
                 if doc.get('#comment') != PENDING_LEVEL_COMMENT}
    authored = data['m_eventList']
    events = [e for e in authored if e['m_eventType'] == 'level']
    mapped = {e['m_dataString'].lower() for e in events}
    # Aster retains older copies of the two minigames in its package, but
    # its authored map uses threepigs/oakshooter. Do not invent new islands.
    archived = {f'dark_challenge_{name}_{suffix}'
                for name in ('sunbombs', 'single') for suffix in ('a', 'b', 'c')}
    if available - mapped - archived:
        raise ValueError(f'Imported levels have no Aster map node: {available - mapped - archived}')
    # These authored intermediate sites keep the route on the paths. Only
    # sunshroom is an implemented reward; other Aster-only unlocks are plain
    # native path nodes until their rewards have an international equivalent.
    connectors = {'dark_rewardplantbox_sunshroom', 'dark_rewardplantbox_streetlamp',
                  'dark_rewardplantbox_coffeebean', 'dark_rewardupgrade_mower'}
    gates = {'dark_keygate_threepigs', 'dark_keygate_chal_hypnoshroom',
             'dark_keygate_chal_oakshooter'}
    events.extend(e for e in authored if e['m_name'] in connectors | gates)
    for event in events:
        event.update(m_autoVisible=True, m_visibleFrom='')
        if event['m_name'] == 'dark_level_91':
            event['m_unlockedFrom'] = ''
        if event['m_name'] in connectors - {'dark_rewardplantbox_sunshroom'}:
            event.update(m_eventType='path_node', m_dataString='')
        if event['m_name'] in gates:
            event['m_cost'] = 0

    # Missing implementations remain real, locked level markers at their
    # original coordinates. Do not splice distant playable nodes together or
    # turn ordinary campaign levels into empty victories. A hidden key gate
    # supplies the engine's existing unlock predicate without a dangling ref.
    blocker = deepcopy(next(e for e in authored if e['m_name'] == 'dark_stargate_exit'))
    bounds = data['m_boundingRect']
    blocker.update(m_name='iris_dark_port_pending', m_eventType='key_gate',
                   m_position={'x': float(bounds['mX'] + 1), 'y': float(bounds['mY'] + 1)}, m_eventId=200,
                   m_cost=2147483647, m_autoVisible=False, m_parentEvent='',
                   m_unlockedFrom='', m_visibleFrom='', m_dataString='', m_displayText='')
    for event in events:
        if event['m_eventType'] == 'level' and event['m_dataString'].lower() not in available:
            event.update(m_unlockedFrom=blocker['m_name'],
                         m_displayText=event['m_displayText'] + '·待移植')
    data['m_eventList'] = events + [blocker]


def validate_levels(levels, native_documents):
    aliases = {}
    for package, doc in native_documents.items():
        aliases[package.lower()] = {a for o in doc['objects'] for a in o.get('aliases', [])}
    for path, level in levels.items():
        current = {a for o in level['objects'] for a in o.get('aliases', [])}
        for name, package in re.findall(r'RTID\(([^@]+)@([^\)]+)\)', json.dumps(level)):
            available = current if package.lower() == 'currentlevel' else aliases.get(package.lower())
            if available is None or name not in available:
                raise ValueError(f'{path}: unresolved RTID({name}@{package})')


def resize_world_nav(ui, worlds):
    count = sum(not w.get('Hidden', False) and not w.get('ComingSoon', False)
                and not w.get('Disabled', False) for w in worlds)
    # Native icon layout: 57 units/icon + 10 units/gap (ELF 0x5d6640).
    # Keep the stock 12-unit total inner padding. Edge-anchored map/zoom
    # controls and the native three-piece background follow this width.
    width = max(270, count * 57 + max(0, count - 1) * 10 + 12)
    matches = [o['objdata'] for o in ui['objects'] if 'UIWorldMapNavBar' in o.get('aliases', [])]
    navbar, = matches
    navbar['VirtualWidth'] = width
    return width
