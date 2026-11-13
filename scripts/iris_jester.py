"""Aster Jester art, whitelist and audio with no rank tables."""
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


def restore_jester(raw,aster_apk,read_index,write_index,decoder,encoder):
    original=ResourceBundle(raw,read_index,write_index);importer=Importer(raw,read_index,write_index,decoder)
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        def bundle(name):
            path,=[p for p in archive.namelist() if p.endswith('/'+name+'.rsb.smf')]
            return ResourceBundle(archive.read(path),read_index,write_index)
        donor=bundle('zombie3');importer.root(donor,'ZombieDarkJesterGroup',decoder)
        group=deepcopy(next(g for g in donor.manifest(decoder)['groups'] if g['id']=='ZombieDarkAgesJESTERAudio'))
        r,=group['resources'];path='\\'.join(r['path']).upper();bank=donor.read(donor.group_for(path),path)
        p=r'SOUNDBANKS\GLOBAL_DATA.BNK';old=original.read(original.group_for(p),p)
        recipe=json.loads((Path(__file__).resolve().parents[1]/'src/dark/jester-audio-v88.json').read_text(encoding='utf8'))
        importer.simple(group,{path:convert_plant_bank(old,bank,recipe)},{})
        source=aster_properties(bundle('dynamic'),r'PACKAGES\PROPERTYSHEETS.RTON',decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index);changes={}
    paths=[r'PACKAGES\ZOMBIETYPES.RTON',r'PACKAGES\PROPERTYSHEETS.RTON',r'PACKAGES\PROJECTILETYPES.RTON']
    types,sheets,shots=[read_rton(result,p,decoder) for p in paths]
    obj=next(o for o in types['objects'] if 'dark_knight' in o.get('aliases',[]))
    # Use the retired Iris knight prototype's enum/UID; this ports Jester,
    # without introducing Aster's unrelated cavalry or progression.
    obj['aliases'].append('dark_juggler')
    obj['objdata'].update(ZombieClass='ZombieIrisJester',AnimRigClass='ZombieAnimRig',
        PopAnim='POPANIM_ZOMBIE_ZOMBIE_DARK_JESTER',ResourceGroups=['ZombieDarkJesterGroup'],
        Properties='RTID(IrisJester@PropertySheets)',AudioGroups=['ZombieDarkAgesJESTERAudio'])
    allowed={k for o in sheets['objects'] if o.get('objclass')=='ZombiePropertySheet' for k in o.get('objdata',{})}
    donor=next(o['objdata'] for o in source['objects'] if 'ZombieDarkJugglerDefault' in o.get('aliases',[]))
    data={k:deepcopy(v) for k,v in donor.items() if k in allowed};data.update(Hitpoints=600,Speed=0.2,EatDPS=100)
    sheets['objects'].append({'objclass':'ZombiePropertySheet','aliases':['IrisJester'],'objdata':data})
    whitelist=set(donor['JuggleableProjectiles']);marked=[]
    # Peanut uses a private Iris alias for its adapted native projectile.
    if 'PeanutDefault' in whitelist:whitelist.add('IrisPeanutDefault')
    for o in shots['objects']:
        if whitelist.intersection(o.get('aliases',[])):
            if o.get('objclass')!='ProjectilePropertySheet':raise ValueError('Derived Jester projectile sheet needs review')
            o['objclass']='IrisJuggleableProjectileProps';marked.extend(o.get('aliases',[]))
    if not {'PeaDefault','IrisPeanutDefault','PuffSporeDefault'}<=set(marked):raise ValueError('Incomplete Jester whitelist')
    for path,doc in zip(paths,(types,sheets,shots)):
        changes.setdefault(result.group_for(path),{})[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes,set())
