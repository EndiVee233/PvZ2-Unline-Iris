"""Use Iris's retained ordinary Gargantuar class with Aster's Dark Ages art."""
from contextlib import closing
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from zipfile import ZipFile
from index_texture_prefetch import ResourceZip
from iris_dark_ages import Importer
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from iris_scaredy_audio import convert_plant_bank
from rsb_local import ResourceBundle


def restore_dark_gargantuar(raw,aster_apk,read_index,write_index,decoder,encoder):
    original=ResourceBundle(raw,read_index,write_index);importer=Importer(raw,read_index,write_index,decoder)
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        def bundle(name):
            path,=[p for p in archive.namelist() if p.endswith('/'+name+'.rsb.smf')]
            return ResourceBundle(archive.read(path),read_index,write_index)
        donor=bundle('zombie3')
        for group in ('ZombieDarkGargantuarGroup','ZombieDarkImpGroup'):importer.root(donor,group,decoder)
        group=deepcopy(next(g for g in donor.manifest(decoder)['groups'] if g['id']=='ZombieDarkAgesGargantuarAudio'))
        resource,=group['resources'];path='\\'.join(resource['path']).upper();bank=donor.read(donor.group_for(path),path)
        global_path=r'SOUNDBANKS\GLOBAL_DATA.BNK';old=original.read(original.group_for(global_path),global_path)
        recipe=json.loads((Path(__file__).resolve().parents[1]/'src/dark/garg-audio-v88.json').read_text(encoding='utf8'))
        importer.simple(group,{path:convert_plant_bank(old,bank,recipe)},{})
        source=aster_properties(bundle('dynamic'),r'PACKAGES\PROPERTYSHEETS.RTON',decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index)
    paths=[r'PACKAGES\ZOMBIETYPES.RTON',r'PACKAGES\PROPERTYSHEETS.RTON'];types,sheets=[read_rton(result,p,decoder) for p in paths]
    if any('dark_gargantuar' in o.get('aliases',[]) for o in types['objects']):raise ValueError('Dark Gargantuar already defined')
    garg=deepcopy(next(o for o in types['objects'] if 'future_gargantuar' in o.get('aliases',[])))
    if any(o.get('uid')=='1.1004.1' for o in types['objects']):raise ValueError('Dark Gargantuar UID already used')
    garg['uid']='1.1004.1';garg['aliases']=['dark_gargantuar']
    # Keep the existing statistics enum, as with the other newly ported actors.
    # The ordinary parent class has no laser or EMP state machine.
    garg['objdata'].update(ZombieClass='ZombieGargantuar',AnimRigClass='ZombieAnimRig',
        Properties='RTID(IrisDarkGargantuar@PropertySheets)',ResourceGroups=['ZombieDarkGargantuarGroup','ZombieDarkImpGroup'],
        AudioGroups=['ZombieDarkAgesGargantuarAudio'],PopAnim='POPANIM_ZOMBIE_DARK_GARGANTUAR',HomeWorld='dark')
    types['objects'].append(garg)
    donor=next(o['objdata'] for o in source['objects'] if 'ZombieDarkGargantuar' in o.get('aliases',[]))
    allowed=set(next(o['objdata'] for o in sheets['objects'] if 'ZombieGargantuarMech' in o.get('aliases',[])))
    allowed-={k for k in allowed if k.startswith('EyeLaser') or k in ('SoundOnActivate','SoundOnDeactivate')}
    data={k:deepcopy(v) for k,v in donor.items() if k in allowed}
    # These sounds are authored in the donor PAM. Do not play them twice.
    data.update(HealthPercentThrowImp=.5,SoundOnSmash='',SoundOnCannon='',SoundOnDeath='')
    sheets['objects'].append({'objclass':'ZombieGargantuarProps','aliases':['IrisDarkGargantuar'],'objdata':data})
    imp=next(o for o in types['objects'] if 'dark_imp' in o.get('aliases',[]))
    imp['objdata'].update(PopAnim='POPANIM_ZOMBIE_ZOMBIE_DARK_IMP_MONK',ResourceGroups=['ZombieDarkImpGroup'])
    changes={}
    for path,doc in zip(paths,(types,sheets)):
        changes.setdefault(result.group_for(path),{})[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes,set())
