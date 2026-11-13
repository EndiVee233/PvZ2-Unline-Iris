"""Import potion jars/effects and data without donor object layouts or grades."""
from contextlib import closing
from copy import deepcopy
from io import StringIO
import json
import struct
import sys
from pathlib import Path
from zipfile import ZipFile
from index_texture_prefetch import ResourceZip
from iris_dark_ages import Importer
from iris_future_gargantuar import aster_properties
from iris_future_world import read_rton
from rsb_local import ResourceBundle
from iris_scaredy_audio import convert_plant_bank


def append_idle_pose(raw, appearance_frames):
    """Add a clean stopped pose, removing the intro's hand/dirt display list.

    The two donor labels are alternate appearances, not an idle animation.
    Starting the second label on a fresh Effect retained layers from frame 0.
    """
    donor_scripts = Path(__file__).resolve().parents[2] / 'PvZ2-Unline-Aster/scripts'
    if str(donor_scripts) not in sys.path: sys.path.append(str(donor_scripts))
    from pam_transform_index import PamIndex
    pam = PamIndex(raw); main = pam.sprites[-1]
    active, moves = {}, {}
    for f in main['frames'][:appearance_frames]:
        for index in f['rem']: active.pop(index, None); moves.pop(index, None)
        for add in f['adds']: active[add['index']] = add
        for move in f['moves']: moves[move['index']] = move
    def count(n): return bytes([n]) if n < 255 else b'\xff' + struct.pack('<H', n)
    # A separate idle PAM never instantiates the appearance's arm/dirt layers.
    # Keep the authored jar/contents/glass; particles belong to appearance only.
    permanent = {0, 1, 6, 7, 8} if appearance_frames == 50 else {0, 1, 2, 3, 7, 8}
    active = {i:a for i,a in active.items() if not a['sprite'] and a['res'] in permanent}
    frame = bytearray([14])
    frame.extend(count(len(active)))
    for index, add in sorted(active.items()):
        if add['name'] or add['res'] >= 255: raise ValueError('Unreviewed potion placement')
        frame.extend(struct.pack('<HB', index | (0x8000 if add['sprite'] else 0), add['res']))
    frame.extend(count(len(active)))
    for index in sorted(active):
        m = moves[index]; frame.extend(raw[m['start']:m['end']])
    label = b'animation'; frame.extend(struct.pack('<H', len(label)) + label)
    count_offset = main['frames'][0]['start'] - 6
    result = bytearray(raw[:count_offset]); result.extend(struct.pack('<Hhh', 2, 0, 1))
    result.extend(frame); result.extend(b'\0')
    checked = PamIndex(result)
    assert checked.sprites[-1]['frames'][0]['label'] == 'animation'
    return bytes(result)


def adapt_potion_module(data):
    """Keep each level's spawn settings, using Iris's reflected scalar types."""
    result = deepcopy(data)
    types = result.pop('PotionTypes')
    if not types or len(types) != len(set(types)) or set(types) - {'zombiepotion_speed', 'zombiepotion_toughness'}:
        raise ValueError(f'Unreviewed potion spawn list: {types}')
    delay = result.pop('PotionSpawnTimer')
    result.update(IrisMinSpawnDelay=delay['Min'], IrisMaxSpawnDelay=delay['Max'],
                  IrisPotionMask=(1 if 'zombiepotion_speed' in types else 0) |
                                (2 if 'zombiepotion_toughness' in types else 0))
    groups = result.setdefault('ResourceGroupNames', [])
    for group in ('GridItemZombiePotion', 'IrisPotionIdle', 'PlantEvilShroomAudio'):
        if group not in groups: groups.append(group)
    return result


def restore_potions(raw, aster_apk, read_index, write_index, decoder, encoder):
    importer = Importer(raw, read_index, write_index, decoder)
    stream = ResourceZip(aster_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def bundle(name):
            path, = [p for p in archive.namelist() if p.endswith('/' + name + '.rsb.smf')]
            return ResourceBundle(archive.read(path), read_index, write_index)
        importer.root(bundle('dark'), 'GridItemZombiePotion', decoder)
        audio = bundle('plant2')
        group = deepcopy(next(g for g in audio.manifest(decoder)['groups'] if g['id'] == 'PlantEvilShroomAudio'))
        resource, = group['resources']; bank_path = '\\'.join(resource['path']).upper()
        bank = audio.read(audio.group_for(bank_path), bank_path)
        original = ResourceBundle(raw, read_index, write_index)
        global_path = r'SOUNDBANKS\GLOBAL_DATA.BNK'
        recipe = json.loads((Path(__file__).resolve().parents[1] / 'src/dark/potion-audio-v88.json').read_text(encoding='utf8'))
        importer.simple(group, {bank_path: convert_plant_bank(original.read(original.group_for(global_path), global_path), bank, recipe)}, {})
        source = aster_properties(bundle('dynamic'), r'PACKAGES\PROPERTYSHEETS.RTON', decoder)
    result = ResourceBundle(importer.finish(), read_index, write_index)
    paths = [r'PACKAGES\GRIDITEMTYPES.RTON', r'PACKAGES\PROPERTYSHEETS.RTON']
    grids, sheets = [read_rton(result, p, decoder) for p in paths]
    for kind, cls in (('speed', 'IrisSpeedPotion'), ('toughness', 'IrisToughnessPotion')):
        alias = 'zombiepotion_' + kind
        if any(alias in o.get('aliases', []) for o in grids['objects']):
            raise ValueError('Potion type already defined')
        donor = next(o['objdata'] for o in source['objects']
                     if ('ZombiePotion' + kind.title() + 'Default') in o.get('aliases', []))
        assert donor['Hitpoints'] == 50
        sheet = 'IrisPotion' + kind.title()
        sheets['objects'].append({'objclass': 'GridItemPropertySheet', 'aliases': [sheet],
                                  'objdata': {key: deepcopy(donor[key]) for key in
                                              ('Hitpoints', 'HitRectOffsetX', 'HitRectOffsetWidth', 'Height')}})
        grids['objects'].append({'objclass': 'GridItemType', 'aliases': [alias], 'objdata': {
            'TypeName': alias, 'GridItemClass': cls, 'Properties': f'RTID({sheet}@PropertySheets)',
            'ResourceGroups': ['GridItemZombiePotion', 'IrisPotionIdle', 'PlantEvilShroomAudio']}})
    grids['objects'].append({'objclass': 'GridItemType', 'aliases': ['iris_potion_buff'], 'objdata': {
        'TypeName': 'iris_potion_buff', 'GridItemClass': 'IrisPotionBuff',
        'Properties': 'RTID(IrisPotionOwner@PropertySheets)', 'ResourceGroups': []}})
    sheets['objects'].append({'objclass': 'GridItemPropertySheet', 'aliases': ['IrisPotionOwner'],
                              'objdata': {'Hitpoints': 1000}})
    changes = {}
    idle_files, idle_resources = {}, []
    for kind, frames in (('SPEED', 50), ('POWER', 100)):
        ending = 'POTION_' + kind + '.PAM'
        path, = [p for p in result.files if p.endswith(ending)]
        group = result.group_for(path)
        idle_path = 'POPANIM\\IRIS_POTION_' + kind + '_IDLE.PAM'
        idle_files[idle_path] = append_idle_pose(result.read(group, path), frames)
        idle_resources.append({'type':'PopAnim', 'id':'POPANIM_IRIS_POTION_'+kind+'_IDLE',
                               'path':idle_path.lower().split('\\')})
    for path, doc in zip(paths, (grids, sheets)):
        changes.setdefault(result.group_for(path), {})[path] = encoder().encode_root_object(StringIO(json.dumps(doc)))
    extra = Importer(result.replace(changes, set()), read_index, write_index, decoder)
    extra.simple({'type':'simple', 'id':'IrisPotionIdle', 'resources':idle_resources}, idle_files, {})
    return extra.finish()
