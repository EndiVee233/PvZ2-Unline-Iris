"""Adapt the audited official CN 4.2.8 Scaredy-shroom assets to Iris.

This prepares resources, not a replacement plant framework. Activation is kept
separate so the native cower and plant-food adapter can be verified first.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import struct
import json
from io import StringIO

from cn_rslb import unpack_rslb
from rsb_local import ResourceBundle


OFFICIAL_APK_SHA256 = '64b0f2cddb6221baf35fb32d4a0f6e64153428edf5ee5922beddb9726bedbda4'
ROOT = 'PlantScaredyshroom'


def rename_main_label(raw, old, new):
    """Change one label without reserializing authored frame commands."""
    from pam_transform_index import PamIndex
    edits = []
    for frame in PamIndex(raw).sprites[-1]['frames']:
        if frame['label'] != old:
            continue
        before = struct.pack('<H', len(old)) + old.encode()
        after = struct.pack('<H', len(new)) + new.encode()
        fragment = raw[frame['start']:frame['end']]
        if fragment.count(before) != 1:
            raise ValueError('Ambiguous Scaredy-shroom plant-food label')
        edits.append((frame['start'] + fragment.index(before), len(before), after))
    if len(edits) != 1:
        raise ValueError('Missing official Scaredy-shroom plant-food label')
    for at, size, replacement in reversed(edits):
        raw = raw[:at] + replacement + raw[at + size:]
    PamIndex(raw)
    return raw


def native_labels(raw):
    return rename_main_label(raw, 'pf', 'plantfood')


def rename_resource(value):
    """Keep PAM image IDs intact; normalize only resolution and group names."""
    if isinstance(value, dict):
        return {key: rename_resource(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rename_resource(item) for item in value]
    if isinstance(value, str):
        return value.replace('PlantScaredyShroom', ROOT).replace('_1200', '_1536') if value != '1200' else '1536'
    return value


class ScaredyAssets:
    """An Iris-resolution view of the official model and projectile bundle.

    1200 is this APK's resource selection bucket. PAM canvas, sprite dimensions
    and image matrices use the same units as Iris; they must not be enlarged by
    1536/1200. Importer subsequently generates the lower Iris resolutions.
    """
    def __init__(self, bundle, decoder):
        self.bundle = bundle
        manifest = bundle.manifest(decoder)
        source = {group['id']: group for group in manifest['groups']}
        names = ['PlantScaredyShroom', 'PlantScaredyShroom_1200', 'PlantScaredyShroom_Common']
        self._manifest = {'groups': [rename_resource(deepcopy(source[name])) for name in names]}
        self.paths = {}
        for name in names:
            for resource in source[name].get('resources', []):
                old = '\\'.join(resource['path']).upper()
                if resource.get('atlas'):
                    old += '.PTX'
                new = '\\'.join(rename_resource(resource['path'])).upper()
                if resource.get('atlas'):
                    new += '.PTX'
                self.paths[new] = old

    def manifest(self, decoder):
        return deepcopy(self._manifest)

    def group_for(self, path):
        return self.bundle.group_for(self.paths[path])

    def read(self, group, path):
        raw = self.bundle.read(group, self.paths[path])
        if path.endswith('SCAREDYSHROOM\\SCAREDYSHROOM.PAM'):
            return native_labels(raw)
        if path.endswith('SCAREDYSHROOM_PROJECTILE\\SCAREDYSHROOM_PROJECTILE.PAM'):
            return rename_main_label(raw, 'animation2', 'iris_scaredy_plantfood')
        return raw

    def texture(self, group, path):
        return self.bundle.texture(group, self.paths[path])


def official_bundle(apk, part, read_index, write_index, *, verified=False):
    apk = Path(apk)
    if not verified:
        with apk.open('rb') as stream:
            digest = sha256()
            while block := stream.read(8 * 1024 * 1024):
                digest.update(block)
        if digest.hexdigest() != OFFICIAL_APK_SHA256:
            raise ValueError('Unexpected official CN APK; audit the new version before importing')
    with ZipFile(apk) as archive:
        name, = [name for name in archive.namelist() if name.endswith('/' + part + '.rsb.smf')]
        return ResourceBundle(unpack_rslb(archive.read(name)), read_index, write_index)


def import_model(importer, bundle, decoder):
    donor = ScaredyAssets(bundle, decoder)
    existing = {group['id'] for group in importer.manifest['groups']}
    if ROOT in existing:
        raise ValueError('Scaredy model already exists; replacing groups requires an explicit migration')
    importer.root(donor, ROOT, decoder)
    return donor


class ScaredyPortrait(ScaredyAssets):
    """Map the official fragment portrait into Iris's original seed atlas."""
    def __init__(self, bundle, decoder):
        self.bundle = bundle
        groups = {group['id']: group for group in bundle.manifest(decoder)['groups']}
        source = groups['UI_Fragment_Pieces_1200']['resources']
        image = deepcopy(next(r for r in source if r['id'] == 'IMAGE_UI_FRAGMENT_PIECES_PACKETS_SCAREDYSHROOM'))
        atlas = deepcopy(next(r for r in source if r['id'] == image['parent']))
        image['id'] = 'IMAGE_UI_PACKETS_SCAREDYSHROOM'
        image['path'] = ['1536' if part == '1200' else part for part in image['path']]
        # Use the same source geometry solely to compute the scaling and
        # bearing against the original Peashooter card. Do not replace it.
        reference = deepcopy(image)
        reference['id'] = 'IMAGE_UI_PACKETS_PEASHOOTER'
        self._manifest = {'groups': [{'id': 'ScaredyPortrait_1536', 'type': 'simple',
                                      'res': '1536', 'resources': [atlas, image, reference]}]}
        path = '\\'.join(atlas['path']).upper() + '.PTX'
        self.paths = {path: path}


def import_portrait(importer, original, bundle, decoder, etc1tool):
    importer.images(original, ScaredyPortrait(bundle, decoder), 'ScaredyPortrait', 'UIImages',
                    ['IMAGE_UI_PACKETS_SCAREDYSHROOM'], decoder,
                    reference='IMAGE_UI_PACKETS_PEASHOOTER', etc1tool=etc1tool)


def import_audio(importer, bundle, decoder, legacy_global):
    from iris_scaredy_audio import port_scaredy_audio
    source = next(group for group in bundle.manifest(decoder)['groups'] if group['id'] == 'PlantScaredyShroomAudio')
    audio, = source['resources']
    path = '\\'.join(audio['path']).upper()
    raw = bundle.read(bundle.group_for(path), path)
    converted = port_scaredy_audio(legacy_global, raw)
    if struct.unpack_from('<II', converted, 8) != (88, 2669017340):
        raise ValueError('Unexpected converted Scaredy-shroom sound bank')
    group = deepcopy(source)
    group['id'] = 'PlantScaredyshroomAudio'
    importer.simple(group, {path: converted}, {})


def adapt_properties(plants, sheets, projectiles, donor_sheets, donor_projectiles):
    """Keep Iris's registered classes while supplying the audited tier-1 data."""
    def alias(document, name):
        return next(obj for obj in document['objects'] if name in obj.get('aliases', []))
    latest = alias(donor_sheets, 'ScaredyShroomDefault')['objdata']
    target = alias(sheets, 'ScaredyshroomDefault')['objdata']
    for key in ('Cost', 'Hitpoints', 'PacketCooldown', 'PlantFoodDurationSeconds',
                'PlantFoodProjectileCount', 'PlantFoodActivationSound', 'ArtCenter', 'PlantStats'):
        target[key] = deepcopy(latest[key])
    target.update(ScaredRangeWidth=3, ScaredRangeHeight=3)
    target['Actions'] = deepcopy(latest['Actions'][:2])
    target['Actions'][0]['Projectile'] = 'RTID(ScaredySpore@ProjectileTypes)'
    target['Actions'][1]['Projectile'] = 'RTID(IrisScaredyPlantfood@ProjectileTypes)'

    # Newer flags and class-specific fields are not valid old-engine enums.
    # The existing native ProjectilePropertySheet schema provides the common
    # render/velocity/damage fields; knockback is supplied by the native hook.
    allowed = {key for obj in projectiles['objects'] if obj.get('objclass') == 'ProjectilePropertySheet'
               for key in obj['objdata']}
    normal = alias(donor_projectiles, 'ScaredyShroomDefault')['objdata']
    food = alias(donor_projectiles, 'ScaredyShroomPlantfood')['objdata']
    for data, name in ((normal, 'ScaredySpore'), (food, 'IrisScaredyPlantfood')):
        converted = {key: deepcopy(value) for key, value in data.items()
                     if key in allowed and key != 'DamageFlags'}
        converted['ClassName'] = 'RangedPlantProjectile'
        if name == 'IrisScaredyPlantfood':
            converted['AttachedPAMAnimationToPlay'] = 'iris_scaredy_plantfood'
            projectiles['objects'].append({'objclass': 'ProjectilePropertySheet',
                                           'aliases': [name], 'objdata': converted})
        else:
            alias(projectiles, name)['objdata'] = converted
    for obj in plants['objects']:
        data = obj.get('objdata', {})
        if data.get('TypeName') == 'scaredyshroom':
            data['PlantAudioGroups'] = ['PlantScaredyshroomAudio', 'PlantPuffShroomAudio', 'PlantBloomerangAudio']
        if data.get('TypeName') in ('sunshroom', 'sunshroom_grown', 'sunshroom_stage3'):
            data['PlantAudioGroups'] = ['PlantSunShroomAudio']
        if data.get('TypeName') == 'puffshroom':
            data['PlantAudioGroups'] = ['PlantPuffShroomAudio']


def restore_scaredy(source, official_apk, aster_apk, read_index, write_index, decoder, encoder, etc1tool):
    """Wire the official plant's model, portrait, audio and native-ready data."""
    from contextlib import closing
    from iris_dark_ages import Importer
    from iris_dark_plants import import_audio as import_aster_audio
    from iris_future_audio import GLOBAL
    from iris_future_world import read_rton
    from iris_future_gargantuar import aster_properties
    from index_texture_prefetch import ResourceZip

    original = ResourceBundle(source, read_index, write_index)
    importer = Importer(source, read_index, write_index, decoder)
    plant = official_bundle(official_apk, 'plant2', read_index, write_index)
    import_model(importer, plant, decoder)
    import_audio(importer, plant, decoder, original.read(original.group_for(GLOBAL), GLOBAL))
    del plant
    ui = official_bundle(official_apk, 'uiactive', read_index, write_index, verified=True)
    import_portrait(importer, original, ui, decoder, etc1tool)
    del ui
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        name, = [name for name in archive.namelist() if name.endswith('/plant2.rsb.smf')]
        audio = ResourceBundle(archive.read(name), read_index, write_index)
        import_aster_audio(importer, audio, decoder, original.read(original.group_for(GLOBAL), GLOBAL))
    del audio
    modern = official_bundle(official_apk, 'dynamic', read_index, write_index, verified=True)
    modern_sheets = aster_properties(modern, r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
    modern_projectiles = aster_properties(modern, r'PACKAGES\PROJECTILETYPES.RTON', decoder)
    del modern
    bundle = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\PLANTTYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON', r'PACKAGES\PROJECTILETYPES.RTON']
    documents = [read_rton(bundle, path, decoder) for path in paths]
    adapt_properties(*documents, modern_sheets, modern_projectiles)
    resources = {group['id'] for group in importer.manifest['groups']}
    for obj in documents[0]['objects']:
        data = obj.get('objdata', {})
        if data.get('TypeName') == 'scaredyshroom' and not set(data['PlantAudioGroups']) <= resources:
            raise ValueError('Missing Scaredy-shroom audio dependency')
    changes = {}
    for path, document in zip(paths, documents):
        changes.setdefault(bundle.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(document)))
    return bundle.replace(changes, set())
