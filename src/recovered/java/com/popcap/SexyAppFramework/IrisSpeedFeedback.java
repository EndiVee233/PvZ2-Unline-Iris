package com.popcap.SexyAppFramework;

import android.app.Activity;
import android.content.res.AssetFileDescriptor;
import android.graphics.Color;
import android.media.AudioAttributes;
import android.media.SoundPool;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;
import java.io.IOException;

/** Aster's speed cues and flash, dispatched only after Iris commits a speed change. */
final class IrisSpeedFeedback {
    private static final String TAG = "IrisSpeedFeedback";
    private static final String[] ASSETS = {
        "game-audio/fast-forward-off.wav", "game-audio/fast-forward-on.wav"
    };
    private static final int[] samples = new int[ASSETS.length];
    private static final boolean[] ready = new boolean[ASSETS.length];
    private static final boolean bridgeLoaded = loadBridge();
    private static SoundPool pool;
    private static boolean foreground;
    private static int stream;
    private static int pending = -1;
    private static float pendingGain;
    private static View flash;

    private static boolean loadBridge() {
        try {
            System.loadLibrary("IrisSpeedFeedback");
            return true;
        } catch (UnsatisfiedLinkError error) {
            Log.w(TAG, "Could not load the speed feedback bridge", error);
            return false;
        }
    }

    private static native long poll();

    static void frame() {
        if (!bridgeLoaded) return;
        long event = poll();
        int mode = (int) event;
        if (mode == 0) return;
        Activity activity = SexyAppFrameworkActivity.instance();
        if (activity != null) {
            float gain = Float.intBitsToFloat((int) (event >>> 32));
            activity.runOnUiThread(() -> play(activity, mode, gain));
        }
    }

    static void resume(Activity activity) {
        foreground = true;
        if (!bridgeLoaded || pool != null) return;
        try {
            pool = new SoundPool.Builder().setMaxStreams(1)
                .setAudioAttributes(new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_GAME)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build())
                .build();
            pool.setOnLoadCompleteListener((source, sample, status) -> {
                if (source != pool) return;
                for (int index = 0; index < samples.length; ++index) {
                    if (samples[index] != sample) continue;
                    ready[index] = status == 0;
                    if (!ready[index]) Log.w(TAG, "Could not decode " + ASSETS[index] + " status=" + status);
                    if (pending == index) {
                        pending = -1;
                        if (ready[index] && foreground) playSample(index, pendingGain);
                    }
                    return;
                }
            });
            for (int index = 0; index < ASSETS.length; ++index) {
                try (AssetFileDescriptor asset = activity.getAssets().openFd(ASSETS[index])) {
                    samples[index] = pool.load(asset, 1);
                }
            }
        } catch (IOException | RuntimeException error) {
            Log.w(TAG, "Could not preload speed cues", error);
        }
    }

    private static void play(Activity activity, int mode, float gain) {
        if (!foreground || activity.isFinishing() || activity.isDestroyed() || mode < 1 || mode > 2) return;
        flash(activity);
        stopSound();
        gain = Math.min(1f, gain);
        if (pool == null || !(gain > 0f)) return;
        int index = mode - 1;
        if (ready[index]) playSample(index, gain);
        else if (samples[index] != 0) {
            pending = index;
            pendingGain = gain;
        }
    }

    private static void playSample(int index, float gain) {
        stream = pool.play(samples[index], gain, gain, 1, 0, 1f);
        Log.i(TAG, "Speed " + (index + 1) + "x sound stream=" + stream);
    }

    private static void flash(Activity activity) {
        ViewGroup content = activity.findViewById(android.R.id.content);
        if (content == null) return;
        clearFlash();
        View view = new View(activity);
        view.setBackgroundColor(Color.WHITE);
        view.setAlpha(0.35f);
        view.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        content.addView(view, new ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        flash = view;
        view.animate().alpha(0f).setDuration(150).withEndAction(() -> {
            if (flash == view) clearFlash();
        }).start();
    }

    private static void clearFlash() {
        View view = flash;
        flash = null;
        if (view == null) return;
        view.animate().cancel();
        if (view.getParent() instanceof ViewGroup) ((ViewGroup) view.getParent()).removeView(view);
    }

    private static void stopSound() {
        pending = -1;
        if (pool != null && stream != 0) pool.stop(stream);
        stream = 0;
    }

    static void pause() {
        foreground = false;
        clearFlash();
        stopSound();
    }

    static void shutdown() {
        pause();
        if (pool != null) {
            pool.release();
            pool = null;
        }
        for (int index = 0; index < samples.length; ++index) {
            samples[index] = 0;
            ready[index] = false;
        }
    }
}
