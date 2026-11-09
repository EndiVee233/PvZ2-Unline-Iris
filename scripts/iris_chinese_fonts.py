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


def text_style(key, value):
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


def build_aliases(translations, fonts):
    # Old widgets share font slots. Route only visible Chinese glyphs from
    # known labels and leave NPC commands, format variables and player names intact.
    used = set().union(*(font.getBestCmap() for font in fonts.values()))
    aliases = defaultdict(dict)
    next_alias = 0xE000
    translations['MAINMENU_PLAY'] = '开始游戏'
    for key, value in translations.items():
        style = text_style(key, value)
        if style is None:
            continue
        face, _ = style
        cmap = fonts[face].getBestCmap()
        table = aliases[style]
        for char in map(ord, value):
            if (not (0x3400 <= char <= 0x9FFF or char in CHINESE_PUNCTUATION)
                    or char not in cmap or char in table):
                continue
            while next_alias in used:
                next_alias += 1
            if next_alias > 0xF8FF:
                raise ValueError('Chinese font aliases exceed the private-use range')
            table[char] = next_alias
            next_alias += 1
        translations[key] = value.translate(table)
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


def prepare_fonts(standard, aster, translations):
    def read_donor(name):
        path = font_path(name)
        return aster.read(aster.group_for(path), path)

    names = ('BRIANNE', 'FZY4JW', 'FZKATJW', 'FZSEJW', 'FBUSV8C5EI', 'PICO', 'ASHLEYSCRIPT')
    donors = {name: read_donor(name) for name in names}
    with ExitStack() as stack:
        fonts = {name: stack.enter_context(TTFont(BytesIO(data), recalcTimestamp=False))
                 for name, data in donors.items()}
        aliases = build_aliases(translations, fonts)
        for face in {face for face, _ in aliases}:
            scale_upem(fonts[face], 2048)
        hud = {ord(char): ord(char) for char in HUD_CHARACTERS}
        replacements = {}
        for slot, face in SLOTS.items():
            path = font_path(slot)
            with TTFont(BytesIO(donors[face]), recalcTimestamp=False) as font:
                if face == 'FZY4JW':
                    with TTFont(BytesIO(standard.read('LoadingFonts', path))) as previous:
                        adapt_round_font(font, previous)
                for (name, scale), glyphs in aliases.items():
                    copy_glyphs(font, fonts[name], glyphs, scale)
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
