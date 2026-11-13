"""Oak-shooter's authored art and tier-one properties, without rank tables."""
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
from iris_growth_shrooms import action_commands
from rsb_local import ResourceBundle


def restore_oakshooter(raw, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    original=ResourceBundle(raw,read_index,write_index)
    importer=Importer(raw,read_index,write_index,decoder)
    stream=ResourceZip(aster_apk)
    with closing(stream.file),closing(stream.map),ZipFile(stream) as archive:
        def bundle(name):
            path,=[p for p in archive.namelist() if p.endswith('/'+name+'.rsb.smf')]
            return ResourceBundle(archive.read(path),read_index,write_index)
        importer.root(bundle('plant2'),'PlantOakshooter',decoder)
        importer.images(original,bundle('uiactive'),'UIImages_Dynamic','UIImages',
                        ['IMAGE_UI_PACKETS_OAKSHOOTER'],decoder,
                        reference='IMAGE_UI_PACKETS_SUNSHROOM',etc1tool=etc1tool)
        dynamic=bundle('dynamic')
        donor_types=aster_properties(dynamic,r'PACKAGES\PLANTTYPES.RTON',decoder)
        donor_sheets=aster_properties(dynamic,r'PACKAGES\PROPERTYSHEETS.RTON',decoder)
        donor_shots=aster_properties(dynamic,r'PACKAGES\PROJECTILETYPES.RTON',decoder)
    result=ResourceBundle(importer.finish(),read_index,write_index)
    paths=[r'PACKAGES\PLANTTYPES.RTON',r'PACKAGES\PROPERTYSHEETS.RTON',r'PACKAGES\PROJECTILETYPES.RTON']
    types,sheets,shots=[read_rton(result,p,decoder) for p in paths]
    if any('oakshooter' in o.get('aliases',[]) for o in types['objects']):raise ValueError('Oak-shooter already defined')
    def alias(doc,name):return next(o['objdata'] for o in doc['objects'] if name in o.get('aliases',[]))
    source=alias(donor_types,'oakshooter')
    plant={k:deepcopy(source[k]) for k in ('TypeName','PopAnim','HomeWorld','PlantAudioGroups')}
    plant.update(PlantFramework='PlantIrisDark',AnimRigClass='PlantAnimRig',Properties='RTID(IrisOakDefault@PropertySheets)')
    plant['PlantAudioGroups'].insert(0,'PlantOakshooter')
    types['objects'].append({'objclass':'PlantType','aliases':['oakshooter'],'objdata':plant})
    source=alias(donor_sheets,'OakshooterDefault')
    props={k:deepcopy(source[k]) for k in ('Cost','Hitpoints','PacketCooldown','PlantGridType','ArtCenter','PlantStats')}
    # Source level two uses the split-arrow animation. Its centre shot is
    # 130 and the two side shots are 65; no 1.5x attack/health multiplier.
    props.update(Actions=[deepcopy(source['Actions'][i]) for i in (0,1,3,4,5,6,7)],
                 PlantFoodDurationSeconds=80/30,PlantFoodPlayCount=1)
    # Only the ordinary action participates in Iris's automatic scheduler.
    # Food, split and manual arrows are selected explicitly by the adapter.
    for action in props['Actions'][1:]:action['Type']='special'
    sheets['objects'].append({'objclass':'PlantPropertySheet','aliases':['IrisOakDefault'],'objdata':props})
    allowed={k for o in shots['objects'] if o.get('objclass')=='ProjectilePropertySheet' for k in o.get('objdata',{})}
    flags={f for o in shots['objects'] for f in o.get('objdata',{}).get('CollisionFlags',[])}
    for obj in donor_shots['objects']:
        if not any(a.startswith('Oak') and a!='OakPlantAvatarFood' for a in obj.get('aliases',[])):continue
        data={k:deepcopy(v) for k,v in obj['objdata'].items() if k in allowed}
        data['ClassName']='Projectile'
        data['InitialVelocity'][1:]=[{'Min':0,'Max':0},{'Min':0,'Max':0}]
        data['CollisionFlags']=[f for f in data.get('CollisionFlags',[]) if f in flags]
        data['DamageFlags']=['lobbed'] if 'OakPlantFood' in obj['aliases'] else ['shooter']
        shots['objects'].append({'objclass':'ProjectilePropertySheet','aliases':deepcopy(obj['aliases']),'objdata':data})
    changes={}
    for path,doc in zip(paths,(types,sheets,shots)):
        changes.setdefault(result.group_for(path),{})[path]=encoder().encode_root_object(StringIO(json.dumps(doc)))
    resource=next(r for g in result.manifest(decoder)['groups'] for r in g.get('resources',[]) if r['id']=='POPANIM_PLANT_OAKSHOOTER')
    path='\\'.join(resource['path']).upper();pam=result.read(result.group_for(path),path)
    pam=rename_main_label(pam,'attack','iris_tier1_attack')
    pam=rename_main_label(pam,'attack2','attack');pam=action_commands(pam)
    changes.setdefault(result.group_for(path),{})[path]=pam
    return result.replace(changes,set())
