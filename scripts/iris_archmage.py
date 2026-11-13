"""Archmage artwork and sleep effect, with fixed first-tier attributes."""
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


def restore_archmage(raw,aster_apk,read_index,write_index,decoder,encoder):
    importer=Importer(raw,read_index,write_index,decoder);stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        def bundle(name):
            path,=[p for p in archive.namelist() if p.endswith('/'+name+'.rsb.smf')]
            return ResourceBundle(archive.read(path),read_index,write_index)
        donor=bundle('zombie3');manifest=donor.manifest(decoder)
        roots={'ZombieArchmageGroup'}
        for g in manifest['groups']:
            if any(r.get('id')=='POPANIM_EFFECTS_SLEEPPING_PLANT_EFFECT' for r in g.get('resources',[])):
                roots.add(g.get('parent',g['id']))
        for root in sorted(roots):importer.root(donor,root,decoder)
        source=aster_properties(bundle('dynamic'),r'PACKAGES\PROPERTYSHEETS.RTON',decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index);changes={}
    paths=[r'PACKAGES\ZOMBIETYPES.RTON',r'PACKAGES\PROPERTYSHEETS.RTON',r'PACKAGES\GRIDITEMTYPES.RTON']
    types,sheets,grids=[read_rton(result,p,decoder) for p in paths]
    # The unused gravedropper enum remains stable for kill/loot persistence.
    obj=next(o for o in types['objects'] if 'dark_gravedropper' in o.get('aliases',[]))
    obj['aliases'].append('dark_archmage');obj['objdata'].update(ZombieClass='ZombieIrisArchmage',AnimRigClass='ZombieAnimRig',
        PopAnim='POPANIM_ZOMBIE_ZOMBIE_ARCHMAGE',ResourceGroups=sorted(roots),Properties='RTID(IrisArchmage@PropertySheets)',AudioGroups=[])
    allowed={k for o in sheets['objects'] if o.get('objclass')=='ZombiePropertySheet' for k in o.get('objdata',{})}
    donor=next(o['objdata'] for o in source['objects'] if 'ZombieArchmageDefault' in o.get('aliases',[]))
    data={k:deepcopy(v) for k,v in donor.items() if k in allowed};data.update(Hitpoints=600,Speed=0.14,EatDPS=100)
    sheets['objects'].append({'objclass':'ZombiePropertySheet','aliases':['IrisArchmage'],'objdata':data})
    grids['objects'].append({'objclass':'GridItemType','aliases':['iris_sleep_spell'],'objdata':{
        'TypeName':'iris_sleep_spell','GridItemClass':'IrisSleepSpell','Properties':'RTID(IrisSleepGround@PropertySheets)','ResourceGroups':sorted(roots)}})
    sheets['objects'].append({'objclass':'GridItemPropertySheet','aliases':['IrisSleepGround'],'objdata':{'Hitpoints':1000}})
    for path,doc in zip(paths,(types,sheets,grids)):
        changes.setdefault(result.group_for(path),{})[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    r=next(r for g in result.manifest(decoder)['groups'] for r in g.get('resources',[]) if r['id']=='POPANIM_ZOMBIE_ZOMBIE_ARCHMAGE')
    path='\\'.join(r['path']).upper();pam=result.read(result.group_for(path),path)
    changes.setdefault(result.group_for(path),{})[path]=rename_main_label(pam,'attack','eat')
    return result.replace(changes,set())
