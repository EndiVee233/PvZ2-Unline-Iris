"""Hypno-shroom tier-one art/data for Iris's own allegiance adapter."""
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


def restore_hypno(raw, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    original = ResourceBundle(raw, read_index, write_index)
    importer = Importer(raw, read_index, write_index, decoder)
    framework_path = r'PROPERTIES\IRIS_HYPNO_FRAMEWORK.TXT'
    importer.simple({'type': 'simple', 'id': 'PlantIrisHypno', 'resources': [
        {'type': 'File', 'id': 'RESFILE_IRIS_HYPNO_FRAMEWORK',
         'path': ['properties', 'iris_hypno_framework.txt']}]},
        {framework_path: b'Iris Hypno-shroom native framework\n'}, {})
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        importer.root(bundle('plant2'), 'PlantHypnoShroom', decoder)
        importer.images(original, bundle('uiactive'), 'UIImages_Dynamic', 'UIImages',
                        ['IMAGE_UI_PACKETS_HYPNOSHROOM'], decoder,
                        reference='IMAGE_UI_PACKETS_SUNSHROOM', etc1tool=etc1tool)
        dynamic = bundle('dynamic')
        donor_types = aster_properties(dynamic, r'PACKAGES\PLANTTYPES.RTON', decoder)
        donor_sheets = aster_properties(dynamic, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
    result = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\PLANTTYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON', r'PACKAGES\GRIDITEMTYPES.RTON']
    types, sheets, grids = [read_rton(result, p, decoder) for p in paths]
    if any('hypnoshroom' in o.get('aliases', []) for o in types['objects']):
        raise ValueError('Hypno-shroom already defined')
    source = next(o['objdata'] for o in donor_types['objects'] if 'hypnoshroom' in o.get('aliases', []))
    plant = {k: deepcopy(source[k]) for k in ('TypeName', 'PopAnim', 'HomeWorld', 'PlantAudioGroups')}
    plant.update(PlantFramework='PlantIrisHypno', AnimRigClass='PlantAnimRig',
                 Properties='RTID(IrisHypnoDefault@PropertySheets)')
    plant['PlantAudioGroups'].insert(0, 'PlantHypnoShroom')
    plant['PlantAudioGroups'].extend(['ZombieDarkGargantuarGroup', 'ZombieDarkImpGroup',
                                    'ZombieDarkAgesGargantuarAudio'])
    types['objects'].append({'objclass': 'PlantType', 'aliases': ['hypnoshroom'], 'objdata': plant})
    source = next(o['objdata'] for o in donor_sheets['objects'] if 'HypnoShroomDefault' in o.get('aliases', []))
    props = {k: deepcopy(source[k]) for k in ('Cost', 'Hitpoints', 'PacketCooldown', 'StartingCooldown',
             'PlantFoodDurationSeconds', 'PlantGridType', 'ArtCenter', 'HitRectAdjust', 'PlantStats', 'IsConsumable')}
    props.update(Actions=[], PlantFoodPlayCount=1)
    sheets['objects'].append({'objclass': 'PlantPropertySheet', 'aliases': ['IrisHypnoDefault'], 'objdata': props})
    grids['objects'].append({'objclass': 'GridItemType', 'aliases': ['iris_hypno_ally'], 'objdata': {
        'TypeName': 'iris_hypno_ally', 'GridItemClass': 'IrisHypnoAlly',
        'Properties': 'RTID(IrisHypnoAllyDefault@PropertySheets)', 'ResourceGroups': []}})
    sheets['objects'].append({'objclass': 'GridItemPropertySheet', 'aliases': ['IrisHypnoAllyDefault'],
                              'objdata': {'Hitpoints': 1000, 'Height': 'low', 'HitRectOffsetX': -20,
                                          'HitRectOffsetWidth': 0}})
    changes = {}
    for path, doc in zip(paths, (types, sheets, grids)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes, set())
