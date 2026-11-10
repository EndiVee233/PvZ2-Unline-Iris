"""Build the signed, offline EN Lite APK from the verified NA input."""

import argparse
from contextlib import closing
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile
import xml.etree.ElementTree as ET

from prepare_baseline import OBB, ROOT, SOURCE, SOURCE_SHA256, sha256
from prepare_localized_resources import LOCALES, apply_overlay, atlas_path, box, locale_path, tokens, values_of
from rsb_local import ResourceBundle
from iris_chinese_fonts import prepare_fonts
from iris_desktop_input import patch_native as patch_input_native
from iris_speed_art import HUD_ATLASES, aster_icons, port_speed_art
from recovery_compile import RECOVERED_JAVA, baseline_classpath


PACKAGE = 'com.ea.game.pvz2_na'
LABEL = 'PvZ2-Unline:Iris'
APK_NAME = 'PvZ2-Unline-Iris.apk'
ANDROID = '{http://schemas.android.com/apk/res/android}'
FRAMEWORK = 'Lcom/popcap/SexyAppFramework/'
RUNTIME = 'Lcom/popcap/PvZ2/LiteRuntime;'
HELP_LINK = 'https://unline.invalid/language?locale={LOCALEINSERT}&platform={PLATFORM}&player={PCPID}'
LANGUAGE = dict(zip(LOCALES, ('Sprache', 'Language', 'Idioma', 'Langue', 'Lingua', 'Idioma')))

def run(*args):
    subprocess.run(args, check=True)


def edit_method(path, method, body):
    source = path.read_text(encoding='utf-8')
    pattern = re.compile(r'(^\.method (?:[^\n]+ )?' + re.escape(method) + r'\n).*?^\.end method', re.M | re.S)
    source, count = pattern.subn(lambda match: match[1] + body + '\n.end method', source)
    if count != 1:
        raise ValueError(f'{path.name}: method {method} matched {count} times')
    path.write_text(source, encoding='utf-8')


def replace_exact(path, before, after, count=1):
    source = path.read_text(encoding='utf-8')
    if source.count(before) != count:
        raise ValueError(f'{path.name}: unexpected input for {before}')
    path.write_text(source.replace(before, after), encoding='utf-8')


def patch_smali(decoded):
    popcap = decoded / 'smali/com/popcap'
    activity = popcap / 'PvZ2/PvZ2GameActivity.smali'
    framework = popcap / 'SexyAppFramework'
    app = framework / 'AndroidGameApp.smali'
    void = '    .locals 0\n    return-void'
    unavailable = '    .locals 1\n    const/4 v0, 0x0\n    return v0'

    replace_exact(activity, '    invoke-static/range {p0 .. p0}, Lcom/savegame/SavesRestoring;->DoSmth(Landroid/content/Context;)V\n', '', 2)
    super_create = f'    invoke-super/range {{p0 .. p1}}, {FRAMEWORK}SexyAppFrameworkActivity;->onCreate(Landroid/os/Bundle;)V'
    replace_exact(activity, super_create,
                  super_create + '\n\n' + f'    invoke-static/range {{p0 .. p0}}, {RUNTIME}->prepare(Landroid/content/Context;)Z\n'
                  '    move-result v10\n    if-nez v10, :lite_expansion_ready\n'
                  f'    invoke-static/range {{p0 .. p0}}, {RUNTIME}->showExpansionError(Landroid/app/Activity;)V\n'
                  '    return-void\n    :lite_expansion_ready')
    edit_method(activity, 'isGooglePlayExpansionEnabled()Z', unavailable)
    edit_method(activity, 'deleteOldExpansionFiles()V', void)
    edit_method(app, 'Info_SysGetUserLocale()Ljava/lang/String;',
                f'    .locals 1\n    iget-object v0, p0, {FRAMEWORK}AndroidGameApp;->mActivity:Landroid/app/Activity;\n'
                f'    invoke-static {{v0}}, {RUNTIME}->locale(Landroid/content/Context;)Ljava/lang/String;\n'
                '    move-result-object v0\n    return-object v0')
    edit_method(app, 'Resources_GetUserDataFolder()Ljava/lang/String;',
                f'    .locals 1\n    iget-object v0, p0, {FRAMEWORK}AndroidGameApp;->mActivity:Landroid/app/Activity;\n'
                '    invoke-virtual {v0}, Landroid/app/Activity;->getFilesDir()Ljava/io/File;\n'
                '    move-result-object v0\n    invoke-virtual {v0}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;\n'
                '    move-result-object v0\n    return-object v0')
    replace_exact(app, '.method private Web_SysOpenURL(Ljava/lang/String;)Z\n    .locals 3',
                  '.method private Web_SysOpenURL(Ljava/lang/String;)Z\n    .locals 3\n'
                  f'    iget-object v0, p0, {FRAMEWORK}AndroidGameApp;->mActivity:Landroid/app/Activity;\n'
                  f'    invoke-static {{v0, p1}}, {RUNTIME}->handleLink(Landroid/app/Activity;Ljava/lang/String;)Z\n'
                  '    move-result v0\n    if-eqz v0, :lite_open_external\n    return v0\n    :lite_open_external')

    play = framework / 'GooglePlay'
    base = play / 'BaseGameActivity.smali'
    for method in ('<init>()V', '<init>(I)V'):
        edit_method(base, method, '    .locals 0\n    invoke-direct {p0}, Landroid/support/v4/app/FragmentActivity;-><init>()V\n    return-void')
    for method in ('onStart()V', 'onStop()V', 'onActivityResult(IILandroid/content/Intent;)V'):
        registers = '{p0, p1, p2, p3}' if method.startswith('onActivityResult') else '{p0}'
        edit_method(base, method, f'    .locals 0\n    invoke-super {registers}, Landroid/support/v4/app/FragmentActivity;->{method}\n    return-void')
    for method in ('launchGame()V', 'beginSilentSignIn()V', 'beginUserInitiatedSignIn()V', 'reconnectClients(I)V', 'signOut()V'):
        edit_method(base, method, void)
    edit_method(base, 'isSignedIn()Z', unavailable)
    for name in ('GooglePlayConnect', 'GooglePlayAchievements', 'GooglePlayLeaderboard'):
        path = play / (name + '.smali')
        for method in re.findall(r'^\.method .*?(Play_\S+)$', path.read_text(encoding='utf-8'), re.M):
            edit_method(path, method, unavailable if method.endswith('Z') else void)

    cloud = framework / 'cloud/Cloud.smali'
    edit_method(cloud, f'<init>({FRAMEWORK}SexyAppFrameworkActivity;)V',
                '    .locals 1\n    invoke-direct {p0}, Ljava/lang/Object;-><init>()V\n    const-string v0, ""\n'
                f'    iput-object v0, p0, {FRAMEWORK}cloud/Cloud;->pcpId:Ljava/lang/String;\n    return-void')
    edit_method(cloud, 'Cloud_SetPcpId(Ljava/lang/String;)V',
                f'    .locals 0\n    iput-object p1, p0, {FRAMEWORK}cloud/Cloud;->pcpId:Ljava/lang/String;\n    return-void')
    for method in ('Cloud_Connect()V', 'Cloud_attemptSilentSync()V', 'Cloud_initiateSync()V', 'loadState()V',
                   'onActivityResult(IILandroid/content/Intent;)V'):
        edit_method(cloud, method, void)

    purchase = framework / 'GooglePlayPurchaseDriver.smali'
    driver = FRAMEWORK + 'GooglePlayPurchaseDriver;'
    edit_method(purchase, '<init>(JLjava/lang/String;)V',
                '    .locals 0\n    invoke-direct {p0}, Ljava/lang/Object;-><init>()V\n'
                f'    iput-wide p1, p0, {driver}->mNativeDriverPtr:J\n    return-void')
    for method in ('CanMakePayments()Z', 'HasUnconfirmedPayments()Z', 'ProductTypeIsSupported(I)Z', 'onActivityResult(IILandroid/content/Intent;)Z'):
        edit_method(purchase, method, unavailable)
    for method in ('Close()V', 'ConfirmDelivery(Ljava/lang/String;)V'):
        edit_method(purchase, method, void)
    edit_method(purchase, 'Refresh([Ljava/lang/String;)V',
                f'    .locals 3\n    iget-wide v0, p0, {driver}->mNativeDriverPtr:J\n    const/4 v2, 0x0\n'
                f'    new-array v2, v2, [{FRAMEWORK}purchase/SkuDetails;\n'
                f'    invoke-virtual {{p0, v0, v1, v2}}, {driver}->FireDidRefresh(J[{FRAMEWORK}purchase/SkuDetails;)V\n    return-void')
    cause = FRAMEWORK + 'GooglePlayPurchaseDriver$CauseForIncompletion;'
    edit_method(purchase, 'RequestPayment(Ljava/lang/String;)V',
                f'    .locals 3\n    iget-wide v0, p0, {driver}->mNativeDriverPtr:J\n'
                f'    sget-object v2, {cause}->ServiceUnavailable:{cause}\n'
                f'    invoke-virtual {{v2}}, {cause}->ordinal()I\n    move-result v2\n'
                f'    invoke-virtual {{p0, v0, v1, p1, v2}}, {driver}->FirePaymentIncomplete(JLjava/lang/String;I)V\n    return-void')


def patch_manifest(decoded):
    path = decoded / 'AndroidManifest.xml'
    ET.register_namespace('android', ANDROID[1:-1])
    tree = ET.parse(path)
    manifest = tree.getroot()
    for child in list(manifest):
        name = child.get(ANDROID + 'name', '')
        if child.tag in ('permission', 'uses-permission') and (
                name.startswith(('com.android.vending.', 'com.google.android.c2dm.'))
                or name.endswith('.C2D_MESSAGE')
                or name in ('android.permission.GET_ACCOUNTS', 'android.permission.WRITE_EXTERNAL_STORAGE')):
            manifest.remove(child)
    app = manifest.find('application')
    app.set(ANDROID + 'label', LABEL)
    for child in list(app):
        name = child.get(ANDROID + 'name', '')
        if name.startswith('com.google.android.gms.') or name in (
                'GooglePlayExpansionEnabled', 'com.popcap.PvZ2.PvZ2DownloaderService',
                'com.popcap.PvZ2.PvZ2AlarmReceiver', 'com.popcap.SexyAppFramework.gcm.GCMReceiver',
                'com.mobileapptracker.Tracker'):
            app.remove(child)
        elif name == 'com.popcap.PvZ2.PvZ2GameActivity':
            child.set(ANDROID + 'label', LABEL)
            child.set(ANDROID + 'exported', 'true')
    tree.write(path, encoding='utf-8', xml_declaration=True)
    config = decoded / 'apktool.yml'
    replace_exact(config, 'minSdkVersion: 9', 'minSdkVersion: 21')
    replace_exact(config, 'targetSdkVersion: 18', 'targetSdkVersion: 23')
    replace_exact(config, 'versionCode: 8', 'versionCode: 19')
    replace_exact(config, 'versionName: 1.6.257161', 'versionName: 1.6.257161-Unline-Iris.10')


def hide_google_art(bundle, decoder, updates):
    for group in bundle.manifest(decoder)['groups']:
        if not group['id'].startswith('UI_GameCenter_'):
            continue
        resources = group['resources']
        atlas, = (resource for resource in resources if resource.get('atlas'))
        path = atlas_path(atlas)
        pool = bundle.group_for(path)
        width, height, _, format_id = bundle.texture(pool, path)
        texture = bytearray(bundle.read(pool, path))
        # Format 147 stores one alpha byte per pixel after the ETC1 blocks.
        alpha = width * height // 2
        if format_id != 147 or len(texture) != alpha + width * height:
            raise ValueError(f'Unexpected Google atlas format: {path}')
        for resource in resources:
            if resource['id'].startswith(('IMAGE_UI_GAMECENTER_ANDROID_GOOGLE', 'IMAGE_UI_GAMECENTER_ANDROID_SIGNIN')):
                left, top, right, bottom = box(resource)
                if not (0 <= left < right <= width and 0 <= top < bottom <= height):
                    raise ValueError(f'Invalid Google sprite bounds: {resource["id"]}')
                row = bytes(right - left)
                for y in range(top, bottom):
                    start = alpha + y * width + left
                    texture[start:start + len(row)] = row
        updates.setdefault(pool, {})[path] = texture


def chinese_expansion(standard, cn_apk, read_index, write_index):
    from index_texture_prefetch import ResourceZip

    stream = ResourceZip(cn_apk)
    with closing(stream.file), closing(stream.map), ZipFile(stream) as archive:
        def donor(name):
            path, = (path for path in archive.namelist() if path.endswith('/' + name + '.rsb.smf'))
            return ResourceBundle(archive.read(path), read_index, write_index)

        strings = donor('dynamic')
        path = 'PROPERTIES\\LAWNSTRINGS.TXT'
        chinese = values_of(strings.read(strings.group_for(path), path).decode('utf-8-sig'))
        del strings
        path = locale_path('en-US')
        group = standard.group_for(path)
        english = standard.read(group, path)
        translations = {key: chinese[key] for key, value in values_of(english.decode('utf-16')).items()
                        if chinese.get(key) and tokens(chinese[key]) == tokens(value)}
        translations.update(
            SETTINGS_HELP_TITLE='语言', SETTINGS_HELP_URL=HELP_LINK,
            SETTINGS_BUILDVERSION_TITLE='版本信息', SETTINGS_DISPLAY_VERSION='版本',
            SETTINGS_DISPLAY_PCPID='玩家 ID', TUTORIAL_LEVEL_NAME='{PLAYER}的房子 - 第{LEVEL_NUMBER}天',
            MAINMENU_CLICK_TO_ADD_PLAYER='<点击添加玩家>', PAUSED_HEADER='游戏暂停',
        )

        fonts = donor('init')
        replacements = prepare_fonts(standard, fonts, translations)
        updates = {group: {path: apply_overlay(english, translations)}, 'LoadingFonts': replacements}
    result = standard.replace(updates, set())
    verified = ResourceBundle(result, read_index, write_index)
    if any(verified.read(group, path) != value for group, files in updates.items() for path, value in files.items()):
        raise ValueError('Chinese expansion entries failed verification')
    print(f'Chinese locale: {len(translations)} matching strings')
    return result


def write_chinese_delta(stream, standard, chinese):
    # RSB replacement appends changed groups and updates a few table pages.
    # Keep only those differences so the APK carries one base expansion.
    page_size = 4096
    offsets = [offset for offset in range(0, len(standard), page_size)
               if standard[offset:offset + page_size] != chinese[offset:offset + page_size]]
    stream.write(struct.pack('>I', len(offsets) + 1))
    for offset in offsets:
        page = chinese[offset:min(offset + page_size, len(standard))]
        stream.write(struct.pack('>II', offset, len(page)))
        stream.write(page)
    stream.write(struct.pack('>II', len(standard), len(chinese) - len(standard)))
    stream.write(memoryview(chinese)[len(standard):])


def relocate_battle_coins(bundle, decoder, encoder, updates):
    for platform in ('ANDROID', 'IPAD', 'IPHONE', 'IPHONE5'):
        path = f'PACKAGES\\UI_{platform}.RTON'
        group = bundle.group_for(path)
        source = BytesIO(bundle.read(group, path)[4:])
        source.name = path
        layout = json.loads(decoder(repairFiles=False).parse_root_object(source))
        coin, = (item['objdata'] for item in layout['objects'] if 'UICoinBank' in item.get('aliases', []))
        start, = (item['objdata'] for item in layout['objects'] if 'UIStartGameButton' in item.get('aliases', []))
        if coin['Parent'] != 'UITopBar' or coin['Class'] != 'CoinBank':
            raise ValueError(f'Unexpected battle coin bank in {path}')
        if start['Parent'] == 'UICoinBank':
            # Keep the seed chooser's Start button in its original top HUD area.
            start.update(Parent='UITopBar', ParentAnchor='TopRight', ScalePositionOffset=True,
                         PositionOffset={'x': coin['PositionOffset']['x'] - coin['VirtualWidth']
                                             + start['PositionOffset']['x'],
                                         'y': coin['PositionOffset']['y'] + start['PositionOffset']['y']})
        # The phone bottom bars are shorter than the shovel, so anchor the
        # coin bank above the tool from the shared bottom edge.
        coin.update(Parent='UIBottomBar', ParentAnchor='BottomRight', Anchor='BottomRight',
                    PositionOffset={'x': -14, 'y': -92})
        data = encoder().encode_root_object(StringIO(json.dumps(layout)))
        verified = BytesIO(data[4:])
        verified.name = path
        if json.loads(decoder(repairFiles=False).parse_root_object(verified)) != layout:
            raise ValueError(f'Battle HUD failed round-trip in {path}')
        updates.setdefault(group, {})[path] = data


def package_expansion(source, destination, cn, rton, cn_apk, etc1tool):
    sys.path[:0] = [str(rton.resolve()), str((cn / 'scripts').resolve())]
    from merge_legacy_pvp_resources import trie_read, trie_write
    from pyvz2rton import JSONDecoder, RTONDecoder

    bundle = ResourceBundle(source.read_bytes(), trie_read, trie_write)
    updates = {}
    for locale, title in LANGUAGE.items():
        path = locale_path(locale)
        group = bundle.group_for(path)
        original = bundle.read(group, path)
        updates[group] = {path: apply_overlay(original, {'SETTINGS_HELP_TITLE': title, 'SETTINGS_HELP_URL': HELP_LINK})}
    hide_google_art(bundle, RTONDecoder, updates)
    relocate_battle_coins(bundle, RTONDecoder, JSONDecoder, updates)
    icons = aster_icons(cn_apk, trie_read, trie_write, RTONDecoder)
    port_speed_art(bundle, RTONDecoder, JSONDecoder, icons, etc1tool, updates)
    result = bundle.replace(updates, set(), preserve_compression=HUD_ATLASES)
    verified = ResourceBundle(result, trie_read, trie_write)
    if any(verified.read(group, path) != value for group, files in updates.items() for path, value in files.items()):
        raise ValueError('Expansion entries failed verification')
    if any(bundle.groups[group][2] != verified.groups[group][2] for group in bundle.groups if group not in updates):
        raise ValueError('Unexpected expansion changes')
    chinese = chinese_expansion(verified, cn_apk, trie_read, trie_write)
    with ZipFile(destination, 'w', compression=ZIP_DEFLATED, compresslevel=1) as archive:
        archive.writestr(OBB, result)
        with archive.open('chinese.delta', 'w') as delta:
            write_chinese_delta(delta, result, chinese)
    return len(result), hashlib.sha256(result).hexdigest(), len(chinese), hashlib.sha256(chinese).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, default=Path('Y:/Android/Sdk'))
    parser.add_argument('--ndk', type=Path)
    parser.add_argument('--jdk', type=Path, default=Path('M:/Program Files/Zulu/zulu-21'))
    parser.add_argument('--expansion', type=Path, default=ROOT / 'work/localized' / OBB)
    parser.add_argument('--cn-workspace', type=Path, default=ROOT.parent / 'PvZ2-Unline-Aster')
    parser.add_argument('--cn-apk', type=Path, required=True, help='local Aster APK with Chinese text and fonts')
    parser.add_argument('--rton-tools', type=Path, default=ROOT / 'tools/pyvz2/OBBEdit/libraries')
    parser.add_argument('--output', type=Path, default=ROOT / 'work/lite')
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        parser.error('Output already exists. Specify a new --output directory.')
    if sha256(SOURCE) != SOURCE_SHA256:
        parser.error('Unexpected NA input APK hash')
    sdk = args.sdk.resolve()
    tools = sdk / 'build-tools/34.0.0'
    platform = sdk / 'platforms/android-34/android.jar'
    jdk = args.jdk.resolve() / 'bin'
    java = jdk / 'java.exe'
    apktool = ROOT / 'tools/apktool.jar'
    out.mkdir(parents=True)
    decoded = out / 'decoded'
    run(java, '-jar', apktool, 'd', '-p', out / 'framework', '-o', decoded, SOURCE)
    patch_manifest(decoded)
    patch_smali(decoded)
    framework = decoded / 'smali/com/popcap/SexyAppFramework'
    # The Java source replaces these classes in classes2.dex.
    for name, suffixes in RECOVERED_JAVA.items():
        old_classes = {framework / (name + suffix + '.smali') for suffix in suffixes}
        found = set(framework.glob(name + '$*.smali')) | {framework / (name + '.smali')}
        if found != old_classes or any(not path.is_file() for path in old_classes):
            raise ValueError(f'Unexpected original {name} class family')
        for path in old_classes:
            path.unlink()
    native = 'lib/armeabi-v7a/libPVZ2.so'
    ndk = args.ndk or sdk / 'ndk/27.0.12077973'
    patch_input_native(decoded / native, ROOT / 'src/desktop-input/iris.cpp', ndk, out)
    bridge = decoded / 'lib/armeabi-v7a/libIrisSpeedFeedback.so'
    run(ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin/clang++.exe',
        '--target=armv7a-linux-androideabi21', '-Os', '-shared', '-fPIC', '-fno-exceptions',
        '-fno-rtti', '-nostdlib++', '-Wl,--no-undefined', '-Wl,-soname,libIrisSpeedFeedback.so',
        ROOT / 'src/desktop-input/speed_feedback.cpp', '-ldl', '-o', bridge)
    size, digest, zh_size, zh_digest = package_expansion(
        args.expansion, decoded / 'assets/extobb.save', args.cn_workspace, args.rton_tools,
        args.cn_apk, sdk / 'platform-tools/etc1tool.exe')
    (decoded / 'assets/data.save').unlink()

    spec = out / 'ExpansionSpec.java'
    spec.write_text('package com.popcap.PvZ2;\nfinal class ExpansionSpec {\n'
                    f'    static final String LABEL = "{LABEL}";\n'
                    f'    static final long SIZE = {size}L, CHINESE_SIZE = {zh_size}L;\n'
                    f'    static final String SHA256 = "{digest}", CHINESE_SHA256 = "{zh_digest}";\n'
                    '}\n', encoding='ascii')
    classes = out / 'classes'
    classes.mkdir()
    baseline_api = baseline_classpath(SOURCE, args.cn_workspace, out / 'baseline-compile-only.jar')
    recovered = ROOT / 'src/recovered/java/com/popcap/SexyAppFramework'
    # D8 in Build Tools 34 expects names for javac's mandated inner-class parameters.
    run(jdk / 'javac.exe', '--release', '8', '-parameters', '-encoding', 'UTF-8',
        '-cp', f'{platform};{baseline_api}', '-d', classes,
        ROOT / 'src/lite/com/popcap/PvZ2/LiteRuntime.java',
        recovered / 'IrisSpeedFeedback.java',
        *(recovered / f'{name}.java' for name in RECOVERED_JAVA), spec)
    run(jdk / 'jar.exe', 'cf', out / 'lite.jar', '-C', classes, '.')
    run(java, '-cp', tools / 'lib/d8.jar', 'com.android.tools.r8.D8', '--min-api', '21', '--lib', platform,
        '--classpath', baseline_api, '--force-passthrough-assertions:com.popcap.SexyAppFramework...',
        '--output', out, out / 'lite.jar')
    run(java, '-jar', apktool, 'b', '-p', out / 'framework', '-o', out / 'recompiled.apk', decoded)
    with ZipFile(out / 'recompiled.apk', 'a') as package, ZipFile(args.cn_apk) as donor:
        package.write(out / 'classes.dex', 'classes2.dex', compress_type=ZIP_DEFLATED)
        for mode in ('on', 'off'):
            name = f'assets/game-audio/fast-forward-{mode}.wav'
            package.writestr(name, donor.read(name), compress_type=ZIP_STORED)
    run(tools / 'zipalign.exe', '-f', '4', out / 'recompiled.apk', out / 'aligned.apk')
    key = ROOT / 'work/signing/unline-lite.jks'
    if not key.exists():
        key.parent.mkdir(parents=True, exist_ok=True)
        run(jdk / 'keytool.exe', '-genkeypair', '-keystore', key, '-storepass', 'android', '-keypass', 'android',
            '-alias', 'unline-lite', '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000', '-dname', 'CN=PvZ2 Unline Lite Local')
    final = out / APK_NAME
    signer = tools / 'lib/apksigner.jar'
    run(java, '-jar', signer, 'sign', '--ks', key, '--ks-pass', 'pass:android', '--ks-key-alias', 'unline-lite',
        '--out', final, out / 'aligned.apk')
    run(java, '-jar', signer, 'verify', '--verbose', final)
    run(tools / 'zipalign.exe', '-c', '4', final)
    with ZipFile(final) as package:
        if package.read(native) != (decoded / native).read_bytes() or 'assets/data.save' in package.namelist():
            raise ValueError('Unexpected packaged native code or legacy assets')
    (out / 'aligned.apk').unlink()
    (out / 'recompiled.apk').unlink()
    print(f'{final}\nSHA-256 {sha256(final)}')


if __name__ == '__main__':
    main()
