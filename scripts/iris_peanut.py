"""Tier-one Peanut data and artwork; combat is supplied by the native adapter."""
from contextlib import closing
from copy import deepcopy
from io import StringIO
import json
from zipfile import ZipFile
from index_texture_prefetch import ResourceZip
from iris_dark_ages import Importer
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from rsb_local import ResourceBundle


def restore_peanut(raw, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    original = ResourceBundle(raw, read_index, write_index)
    importer = Importer(raw, read_index, write_index, decoder)
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        importer.root(bundle('plant2'), 'PlantPeanut', decoder)
        importer.images(original, bundle('uiactive'), 'UIImages_Dynamic', 'UIImages',
                        ['IMAGE_UI_PACKETS_PEANUT'], decoder,
                        reference='IMAGE_UI_PACKETS_SUNSHROOM', etc1tool=etc1tool)
        dynamic = bundle('dynamic')
        donor_types = aster_properties(dynamic, r'PACKAGES\PLANTTYPES.RTON', decoder)
        donor_sheets = aster_properties(dynamic, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
        donor_projectiles = aster_properties(dynamic, r'PACKAGES\PROJECTILETYPES.RTON', decoder)
    def alias(doc, name):
        return next(o for o in doc['objects'] if name in o.get('aliases', []))
    result = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\PLANTTYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON',
             r'PACKAGES\PROJECTILETYPES.RTON']
    types, sheets, projectiles = [read_rton(result, p, decoder) for p in paths]
    if any('peanut' in o.get('aliases', []) for o in types['objects']):
        raise ValueError('Peanut already defined')
    source = alias(donor_types, 'peanut')['objdata']
    plant = {k: deepcopy(source[k]) for k in ('TypeName', 'PopAnim', 'HomeWorld', 'PlantAudioGroups')}
    plant.update(PlantFramework='PlantRepeater', AnimRigClass='PlantAnimRig',
                 Properties='RTID(IrisPeanutDefault@PropertySheets)')
    plant['PlantAudioGroups'].insert(0, 'PlantPeanut')
    types['objects'].append({'objclass': 'PlantType', 'aliases': ['peanut'], 'objdata': plant})
    source = alias(donor_sheets, 'PeanutDefault')['objdata']
    props = {k: deepcopy(source[k]) for k in ('Cost', 'Hitpoints', 'PacketCooldown',
             'PlantGridType', 'PlantFoodDurationSeconds', 'PlantFoodProjectileCount',
             'PlantFoodActivationSound', 'ArtCenter', 'PlantStats', 'CanReceiveFirstAid', 'Actions')}
    props.update(PlantFoodPlayCount=1, StartingCooldown=0)
    props['Actions'][0]['Projectile'] = 'RTID(IrisPeanutDefault@ProjectileTypes)'
    sheets['objects'].append({'objclass': 'RepeaterProps', 'aliases': ['IrisPeanutDefault'], 'objdata': props})
    allowed = {k for o in projectiles['objects'] if o.get('objclass') == 'ProjectilePropertySheet'
               for k in o['objdata']}
    source = alias(donor_projectiles, 'PeanutDefault')['objdata']
    projectile = {k: deepcopy(v) for k, v in source.items() if k in allowed and k != 'DamageFlags'}
    projectile.update(ClassName='RangedPlantProjectile', Damage=20)
    # Use Iris's horizontal projectile convention for the transverse axes.
    projectile['InitialVelocity'][1:] = [{'Min': 0.0, 'Max': 0.0},
                                         {'Min': 0.0, 'Max': 0.0}]
    projectiles['objects'].append({'objclass': 'ProjectilePropertySheet',
                                   'aliases': ['IrisPeanutDefault'], 'objdata': projectile})
    changes = {}
    for path, doc in zip(paths, (types, sheets, projectiles)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes, set())
