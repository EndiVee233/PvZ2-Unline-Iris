package com.popcap.PvZ2;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Process;
import android.util.Log;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** The local expansion and language settings used by the original engine. */
public final class LiteRuntime {
    private static final String TAG = "UnlineIris";
    private static final String PREFS = "unline_lite";
    private static final String LANGUAGE = "language";
    private static final String EXPANSION = "main.7.com.ea.game.pvz2_na.obb";
    private static final int CHINESE = 6;
    private static final String[] CODES = {"en_US", "de_DE", "es_ES", "fr_FR", "it_IT", "pt_BR", "zh_CN"};
    private static final String[] NAMES = {"English", "Deutsch", "Español", "Français", "Italiano", "Português (Brasil)", "简体中文"};
    private static final String[] TITLES = {"Language", "Sprache", "Idioma", "Langue", "Lingua", "Idioma", "语言"};
    private static final String[] RESTART = {"Close the game and reopen it to apply the language.",
            "Schließe das Spiel und öffne es erneut, um die Sprache anzuwenden.",
            "Cierra y vuelve a abrir el juego para aplicar el idioma.",
            "Fermez puis relancez le jeu pour appliquer la langue.",
            "Chiudi e riapri il gioco per applicare la lingua.",
            "Feche e reabra o jogo para aplicar o idioma.", "请关闭并重新打开游戏，以应用语言设置。"};
    private static final String[] CLOSE = {"Close game", "Spiel schließen", "Cerrar el juego",
            "Fermer le jeu", "Chiudi il gioco", "Fechar jogo", "关闭游戏"};
    private static final String[] LATER = {"Later", "Später", "Más tarde", "Plus tard", "Più tardi", "Mais tarde", "稍后"};
    private static final String[] SAVE = {"Apply", "Übernehmen", "Aplicar", "Appliquer", "Applica", "Aplicar", "应用"};
    private static final String[] CANCEL = {"Cancel", "Abbrechen", "Cancelar", "Annuler", "Annulla", "Cancelar", "取消"};

    public static String locale(Context context) {
        int index = languageIndex(context);
        // The engine has no zh-CN resource slot. The Chinese expansion supplies en-US instead.
        return CODES[index == CHINESE ? 0 : index];
    }

    private static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static int languageIndex(Context context) {
        String preferred = preferences(context).getString(LANGUAGE, Locale.getDefault().toString());
        for (int index = 0; index < CODES.length; index++) {
            if (preferred.equals(CODES[index]) || preferred.startsWith(CODES[index].substring(0, 2) + "_")
                    || preferred.equals(CODES[index].substring(0, 2))) return index;
        }
        return 0;
    }

    public static boolean handleLink(Activity activity, String url) {
        if (url == null || !url.startsWith("https://unline.invalid/language?")) return false;
        activity.runOnUiThread(() -> showLanguage(activity));
        return true;
    }

    private static void showLanguage(Activity activity) {
        if (activity.isFinishing()) return;
        int original = languageIndex(activity);
        int[] selection = {original};
        new AlertDialog.Builder(activity).setTitle(TITLES[original])
                .setSingleChoiceItems(NAMES, original, (dialog, index) -> selection[0] = index)
                .setNegativeButton(CANCEL[original], null)
                .setPositiveButton(SAVE[original], (dialog, button) -> {
                    if (selection[0] == original) return;
                    if (!preferences(activity).edit().putString(LANGUAGE, CODES[selection[0]]).commit()) {
                        Log.e(TAG, "Cannot save language preference");
                        return;
                    }
                    new AlertDialog.Builder(activity).setTitle(TITLES[original]).setMessage(RESTART[original])
                            .setNegativeButton(LATER[original], null)
                            .setPositiveButton(CLOSE[original], (restart, close) -> {
                                activity.finishAffinity();
                                // The original engine keeps process-wide native state.
                                new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(
                                        () -> Process.killProcess(Process.myPid()), 500);
                            }).show();
                }).show();
    }

    private static File expansion(Context context) {
        return new File(new File(context.getFilesDir(), "expansion"), EXPANSION);
    }

    public static String expansionPath(Context context) {
        return expansion(context).getAbsolutePath();
    }

    public static boolean prepare(Context context) {
        boolean chinese = languageIndex(context) == CHINESE;
        long expectedSize = chinese ? ExpansionSpec.CHINESE_SIZE : ExpansionSpec.SIZE;
        String expectedHash = chinese ? ExpansionSpec.CHINESE_SHA256 : ExpansionSpec.SHA256;
        File target = expansion(context);
        if (target.isFile() && target.length() == expectedSize
                && expectedHash.equals(preferences(context).getString("expansion", ""))) return true;
        File dir = target.getParentFile();
        File partial = new File(dir, EXPANSION + ".partial");
        try {
            if (!dir.isDirectory() && !dir.mkdirs()) throw new IOException("Cannot create expansion directory");
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (ZipInputStream input = new ZipInputStream(context.getAssets().open("extobb.save"))) {
                ZipEntry entry = input.getNextEntry();
                if (entry == null || !EXPANSION.equals(entry.getName())) throw new IOException("Unexpected expansion entry");
                long size = 0;
                try (FileOutputStream output = new FileOutputStream(partial)) {
                    byte[] buffer = new byte[128 * 1024];
                    int n;
                    while ((n = input.read(buffer)) != -1) {
                        size += n;
                        if (size > ExpansionSpec.SIZE) throw new IOException("Expansion is too large");
                        digest.update(buffer, 0, n);
                        output.write(buffer, 0, n);
                    }
                    output.getFD().sync();
                }
                if (size != ExpansionSpec.SIZE || !ExpansionSpec.SHA256.equals(hex(digest.digest()))) {
                    throw new IOException("Expansion integrity check failed");
                }
                if (chinese) installChineseDelta(input, partial, digest);
            }
            if (!partial.renameTo(target)) throw new IOException("Cannot install expansion");
            preferences(context).edit().putString("expansion", expectedHash).commit();
            Log.i(TAG, "Local expansion ready");
            return true;
        } catch (Exception error) {
            Log.e(TAG, "Cannot prepare local expansion", error);
            return false;
        } finally {
            if (partial.isFile()) partial.delete();
        }
    }

    private static String hex(byte[] digest) {
        StringBuilder hash = new StringBuilder(64);
        for (byte value : digest) hash.append(Character.forDigit((value & 255) >>> 4, 16))
                .append(Character.forDigit(value & 15, 16));
        return hash.toString();
    }

    private static void installChineseDelta(ZipInputStream zip, File partial, MessageDigest digest) throws IOException {
        ZipEntry entry = zip.getNextEntry();
        if (entry == null || !"chinese.delta".equals(entry.getName())) throw new IOException("Missing Chinese expansion");
        DataInputStream input = new DataInputStream(zip);
        int count = input.readInt();
        if (count < 1 || count > ExpansionSpec.SIZE / 4096 + 2) throw new IOException("Invalid Chinese delta count");
        byte[] buffer = new byte[128 * 1024];
        try (RandomAccessFile output = new RandomAccessFile(partial, "rw")) {
            long end = 0;
            for (int index = 0; index < count; index++) {
                long offset = input.readInt();
                int length = input.readInt();
                if (offset < end || offset > output.length() || length <= 0
                        || offset + length > ExpansionSpec.CHINESE_SIZE) throw new IOException("Invalid Chinese delta range");
                end = offset + length;
                output.seek(offset);
                while (length > 0) {
                    int chunk = Math.min(length, buffer.length);
                    input.readFully(buffer, 0, chunk);
                    output.write(buffer, 0, chunk);
                    length -= chunk;
                }
            }
            if (input.read() != -1 || output.length() != ExpansionSpec.CHINESE_SIZE) {
                throw new IOException("Invalid Chinese expansion length");
            }
            output.getFD().sync();
        }
        try (FileInputStream result = new FileInputStream(partial)) {
            int n;
            while ((n = result.read(buffer)) != -1) digest.update(buffer, 0, n);
        }
        if (!ExpansionSpec.CHINESE_SHA256.equals(hex(digest.digest()))) throw new IOException("Chinese expansion integrity check failed");
    }

    public static void showExpansionError(Activity activity) {
        new AlertDialog.Builder(activity).setTitle(ExpansionSpec.LABEL)
                .setMessage("Could not unpack the game resources. Check available space and restart the game.")
                .setPositiveButton(android.R.string.ok, (dialog, button) -> activity.finish()).setCancelable(false).show();
    }
}
