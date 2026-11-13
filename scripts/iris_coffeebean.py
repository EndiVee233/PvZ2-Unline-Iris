"""Coffee Bean's original one-tier data, with an owned saved buff controller.

Aster's unused Sunflower rank table is deliberately excluded. The native
framework owns the authored animation, wake-up and six-second 10% attack buff.
"""
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

ENGLISH = {
    'COFFEEBEAN': 'Coffee Bean',
    'COFFEEBEAN_TOOLTIP': 'Wakes plants and briefly increases their attack damage.',
    'COFFEEBEAN_PRODUCT_SHORT_DESC': 'Wakes sleeping plants and temporarily boosts their attack damage.',
    'COFFEEBEAN_DESCRIPTION_HEADER': 'Coffee Bean wakes nearby sleeping plants and briefly boosts their attack damage.',
    'COFFEEBEAN_DESCRIPTION': '{KEYWORD}Plant feature: {STAT}Short\n{FLAVOR}Coffee Bean has one reliable way to start the day: wake everyone up.',
}


def restore_coffeebean(raw, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    original = ResourceBundle(raw, read_index, write_index)
    importer = Importer(raw, read_index, write_index, decoder)
    importer.simple({'type': 'simple', 'id': 'PlantIrisCoffee', 'resources': [
        {'type': 'File', 'id': 'RESFILE_IRIS_COFFEE_FRAMEWORK',
         'path': ['properties', 'iris_coffee_framework.txt']}]},
        {r'PROPERTIES\IRIS_COFFEE_FRAMEWORK.TXT': b'Iris Coffee Bean native framework\n'}, {})
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        for owner, group in (('plant2', 'PlantCoffeeBean'), ('plant1', 'PlantPeach')):
            if group not in importer.names:
                importer.root(bundle(owner), group, decoder)
        importer.images(original, bundle('uiactive'), 'UIImages_Dynamic', 'UIImages',
                        ['IMAGE_UI_PACKETS_COFFEEBEAN'], decoder,
                        reference='IMAGE_UI_PACKETS_SUNSHROOM', etc1tool=etc1tool)
        dynamic = bundle('dynamic')
        donor_types = aster_properties(dynamic, r'PACKAGES\PLANTTYPES.RTON', decoder)
        donor_sheets = aster_properties(dynamic, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
    result = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\PLANTTYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON', r'PACKAGES\GRIDITEMTYPES.RTON']
    types, sheets, grids = [read_rton(result, p, decoder) for p in paths]
    if any('coffeebean' in o.get('aliases', []) for o in types['objects']):
        raise ValueError('Coffee Bean already defined')
    source = next(o['objdata'] for o in donor_types['objects'] if 'coffeebean' in o.get('aliases', []))
    plant = {k: deepcopy(source[k]) for k in ('TypeName', 'PopAnim', 'HomeWorld', 'PlantAudioGroups')}
    plant.update(PlantFramework='PlantIrisCoffee', AnimRigClass='PlantAnimRig',
                 Properties='RTID(IrisCoffeeDefault@PropertySheets)')
    plant['PlantAudioGroups'].insert(0, 'PlantCoffeeBean')
    types['objects'].append({'objclass': 'PlantType', 'aliases': ['coffeebean'], 'objdata': plant})
    source = next(o['objdata'] for o in donor_sheets['objects'] if 'CoffeeBeanDefault' in o.get('aliases', []))
    props = {k: deepcopy(source[k]) for k in ('Cost', 'Hitpoints', 'PacketCooldown',
             'PlantGridType', 'ArtCenter', 'PlantStats')}
    props.update(Actions=[], StartingCooldown=0, PlantFoodPlayCount=1)
    sheets['objects'].append({'objclass': 'PlantPropertySheet', 'aliases': ['IrisCoffeeDefault'], 'objdata': props})
    grids['objects'].append({'objclass': 'GridItemType', 'aliases': ['iris_coffee_buff'], 'objdata': {
        'TypeName': 'iris_coffee_buff', 'GridItemClass': 'IrisCoffeeBuff',
        'Properties': 'RTID(IrisCoffeeBuffDefault@PropertySheets)', 'ResourceGroups': ['PlantPeach']}})
    sheets['objects'].append({'objclass': 'GridItemPropertySheet', 'aliases': ['IrisCoffeeBuffDefault'],
                              'objdata': {'Hitpoints': 1000, 'Height': 'low'}})
    changes = {}
    for path, doc in zip(paths, (types, sheets, grids)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    for path in result.files:
        if path.startswith('LOCALES\\') and path.endswith('\\PROPERTIES\\LAWNSTRINGS.TXT'):
            text = result.read(result.group_for(path), path).decode('utf-16')
            for key, value in ENGLISH.items():
                if '[' + key + ']' not in text:
                    text += '\r\n[' + key + ']\r\n' + value + '\r\n'
            changes.setdefault(result.group_for(path), {})[path] = text.encode('utf-16')
    return result.replace(changes, set())
