"""Explicit development-only battle fixture; never used in the main package."""
from io import StringIO
from copy import deepcopy
import json
from iris_future_world import read_rton
from rsb_local import ResourceBundle


def install_fixture(raw, read_index, write_index, decoder, encoder):
    bundle = ResourceBundle(raw, read_index, write_index)
    path = r'PACKAGES\LEVELS\DARK1.RTON'
    level = read_rton(bundle, path, decoder)
    original = next(o['objdata'] for o in level['objects'] if o['objclass'] == 'LevelDefinition')
    definition = deepcopy(original)
    definition.pop('FirstIntroNarrative', None)
    definition['Modules'] = ['RTID(StandardIntro@LevelModules)', 'RTID(DarkMowers@LevelModules)',
                             'RTID(Mist@CurrentLevel)',
                             'RTID(SeedBank@CurrentLevel)', 'RTID(Plants@CurrentLevel)',
                             'RTID(PotionJars@CurrentLevel)',
                             'RTID(PotionSpawner@CurrentLevel)',
                             'RTID(Waves@CurrentLevel)',
                             'RTID(ZombiesDeadWinCon@LevelModules)',
                             'RTID(DefaultZombieWinCondition@LevelModules)']
    # Isolate consumption, native Gargantuar and persistent potion visuals.
    # The preceding fixture's automatic fire wall moved and killed targets.
    plants = [('hypnoshroom', 5, 3), ('hypnoshroom', 5, 4),
              ('peanut', 3, 1), ('sunshroom', 1, 0), ('streetlamp', 2, 2)]
    fixture = {'version': 1, '#comment': 'Development fixture; isolated package only', 'objects': [
        {'objclass': 'LevelDefinition', 'objdata': definition},
        {'objclass': 'SeedBankProperties', 'aliases': ['SeedBank'],
         'objdata': {'SelectionMethod': 'preset',
                     'PresetPlantList': ['iceshroom', 'fireshroom', 'sunshroom',
                                         'oakshooter', 'streetlamp', 'blover']}},
        {'objclass': 'WarMistProperties', 'aliases': ['Mist'],
         'objdata': {'ResourceGroupNames': ['War_Misty'], 'm_iNormValX': 700,
                     'm_iBloverEffectInterval': 15, 'm_iInitMistPosX': 9}},
        {'objclass': 'ProtectThePlantChallengeProperties', 'aliases': ['Plants'],
         'objdata': {'MustProtectCount': 0,
                     'Plants': [{'PlantType': p, 'GridX': x, 'GridY': y} for p, x, y in plants]}},
        {'objclass': 'GravestoneProperties', 'aliases': ['PotionJars'],
         'objdata': {'ForceSpawnData': [{'GridX': x, 'GridY': y,
                                        'TypeName': 'zombiepotion_' + kind}
                                       for kind, y in (('speed', 0), ('toughness', 3))
                                       for x in (6, 7, 8)]}},
        {'objclass': 'ZombiePotionModuleProperties', 'aliases': ['PotionSpawner'],
         'objdata': {'InitialPotionCount': 2, 'MaxPotionCount': 10,
                     'IrisMinSpawnDelay': 3, 'IrisMaxSpawnDelay': 5,
                     'IrisPotionMask': 3, 'ResourceGroupNames': ['GridItemZombiePotion', 'PlantEvilShroomAudio']}},
        {'objclass': 'WaveGeneratorProperties', 'aliases': ['Waves'],
         'objdata': {'WaveCount': 3, 'FlagWaveInterval': 10,
                     'WaveSpendingPoints': 0, 'SpawnColStart': 5, 'SpawnColEnd': 5,
                     'ZombiePool': [], 'Waves': [{'DisableRandomSpawns': True,
                         'SpawnColStart': 5, 'SpawnColEnd': 5,
                         'Zombies': [{'Type': ('RTID(dark_king@ZombieTypes)' if row==4 else 'RTID(iris_dark_smoke_archmage@ZombieTypes)' if row==3 and wave==2 else 'RTID(iris_dark_smoke_dummy@ZombieTypes)' if row==3 else 'RTID(dark_juggler@ZombieTypes)' if row==2 else 'RTID(dark_rogue@ZombieTypes)') if wave>0 else 'RTID(iris_dark_smoke_dummy@ZombieTypes)', 'Row': str(row)}
                                     for row in ((1,2,3,4) if wave==1 else (1,2,3,5))]} for wave in range(3)]}}
    ]}
    types_path, sheets_path = r'PACKAGES\ZOMBIETYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON'
    types = read_rton(bundle, types_path, decoder)
    sheets = read_rton(bundle, sheets_path, decoder)
    zombie = deepcopy(next(o for o in types['objects'] if 'dark_armor2' in o.get('aliases', [])))
    # ZombieType identities are persistent typed handles in this engine.
    # Use a development-only identity outside its stock range.
    zombie['uid'] = '1.1001.1'
    zombie['aliases'] = ['iris_dark_smoke_dummy']
    # Keep the registered enum name: kill/almanac bookkeeping uses map::at
    # on TypeName and cannot accept an invented development-only string.
    zombie['objdata']['Properties'] = 'RTID(IrisDarkSmokeDummy@PropertySheets)'
    props = deepcopy(next(o for o in sheets['objects']
                          if 'ZombieDarkArmor2Default' in o.get('aliases', [])))
    props['aliases'] = ['IrisDarkSmokeDummy']
    props['objdata'].update(Hitpoints=2000, Speed=0.05, EatDPS=100)
    types['objects'].append(zombie)
    sheets['objects'].append(props)
    wizard=deepcopy(next(o for o in types['objects'] if 'dark_wizard' in o.get('aliases',[])))
    wizard.update(uid='1.1002.1',aliases=['iris_dark_smoke_wizard'])
    wizard['objdata']['Properties']='RTID(IrisDarkSmokeWizard@PropertySheets)'
    props=deepcopy(next(o for o in sheets['objects'] if 'ZombieWizardDefault' in o.get('aliases',[])))
    props['aliases']=['IrisDarkSmokeWizard'];props['objdata'].update(Hitpoints=10000,Speed=0.05)
    types['objects'].append(wizard);sheets['objects'].append(props)
    mage=deepcopy(next(o for o in types['objects'] if 'dark_archmage' in o.get('aliases',[])))
    mage.update(uid='1.1003.1',aliases=['iris_dark_smoke_archmage'])
    mage['objdata']['Properties']='RTID(IrisDarkSmokeArchmage@PropertySheets)'
    props=deepcopy(next(o for o in sheets['objects'] if 'IrisArchmage' in o.get('aliases',[])))
    props['aliases']=['IrisDarkSmokeArchmage'];props['objdata'].update(Hitpoints=10000,Speed=0.05)
    types['objects'].append(mage);sheets['objects'].append(props)
    waves = fixture['objects'][-1]['objdata']['Waves']
    for wave in waves:
        wave['SpawnColStart'] = wave['SpawnColEnd'] = 7
        wave['Zombies'] = [{'Type': 'RTID(dark_gargantuar@ZombieTypes)', 'Row': '2'},
                            *[{'Type': 'RTID(iris_dark_smoke_dummy@ZombieTypes)', 'Row': str(r)}
                              for r in (1, 4, 5)]]
    # Aiming-game integration fixture. Keep the same separate package/player;
    # campaign Dark 22 and its full authored schedule are unaffected.
    fixture=deepcopy(read_rton(bundle,r'PACKAGES\LEVELS\DARK22.RTON',decoder))
    definition=next(o['objdata'] for o in fixture['objects'] if o['objclass']=='LevelDefinition')
    definition.update(LevelNumber=original.get('LevelNumber',1),LevelIndex=original.get('LevelIndex',601))
    aiming=next(o['objdata'] for o in fixture['objects'] if o['objclass']=='IrisOakTrainProperties')
    aiming.update(IrisTargetCount=4,IrisWaveCount=4)
    for i,(time,kind,x,y,life) in enumerate(((3,0,5,1,0),(6,5,6,3,10),(10,1,7,2,0),(14,3,5,4,12))):
        for name,value in zip(('Time','Kind','X','Y','Life','Wave'),(time,kind,x,y,life,i+1)):
            aiming[f'Target{i:03}{name}']=value
    changes = {}
    for name, doc in ((path, fixture), (types_path, types), (sheets_path, sheets)):
        changes.setdefault(bundle.group_for(name), {})[name] = encoder().encode_root_object(
            StringIO(json.dumps(doc)))
    return bundle.replace(changes, set())
