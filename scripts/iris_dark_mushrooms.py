"""Tier-one Sun-shroom and Puff-shroom data for Iris's native frameworks."""
from contextlib import closing
from copy import deepcopy
from io import StringIO
import json
from zipfile import ZipFile

from index_texture_prefetch import ResourceZip
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from rsb_local import ResourceBundle


SUN_TYPES = ('iris_dark_sun', 'iris_dark_sun_medium', 'iris_dark_sun_large')


def adapt_mushrooms(sheets, collectables, donor_sheets, donor_collectables):
    def prop(document, alias):
        return next(o['objdata'] for o in document['objects'] if alias in o.get('aliases', []))

    donor = prop(donor_sheets, 'Sunshroom')
    stages = donor['GrowthStages']
    for i, name in enumerate(('SunshroomSmall', 'SunshroomGrown', 'SunshroomStage3')):
        target = prop(sheets, name)
        for key in ('Cost', 'Hitpoints', 'PacketCooldown', 'PlantFoodDurationSeconds',
                    'StartingCooldown', 'PlantFoodSunCount', 'Actions', 'ArtCenter', 'PlantStats'):
            target[key] = deepcopy(donor[key])
        target['CollectibleTypeName'] = SUN_TYPES[i]
        if i < 2:
            target['MutationWaitSeconds'] = stages[i]['TimeToGrowInSeconds']
    # Scope the Aster 25/50/75 sun values to these plants. Iris's original
    # sunflower and other worlds retain their existing collectible economy.
    existing = {o.get('objdata', {}).get('TypeName') for o in collectables['objects']}
    for name, stage in zip(SUN_TYPES, stages):
        if name in existing:
            raise ValueError('Dark sun collectible already exists')
        source = next(o for o in donor_collectables['objects']
                      if o.get('objdata', {}).get('TypeName') == stage['CollectibleTypeName'])
        added = deepcopy(source)
        added.pop('uid', None)
        added['objdata']['TypeName'] = name
        collectables['objects'].append(added)

    source = prop(donor_sheets, 'PuffshroomDefault')
    target = prop(sheets, 'PuffshroomDefault')
    for key in ('Cost', 'Hitpoints', 'PacketCooldown', 'StartingCooldown', 'PlantGridType',
                'PlantFoodDurationSeconds', 'PlantFoodProjectileCount', 'ExpirationDurationSeconds',
                'ArtCenter', 'PlantStats'):
        target[key] = deepcopy(source[key])
    # This version has one tier-one projectile action. The additional Aster
    # action belongs to its rank skill, which is not enabled for Puff-shroom.
    target['Actions'] = deepcopy(source['Actions'][:1])
    target['ExpirationEndingScale'] = 1.0


def restore_mushrooms(raw, aster_apk, read_index, write_index, decoder, encoder):
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        name, = [n for n in archive.namelist() if n.endswith('/dynamic.rsb.smf')]
        donor = ResourceBundle(archive.read(name), read_index, write_index)
        source_sheets = aster_properties(donor, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
        source_sun = aster_properties(donor, r'PACKAGES\COLLECTABLETYPES.RTON', decoder)
    bundle = ResourceBundle(raw, read_index, write_index)
    paths = (r'PACKAGES\PROPERTYSHEETS.RTON', r'PACKAGES\COLLECTABLETYPES.RTON')
    documents = [read_rton(bundle, path, decoder) for path in paths]
    adapt_mushrooms(*documents, source_sheets, source_sun)
    changes = {}
    for path, document in zip(paths, documents):
        changes.setdefault(bundle.group_for(path), {})[path] = encoder().encode_root_object(
            StringIO(json.dumps(document)))
    return bundle.replace(changes, set())
