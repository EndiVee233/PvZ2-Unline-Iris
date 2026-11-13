"""Resource preparation for the expanded Aster Dark Ages plant roster.

The game types and level gates remain separate: having a valid model is not
evidence that its native framework or special ability has been implemented.
"""
from copy import deepcopy
import json
from pathlib import Path

from iris_dark_ages import Importer
from iris_scaredy_audio import convert_plant_bank


MODEL_ROOTS = {
    'fumeshroom': 'PlantFumeshroom',
    'sunbean': 'PlantSunBean',
    'magnetshroom': 'PlantMagnetShroom',
    'peanut': 'PlantPeanut',
    'streetlamp': 'PlantStreetLamp',
    'oakshooter': 'PlantOakshooter',
    'fireshroom': 'PlantFireShroom',
    'iceshroom': 'PlantIceShroom',
}
DEPENDENCY_ROOTS = {'hypnoshroom': 'PlantHypnoShroom', 'coffeebean': 'PlantCoffeeBean'}
AUDIO_GROUPS = (
    'PlantSunShroomAudio', 'PlantPuffShroomAudio', 'PlantFumeShroomAudio',
    'PlantSunBeanAudio', 'PlantMagnetShroomAudio', 'PlantPeanutAudio',
    'PlantIceShroomAudio', 'PlantHypnoShroomAudio', 'PlantCoffeeBeanAudio',
)


def prepare_models(source, donor, read_index, write_index, decoder, *, dependencies=True):
    importer = Importer(source, read_index, write_index, decoder)
    roots = MODEL_ROOTS | (DEPENDENCY_ROOTS if dependencies else {})
    for root in roots.values():
        importer.root(donor, root, decoder)
    return importer.finish()


def import_audio(importer, donor, decoder, legacy_global):
    recipes = json.loads((Path(__file__).resolve().parents[1] / 'src/dark/plant-audio-v88.json').read_text())['banks']
    groups = {group['id']: group for group in donor.manifest(decoder)['groups']}
    for name in AUDIO_GROUPS:
        group = deepcopy(groups[name])
        bank, = group['resources']
        path = '\\'.join(bank['path']).upper()
        raw = donor.read(donor.group_for(path), path)
        importer.simple(group, {path: convert_plant_bank(legacy_global, raw, recipes[name])}, {})
