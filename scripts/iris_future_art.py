"""Use Aster's Far Future sprites in the original NA atlas geometry."""

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image

from prepare_localized_resources import atlas_image, atlas_path, box


BACKGROUND = 'IMAGE_BACKGROUNDS_FUTURE'


def sprite_changes(iris_groups, aster_groups):
    for size in (384, 768, 1536):
        group = f'DelayLoad_Background_Future_{size}'
        donor = aster_groups['DelayLoad_Background_Future_1536']
        for key in ('TEXTURE_LEFT', 'TEXTURE_RIGHT', 'DOOR_OVERLAY'):
            yield iris_groups[group][f'{BACKGROUND}_TEMP_{key}'], donor[f'{BACKGROUND}_{key}']


def polish_art(iris, future, decoder, etc1tool):
    def groups(bundle):
        return {group['id']: {resource['id']: resource for resource in group.get('resources', [])}
                for group in bundle.manifest(decoder)['groups']}

    iris_groups, aster_groups = map(groups, (iris, future))
    atlases = {key: atlas_path(resource) for group in iris_groups.values()
               for key, resource in group.items() if resource.get('atlas')}
    donor_atlases = {key: atlas_path(resource) for group in aster_groups.values()
                     for key, resource in group.items() if resource.get('atlas')}
    changes = {}
    for original, donor in sprite_changes(iris_groups, aster_groups):
        changes.setdefault(atlases[original['parent']], []).append(
            (box(original), donor_atlases[donor['parent']], box(donor))
        )
    decoded = {}
    updates = {}
    with TemporaryDirectory(prefix='iris-future-art-') as temp:
        png = Path(temp) / 'atlas.png'
        etc = Path(temp) / 'atlas.etc1'
        for path, sprites in changes.items():
            group = iris.group_for(path)
            width, height, _, fmt = iris.texture(group, path)
            image = atlas_image(iris, group, path)
            for target, source, crop in sprites:
                if source not in decoded:
                    decoded[source] = atlas_image(future, future.group_for(source), source)
                sprite = decoded[source].crop(crop)
                x, y, right, bottom = target
                image.paste(sprite.resize((right - x, bottom - y), Image.Resampling.LANCZOS), (x, y))
            if fmt == 0:
                updates[path] = image.tobytes('raw', 'BGRA')
                continue
            if fmt != 147:
                raise ValueError(f'Unsupported Far Future atlas format {fmt}')
            image.convert('RGB').save(png)
            subprocess.run([etc1tool, png, '--encodeNoHeader', '-o', etc], check=True)
            rgb = etc.read_bytes()
            rgb_size = width * height // 2
            if len(rgb) != rgb_size:
                raise ValueError(f'Unexpected ETC1 size at {path}')
            raw = bytearray(iris.read(group, path))
            for (x, y, right, bottom), _, _ in sprites:
                # Preserve untouched blocks in shared character atlases.
                for row in range(y // 4, (bottom + 3) // 4):
                    begin = row * width * 2 + x // 4 * 8
                    end = row * width * 2 + (right + 3) // 4 * 8
                    raw[begin:end] = rgb[begin:end]
            raw[rgb_size:] = image.getchannel('A').tobytes()
            updates[path] = raw
    return updates
