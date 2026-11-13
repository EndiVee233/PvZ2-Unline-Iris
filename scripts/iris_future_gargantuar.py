"""Port the Aster mech Gargantuar to the Iris resource and property layouts."""

from copy import deepcopy
from hashlib import md5
from io import BytesIO
import json
from math import ceil
from pathlib import Path, PureWindowsPath
import struct
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image

from prepare_localized_resources import atlas_image, atlas_path, box


GARGANTUAR_GROUP = 'ZombieFutureGargantuarGroup'
GARGANTUAR_ATLAS = GARGANTUAR_GROUP + '_1536'
GARGANTUAR_COMMON = GARGANTUAR_GROUP + '_Common'
BEAM_DRAW = 0x63FC3C
BEAM_DRAW_END = 0x63FE34
LASER_START_SOUND = b'Play_Zomb_Future_Gargantuar_Mvmt_Attack_DeathRay'


def link_mech_patch(source, ndk, out, address, symbols):
    toolchain = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj, payload = out / f'{source.stem}.o', out / f'{source.stem}.bin'
    subprocess.run([toolchain / 'clang.exe', '--target=armv7a-linux-androideabi21',
                    '-c', source, '-o', obj], check=True)
    subprocess.run([toolchain / 'ld.lld.exe', f'-Ttext={address:#x}', '--oformat=binary',
                    *(f'--defsym={name}={value:#x}' for name, value in symbols.items()),
                    '-o', payload, obj], check=True)
    return payload.read_bytes()


def patch_mech_beam(data, source, ndk, out):
    native_symbols = {
        'iris_atan2f': 0xE88A4,
        'iris_lock_beam_effect': 0x1DC9F4,
        'iris_get_pop_anim': 0x1D26A0,
        'iris_set_effect_world_position': 0x4E6BB8,
        'iris_set_effect_visible': 0x4E6B28,
        'iris_draw_effect': 0x4E6F70,
    }
    replacement = link_mech_patch(source, ndk, out, BEAM_DRAW, native_symbols)
    labels = b'laser_beam\0laser_hit\0'
    original = {
        BEAM_DRAW: 0xE92D48F0,
        0x63E2CC: 0xE3A01001,
        0x63E3A8: 0xFFF663EF,
        0x63EDC4: 0xFFF663EF,
    }
    if (len(replacement) > BEAM_DRAW_END - BEAM_DRAW or replacement[0x1C0:] != labels
            or any(struct.unpack_from('<I', data, address)[0] != instruction
                   for address, instruction in original.items())):
        raise ValueError('Unexpected Iris mech renderer layout')
    data[BEAM_DRAW:BEAM_DRAW + len(replacement)] = replacement
    # Keep the scene graphics transform and play the authored effect labels.
    struct.pack_into('<I', data, 0x63E2CC, 0xE3A01000)
    for address, offset in ((0x63E3A8, 0x1C0), (0x63EDC4, 0x1CB)):
        struct.pack_into('<I', data, address, (BEAM_DRAW + offset - 0xD01B04) & 0xffffffff)


def patch_mech_laser_state(data, source, ndk, out):
    phoff, = struct.unpack_from('<I', data, 28)
    stride, count = struct.unpack_from('<HH', data, 42)
    for header in range(phoff, phoff + stride * count, stride):
        kind, file_start, address, _, filesz, memsz, flags, _ = struct.unpack_from('<8I', data, header)
        if (kind, flags, filesz) == (1, 5, memsz) and file_start + filesz == len(data):
            break
    else:
        raise ValueError('Missing Iris executable patch segment')
    start = address + filesz
    symbols = {
        'iris_state_patch_base': start,
        'iris_find_laser_target': 0x63F974,
        'iris_stop_walking': 0x5E4F20,
        'iris_start_walking': 0x5E4C54,
        'iris_update_walking': 0x63BE74,
        'iris_update_laser': 0x63EDF0,
        'iris_get_zombie_rig': 0x3D9CB4,
        'iris_rig_animation_finished': 0x44DEC4,
        'iris_make_string': 0xB75560,
        'iris_string_release': 0xB39A54,
        'iris_string_destroy': 0xB739D8,
        'iris_post_zombie_sound': 0x1A4280,
        'iris_after_mech_init': 0x63CC1C,
        'iris_lock_scorch_effect': 0x1DC9F4,
        'iris_set_scorch_position': 0x4E6BB8,
        'iris_after_scorch': 0x63ED0C,
        'iris_spawn_scorch': 0x63EB30,
        'iris_play_scorch': 0x23AB44,
        'iris_assign_weak': 0x13DEA0,
        'iris_hide_scorch': 0x4E6B28,
        'iris_after_walk_exit_prologue': 0x63FB48,
        'iris_destroy_zombie_base': 0x5DEAFC,
    }
    payload = link_mech_patch(source, ndk, out, start, symbols)
    if not payload or filesz % 4 or filesz + len(payload) > 8192:
        raise ValueError('Unexpected Iris laser state payload size')
    hooks = (
        (0x63F944, 0xEB00000A, 0),
        (0x63F94C, 0xEBFFF148, 1),
        (0x63E8C4, 0xEB000149, 2),
        (0x63CC18, 0xE58401E4, 3),
        (0x63EA48, 0xE3500000, 4),
        (0x63ECF0, 0xEBEFEF93, 5),
        (0x63FB44, 0xE92D4800, 6),
        (0x6400A4, 0xEBFE7A94, 7),
        (0x64010C, 0xEBFE7A7A, 7),
    )
    render = {
        # Only the sweep emits a beam. The body handles the wind-up and recovery.
        0x63E460: (0xE3500000, 0xE3500002),
        0x63E464: (0x0A0000C4, 0x1A0000C4),
        # Aster's eye offsets, expressed in Iris's projected (x, y - z).
        0x63E4F8: (0xE3447130, 0xE34470C0),  # x +6
        0x63E510: (0xE34C61B8, 0xE34C6140),  # z -12
        0x63E514: (0xE3440204, 0xE34401E0),  # x +28
        0x63E520: (0xE34C71B0, 0xE34C7130),  # z -11
        # Reserve a weak handle and an audio flag after the original fields.
        0x63CB98: (0xE3A00F7A, 0xE3A00F7E),
        0x63CD0C: (0xE3A03F7A, 0xE3A03F7E),
        # The per-sweep impact effect supersedes the periodic scorch timestamp.
        0x63EB40: (0xED840A79, 0xE320F000),
    }
    expected = {pc: original for pc, original, _ in hooks} | {pc: pair[0] for pc, pair in render.items()}
    if any(struct.unpack_from('<I', data, pc)[0] != opcode for pc, opcode in expected.items()):
        raise ValueError('Unexpected Iris laser state layout')
    for pc, original, index in hooks:
        displacement = start + 4 * index - pc - 8
        if displacement % 4 or not -0x2000000 <= displacement < 0x2000000:
            raise ValueError('Iris laser hook exceeds the ARM branch range')
        branch = 0xEB000000 if original >> 24 == 0xEB else 0xEA000000
        struct.pack_into('<I', data, pc, branch | (displacement // 4 & 0xFFFFFF))
    for pc, (_, replacement) in render.items():
        struct.pack_into('<I', data, pc, replacement)
    data.extend(payload)
    struct.pack_into('<II', data, header + 16, filesz + len(payload), memsz + len(payload))


def aster_properties(bundle, path, decoder):
    from py3rijndael import RijndaelCbc, ZeroPadding

    raw = bundle.read(bundle.group_for(path), path)
    if raw.startswith(b'\x10\0'):
        key = md5(b'com_popcap_pvz2_magento_product_2013_05_05').hexdigest().encode()
        raw = RijndaelCbc(key, key[4:28], ZeroPadding(24), block_size=24).decrypt(raw[2:])
    if not raw.startswith(b'RTON'):
        raise ValueError(f'Expected Aster RTON at {path}')
    stream = BytesIO(raw[4:])
    stream.name = path
    return json.loads(decoder(repairFiles=False).parse_root_object(stream))


def update_mech_properties(iris, aster):
    def mech(sheet):
        entry, = (item for item in sheet['objects'] if 'ZombieGargantuarMech' in item.get('aliases', []))
        return entry['objdata']

    original, donor = mech(iris), mech(aster)
    # Keep Iris wave selection and translate Aster's one-shot ammo threshold
    # into the scalar consumed by the older mech implementation.
    wave_fields = {'Cost', 'FirstWave', 'WavePointCost', 'Weight'}
    original.update({key: donor[key] for key in (original.keys() & donor.keys()) - wave_fields})
    threshold, = donor['HealthThresholdToImpAmmoLayers']
    original['HealthPercentThrowImp'] = threshold['HealthPercentThrowImp']
    original['NormalDeathWhenMowed'] = donor['NormalDeathWhenMowed']


def mech_layout(donor_atlas):
    """Convert Aster's display sizes and pixel offsets to Iris atlas rectangles."""
    sprites = sorted((entry for entry in donor_atlas if 'parent' in entry),
                     key=lambda entry: entry['ah'], reverse=True)
    positions = {}
    x = y = row_height = 0
    for sprite in sprites:
        width, height = sprite['aw'], sprite['ah']
        # Align the cells to four pixels so the two smaller atlases retain
        # a gap between neighboring sprites when the layout is downscaled.
        cell_width = ceil(width / 4) * 4 + 4
        cell_height = ceil(height / 4) * 4 + 4
        if x + cell_width > 1024:
            x = 0
            y += row_height
            row_height = 0
        positions[sprite['id']] = (x, y)
        x += cell_width
        row_height = max(row_height, cell_height)
    if y + row_height > 2048:
        raise ValueError('Aster mech sprites do not fit in the Iris atlas')
    return positions


def mech_manifest(group, donor_atlas, layout):
    size = int(group['id'].rsplit('_', 1)[1])
    scale = 1536 // size
    target, = (entry for entry in group['resources'] if entry.get('atlas'))
    if (target['width'] * scale, target['height'] * scale) != (1024, 2048):
        raise ValueError('Unexpected Iris mech atlas dimensions')

    entries = [target]
    for entry in donor_atlas:
        if entry.get('atlas'):
            continue
        sprite = deepcopy(entry)
        x, y = layout[sprite['id']]
        sprite.update(parent=target['id'], ax=x // scale, ay=y // scale,
                      aw=round(sprite['aw'] / scale), ah=round(sprite['ah'] / scale))
        # Image names inside the PAMs stay exactly as authored in Aster.
        sprite['path'][1] = str(size)
        entries.append(sprite)
    group['resources'] = entries


def mech_assets(iris, aster, donor_groups, decoder, etc1tool):
    aster_atlas, = (entry for entry in donor_groups[GARGANTUAR_ATLAS] if entry.get('atlas'))
    image = atlas_image(aster, GARGANTUAR_ATLAS, atlas_path(aster_atlas))
    sprites = {}
    for entry in donor_groups[GARGANTUAR_ATLAS]:
        if entry.get('atlas'):
            continue
        x, y = entry['ax'], entry['ay']
        # Aster 1536 stores offsets in pixels but dimensions at 128%.
        # Crop the true pixels before resampling into Iris's 1536 layout.
        right = x + round(entry['aw'] * 25 / 32)
        bottom = y + round(entry['ah'] * 25 / 32)
        if right > image.width or bottom > image.height:
            raise ValueError(f'Invalid Aster mech sprite bounds: {entry["id"]}')
        sprites[entry['id']] = image.crop((x, y, right, bottom))
    groups = {group['id']: group.get('resources', []) for group in iris.manifest(decoder)['groups']}
    updates = {}
    with TemporaryDirectory(prefix='iris-mech-atlas-') as temp:
        png = Path(temp) / 'atlas.png'
        etc = Path(temp) / 'atlas.etc1'
        for size in (384, 768, 1536):
            group = f'{GARGANTUAR_GROUP}_{size}'
            atlas, = (entry for entry in groups[group] if entry.get('atlas'))
            path = atlas_path(atlas)
            width, height, _, fmt = iris.texture(group, path)
            if fmt != 147:
                raise ValueError(f'Expected Iris ETC1/A8 atlas at {path}')
            canvas = Image.new('RGBA', (width, height))
            for entry in groups[group]:
                if entry is atlas:
                    continue
                x, y, right, bottom = box(entry)
                scaled = sprites[entry['id']].resize((right - x, bottom - y), Image.Resampling.LANCZOS)
                canvas.paste(scaled, (x, y))
            canvas.convert('RGB').save(png)
            subprocess.run([etc1tool, png, '--encodeNoHeader', '-o', etc], check=True)
            rgb = etc.read_bytes()
            if len(rgb) != width * height // 2:
                raise ValueError(f'Unexpected mech ETC1 size at {path}')
            updates[path] = rgb + canvas.getchannel('A').tobytes()

    aster_pams = {entry['id']: entry for entry in donor_groups[GARGANTUAR_COMMON]}
    for entry in groups[GARGANTUAR_COMMON]:
        donor = aster_pams[entry['id']]
        target_path = str(PureWindowsPath(*entry['path'])).upper()
        source_path = str(PureWindowsPath(*donor['path'])).upper()
        data = aster.read(GARGANTUAR_COMMON, source_path)
        if entry['id'] == 'POPANIM_ZOMBIE_GARGANTUAR':
            # Both events need the same zombie as their emitter. Transfer the
            # frame's lone PlaySample to the native charge transition.
            frame, end = 122636, 122959
            command = b'\x01\x0a\0PlaySample' + struct.pack('<H', len(LASER_START_SOUND)) + LASER_START_SOUND
            if data[frame] != 0x24 or data[end - len(command):end] != command or data.count(command) != 1:
                raise ValueError('Unexpected Aster mech laser sound frame')
            data = data[:frame] + b'\x04' + data[frame + 1:end - len(command)] + data[end:]
        updates[target_path] = data
    return updates
