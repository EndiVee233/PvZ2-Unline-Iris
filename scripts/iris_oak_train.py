"""Translate the authored aiming game into Iris-owned reflected data.

Do not hand this schedule to WaveGenerator: Iris's WaveData does not contain
WaveSpawnTime, Rise_GridX/Y or TargetValidTime and silently drops those fields.
The fixed scalar schema is shared with oak_train.cpp and survives battle saves.
"""
from copy import deepcopy
import math
import re

MAX_TARGETS = 256
TARGETS = ('zombie_target_wizard', 'zombie_target_archmage',
           'zombie_target_gargantuar', 'zombie_target_bottle',
           'zombie_target_arrow_yellow', 'zombie_target_arrow_blue',
           'zombie_target_arrow_purple')
SETTINGS = ('TotalLife', 'ArrowScore', 'WizardScore', 'ArchmageScore',
            'BossScore', 'HealNum', 'ArrowPowerNum', 'ArrowMultipleNum',
            'ArrowTrackNum')


def aiming_schedule(source):
    """Preserve each explicit spawn; reject unreviewed donor extensions."""
    objects = source['objects']
    settings, = [o['objdata'] for o in objects if o['objclass'] == 'OakTrainProperties']
    if set(settings) != set(SETTINGS) | {'InitArrowsNum'}:
        raise ValueError('Unreviewed OakTrain settings: ' + repr(set(settings)))
    if len(settings['InitArrowsNum']) != 4:
        raise ValueError('OakTrain requires four arrow inventories')
    generator, = [o['objdata'] for o in objects if o['objclass'] == 'WaveGeneratorProperties']
    if len(generator['Waves']) != generator['WaveCount']:
        raise ValueError('Incomplete aiming schedule')
    data = {k: settings[k] for k in SETTINGS}
    data.update({f'Arrow{i}': n for i, n in enumerate(settings['InitArrowsNum'])})
    data.update(IrisWaveCount=generator['WaveCount'])
    elapsed, count = 0.0, 0
    for wave_number, wave in enumerate(generator['Waves'], 1):
        if set(wave) - {'DisableRandomSpawns', 'WaveSpawnTime', 'Zombies'}:
            raise ValueError('Unreviewed aiming wave fields')
        if wave.get('DisableRandomSpawns') is not True:
            raise ValueError('Aiming game must use its authored targets')
        delay = wave['WaveSpawnTime']
        if not math.isfinite(delay) or delay <= 0:
            raise ValueError('Invalid aiming wave delay')
        elapsed += delay
        for spawn in wave['Zombies']:
            if set(spawn) - {'Row', 'Type', 'Level', 'Rise_GridX', 'Rise_GridY', 'TargetValidTime'}:
                raise ValueError('Unreviewed aiming target fields')
            match = re.fullmatch(r'RTID\(([^@]+)@ZombieTypes\)', spawn['Type'])
            if not match or match[1] not in TARGETS:
                raise ValueError('Unported aiming target: ' + spawn['Type'])
            kind = TARGETS.index(match[1])
            # Missing coordinates remain random until the actual spawn. The
            # selected position is stored on the actor, never re-randomized.
            x = int(spawn['Rise_GridX']) if 'Rise_GridX' in spawn else -1
            row = spawn.get('Rise_GridY', spawn.get('Row', '?'))
            y = -1 if row == '?' else int(row)
            if not (-1 <= x <= 8 and -1 <= y <= 4):
                raise ValueError('Aiming target outside the lawn')
            lifetime = float(spawn.get('TargetValidTime', 0))
            if not math.isfinite(lifetime) or lifetime < 0:
                raise ValueError('Invalid aiming target lifetime')
            if count >= MAX_TARGETS:
                raise ValueError('Aiming schedule exceeds the reflected capacity')
            values = (elapsed, kind, x, y, lifetime, wave_number)
            for suffix, value in zip(('Time', 'Kind', 'X', 'Y', 'Life', 'Wave'), values):
                data[f'Target{count:03}{suffix}'] = value
            count += 1
    data['IrisTargetCount'] = count
    data['ResourceGroupNames'] = ['PlantOakshooter', 'Oak_Train', 'ZombieTargetGroup',
                                  'ZombieDarkWizardGroup', 'ZombieArchmageGroup',
                                  'ZombieDarkGargantuarGroup', 'ZombieDarkImpGroup',
                                  'ZombieDarkAgesWizardAudio', 'ZombieDarkAgesGargantuarAudio']
    return data


def adapt_aiming_level(source):
    """Use the real game module and a native protected Oak, never empty waves."""
    data = aiming_schedule(source)
    definition = deepcopy(next(o['objdata'] for o in source['objects']
                               if o['objclass'] == 'LevelDefinition'))
    definition.update(Name='[DARKAGES_LEVEL_NAME]', Description='[IRIS_OAK_TRAIN_DESCRIPTION]',
                      NormalPresentTable='egypt_normal_01', ShinyPresentTable='egypt_shiny_01',
                      StageModule='RTID(DarkStage@LevelModules)',
                      Modules=['RTID(StandardIntro@LevelModules)',
                               'RTID(OakTrain@CurrentLevel)',
                               'RTID(Oak@CurrentLevel)',
                               'RTID(Waves@CurrentLevel)',
                               'RTID(ZombiesDeadWinCon@LevelModules)'])
    # The owned module gates ZombiesDeadWinCon while its schedule is active.
    # This native WaveManager supplies the ordinary result/loot lifecycle.
    result = {'version': 1, 'objects': [
        {'objclass': 'LevelDefinition', 'objdata': definition},
        {'objclass': 'IrisOakTrainProperties', 'aliases': ['OakTrain'], 'objdata': data},
        {'objclass': 'ProtectThePlantChallengeProperties', 'aliases': ['Oak'],
         'objdata': {'MustProtectCount': 1, 'Plants': [
             {'PlantType': 'oakshooter', 'GridX': 0, 'GridY': 2}]}},
        {'objclass': 'WaveGeneratorProperties', 'aliases': ['Waves'],
         'objdata': {'WaveCount': 1, 'FlagWaveInterval': 1, 'WaveSpendingPoints': 0,
                     'IgnoreFlagCarriers': True,
                     'ZombiePool': [], 'Waves': [{'DisableRandomSpawns': True, 'Zombies': []}]}}
    ]}
    # Keep the donor's real completion challenges/reward bookkeeping. All four
    # current aiming levels use the native BeatTheLevel challenge family.
    challenges=[deepcopy(o) for o in source['objects'] if o['objclass'].startswith('StarChallenge')]
    if any(o['objclass'] not in {'StarChallengeModuleProperties','StarChallengeBeatTheLevelProps'}
           for o in challenges):
        raise ValueError('Unreviewed aiming challenge implementation')
    if challenges:
        definition['Modules'].append('RTID(ChallengeModule@CurrentLevel)')
        result['objects'].extend(challenges)
    return result


def restore_aiming_resources(raw, aster_apk, read_index, write_index, decoder, encoder):
    """Import target/UI art and tier-one sheets; the new classes own behavior."""
    from contextlib import closing
    from io import StringIO
    from zipfile import ZipFile
    import json
    from index_texture_prefetch import ResourceZip
    from iris_dark_ages import Importer
    from iris_future_gargantuar import aster_properties
    from iris_future_world import read_rton
    from rsb_local import ResourceBundle
    importer=Importer(raw,read_index,write_index,decoder)
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        def bundle(name):
            path,=[p for p in archive.namelist() if p.endswith('/'+name+'.rsb.smf')]
            return ResourceBundle(archive.read(path),read_index,write_index)
        importer.root(bundle('zombie3'),'ZombieTargetGroup',decoder)
        importer.root(bundle('dark'),'Oak_Train',decoder)
        donor=bundle('dynamic')
        donor_types=aster_properties(donor,r'PACKAGES\ZOMBIETYPES.RTON',decoder)
        donor_sheets=aster_properties(donor,r'PACKAGES\PROPERTYSHEETS.RTON',decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index)
    paths=[r'PACKAGES\ZOMBIETYPES.RTON',r'PACKAGES\PROPERTYSHEETS.RTON']
    types,sheets=[read_rton(result,p,decoder) for p in paths]
    allowed=set(next(o['objdata'] for o in sheets['objects'] if 'ZombieDarkArmor2Default' in o.get('aliases',[])))
    classes=('Wizard','Archmage','Gargantuar','Bottle','ArrowYellow','ArrowBlue','ArrowPurple')
    for i,(alias,cls) in enumerate(zip(TARGETS,classes)):
        source=deepcopy(next(o['objdata'] for o in donor_types['objects'] if alias in o.get('aliases',[])))
        name=source['Properties'].split('(')[1].split('@')[0]
        props=next(o['objdata'] for o in donor_sheets['objects'] if name in o.get('aliases',[]))
        data={k:deepcopy(v) for k,v in props.items() if k in allowed}
        # The source's grade tables and extended-layout fields never enter Iris.
        data.update(HeadDropFraction=-1,ArmDropFraction=-1,Speed=0,
                    CanSpawnPlantFood=False,SoundOnDeath='',SoundOnIdle='')
        sheets['objects'].append({'objclass':'ZombiePropertySheet','aliases':['IrisTarget'+cls], 'objdata':data})
        source.update(TypeName='dark',ZombieClass='ZombieIrisTarget'+cls,AnimRigClass='ZombieAnimRig',
                      Properties='RTID(IrisTarget'+cls+'@PropertySheets)')
        if any(o.get('uid')==f'1.{1010+i}.1' for o in types['objects']):raise ValueError('Target UID collision')
        types['objects'].append({'uid':f'1.{1010+i}.1','objclass':'ZombieType','aliases':[alias],'objdata':source})
    changes={}
    for p,d in zip(paths,(types,sheets)):
        changes.setdefault(result.group_for(p),{})[p]=encoder().encode_root_object(StringIO(json.dumps(d)))
    return result.replace(changes,set())
