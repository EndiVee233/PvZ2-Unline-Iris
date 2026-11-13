"""Reconnect the ordinary Aster campaign only after its actor types are present.

The r36 adapter remains the initial bootstrap. This final pass uses the user's
expanded port scope and never substitutes ordinary levels for special games.
"""
from contextlib import closing
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from zipfile import ZipFile
from index_texture_prefetch import ResourceZip
from iris_dark_ages import Importer
from iris_dark_levels import adapt_level, source_hash, validate_levels, CATALOG
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from rsb_local import ResourceBundle

POLICY = Path(__file__).resolve().parents[1]/'src/dark/port-policy.json'
SPECIAL = {'TowerDefendProperties', 'OakTrainProperties', 'ZombossMechBattleModuleProperties'}
NARRATIVE = {
 'IRIS_OAK_TRAIN_DESCRIPTION':'Use Oak-shooter to hit the targets.',
 'IRIS_THEATRE_DESCRIPTION':"Protect the pig's house.",
 'IRIS_DARK_ROSTER_CONVEYOR':'Complete the Dark Ages conveyor challenge.',
 'NARRATIVE_DARK_HYPNOSHROOM_INTRO_1':'{NPC_ENTER:crazydave}{NPC_ENTER:winnie}{SAY:crazydave}Looks like we are surrounded!',
 'NARRATIVE_DARK_HYPNOSHROOM_INTRO_2':'{SAY:winnie}Your Hypno-shroom friends can help us!',
 'NARRATIVE_DARK_HYPNOSHROOM_INTRO_3':'{SAY:crazydave}Plant Food makes those Hypno-shrooms even more powerful!',
 'NARRATIVE_DARK_HYPNOSHROOM_INTRO_4':'{SAY:winnie}Save them for the toughest opponents!',
 'NARRATIVE_DARK_HYPNOSHROOM_INTRO_5':'{SAY:crazydave}Forward, Hypno-shrooms!',
}


def validate_preloads(bundle, decoder):
    """Check native dependency names, including the generated music group.

    RTID closure alone cannot detect this: the loader generates a resource
    group from MusicType/MusicSuffix and waits indefinitely when it is absent.
    """
    manifest={g['id']:g for g in bundle.manifest(decoder)['groups']}
    groups=set(manifest)
    world_list=read_rton(bundle,r'PACKAGES\WORLDMAPLIST.RTON',decoder)
    dark,=[w for w in world_list['objects'][0]['objdata']['MapList'] if w['MapName']=='dark']
    map_groups=set(dark['WorldResources']['ResGroups'])
    types=read_rton(bundle,r'PACKAGES\PLANTTYPES.RTON',decoder)
    # The chooser asks IsOwned even for hidden/disabled PlantType entries.
    # Dependency checks must include private theatre houses and growth forms.
    from iris_plant_ids_native import ALL_PLANT_IDS
    unmapped={o['objdata']['TypeName'] for o in types['objects']}-ALL_PLANT_IDS.keys()
    if unmapped:raise ValueError('Native plant enum has no IDs for resource types: '+repr(sorted(unmapped)))
    from iris_chooser_preview import PREVIEW_ROOTS
    chooser=manifest['UI_SeedChooser']
    preview_groups={c['id'] for c in chooser['subgroups']}
    for root in PREVIEW_ROOTS:
        missing={c['id'] for c in manifest[root]['subgroups']}-preview_groups
        if missing:raise ValueError('Seed chooser does not preload '+root+': '+repr(sorted(missing)))
    plant_types={a:o['objdata'] for o in types['objects'] for a in o.get('aliases',[])}
    map_data=read_rton(bundle,r'PACKAGES\WORLDS\DARK\WORLDMAP.RTON',decoder)['objects'][0]['objdata']
    event_names={e['m_name'] for e in map_data['m_eventList']}
    if not dark.get('ExitPoint') or dark['ExitPoint'] not in event_names:
        raise ValueError('Dark world completion has no valid exit event')
    for event in map_data['m_eventList']:
        for field in ('m_parentEvent','m_unlockedFrom','m_visibleFrom'):
            if event.get(field) and event[field] not in event_names:
                raise ValueError('Dark map event has a dangling '+field+': '+event['m_name'])
    reward_art=set()
    for e in map_data['m_eventList']:
        if e['m_eventType'] not in ('plant','plantbox'):continue
        plant=plant_types[e['m_dataString']]
        reward_art.add(plant['PlantFramework'])
        reward_art.update(plant.get('PlantAudioGroups',[]))
    if not reward_art<=map_groups or map_groups-groups:
        raise ValueError('Dark map reward artwork is not preloaded: '+repr(sorted(reward_art-map_groups | map_groups-groups)))
    for name in ('Music_MainPath_DarkAges', 'Music_MiniGame_A_DarkAges',
                 'Music_MiniGame_B_DarkAges'):
        group=manifest.get(name)
        if not group or not group.get('resources'):
            raise ValueError(name+': empty music dependency cannot finish native loading')
        for resource in group['resources']:
            if resource['type'] in ('File', 'SoundBank'):
                path='\\'.join(resource['path']).upper()
                if not bundle.read(bundle.group_for(path),path):
                    raise ValueError(name+': zero-byte music dependency '+path)
    modules=read_rton(bundle,r'PACKAGES\LEVELMODULES.RTON',decoder)
    aliases={a:o['objdata'] for o in modules['objects'] for a in o.get('aliases',[])}
    plant_doc=read_rton(bundle,r'PACKAGES\PLANTTYPES.RTON',decoder)
    plants={a:o['objdata'] for o in plant_doc['objects'] for a in o.get('aliases',[])}
    zombie_doc=read_rton(bundle,r'PACKAGES\ZOMBIETYPES.RTON',decoder)
    zombies={a:o['objdata'] for o in zombie_doc['objects'] for a in o.get('aliases',[])}
    collectables=read_rton(bundle,r'PACKAGES\COLLECTABLETYPES.RTON',decoder)
    collectable_names={o['objdata']['TypeName'] for o in collectables['objects']}
    authored_paths={'PACKAGES\\LEVELS\\'+e['file'].upper()+'.RTON'
                    for e in json.loads(CATALOG.read_text(encoding='utf8'))['levels']}
    checked=0
    for path in bundle.files:
        if not path.startswith('PACKAGES\\LEVELS\\DARK') or not path.endswith('.RTON'):
            continue
        level=read_rton(bundle,path,decoder)
        if level.get('#comment')=='Iris map metadata only: level implementation pending':
            continue
        definition=next(o['objdata'] for o in level['objects'] if o['objclass']=='LevelDefinition')
        if definition.get('FirstRewardType')=='worldtrophy' and definition.get('FirstRewardParam') not in collectable_names:
            raise ValueError(path+': first-clear collectable is not registered: '+str(definition.get('FirstRewardParam')))
        reference=definition['StageModule']
        stage=aliases[reference.split('(')[1].split('@')[0]]
        required=set(stage.get('ResourceGroupNames',[]))
        required.add('Music_'+definition.get('MusicType','MainPath')+'_'+stage['MusicSuffix'])
        for o in level['objects']:
            required.update(o['objdata'].get('ResourceGroupNames',[]))
        referenced=set()
        def visit(value):
            if isinstance(value,list):
                for item in value:visit(item)
            elif isinstance(value,dict):
                if isinstance(value.get('PlantType'),str):referenced.add(value['PlantType'])
                for item in value.get('PresetPlantList',[]):
                    if isinstance(item,str):referenced.add(item)
                for item in value.values():visit(item)
        # Retained Iris engineering fixtures such as BLACKSMITHTEST are not
        # authored Aster campaign sites and still reference trimmed prototypes.
        if path in authored_paths:visit(level)
        if path in authored_paths:
            import re
            for name in set(re.findall(r'RTID\(([^@]+)@ZombieTypes\)',json.dumps(level))):
                if name not in zombies:raise ValueError(path+': missing zombie registry entry '+name)
                required.update(zombies[name].get('ResourceGroups',[]))
                required.update(zombies[name].get('AudioGroups',[]))
        for o in level['objects']:
            if o['objclass']=='IrisTheatreProperties':
                from iris_theatre import TOWER_PLANTS
                d=o['objdata']
                for i in range(d['TreeCount']):
                    for j in range(d[f'Tree{i}Count']):
                        referenced.add(TOWER_PLANTS[d[f'Tree{i}Step{j}Plant']])
        for name in referenced:
            if name not in plants:raise ValueError(path+': missing plant registry entry '+name)
            data=plants[name]
            if name.startswith('iris_theatre_house_') and data.get('TypeName')!=name:
                raise ValueError(path+': house TypeName differs from its registry key '+name)
            required.add(data['PlantFramework'])
            required.update(data.get('PlantAudioGroups',[]))
        missing=required-groups
        if missing:
            raise ValueError(path+': missing preload groups '+repr(sorted(missing)))
        checked+=1
    print(f'Dark preloads: {checked} level dependency sets including generated music names checked')


def canonical_level(source, name):
    """Resolve only the two reviewed duplicate aliases in the donor document.

    Their later definitions are the final authored challenge settings. Any
    additional ambiguous alias is rejected by reachable_objects as before.
    """
    result = deepcopy(source)
    alias = {'dark16':'SunHoldout', 'dark19':'ChallengeModule'}.get(name)
    if alias:
        objects = result['objects']
        matches = [i for i,o in enumerate(objects) if alias in o.get('aliases',[])]
        if len(matches)!=2: raise ValueError(f'Changed donor duplicate: {name}/{alias}')
        first, last = [objects[i] for i in matches]
        if name=='dark16':
            if [o['objdata'] for o in (first,last)] != [{'HoldoutSeconds':60},{'HoldoutSeconds':45}]:
                raise ValueError('Changed Dark 16 holdout settings')
        elif first['objdata'].get('ChallengesAlwaysAvailable') is not True or len(last['objdata']['Challenges'])!=3:
            raise ValueError('Changed Dark 19 challenge definitions')
        del objects[matches[0]]
    return result


def restore_campaign(raw, aster_apk, read_index, write_index, decoder, encoder):
    result = ResourceBundle(raw,read_index,write_index)
    policy = json.loads(POLICY.read_text(encoding='utf8'))
    catalog = json.loads(CATALOG.read_text(encoding='utf8'))['levels']
    changes = {}; levels = {}; imported = []
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        name,=[p for p in archive.namelist() if p.endswith('/dynamic.rsb.smf')]
        donor=ResourceBundle(archive.read(name),read_index,write_index)
        world=aster_properties(donor,r'PACKAGES\WORLDS\DARK.RTON',decoder)
        for entry in catalog:
            path='PACKAGES\\LEVELS\\'+entry['file'].upper()+'.RTON'
            source=aster_properties(donor,path,decoder)
            if source_hash(source)!=entry['sha256']:raise ValueError('Donor campaign changed: '+path)
            if any(o['objclass']=='ZombossMechBattleModuleProperties' for o in source['objects']):
                from iris_dark_finale import roster_conveyor
                levels[path]=roster_conveyor(source)
                imported.append(entry['file'])
                continue
            if any(o['objclass']=='TowerDefendProperties' for o in source['objects']):
                from iris_theatre import adapt_theatre_level
                levels[path],_,_=adapt_theatre_level(source,policy)
                imported.append(entry['file'])
                continue
            oak=next((o['objdata'] for o in source['objects'] if o['objclass']=='OakTrainProperties'),None)
            if oak and 'InitArrowsNum' in oak:
                from iris_oak_train import adapt_aiming_level
                levels[path]=adapt_aiming_level(source)
                imported.append(entry['file'])
                continue
            if any(o['objclass'] in SPECIAL for o in source['objects']):
                if path in result.files:levels[path]=read_rton(result,path,decoder)
                continue
            levels[path]=adapt_level(canonical_level(source,entry['file']),policy=policy)
            imported.append(entry['file'])
    native={name:read_rton(result,'PACKAGES\\'+name.upper()+'.RTON',decoder)
            for name in ('LevelModules','PlantTypes','ZombieTypes','PropertySheets')}
    validate_levels(levels,native)
    def update(path,doc):changes.setdefault(result.group_for(path),{})[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    added={}
    for path,doc in levels.items():
        if path in result.files:update(path,doc)
        else:added[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    # Keep the authored geometry, ids and all current unlock conditions. The
    # availability pass only removes the explicit pending gate for new levels.
    map_path=r'PACKAGES\WORLDS\DARK\WORLDMAP.RTON'
    current=read_rton(result,map_path,decoder)
    authored={e['m_name']:e for e in world['objects'][0]['objdata']['m_eventList']}
    present={e['m_name'] for e in current['objects'][0]['objdata']['m_eventList']}
    # Hidden plant reward events are referenced by native first-clear rewards.
    # The bootstrap omitted them while those plants were unavailable.
    current['objects'][0]['objdata']['m_eventList'].extend(
        deepcopy(e) for e in authored.values()
        if e['m_eventType']=='plant' and e['m_name'] not in present)
    last,=[e['m_name'] for e in authored.values() if e['m_eventType']=='level' and e['m_dataString']=='dark30']
    for name in ('dark_stargate_start','dark_stargate_exit'):
        gate=deepcopy(authored[name])
        gate.update(m_cost=0,m_unlockedFrom='' if name.endswith('_start') else last)
        existing=next((e for e in current['objects'][0]['objdata']['m_eventList'] if e['m_name']==name),None)
        if existing is None:current['objects'][0]['objdata']['m_eventList'].append(gate)
        else:existing.update(gate)
    for event in current['objects'][0]['objdata']['m_eventList']:
        if event['m_eventType']=='level' and event['m_dataString'].lower() in imported:
            original=authored[event['m_name']]
            event['m_unlockedFrom']=original['m_unlockedFrom']
            event['m_displayText']=original['m_displayText']
        elif event['m_name'] in ('dark_rewardplantbox_streetlamp','dark_rewardplantbox_coffeebean'):
            original=authored[event['m_name']]
            for key in ('m_eventType','m_dataString','m_unlockedFrom','m_visibleFrom','m_parentEvent'):
                event[key]=deepcopy(original[key])
    update(map_path,current)
    # The map's plantbox renderer requests the actual PopAnim directly. It
    # does not load PlantAudioGroups, unlike battle preloading. Generic owned
    # frameworks therefore need their reward artwork in the map dependency set.
    list_path=r'PACKAGES\WORLDMAPLIST.RTON'
    world_list=read_rton(result,list_path,decoder)
    dark,=[w for w in world_list['objects'][0]['objdata']['MapList'] if w['MapName']=='dark']
    dark['ExitPoint']='dark_stargate_exit'
    plant_types={a:o['objdata'] for o in native['PlantTypes']['objects'] for a in o.get('aliases',[])}
    rewards=set()
    for event in current['objects'][0]['objdata']['m_eventList']:
        if event['m_eventType'] not in ('plant','plantbox'):continue
        plant=plant_types[event['m_dataString']]
        rewards.add(plant['PlantFramework'])
        rewards.update(plant.get('PlantAudioGroups',[]))
    for name in sorted(rewards):
        if name not in dark['WorldResources']['ResGroups']:
            dark['WorldResources']['ResGroups'].append(name)
    update(list_path,world_list)
    for path in result.files:
        if path.startswith('LOCALES\\') and path.endswith('\\PROPERTIES\\LAWNSTRINGS.TXT'):
            text=result.read(result.group_for(path),path).decode('utf-16')
            for key,value in NARRATIVE.items():
                if '['+key+']' not in text:text+='\r\n['+key+']\r\n'+value+'\r\n'
            changes.setdefault(result.group_for(path),{})[path]=text.encode('utf-16')
    print(f'Dark campaign: {len(imported)} ordinary, aiming, theatre and replacement conveyor levels connected')
    raw=result.replace(changes,set())
    if added:
        result=ResourceBundle(raw,read_index,write_index)
        extra=Importer(raw,read_index,write_index,decoder)
        group=deepcopy(next(g for g in extra.manifest['groups'] if g['id']=='Packages'))
        files={p:result.read('Packages',p) for p in result.groups['Packages'][3]}
        files.update(added)
        for path in added:
            group['resources'].append({'type':'File','id':'RESFILE_'+path[:-5].replace('\\','_'),
                                       'path':path.lower().split('\\')})
        extra.simple(group,files,{},replace=True);raw=extra.finish()
    return raw
