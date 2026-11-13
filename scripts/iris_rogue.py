"""Rogue artwork and stable Iris prototype identity, with a native adapter."""
from contextlib import closing
from copy import deepcopy
from io import StringIO
import json
from zipfile import ZipFile
from index_texture_prefetch import ResourceZip
from iris_dark_ages import Importer
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from iris_cn_scaredy import rename_main_label
from rsb_local import ResourceBundle


def restore_rogue(raw,aster_apk,read_index,write_index,decoder,encoder):
    importer=Importer(raw,read_index,write_index,decoder)
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        def bundle(name):
            path,=[p for p in archive.namelist() if p.endswith('/'+name+'.rsb.smf')]
            return ResourceBundle(archive.read(path),read_index,write_index)
        importer.root(bundle('zombie3'),'ZombieRogueGroup',decoder)
        source=aster_properties(bundle('dynamic'),r'PACKAGES\PROPERTYSHEETS.RTON',decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index);changes={}
    paths=[r'PACKAGES\ZOMBIETYPES.RTON',r'PACKAGES\PROPERTYSHEETS.RTON']
    types,sheets=[read_rton(result,p,decoder) for p in paths]
    obj=next(o for o in types['objects'] if 'dark_thief' in o.get('aliases',[]))
    # The unused Iris thief slot is retained: native kill stats and existing
    # saves know this enum. Level data can use Aster's dark_rogue alias.
    obj['aliases'].append('dark_rogue')
    obj['objdata'].update(ZombieClass='ZombieIrisRogue',AnimRigClass='ZombieAnimRig',
        PopAnim='POPANIM_ZOMBIE_ZOMBIE_DARK_ROGUE',ResourceGroups=['ZombieRogueGroup'],
        Properties='RTID(IrisRogue@PropertySheets)',AudioGroups=[])
    allowed={k for o in sheets['objects'] if o.get('objclass')=='ZombiePropertySheet' for k in o.get('objdata',{})}
    donor=next(o['objdata'] for o in source['objects'] if 'ZombieDarkRogue' in o.get('aliases',[]))
    data={k:deepcopy(v) for k,v in donor.items() if k in allowed}
    data.update(Hitpoints=600,Speed=0.185,EatDPS=100)
    sheets['objects'].append({'objclass':'ZombiePropertySheet','aliases':['IrisRogue'],'objdata':data})
    for path,doc in zip(paths,(types,sheets)):
        changes.setdefault(result.group_for(path),{})[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    resource=next(r for g in result.manifest(decoder)['groups'] for r in g.get('resources',[]) if r['id']=='POPANIM_ZOMBIE_ZOMBIE_DARK_ROGUE')
    path='\\'.join(resource['path']).upper();pam=result.read(result.group_for(path),path)
    changes.setdefault(result.group_for(path),{})[path]=rename_main_label(pam,'attack','eat')
    return result.replace(changes,set())
