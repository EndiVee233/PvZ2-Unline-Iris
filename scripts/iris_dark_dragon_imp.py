"""Standalone dragon imp for ordinary waves; imports no Zomboss actor/module."""
from contextlib import closing
from copy import deepcopy
from io import StringIO
from pathlib import Path
from zipfile import ZipFile
import json
import struct
from index_texture_prefetch import ResourceZip
from iris_dark_ages import Importer
from iris_future_audio import chunks, media
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from iris_scaredy_audio import convert_plant_bank
from rsb_local import ResourceBundle


def restore_dragon_imp(raw, aster_apk, read_index, write_index, decoder, encoder):
    original=ResourceBundle(raw,read_index,write_index)
    importer=Importer(raw,read_index,write_index,decoder)
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        def bundle(name):
            path,=[p for p in archive.namelist() if p.endswith('/'+name+'.rsb.smf')]
            return ResourceBundle(archive.read(path),read_index,write_index)
        art=bundle('zombie3');importer.root(art,'ZombieDarkImpDragonGroup',decoder)
        # Jump and landing commands are authored in this imp's PAM, while
        # their samples live in the shared Dark audio bank. Reuse the already
        # audited conversion; the cancelled boss's classes stay unregistered.
        audio=deepcopy(next(g for g in art.manifest(decoder)['groups'] if g['id']=='ZombossDarkAgesAudio'))
        resource,=audio['resources'];path='\\'.join(resource['path']).upper()
        bank=art.read(art.group_for(path),path)
        recipe=json.loads((Path(__file__).resolve().parents[1]/'src/dark/dragon-audio-v88.json').read_text())
        samples=media(chunks(bank));required={r['media'] for r in recipe['nodes'].values() if 'media' in r}
        if required-samples.keys() or any(v[:4]!=b'RIFF' or struct.unpack_from('<I',v,4)[0]+8!=len(v) for v in samples.values()):
            raise ValueError('Dragon imp requires the audited complete embedded samples')
        global_path=r'SOUNDBANKS\GLOBAL_DATA.BNK'
        importer.simple(audio,{path:convert_plant_bank(original.read(original.group_for(global_path),global_path),bank,recipe)},{})
        dynamic=bundle('dynamic')
        donor_types=aster_properties(dynamic,r'PACKAGES\ZOMBIETYPES.RTON',decoder)
        donor_sheets=aster_properties(dynamic,r'PACKAGES\PROPERTYSHEETS.RTON',decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index)
    paths=[r'PACKAGES\ZOMBIETYPES.RTON',r'PACKAGES\PROPERTYSHEETS.RTON']
    types,sheets=[read_rton(result,p,decoder) for p in paths]
    if any('dark_imp_dragon' in o.get('aliases',[]) for o in types['objects']):raise ValueError('Dragon imp already registered')
    uid='1.2201.1'
    if any(o.get('uid')==uid for o in types['objects']):raise ValueError('Dragon imp identity collision')
    data=deepcopy(next(o['objdata'] for o in donor_types['objects'] if 'dark_imp_dragon' in o.get('aliases',[])))
    # Both versions retain this actual native actor and its flying/landing rig.
    native=next(o['objdata'] for o in types['objects'] if 'future_imp' in o.get('aliases',[]))
    if (data['ZombieClass'],data['AnimRigClass'])!=(native['ZombieClass'],native['AnimRigClass']):
        raise ValueError('Review dragon imp native class compatibility')
    data.update(TypeName='dark_imp',Properties='RTID(IrisDarkDragonImp@PropertySheets)',
                AudioGroups=['ZombossDarkAgesAudio'])
    types['objects'].append({'objclass':'ZombieType','aliases':['dark_imp_dragon'],'uid':uid,'objdata':data})
    allowed={k for o in sheets['objects'] if o.get('objclass')=='ZombiePropertySheet' for k in o['objdata']}
    source=next(o['objdata'] for o in donor_sheets['objects'] if 'ZombieDarkImpDragonDefault' in o.get('aliases',[]))
    props={k:deepcopy(v) for k,v in source.items() if k in allowed}
    if source['FireDamageMultiplier']!=0:raise ValueError('Changed dragon imp fire immunity')
    sheets['objects'].append({'objclass':'ZombiePropertySheet','aliases':['IrisDarkDragonImp'],'objdata':props})
    changes={}
    for path,doc in zip(paths,(types,sheets)):
        changes.setdefault(result.group_for(path),{})[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes,set())
