"""Missing Dark Ages captions, with the original user translations preserved."""
from prepare_localized_resources import LOCALES,locale_path,values_of

PLANT_COPY = {
 'sunshroom': ('Sun-shroom','Produces sun and grows over time.'),
 'puffshroom': ('Puff-shroom','Fires short-range spores and has a limited lifetime.'),
 'fumeshroom': ('Fume-shroom','Damages several zombies in front of it with fumes.'),
 'sunbean': ('Sun Bean','Makes the zombie that eats it release sun when damaged.'),
 'magnetshroom': ('Magnet-shroom','Removes metal helmets from nearby zombies.'),
 'hypnoshroom': ('Hypno-shroom','Turns the zombie that eats it into an ally.'),
 'peanut': ('Pea-nut','Shoots peas while blocking zombies.'),
 'oakshooter': ('Oak-shooter','Shoots arrows at approaching zombies.'),
 'iceshroom': ('Ice-shroom','Grows over time and attacks zombies with ice.'),
 'fireshroom': ('Fire-shroom','Grows over time and attacks zombies with fire.'),
 'coffeebean': ('Coffee Bean','Wakes nearby plants and briefly boosts their attack damage.'),
 'streetlamp': ('Streetlamp','Lights nearby fog and reveals hidden enemies.'),
 'scaredyshroom': ('Scaredy-shroom','Fires spores from a distance and hides from nearby zombies.'),
}
ENGLISH={}
for plant,(name,description) in PLANT_COPY.items():
    key=plant.upper()
    ENGLISH.update({key:name,key+'_TOOLTIP':description,key+'_DESCRIPTION_HEADER':description,
                    key+'_PRODUCT_SHORT_DESC':description,
                    key+'_DESCRIPTION':'{KEYWORD}Plant feature: {STAT}Dark Ages\n{FLAVOR}'+description})
ENGLISH['STREETLAMP_DESCRIPTION']='{FLAVOR}Streetlamp lights nearby fog and reveals hidden enemies.'
ENGLISH['MAGNETSHROOM_DESCRIPTION']='{KEYWORD}Special: {STAT}Removes metal helmets\n{KEYWORD}Plant feature: {STAT}Mushroom\n{FLAVOR}Magnet-shroom has a strong attraction to metal.'
ENGLISH['HYPNOSHROOM_DESCRIPTION']='{KEYWORD}Special: {STAT}Turns its eater into an ally\n{KEYWORD}Plant feature: {STAT}Mushroom\n{FLAVOR}Hypno-shroom convinces zombies to change sides.'
for stem,title,description in (
    ('DARK_CONVEYOR','Conveyor','Survive the Dark Ages conveyor challenge.'),
    ('DARK_FINALE','Final Night','Survive the Dark Ages zombie attack.'),
    ('HYPNOSHROOM','Turn the Tables','Use Hypno-shrooms to defend against the zombies.'),
    ('OAKSHOOTER','Archery','Hit the targets with Oak-shooter.'),
    ('SINGLE','Lone Defender','Survive the zombie attack.'),
    ('THREEPIGS','Theatre','Protect the house from the zombies.')):
    ENGLISH['STARCHALLENGE_'+stem]=description
    ENGLISH['STARCHALLENGE_'+stem+'_NAME']=title


def extend_dark_locale(raw,read_index,write_index,decoder):
    from rsb_local import ResourceBundle
    bundle=ResourceBundle(raw,read_index,write_index);changes={}
    for locale in LOCALES:
        path=locale_path(locale);text=bundle.read(bundle.group_for(path),path).decode('utf-16')
        existing=values_of(text)
        for key,value in ENGLISH.items():
            if key not in existing:text+='\r\n['+key+']\r\n'+value+'\r\n'
        after=values_of(text)
        if not ENGLISH.keys()<=after.keys():raise ValueError('Incomplete Dark Ages string extension')
        changes.setdefault(bundle.group_for(path),{})[path]=text.encode('utf-16')
    return bundle.replace(changes,set())
