package com.popcap.SexyAppFramework;

import android.app.ActivityManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ConfigurationInfo;
import android.content.res.Configuration;
import android.graphics.Point;
import android.graphics.Rect;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.Display;
import android.view.ViewGroup;
import android.view.WindowManager;
import com.popcap.PvZ2.LiteRuntime;
import com.popcap.SexyAppFramework.GooglePlay.BaseGameActivity;
import com.popcap.SexyAppFramework.cloud.Cloud;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;

// Recovered from the NA 1.6.257161 DEX and checked against Iris Smali.
public class SexyAppFrameworkActivity extends BaseGameActivity {
    private static final int PLAY_SERVICES_RESOLUTION_REQUEST = 9000;
    private static final String TAG = "SexyAppFramework";
    private static GooglePlayPurchaseDriver mPurchaseDriver;
    private static AndroidSplashScreen mSplashScreen;
    private Cloud mCloud;
    private AndroidSurfaceView mGLView;
    private AndroidGameApp mGameApp;
    private Bundle mSavedInstanceState;
    private AndroidUIEventManager mUIEventManager;
    private static SexyAppFrameworkActivity sTheActivity = null;
    private static ArrayList<AndroidSplashScreen.SplashImage> mSplashScreenImages = null;

    public static String FrameworkInfo_SysGetMainExpansionFilePath() {
        return LiteRuntime.expansionPath(instance());
    }

    private boolean checkPlayServices() {
        return false;
    }

    public boolean irisKeyboardShowing() {
        AndroidGameApp gameApp = this.mGameApp;
        return gameApp != null && gameApp.Device_IsKeyboardShowing();
    }

    public static SexyAppFrameworkActivity instance() {
        return sTheActivity;
    }

    public static String getAndroidPackageName() {
        return instance().getPackageName();
    }

    public SexyAppFrameworkActivity() {
        synchronized (SexyAppFrameworkActivity.class) {
            sTheActivity = this;
        }
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        Log.i(TAG, "onCreate");
        super.onCreate(savedInstanceState);
        this.mSavedInstanceState = savedInstanceState;
        this.mUIEventManager = new AndroidUIEventManager();
    }

    public Point getDisplaySize() {
        Display display = ((WindowManager) getSystemService(Context.WINDOW_SERVICE)).getDefaultDisplay();
        int width = display.getWidth();
        int height = display.getHeight();
        Point size = new Point(width, height);
        return size;
    }

    @Override
    public void launchGame() {
        Log.d(TAG, "SexyAppFrameworkActivity::LaunchGame");
        ActivityManager am = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        ConfigurationInfo info = am.getDeviceConfigurationInfo();
        boolean bGLES2Supported = info.reqGlEsVersion >= 0x20000 || Build.FINGERPRINT.startsWith("generic");
        int iGLESVersionSupported = bGLES2Supported ? 2 : 1;
        this.mGLView = new AndroidSurfaceView(getApplicationContext(), getWindowManager(), this.mUIEventManager, iGLESVersionSupported);
        this.mCloud = new Cloud(sTheActivity);
        this.mGameApp = new AndroidGameApp(this, this.mGLView, this.mUIEventManager, this.mCloud);
        Point displaySize = getDisplaySize();
        this.mGLView.SetScreenSizeInPixels(displaySize.x, displaySize.y);
        this.mGLView.init(8, 8, 8, 0, 16, 0);
        setContentView(this.mGLView);
        AddSplashScreen();
        this.mGameApp.onActivityCreate(this.mSavedInstanceState, getIntent());
        Uri data = getIntent().getData();
        if (data != null) {
            this.mGameApp.setStartUrl(data.toString());
            getIntent().setData(null);
        }
        this.mGameApp.onActivityStart();
        super.launchGame();
    }

    public void AddSplashScreen() {
        if (!mSplashScreenImages.isEmpty()) {
            if (mSplashScreen == null) {
                mSplashScreen = new AndroidSplashScreen(getApplicationContext());
                ViewGroup.LayoutParams lp = new ViewGroup.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                addContentView(mSplashScreen, lp);
            }
            return;
        }
        Log.e(TAG, "No splash screen specified for app. Add a call AddSplashScreenImage in your source wrapper to enable a splash screen.");
    }

    public void RemoveSplashScreen() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (SexyAppFrameworkActivity.this.SplashScreenShowing()) {
                    ViewGroup vg = (ViewGroup) SexyAppFrameworkActivity.mSplashScreen.getParent();
                    vg.removeView(SexyAppFrameworkActivity.mSplashScreen);
                    SexyAppFrameworkActivity.mSplashScreen = null;
                }
            }
        });
    }

    public boolean SplashScreenShowing() {
        return mSplashScreen != null;
    }

    @Override
    public void onRestart() {
        Log.i(TAG, "onRestart");
        super.onRestart();
        if (this.mGameApp != null) {
            this.mGameApp.onActivityRestart();
        }
    }

    @Override
    public void onStart() {
        Log.i(TAG, "onStart");
        super.onStart();
    }

    @Override
    public void onResume() {
        Log.i(TAG, "onResume");
        super.onResume();
        IrisSpeedFeedback.resume(this);
        if (this.mGLView != null && this.mGameApp != null) {
            this.mGLView.onResume();
            this.mGameApp.onActivityResume();
            this.mGLView.requestFocus();
        }
    }

    @Override
    public void onPause() {
        Log.i(TAG, "onPause");
        IrisSpeedFeedback.pause();
        super.onPause();
        if (this.mGLView != null && this.mGameApp != null) {
            this.mGameApp.onActivityPause();
            this.mGLView.onPause();
        }
    }

    @Override
    public void onStop() {
        Log.i(TAG, "onStop");
        super.onStop();
        if (this.mGameApp != null) {
            this.mGameApp.onActivityStop();
        }
    }

    @Override
    public void onDestroy() {
        Log.i(TAG, "onDestroy");
        IrisSpeedFeedback.shutdown();
        super.onDestroy();
        if (this.mGameApp != null) {
            this.mGameApp.onActivityDestroy();
            this.mGameApp = null;
        }
        this.mGLView = null;
        this.mUIEventManager = null;
        synchronized (SexyAppFrameworkActivity.class) {
            if (this == sTheActivity) {
                sTheActivity = null;
            }
        }
        System.exit(0);
    }

    @Override
    public void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        if (this.mGameApp != null) {
            this.mGameApp.onSaveInstanceState(outState);
        }
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        this.mGameApp.HandleOnConfigurationChanged(newConfig);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (this.mGameApp != null) {
            this.mGameApp.onWindowFocusChanged(hasFocus);
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        setIntent(intent);
    }

    public void setPurchaseDriver(GooglePlayPurchaseDriver driver) {
        mPurchaseDriver = driver;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        Log.e(TAG, String.format("onActivityResult: requestCode: %d; resultCode: %d", Integer.valueOf(requestCode), Integer.valueOf(resultCode)));
        boolean isPurchaseResult = mPurchaseDriver != null && mPurchaseDriver.onActivityResult(requestCode, resultCode, data);
        if (!isPurchaseResult) {
            super.onActivityResult(requestCode, resultCode, data);
            this.mCloud.onActivityResult(requestCode, resultCode, data);
            if (this.mGameApp != null) {
                this.mGameApp.onActivityResult(requestCode, resultCode, data);
            }
        }
    }

    protected static void AddSplashScreenImage(int aBGResourceID, int aBGResourceWidth, int aBGResourceHeight) {
        if (mSplashScreenImages == null) {
            mSplashScreenImages = new ArrayList<>();
        }
        mSplashScreenImages.add(new AndroidSplashScreen.SplashImage(aBGResourceID, aBGResourceWidth, aBGResourceHeight));
    }

    public static class SplashImageComparator implements Comparator<AndroidSplashScreen.SplashImage> {
        @Override
        public int compare(AndroidSplashScreen.SplashImage lhs, AndroidSplashScreen.SplashImage rhs) {
            return lhs.GetIntendedArea().compareTo(rhs.GetIntendedArea());
        }
    }

    public static int GetBestFitSplashImage(int aDisplayWidth, int aDisplayHeight) {
        int aSplashResourceID = -1;
        if (!mSplashScreenImages.isEmpty()) {
            Collections.sort(mSplashScreenImages, new SplashImageComparator());
            Rect aDisplayRect = new Rect(0, 0, aDisplayWidth, aDisplayHeight);
            for (AndroidSplashScreen.SplashImage img : mSplashScreenImages) {
                Rect aIntendedDisplayRect = img.GetIntendedDisplayRect();
                if (aIntendedDisplayRect.contains(aDisplayRect)) {
                    aSplashResourceID = img.GetResourceID();
                    break;
                }
            }
        }
        if (aSplashResourceID == -1) {
            Log.e(TAG, String.format("No splash screen for display size: %dx%d", Integer.valueOf(aDisplayWidth), Integer.valueOf(aDisplayHeight)));
        }
        return aSplashResourceID;
    }

    @Override
    public void onBackPressed() {
        Log.d(TAG, "Back Button pressed.");
        this.mUIEventManager.onBackButtonPressed();
    }

    public void onKeyboardDismissedWithBackButton() {
        if (this.mGameApp != null && this.mGameApp.mbIsKeyboardShowing) {
            this.mGameApp.mbIsKeyboardShowing = false;
        }
    }

    @Override
    public void onSignInSucceeded() {
        this.mCloud.Cloud_attemptSilentSync();
    }
}
