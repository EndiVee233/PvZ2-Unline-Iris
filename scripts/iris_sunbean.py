"""Sun Bean's tier-one data for the scoped native consumption adapter."""
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


def restore_sunbean(raw, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    original = ResourceBundle(raw, read_index, write_index)
    importer = Importer(raw, read_index, write_index, decoder)
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        importer.root(bundle('plant2'), 'PlantSunBean', decoder)
        importer.images(original, bundle('uiactive'), 'UIImages_Dynamic', 'UIImages',
                        ['IMAGE_UI_PACKETS_SUNBEAN'], decoder,
                        reference='IMAGE_UI_PACKETS_SUNSHROOM', etc1tool=etc1tool)
        dynamic = bundle('dynamic')
        donor_types = aster_properties(dynamic, r'PACKAGES\PLANTTYPES.RTON', decoder)
        donor_sheets = aster_properties(dynamic, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
    def alias(doc, name):
        return next(o for o in doc['objects'] if name in o.get('aliases', []))
    result = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\PLANTTYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON']
    types, sheets = [read_rton(result, p, decoder) for p in paths]
    if any('sunbean' in o.get('aliases', []) for o in types['objects']):
        raise ValueError('Sun Bean already defined')
    source = alias(donor_types, 'sunbean')['objdata']
    plant = {k: deepcopy(source[k]) for k in ('TypeName', 'PopAnim', 'HomeWorld', 'PlantAudioGroups')}
    plant.update(PlantFramework='PlantChilibean', AnimRigClass='PlantAnimRig',
                 Properties='RTID(IrisSunBeanDefault@PropertySheets)')
    plant['PlantAudioGroups'].insert(0, 'PlantSunBean')
    types['objects'].append({'objclass': 'PlantType', 'aliases': ['sunbean'], 'objdata': plant})
    source = alias(donor_sheets, 'SunBeanDefault')['objdata']
    props = {k: deepcopy(source[k]) for k in ('Cost', 'Hitpoints', 'PacketCooldown',
             'StartingCooldown', 'PlantGridType', 'ArtCenter', 'HitRectAdjust', 'Actions', 'PlantStats')}
    # Play the full 31-frame activation before retaining the charged idle.
    props.update(PlantFoodPlayCount=1, PlantFoodDurationSeconds=31 / 30, PlantFoodSpawnCount=0)
    sheets['objects'].append({'objclass': 'ChilibeanProps', 'aliases': ['IrisSunBeanDefault'], 'objdata': props})
    changes = {}
    for path, doc in zip(paths, (types, sheets)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    return result.replace(changes, set())
