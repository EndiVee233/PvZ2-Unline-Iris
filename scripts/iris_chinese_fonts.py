"""Route localized text to Aster's typefaces in Iris's shared font slots."""

from collections import defaultdict
from contextlib import ExitStack
from io import BytesIO
import re

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from prepare_localized_resources import TOKENS


SLOTS = {
    'BRIANNETOD': 'BRIANNE',
    'HOUSE OF TERROR': 'BRIANNE',
    'FBUSV8C5EI': 'FZY4JW',
    'MONOLINESCRIPTMTSTD': 'FZY4JW',
    'PICO12__': 'FZY4JW',
}
NARRATORS = {
    'crazydave': 'BRIANNE', 'crazydaveicon': 'BRIANNE',
    'winnie': 'PICO', 'winnieicon': 'PICO',
    'zombossicon': 'ASHLEYSCRIPT',
}
SPEAKER = re.compile(r'\{(?:NPC_ENTER|SAY|EXCITED|PLAYFUL|TIRED|SHOUT):([a-z]+)\}', re.I)
STORE_PRODUCT_COPY = re.compile(r'product_\d+_(?:description|short_description|name)')
STORE_PROFILE_CAPTIONS = {'STORE_COINS_CURRENT_PROFILE', 'STORE_PLANTS_ALL_PROFILES'}
HUD_CHARACTERS = '0123456789,./:%+-'
CHINESE_PUNCTUATION = set(map(ord, '，。！？：；、…“”《》（）'))
PLAY_SCALE = 0.84
TUTORIAL_SCALE = 0.76
LEGACY_BUTTONS = {
    'ALMANAC_CLOSE', 'BUY_MORE', 'GO_TO_EVENT', 'LOD_BACK_TO_MAP', 'LOD_EVENT_NEXT',
    'LOD_PARTY_NEXT', 'OPEN_BROWSER', 'PLAY', 'PLAY_CURRENT_LEVEL', 'PLAY_LEVEL',
    'PLAY_NEXT_LEVEL', 'STAT_RANGE_CLOSE', 'STORE_MERCH_LINK', 'STORE_NO_PRICE',
    'TRY_AGAIN', 'UNLOCK_GATE',
}


EXTRA_BUTTONS = {
    'ALMANAC_PLANTS', 'ALMANAC_ZOMBIES', 'ALMANAC_UPGRADES', 'ALMANAC_PLANT_VIEW_ON_MAP',
    'ALMANAC_UPGRADE_VIEW_ON_MAP', 'BACK_TO_MAP', 'BACK_TO_MENU', 'HIDE_LAWN',
    'JUMP_TO_COLLECTIONS_VIEW', 'JUMP_TO_MACHINE_VIEW', 'RESTART_LABEL', 'RESUME_GAME',
    'RETRY', 'SETTINGS_HELP_TITLE', 'VIEW_IN_ALMANAC', 'VIEW_LAWN', 'VIEW_UPGRADES',
    'WORLD_PREVIEW_BUY_NOW', 'WORLD_PREVIEW_STAR_UNLOCK', 'MAINMENU_ACCEPT',
    'MAINMENU_DELETE_PROFILE', 'MAINMENU_EDIT_PROFILE', 'MAINMENU_KEEP_PROFILE',
    'MAINMENU_NEW_PROFILE', 'MAINMENU_PLAY', 'MAINMENU_SAVE', 'OUT_OF_CONTENT_CONFIRM',
    'OUT_OF_CONTENT_REJECT',
}
PAUSE_LABELS = {'PAUSED_HEADER', 'GAME_PAUSED', 'OPTIONS_MUSIC_LABEL', 'OPTIONS_SOUNDFX'}
ASTER_HEADINGS = {
    'MAINMENU_WELCOME', 'MAINMENU_SELECT_PLAYER', 'MAINMENU_NEW_PROFILE', 'WHO_ARE_YOU',
    'MAINMENU_EDIT_PLAYER', 'MAINMENU_EDIT_PROFILE', 'MAINMENU_DELETE_PROFILE_HEADER',
    'SETTINGS_TITLE', 'SETTINGS_ABOUT_TITLE', 'UNIVERSE_MAP_TITLE', 'PREVIEW_BUTTON',
    'LEAVE_GAME_HEADER', 'LEAVE_DANGER_ROOM_GAME_HEADER', 'RESTART_LEVEL_HEADER',
    'BUY_GOLD_HEADER', 'COIN_STORE', 'GEM_STORE', 'STORE_COMING_SOON',
    'YETI_FUE_DIALOG_TITLE', 'YETI_ESCAPE_DIALOG_TITLE', 'CLICK_TO_CONTINUE',
    'CANNON_SCORE', 'CANNON_MINSCORE', 'CANNON_COMBO', 'CREDITS_PVZ_TITLE',
}
ASTER_BODY = {
    'MAINMENU_CLICK_TO_ADD_PLAYER', 'MAINMENU_DELETE_PROFILE_BODY', 'USERNAME_ERROR',
    'LEAVE_GAME_BODY', 'LEAVE_DANGER_ROOM_GAME', 'RESTART_LEVEL', 'RESTART_LEVEL_BODY',
    'DIALOG_SKIP_TUTORIAL', 'BUY_GOLD_DESCRIPTION', 'COIN_STORE_TEXT',
    'YETI_FUE_DIALOG_DESCRIPTION', 'YETI_ESCAPE_DIALOG_TEXT',
    'CAMEL_MINIGAME_TUTORIAL_1', 'CAMEL_MINIGAME_TUTORIAL_2',
    'CAMEL_MINIGAME_TUTORIAL_3', 'CANNON_TUTORIAL_1', 'CANNON_TUTORIAL_2',
}
ASTER_BODY_PREFIXES = (
    'WORLD_PREVIEW_DESCRIPTION_', 'WORLD_PREVIEW_TEASER_', 'WORLDMAP_YETI_',
    'WORLD_MAP_TIME_LEVEL_DECS', 'PURCHASE_DIALOG_', 'PURCHASE_ERROR_',
    'PURCHASE_RESTORE_DIALOG_', 'DANGER_ROOM_', 'STAT_',
)
ASTER_WARNINGS = (
    'WARNING_STANDARD_', 'WARNING_CAMELMINIGAME_', 'WARNING_CANNONMINIGAME_',
    'WARNING_RIVERCROSSING_', 'FAILED_',
)
UNMAPPED = {'PLAYER_PROGRESS_HEADER'}
UNMAPPED_PREFIXES = ('PROGRESS_ITEM_', 'PURCHASE_CROSS_PROFILE_', 'SETTINGS_RESTORE_PURCHASES')
MAP_LATIN_BASE = 0xF800
TRIP_GLYPHS = range(0xF880, 0xF8FF)


def button_caption(key):
    return (key in LEGACY_BUTTONS or key in EXTRA_BUTTONS
            or key.startswith(('BUTTON_', 'DIALOG_STRING_', 'DIALOG_NO_', 'DIALOG_YES_'))
            or key.endswith('_BUTTON') or '_BUTTON_' in key)


def chooser_caption(key):
    return key.startswith('CHOOSER_') or key in ('CHOOSE_YOUR_PLANTS', 'LETS_ROCK_BUTTON')


def aster_style(key, plant, voice):
    if key == 'MAINMENU_PLAY':
        return 'FZSEJW', PLAY_SCALE
    if (key in ASTER_HEADINGS or key in PAUSE_LABELS or key in STORE_PROFILE_CAPTIONS
            or key.startswith(('WORLD_NAME_', 'CREDTIS_'))
            or chooser_caption(key) or (button_caption(key) and key != 'SETTINGS_HELP_TITLE')
            or key.startswith('STARCHALLENGE_CHALLENGE_HEADER_')):
        return 'FZSEJW', 1
    if (key.startswith(ASTER_WARNINGS)
            or key.endswith('_LEVEL_NAME')
            or key in ('PLAYERS_HOUSE', 'ADVICE_HUGE_WAVE', 'WARNING_FINAL_WAVE',
                       'ADVICE_NEW_LEVEL', 'POPCAP_GAMES_PRESENTS')):
        return 'FZKATJW', 1
    if key in ('RESTART_LEVEL', 'RESTART_LEVEL_BODY') or (plant and key.endswith('_TOOLTIP')):
        # Fit the original Iris text box without leaving punctuation on its own line.
        return 'FZY4JW', 0.90
    if key in ASTER_BODY or key.startswith(ASTER_BODY_PREFIXES):
        return 'FZY4JW', 1
    if key.startswith('AWARD_SCREEN_'):
        body = '_DESCRIPTION' in key or key.startswith(('AWARD_SCREEN_STAR_GOAL', 'AWARD_SCREEN_WORLDTROPHY_'))
        face = 'FZY4JW' if body else 'FZSEJW'
        return face, 1
    if STORE_PRODUCT_COPY.fullmatch(key):
        return ('FZSEJW' if key.endswith(('_name', '_short_description')) else 'FZY4JW'), 1
    if key.endswith(('_DESCRIPTION', '_DESCRIPTION_HEADER', '_TOOLTIP')) or key.startswith('STARCHALLENGE_'):
        return 'FZY4JW', 1
    if plant or (key.startswith('UPGRADE_') and not key.endswith('_INFO')):
        return 'FZSEJW', 1
    if key.startswith('NARRATIVE_'):
        return ('FZKATJW' if voice == 'BRIANNE' else 'FZY4JW'), 1
    return None


def text_style(key, value, custom=False, chooser_plant=False, voice=None):
    if custom and key.startswith('PLAYERS_TRIP_TO_'):
        return 'CUSTOM', 1, 'trip'
    if custom and chooser_plant and key.endswith('_TOOLTIP'):
        # Fit the wider custom glyphs within the original plant description box.
        return 'CUSTOM', 0.90
    if custom and (key in PAUSE_LABELS or chooser_plant or chooser_caption(key)):
        return 'CUSTOM', 1
    if custom and button_caption(key):
        return 'FZKATJW', PLAY_SCALE if key == 'MAINMENU_PLAY' else 1
    if not custom:
        if key in UNMAPPED or key.startswith(UNMAPPED_PREFIXES):
            return None
        style = aster_style(key, chooser_plant, voice)
        if style is not None:
            return style
    if key == 'MAINMENU_PLAY':
        return 'FZY4JW', PLAY_SCALE
    if (key.endswith('_LEVEL_NAME') or re.fullmatch(r'CHALLENGE_.*_NAME', key)
            or key == 'PLAYERS_HOUSE' or key.startswith('PLAYERS_TRIP_TO_')):
        return 'FZKATJW', 1
    if key.startswith('WORLD_NAME_'):
        return 'FZSEJW', 1
    if key.startswith(('ADVICE_', 'TUTORIAL_')):
        return 'FZY4JW', TUTORIAL_SCALE
    if (key.startswith(('WARNING_STANDARD_', 'WARNING_CAMELMINIGAME_', 'WARNING_CANNONMINIGAME_',
                        'WORLD_MAP_', 'WORLD_PREVIEW_', 'MAINMENU_', 'SETTINGS_', 'OPTIONS_',
                        'DIALOG_', 'BUTTON_', 'BACK_TO_', 'CONTINUE_', 'LEAVE_GAME_',
                        'RESTART_', 'RESUME_'))
            or key.endswith('_BUTTON') or '_BUTTON_' in key or key == 'PAUSED_HEADER' or key in LEGACY_BUTTONS):
        return 'FZY4JW', 1
    if key.startswith('NARRATIVE_'):
        voices = {NARRATORS.get(speaker.lower()) for speaker in SPEAKER.findall(value)}
        if len(voices) == 1:
            face = voices.pop()
            if face is not None:
                return face, 1
    return None


def build_aliases(translations, fonts, custom=False):
    # Old widgets share font slots. Route only visible Chinese glyphs from
    # known labels and leave NPC commands, format variables and player names intact.
    used = set().union(*(font.getBestCmap() for font in fonts.values()))
    map_latin = {char: MAP_LATIN_BASE + char for char in range(0x21, 0x7f)} if custom else {}
    reserved = set(map_latin.values()) | (set(TRIP_GLYPHS) if custom else set())
    if custom and (used.intersection(reserved) or map_latin.keys() - fonts['CUSTOM'].getBestCmap().keys()):
        raise ValueError('Cannot reserve the custom title and number glyphs')
    used.update(reserved)
    aliases = defaultdict(dict)
    next_alias = 0xE000
    voice, previous_line = None, -2
    for key, value in translations.items():
        plant = key.removesuffix('_TOOLTIP')
        chooser_plant = (plant + '_TOOLTIP' in translations
                         and (plant + '_PLANTFOOD' in translations or plant + '_DESCRIPTION_HEADER' in translations))
        if key.startswith('NARRATIVE_') and key[10:].isdigit():
            line = int(key[10:])
            if line != previous_line + 1:
                voice = None
            speakers = SPEAKER.findall(value)
            if speakers:
                voice = NARRATORS.get(speakers[-1].lower())
            previous_line = line
        style = text_style(key, value, custom, chooser_plant, voice)
        if style is None:
            continue
        face = style[0]
        cmap = fonts[face].getBestCmap()
        table = aliases[style]
        full_style = (key in STORE_PROFILE_CAPTIONS or STORE_PRODUCT_COPY.fullmatch(key) if not custom else
                      button_caption(key) or key in PAUSE_LABELS or chooser_plant or chooser_caption(key))
        parts = []
        start = 0
        for token in TOKENS.finditer(value):
            parts.extend((value[start:token.start()], token.group()))
            start = token.end()
        parts.append(value[start:])
        for char in map(ord, ''.join(parts[::2])):
            if (not (0x3400 <= char <= 0x9FFF or char in CHINESE_PUNCTUATION
                     or (full_style and not chr(char).isspace()))
                    or char not in cmap or char in table):
                continue
            if len(style) == 3:
                if len(table) == len(TRIP_GLYPHS):
                    raise ValueError('Too many localized trip-title glyphs')
                table[char] = TRIP_GLYPHS[len(table)]
                continue
            while next_alias in used:
                next_alias += 1
            if next_alias > 0xF8FF:
                raise ValueError('Chinese font aliases exceed the private-use range')
            table[char] = next_alias
            next_alias += 1
        translations[key] = ''.join(part.translate(table) if index % 2 == 0 else part
                                    for index, part in enumerate(parts))
    if map_latin:
        # The fixed ASCII aliases are used after runtime substitution and formatting.
        aliases['CUSTOM', 1, 'runtime'] = map_latin
    return aliases


def adapt_round_font(font, slot):
    # Aster disables grayscale at 9–24 ppem. Iris needs smoothing there.
    font['gasp'].gaspRange = {65535: 15}
    font['head'].lowestRecPPEM = 9
    font['glyf'].removeHinting()
    for name in ('cvt ', 'fpgm', 'prep'):
        del font[name]
    unicode_map = CmapSubtable.newSubtable(4)
    unicode_map.platformID, unicode_map.platEncID, unicode_map.language = 0, 3, 0
    unicode_map.cmap = dict(font.getBestCmap())
    font['cmap'].tables.append(unicode_map)
    scale_upem(font, 2048)
    for record in font['name'].names:
        if record.nameID in (1, 2, 3, 4, 6, 16, 17):
            value = slot['name'].getDebugName(record.nameID)
            if value:
                record.string = value


def copy_glyphs(font, source, mapping, scale=1):
    assert font['head'].unitsPerEm == source['head'].unitsPerEm
    glyphs, source_cmap = source.getGlyphSet(), source.getBestCmap()
    order = list(font.getGlyphOrder())
    for char, codepoint in mapping.items():
        source_name = source_cmap[char]
        name = source_name
        if font is not source:
            name = f'irisStyle{codepoint:04X}'
            recording = DecomposingRecordingPen(glyphs)
            glyphs[source_name].draw(recording)
            pen = TTGlyphPen(None)
            # Keep smaller lettering centered vertically in the original widget.
            glyph_pen = TransformPen(pen, (scale, 0, 0, scale, 0, 850 * (1 - scale)))
            recording.replay(glyph_pen)
            font['glyf'][name] = pen.glyph()
            advance, bearing = source['hmtx'][source_name]
            font['hmtx'][name] = round(advance * scale), round(bearing * scale)
            if 'vmtx' in font:
                fallback = font.getBestCmap().get(char, '.notdef')
                font['vmtx'][name] = font['vmtx'][fallback]
            order.append(name)
        for table in font['cmap'].tables:
            if table.isUnicode() or (table.platformID == 1 and table.format == 6 and char == codepoint and char < 128):
                table.cmap[codepoint] = name
    font.setGlyphOrder(order)


def font_path(name):
    return f'PRIMEFONTS\\{name}.TTF'


def widen_mac_cmap(font):
    # Format 0 stores only 8-bit glyph indices. The HUD faces are appended.
    for index, table in enumerate(font['cmap'].tables):
        if table.platformID != 1 or table.format != 0:
            continue
        extended = CmapSubtable.newSubtable(6)
        extended.platformID, extended.platEncID, extended.language = table.platformID, table.platEncID, table.language
        extended.cmap = dict(table.cmap)
        font['cmap'].tables[index] = extended


def prepare_fonts(standard, aster, translations, custom_font=None):
    def read_donor(name):
        path = font_path(name)
        return aster.read(aster.group_for(path), path)

    names = ('BRIANNE', 'FZY4JW', 'FZKATJW', 'FZSEJW', 'FBUSV8C5EI', 'PICO', 'ASHLEYSCRIPT')
    donors = {name: read_donor(name) for name in names}
    if custom_font is not None:
        donors['CUSTOM'] = custom_font.read_bytes()
    with ExitStack() as stack:
        fonts = {name: stack.enter_context(TTFont(BytesIO(data), recalcTimestamp=False))
                 for name, data in donors.items()}
        aliases = build_aliases(translations, fonts, custom_font is not None)
        for face in {style[0] for style in aliases}:
            scale_upem(fonts[face], 2048)
        visible = {ord(char) for value in translations.values() for char in TOKENS.sub('', value)
                   if ord(char) >= 0x80 and not char.isspace()}
        hud = {ord(char): ord(char) for char in HUD_CHARACTERS}
        replacements = {}
        for slot, face in SLOTS.items():
            path = font_path(slot)
            with (TTFont(BytesIO(donors[face]), recalcTimestamp=False) as font,
                  TTFont(BytesIO(standard.read('LoadingFonts', path)), recalcTimestamp=False) as previous):
                if face == 'FZY4JW':
                    adapt_round_font(font, previous)
                for (name, scale, *_), glyphs in aliases.items():
                    copy_glyphs(font, fonts[name], glyphs, scale)
                # Preserve original symbols and fill gaps in the Aster face's CJK coverage.
                missing = visible - font.getBestCmap().keys()
                for fallback in (previous, *(fonts[name] for name in names)):
                    glyphs = missing & fallback.getBestCmap().keys()
                    if glyphs:
                        scale_upem(fallback, font['head'].unitsPerEm)
                        copy_glyphs(font, fallback, {code: code for code in sorted(glyphs)})
                        missing -= glyphs
                    if not missing:
                        break
                if slot == 'FBUSV8C5EI':
                    widen_mac_cmap(font)
                    copy_glyphs(font, fonts['FBUSV8C5EI'], hud)
                output = BytesIO()
                font.save(output)
                replacements[path] = output.getvalue()
                with TTFont(BytesIO(replacements[path])) as verified:
                    missing = set().union(*(glyphs.values() for glyphs in aliases.values())) - verified.getBestCmap().keys()
                    if missing:
                        raise ValueError(f'Missing Chinese font aliases in {slot}')
        return replacements
