"""Fume-shroom resources and tier-one data for the scoped native adapter."""
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


def restore_fumeshroom(raw, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    from iris_cn_scaredy import rename_main_label
    original = ResourceBundle(raw, read_index, write_index)
    importer = Importer(raw, read_index, write_index, decoder)
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        donor = bundle('plant2')
        importer.root(donor, 'PlantFumeshroom', decoder)
        # Iris also loads the framework-named resource group before the
        # per-plant model/audio list. Our shared native framework has no art
        # of its own, but the group must exist for that load to complete.
        info_path = r'PROPERTIES\IRIS_DARK_FRAMEWORK.TXT'
        importer.simple({'type': 'simple', 'id': 'PlantIrisDark', 'resources': [
            {'type': 'File', 'id': 'RESFILE_IRIS_DARK_FRAMEWORK',
             'path': ['properties', 'iris_dark_framework.txt']}]},
            {info_path: b'Iris Dark Ages native frameworks\n'}, {})
        del donor
        importer.images(original, bundle('uiactive'), 'UIImages_Dynamic', 'UIImages',
                        ['IMAGE_UI_PACKETS_FUMESHROOM'], decoder,
                        reference='IMAGE_UI_PACKETS_SUNSHROOM', etc1tool=etc1tool)
        dynamic = bundle('dynamic')
        types = aster_properties(dynamic, r'PACKAGES\PLANTTYPES.RTON', decoder)
        sheets = aster_properties(dynamic, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
    donor_type = deepcopy(next(o for o in types['objects'] if 'fumeshroom' in o.get('aliases', [])))
    donor_sheet = next(o for o in sheets['objects'] if 'FumeshroomDefault' in o.get('aliases', []))['objdata']
    result = ResourceBundle(importer.finish(), read_index, write_index)
    changes = {}
    def update(path, value): changes.setdefault(result.group_for(path), {})[path] = value
    path = r'PACKAGES\PLANTTYPES.RTON'
    types = read_rton(result, path, decoder)
    if any('fumeshroom' in o.get('aliases', []) for o in types['objects']):
        raise ValueError('Fume-shroom already defined')
    donor_type.pop('uid', None)
    donor_type['objdata'] = {k: deepcopy(donor_type['objdata'][k]) for k in
                            ('TypeName', 'PlantAudioGroups', 'PopAnim', 'HomeWorld')}
    donor_type['objdata'].update(PlantFramework='PlantIrisDark', AnimRigClass='PlantAnimRig',
                                 Properties='RTID(IrisFumeshroomDefault@PropertySheets)')
    # Iris derives the primary model group from the registered framework
    # name. Its per-plant additional group list must also request our own
    # model when using an existing native framework container.
    donor_type['objdata']['PlantAudioGroups'].insert(0, 'PlantFumeshroom')
    types['objects'].append(donor_type)
    update(path, encoder().encode_root_object(StringIO(json.dumps(types))))
    path = r'PACKAGES\PROPERTYSHEETS.RTON'
    sheets = read_rton(result, path, decoder)
    fields = ('Cost', 'Hitpoints', 'PacketCooldown', 'StartingCooldown', 'PlantGridType',
              'PlantFoodDurationSeconds', 'ArtCenter', 'PlantStats')
    props = {k: deepcopy(donor_sheet[k]) for k in fields}
    props['PlantFoodPlayCount'] = 1
    props['Actions'] = deepcopy(donor_sheet['Actions'][:2])
    # Iris's generic rig starts its normal attack at the "attack" label.
    # The custom native callback supplies area damage instead of a projectile.
    sheets['objects'].append({'objclass': 'PlantPropertySheet',
                              'aliases': ['IrisFumeshroomDefault'], 'objdata': props})
    update(path, encoder().encode_root_object(StringIO(json.dumps(sheets))))
    manifest = result.manifest(decoder)
    resource, = [r for g in manifest['groups'] for r in g.get('resources', [])
                  if r['id'] == 'POPANIM_PLANT_FUMESHROOM']
    path = '\\'.join(resource['path']).upper()
    old = result.read(result.group_for(path), path)
    update(path, rename_main_label(old, 'special', 'attack'))
    return result.replace(changes, set())
