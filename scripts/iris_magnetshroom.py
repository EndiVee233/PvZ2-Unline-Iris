"""Tier-one Magnet-shroom art and data for the native Dark Ages framework."""
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


def restore_magnetshroom(raw, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    original = ResourceBundle(raw, read_index, write_index)
    importer = Importer(raw, read_index, write_index, decoder)
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        importer.root(bundle('plant2'), 'PlantMagnetShroom', decoder)
        importer.images(original, bundle('uiactive'), 'UIImages_Dynamic', 'UIImages',
                        ['IMAGE_UI_PACKETS_MAGNETSHROOM'], decoder,
                        reference='IMAGE_UI_PACKETS_SUNSHROOM', etc1tool=etc1tool)
        donor = bundle('dynamic')
        source_types = aster_properties(donor, r'PACKAGES\PLANTTYPES.RTON', decoder)
        source_sheets = aster_properties(donor, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
    result = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\PLANTTYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON']
    types, sheets = [read_rton(result, p, decoder) for p in paths]
    if any('magnetshroom' in o.get('aliases', []) for o in types['objects']):
        raise ValueError('Magnet-shroom already defined')
    source = next(o['objdata'] for o in source_types['objects'] if 'magnetshroom' in o.get('aliases', []))
    plant = {k: deepcopy(source[k]) for k in ('TypeName', 'PopAnim', 'HomeWorld', 'PlantAudioGroups')}
    plant.update(PlantFramework='PlantIrisDark', AnimRigClass='PlantAnimRig',
                 Properties='RTID(IrisMagnetShroomDefault@PropertySheets)')
    plant['PlantAudioGroups'].insert(0, 'PlantMagnetShroom')
    types['objects'].append({'objclass': 'PlantType', 'aliases': ['magnetshroom'], 'objdata': plant})
    source = next(o['objdata'] for o in source_sheets['objects'] if 'MagnetShroomDefault' in o.get('aliases', []))
    props = {k: deepcopy(source[k]) for k in ('Cost', 'Hitpoints', 'PacketCooldown', 'StartingCooldown',
             'PlantGridType', 'ArtCenter', 'HitRectAdjust', 'PlantStats')}
    props.update(Actions=[], PlantFoodPlayCount=1, PlantFoodDurationSeconds=4.0)
    sheets['objects'].append({'objclass': 'PlantPropertySheet', 'aliases': ['IrisMagnetShroomDefault'], 'objdata': props})
    changes = {}
    for path, doc in zip(paths, (types, sheets)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes, set())
