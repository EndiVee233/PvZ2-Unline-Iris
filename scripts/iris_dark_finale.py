"""The user-requested Dark Ages roster conveyor replaces the cancelled boss."""
from copy import deepcopy
from iris_dark_levels import validate_wave_schema

PLANTS = ('sunshroom', 'puffshroom', 'fumeshroom', 'sunbean', 'magnetshroom',
          'hypnoshroom', 'peanut', 'oakshooter', 'iceshroom', 'fireshroom',
          'coffeebean', 'streetlamp', 'scaredyshroom')
ZOMBIES = ('dark', 'dark_armor1', 'dark_armor2', 'dark_flag', 'dark_armor3',
           'dark_imp', 'dark_imp_dragon', 'dark_wizard', 'dark_juggler',
           'dark_king', 'dark_rogue', 'dark_archmage', 'dark_gargantuar')


def roster_conveyor(source):
    original, = [o['objdata'] for o in source['objects'] if o['objclass'] == 'LevelDefinition']
    definition = deepcopy(original)
    # Keep identity, completion record and authored first-clear reward. None
    # of the old boss-specific intro, reserved columns or module state leaks
    # into the replacement's ordinary native battle lifecycle.
    definition.pop('IsBossFight', None)
    definition.pop('FirstIntroNarrative', None)
    definition.pop('CompletionAchievement', None)
    if definition.get('FirstRewardType')=='worldtrophy' and definition.get('FirstRewardParam')=='worldkey':
        # Aster's CollectableWorldKey does not exist in Iris. Keep the native
        # world-completion lifecycle with an explicitly registered Dark trophy.
        definition['FirstRewardParam']='worldtrophy_dark'
    definition.update(Name='[DARKAGES_LEVEL_NAME]', Description='[IRIS_DARK_ROSTER_CONVEYOR]',
                      MusicType='MiniGame_A', StartingSun=0, StageModule='RTID(DarkStage@LevelModules)',
                      Modules=['RTID(StandardIntro@LevelModules)', 'RTID(DarkMowers@LevelModules)',
                               'RTID(ConveyorBelt@CurrentLevel)', 'RTID(Waves@CurrentLevel)',
                               'RTID(ZombiesDeadWinCon@LevelModules)',
                               'RTID(DefaultZombieWinCondition@LevelModules)',
                               'RTID(ChallengeModule@CurrentLevel)'])
    attack = {'puffshroom', 'fumeshroom', 'peanut', 'oakshooter', 'scaredyshroom'}
    seeds = [{'PlantType': plant, 'Weight': 30 if plant in attack else 6,
              'MinCount': 1, 'MinWeightFactor': 5, 'MaxCount': 5 if plant in attack else 2,
              'MaxWeightFactor': 0} for plant in PLANTS]
    waves = []
    for i, zombie in enumerate(ZOMBIES):
        enemies = [{'Type': 'RTID(' + zombie + '@ZombieTypes)', 'Row': str(i % 5 + 1)}]
        if i > 2:
            enemies.append({'Type': 'RTID(dark@ZombieTypes)', 'Row': str((i + 2) % 5 + 1)})
        waves.append({'DisableRandomSpawns': True, 'SpawnPlantFoodCount': 1 if i % 3 == 2 else 0,
                      'Zombies': enemies})
    waves += [{'DisableRandomSpawns': True, 'SpawnPlantFoodCount': 1,
               'Zombies': [{'Type': 'RTID(' + kind + '@ZombieTypes)', 'Row': str(row)}
                           for row, kind in enumerate(kinds, 1)]} for kinds in (
                               ('dark_armor2', 'dark_rogue', 'dark_wizard', 'dark_imp_dragon', 'dark_armor3'),
                               ('dark_juggler', 'dark_archmage', 'dark_gargantuar', 'dark_king', 'dark_armor2'))]
    generator = {'WaveCount': len(waves), 'FlagWaveInterval': 5, 'IgnoreFlagCarriers': True,
                 'WaveSpendingPoints': 0, 'WaveSpendingPointIncrement': 0, 'ZombiePool': [],
                 'Waves': waves}
    validate_wave_schema(generator)
    return {'version': 1, '#comment': 'User-requested Dark Ages roster conveyor; boss port cancelled',
            'objects': [{'objclass': 'LevelDefinition', 'objdata': definition},
                        {'objclass': 'ConveyorSeedBankProperties', 'aliases': ['ConveyorBelt'],
                         'objdata': {'InitialPlantList': seeds,
                                     'DropDelayConditions': [{'MaxPackets': count, 'Delay': delay}
                                                             for count, delay in ((0, 1), (2, 2), (5, 3), (9, 6))],
                                     'SpeedConditions': [{'MaxPackets': 0, 'Speed': 100}]}},
                        {'objclass': 'WaveGeneratorProperties', 'aliases': ['Waves'], 'objdata': generator},
                        {'objclass': 'StarChallengeModuleProperties', 'aliases': ['ChallengeModule'],
                         'objdata': {'ChallengesAlwaysAvailable': True,
                                     'Challenges': [['RTID(BeatTheLevel@CurrentLevel)']]}},
                        {'objclass': 'StarChallengeBeatTheLevelProps', 'aliases': ['BeatTheLevel'],
                         'objdata': {'Description':'[STARCHALLENGE_DARK_CONVEYOR]',
                                     'DescriptiveName':'[STARCHALLENGE_DARK_CONVEYOR_NAME]'}}]}


def restore_finale_reward(raw, aster_apk, read_index, write_index, decoder, encoder):
    from contextlib import closing
    from io import StringIO
    import json
    from zipfile import ZipFile
    from index_texture_prefetch import ResourceZip
    from iris_dark_ages import Importer
    from iris_future_world import read_rton
    from rsb_local import ResourceBundle
    original=ResourceBundle(raw,read_index,write_index)
    importer=Importer(raw,read_index,write_index,decoder)
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        path,=[p for p in archive.namelist() if p.endswith('/uiactive.rsb.smf')]
        donor=ResourceBundle(archive.read(path),read_index,write_index)
        importer.images(original,donor,'LevelImage_Dynamic','LevelCommon',
                        ['IMAGE_ENDLEVEL_KEY_DARK'],decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index)
    path=r'PACKAGES\COLLECTABLETYPES.RTON'
    types=read_rton(result,path,decoder)
    if any(o['objdata'].get('TypeName')=='worldtrophy_dark' for o in types['objects']):
        raise ValueError('Dark trophy already defined')
    trophy=deepcopy(next(o for o in types['objects'] if o['objdata'].get('TypeName')=='worldtrophy_future'))
    trophy.pop('uid',None)
    trophy['objdata'].update(TypeName='worldtrophy_dark',StandaloneImage='IMAGE_ENDLEVEL_KEY_DARK',
                            RewardDialogImage='IMAGE_ENDLEVEL_KEY_DARK',RewardDialogDescriptions=['[DARK]'])
    types['objects'].append(trophy)
    return result.replace({result.group_for(path):{path:encoder().encode_root_object(StringIO(json.dumps(types)))}},set())
