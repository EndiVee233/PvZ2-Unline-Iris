"""Aster King assets/audio and tier-one values; no progression schema."""
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


def restore_king(raw,aster_apk,read_index,write_index,decoder,encoder):
    original=ResourceBundle(raw,read_index,write_index);importer=Importer(raw,read_index,write_index,decoder)
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        def bundle(name):
            path,=[p for p in archive.namelist() if p.endswith('/'+name+'.rsb.smf')]
            return ResourceBundle(archive.read(path),read_index,write_index)
        donor=bundle('zombie3');importer.root(donor,'ZombieDarkKingGroup',decoder)
        group=deepcopy(next(g for g in donor.manifest(decoder)['groups'] if g['id']=='ZombieDarkAgesKingAudio'))
        r,=group['resources'];path='\\'.join(r['path']).upper();bank=donor.read(donor.group_for(path),path)
        p=r'SOUNDBANKS\GLOBAL_DATA.BNK';old=original.read(original.group_for(p),p)
        recipe=json.loads((Path(__file__).resolve().parents[1]/'src/dark/king-audio-v88.json').read_text(encoding='utf8'))
        external={}
        for record in recipe['nodes'].values():
            if record.get('streamed'):
                uid=record['media'];sample,=[p for p in donor.files if p.endswith('\\'+str(uid)+'.WEM')]
                external[uid]=donor.read(donor.group_for(sample),sample)
        importer.simple(group,{path:convert_plant_bank(old,bank,recipe,external_media=external)},{})
        source=aster_properties(bundle('dynamic'),r'PACKAGES\PROPERTYSHEETS.RTON',decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index);changes={}
    paths=[r'PACKAGES\ZOMBIETYPES.RTON',r'PACKAGES\PROPERTYSHEETS.RTON'];types,sheets=[read_rton(result,p,decoder) for p in paths]
    obj=next(o for o in types['objects'] if 'dark_blacksmith' in o.get('aliases',[]));obj['aliases'].append('dark_king')
    obj['objdata'].update(ZombieClass='ZombieIrisKing',AnimRigClass='ZombieAnimRig',PopAnim='POPANIM_ZOMBIE_ZOMBIE_DARK_KING',
        ResourceGroups=['ZombieDarkKingGroup'],Properties='RTID(IrisKing@PropertySheets)',AudioGroups=['ZombieDarkAgesKingAudio'])
    allowed={k for o in sheets['objects'] if o.get('objclass')=='ZombiePropertySheet' for k in o.get('objdata',{})}
    donor=next(o['objdata'] for o in source['objects'] if 'ZombieDarkKing' in o.get('aliases',[]))
    data={k:deepcopy(v) for k,v in donor.items() if k in allowed};data.update(Hitpoints=1000,Speed=0,EatDPS=100)
    sheets['objects'].append({'objclass':'ZombiePropertySheet','aliases':['IrisKing'],'objdata':data})
    for path,doc in zip(paths,(types,sheets)):
        changes.setdefault(result.group_for(path),{})[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes,set())
