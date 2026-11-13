"""Load the actual plant artwork before SeedChooser creates preview rigs.

Battle loads PlantAudioGroups as well as the framework group; SeedChooser's
preview path only loads the framework. Owned generic frameworks therefore
need their artwork in the chooser's normal composite dependency list.
"""
from copy import deepcopy
import struct
from iris_dark_ages import Importer

PREVIEW_ROOTS=('PlantSunshroom','PlantPuffshroom','PlantFumeshroom','PlantSunBean',
               'PlantMagnetShroom','PlantHypnoShroom','PlantPeanut','PlantOakshooter',
               'PlantIceShroom','PlantFireShroom','PlantCoffeeBean','PlantStreetLamp',
               'PlantScaredyshroom')

def restore_chooser_previews(raw,read_index,write_index,decoder):
    importer=Importer(raw,read_index,write_index,decoder)
    groups={g['id']:g for g in importer.manifest['groups']}
    chooser=groups['UI_SeedChooser'];children=deepcopy(chooser['subgroups'])
    present={c['id'] for c in children}
    for name in PREVIEW_ROOTS:
        for child in groups[name]['subgroups']:
            if child['id'] not in present:
                children.append(deepcopy(child));present.add(child['id'])
    if len(children)>64:raise ValueError('Seed chooser composite exceeds RSB child capacity')
    chooser['subgroups']=children
    row,=[c for c in importer.base.composites if bytes(c[:128]).split(b'\0',1)[0]==b'UI_SeedChooser']
    row[128:1152]=bytes(1024)
    indices={g['ID']:i for i,g in enumerate(importer.base.groups)}
    for i,child in enumerate(children):
        struct.pack_into('<II',row,128+16*i,indices[child['id']],int(child.get('res',0)))
    struct.pack_into('<I',row,1152,len(children))
    importer.validate_animation_dependencies(chooser)
    print(f'Seed chooser preview: {len(PREVIEW_ROOTS)} plant roots, {len(children)} dependency groups')
    return importer.finish()
