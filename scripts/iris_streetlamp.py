"""Streetlamp's original Aster artwork, stats and independent fog resources."""
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
from iris_cn_scaredy import rename_main_label


def restore_streetlamp(raw, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    original = ResourceBundle(raw, read_index, write_index)
    importer = Importer(raw, read_index, write_index, decoder)
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        importer.root(bundle('plant2'), 'PlantStreetLamp', decoder)
        importer.root(bundle('dark'), 'War_Misty', decoder)
        importer.images(original, bundle('uiactive'), 'UIImages_Dynamic', 'UIImages',
                        ['IMAGE_UI_PACKETS_STREETLAMP'], decoder,
                        reference='IMAGE_UI_PACKETS_SUNSHROOM', etc1tool=etc1tool)
        donor = bundle('dynamic')
        source_types = aster_properties(donor, r'PACKAGES\PLANTTYPES.RTON', decoder)
        source_sheets = aster_properties(donor, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
    result = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\PLANTTYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON']
    types, sheets = [read_rton(result, p, decoder) for p in paths]
    if any('streetlamp' in o.get('aliases', []) for o in types['objects']):
        raise ValueError('Streetlamp already defined')
    source = next(o['objdata'] for o in source_types['objects'] if 'streetlamp' in o.get('aliases', []))
    plant = {k: deepcopy(source[k]) for k in ('TypeName', 'PopAnim', 'HomeWorld', 'PlantAudioGroups')}
    plant.update(PlantFramework='PlantIrisDark', AnimRigClass='PlantAnimRig',
                 Properties='RTID(IrisStreetLampDefault@PropertySheets)')
    plant['PlantAudioGroups'].insert(0, 'PlantStreetLamp')
    types['objects'].append({'objclass': 'PlantType', 'aliases': ['streetlamp'], 'objdata': plant})
    source = next(o['objdata'] for o in source_sheets['objects'] if 'StreetLamp' in o.get('aliases', []))
    props = {k: deepcopy(source[k]) for k in ('Cost', 'Hitpoints', 'PacketCooldown', 'StartingCooldown',
             'PlantGridType', 'ArtCenter', 'PlantStats')}
    props.update(Actions=[], PlantFoodPlayCount=1, PlantFoodDurationSeconds=3)
    sheets['objects'].append({'objclass': 'PlantPropertySheet', 'aliases': ['IrisStreetLampDefault'], 'objdata': props})
    changes = {}
    for path, doc in zip(paths, (types, sheets)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    resource, = [r for g in result.manifest(decoder)['groups'] for r in g.get('resources', [])
                  if r['id'] == 'POPANIM_PLANT_STREETLAMP']
    path = '\\'.join(resource['path']).upper()
    pam = result.read(result.group_for(path), path)
    pam = rename_main_label(pam, 'idle01', 'idle')
    changes.setdefault(result.group_for(path), {})[path] = pam
    return result.replace(changes, set())
