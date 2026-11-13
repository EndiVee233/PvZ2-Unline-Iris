"""Adapt Aster's wizard to Iris's existing sheep/restore state machine."""
from contextlib import closing
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import struct
from zipfile import ZipFile
from index_texture_prefetch import ResourceZip
from iris_dark_ages import Importer
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from iris_cn_scaredy import rename_main_label
from iris_scaredy_audio import convert_plant_bank
from rsb_local import ResourceBundle


def label_frame(raw,index,label,*,stop_before=False):
    from pam_transform_index import PamIndex
    frames=PamIndex(raw).sprites[-1]['frames'];f=frames[index]
    if f['label'] is not None:raise ValueError('Wizard frame already has a label')
    commands=f['commands'];size=1+sum(4+len(c.encode())+len(p.encode()) for c,p in commands) if commands else 0
    at=f['end']-size
    out=bytearray(raw);out[f['start']]|=8
    if stop_before:out[frames[index-1]['start']]|=16
    encoded=label.encode();out[at:at]=struct.pack('<H',len(encoded))+encoded
    result=bytes(out);assert PamIndex(result).sprites[-1]['frames'][index]['label']==label
    return result


def wizard_animation(raw):
    raw=rename_main_label(raw,'sheep','casting_start')
    raw=label_frame(raw,470,'casting_fire',stop_before=True)
    raw=label_frame(raw,469,'casting_loop')
    # Iris obtains the spell origin by this named sprite, while Aster's
    # replacement artwork retained an Egypt-flag sprite name.
    from pam_transform_index import PamIndex
    for sprite in reversed(PamIndex(raw).sprites):
        name=sprite['name']
        if name not in ('zombie_egyptflag_hand_inner_01','zombie_egyptflag_hand_inner_02'):continue
        replacement=name.replace('zombie_egyptflag_','zombie_').encode();at=sprite['start']
        raw=raw[:at]+struct.pack('<H',len(replacement))+replacement+raw[at+2+len(name.encode()):]
    PamIndex(raw)
    return raw


def restore_dark_wizard(raw,aster_apk,read_index,write_index,decoder,encoder):
    original=ResourceBundle(raw,read_index,write_index);importer=Importer(raw,read_index,write_index,decoder)
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        def bundle(name):
            path,=[p for p in archive.namelist() if p.endswith('/'+name+'.rsb.smf')]
            return ResourceBundle(archive.read(path),read_index,write_index)
        donor=bundle('zombie3');importer.root(donor,'ZombieDarkWizardGroup',decoder)
        group=deepcopy(next(g for g in donor.manifest(decoder)['groups'] if g['id']=='ZombieDarkAgesWizardAudio'))
        bank,=group['resources'];path='\\'.join(bank['path']).upper()
        bank_raw=donor.read(donor.group_for(path),path)
        global_path=r'SOUNDBANKS\GLOBAL_DATA.BNK'
        legacy=original.read(original.group_for(global_path),global_path)
        recipe=json.loads((Path(__file__).resolve().parents[1]/'src/dark/wizard-audio-v88.json').read_text(encoding='utf-8'))
        importer.simple(group,{path:convert_plant_bank(legacy,bank_raw,recipe)},{})
        sheets_donor=aster_properties(bundle('dynamic'),r'PACKAGES\PROPERTYSHEETS.RTON',decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index);changes={}
    paths=[r'PACKAGES\ZOMBIETYPES.RTON',r'PACKAGES\PROPERTYSHEETS.RTON',r'PACKAGES\PROJECTILETYPES.RTON']
    types,sheets,shots=[read_rton(result,p,decoder) for p in paths]
    wizard=next(o['objdata'] for o in types['objects'] if 'dark_wizard' in o.get('aliases',[]))
    # Keep Iris's stable zombie identity for saves, kill statistics and loot.
    wizard['AudioGroups']=['ZombieDarkAgesWizardAudio']
    props=next(o['objdata'] for o in sheets['objects'] if 'ZombieWizardDefault' in o.get('aliases',[]))
    source=next(o['objdata'] for o in sheets_donor['objects'] if 'ZombieWizardDefault' in o.get('aliases',[]))
    for key in tuple(props):
        if key in source and key not in ('TimeBeforeFirstCasting','TimeBetweenCasting'):props[key]=deepcopy(source[key])
    props.update(TimeBeforeFirstCasting=8,TimeBetweenCasting=12.5,SpellCastingDuration=35/30,
                 SheepPopAnim='POPANIM_EFFECTS_DARK_WIZARD_SHEEPENING')
    shot=next(o['objdata'] for o in shots['objects'] if 'ZombieWizardProjectileDefault' in o.get('aliases',[]))
    shot.pop('RenderImage',None)
    shot.update(AttachedPAM='POPANIM_EFFECTS_DARK_WIZARD_LIGHTNINGBOLT',AttachedPAMAnimationToPlay='animation')
    for path,doc in zip(paths,(types,sheets,shots)):
        changes.setdefault(result.group_for(path),{})[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    for rid in ('POPANIM_ZOMBIE_ZOMBIE_DARK_WIZARD','POPANIM_EFFECTS_ZOMBIE_DARK_WIZARD_PROJECTILE_HIT'):
        r=next(r for g in result.manifest(decoder)['groups'] for r in g.get('resources',[]) if r['id']==rid)
        path='\\'.join(r['path']).upper();pam=result.read(result.group_for(path),path)
        pam=wizard_animation(pam) if rid=='POPANIM_ZOMBIE_ZOMBIE_DARK_WIZARD' else rename_main_label(pam,'idle','animation')
        changes.setdefault(result.group_for(path),{})[path]=pam
    return result.replace(changes,set())
