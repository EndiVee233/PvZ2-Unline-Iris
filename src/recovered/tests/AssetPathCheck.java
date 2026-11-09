package com.popcap.SexyAppFramework;

public final class AssetPathCheck {
    private static void check(String input, String expected) {
        String actual = AndroidAssetUtils.GetAssetNameFromFileName(input);
        if (!expected.equals(actual)) {
            throw new AssertionError(input + " produced " + actual);
        }
    }

    public static void main(String[] args) {
        check("ASSET:properties\\plants", "properties/plants.smf");
        check("ASSET:properties\\plants.rton", "properties/plants.rton");
        check("texture.smf", "texture.smf");
        check("texture.SMF", "texture.SMF.smf");
        check("asset:file", "asset:file.smf");
        System.out.println("Five asset path cases passed");
    }
}
