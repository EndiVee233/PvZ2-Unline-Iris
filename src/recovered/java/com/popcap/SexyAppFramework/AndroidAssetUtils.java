package com.popcap.SexyAppFramework;

import android.util.Log;

// Recovered from the NA 1.6.257161 DEX and checked against Iris Smali.
public class AndroidAssetUtils {
    private static final String sAssetPrefix = "ASSET:";

    public static String GetAssetNameFromFileName(String InFilename) {
        String actualFilename;
        try {
            if (InFilename.startsWith(sAssetPrefix)) {
                actualFilename = InFilename.substring(sAssetPrefix.length());
            } else {
                actualFilename = InFilename;
            }
            String assetName = actualFilename.replace('\\', '/');
            if (!assetName.endsWith(".smf") && !assetName.endsWith(".rton")) {
                return assetName + ".smf";
            }
            return assetName;
        } catch (Exception ex) {
            ex.printStackTrace();
            Log.e("Error", ex.toString());
            return "";
        }
    }
}
