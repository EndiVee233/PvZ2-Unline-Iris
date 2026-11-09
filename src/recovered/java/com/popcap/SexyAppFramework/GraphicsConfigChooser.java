package com.popcap.SexyAppFramework;

import android.opengl.GLSurfaceView;
import javax.microedition.khronos.egl.EGL10;
import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.egl.EGLDisplay;

// Recovered from the NA 1.6.257161 DEX and checked against Iris Smali.
public class GraphicsConfigChooser implements GLSurfaceView.EGLConfigChooser {
    private int mAlphaSize;
    private int mBlueSize;
    private int mDepthSize;
    private int mGLESVersion;
    private int mGreenSize;
    private int mRedSize;
    private int mStencilSize;
    private int[] mValue = new int[1];
    private static final int EGL_RENDERABLE_TYPE = 0x3040;
    private static int EGL_OPENGL_ES_BIT = 1;
    private static int EGL_OPENGL_ES2_BIT = 4;

    public GraphicsConfigChooser(int InRedSize, int InGreenSize, int InBlueSize, int InAlphaSize, int InDepthSize, int InStencilSize, int InGLESVersion) {
        this.mRedSize = InRedSize;
        this.mGreenSize = InGreenSize;
        this.mBlueSize = InBlueSize;
        this.mAlphaSize = InAlphaSize;
        this.mDepthSize = InDepthSize;
        this.mStencilSize = InStencilSize;
        this.mGLESVersion = InGLESVersion;
    }

    public EGLConfig chooseConfigFromList(EGL10 egl, EGLDisplay display, EGLConfig[] configs) {
        EGLConfig closestConfig = null;
        int closestDistance = 1000;
        for (EGLConfig config : configs) {
            int r = findConfigAttrib(egl, display, config, EGL10.EGL_RED_SIZE, 0);
            int g = findConfigAttrib(egl, display, config, EGL10.EGL_GREEN_SIZE, 0);
            int b = findConfigAttrib(egl, display, config, EGL10.EGL_BLUE_SIZE, 0);
            int a = findConfigAttrib(egl, display, config, EGL10.EGL_ALPHA_SIZE, 0);
            int d = findConfigAttrib(egl, display, config, EGL10.EGL_DEPTH_SIZE, 0);
            int s = findConfigAttrib(egl, display, config, EGL10.EGL_STENCIL_SIZE, 0);
            int distance = Math.abs(r - this.mRedSize) + Math.abs(g - this.mGreenSize) + Math.abs(b - this.mBlueSize) + Math.abs(a - this.mAlphaSize) + Math.abs(d - this.mDepthSize) + Math.abs(s - this.mStencilSize);
            if (distance < closestDistance) {
                closestDistance = distance;
                closestConfig = config;
            }
        }
        return closestConfig;
    }

    @Override
    public EGLConfig chooseConfig(EGL10 egl, EGLDisplay display) {
        int RenderableType;
        switch (this.mGLESVersion) {
            case 1:
                RenderableType = EGL_OPENGL_ES_BIT;
                break;
            case 2:
                RenderableType = EGL_OPENGL_ES2_BIT;
                break;
            default:
                RenderableType = -1;
                break;
        }
        int[] configParams = {EGL10.EGL_RED_SIZE, this.mRedSize, EGL10.EGL_GREEN_SIZE, this.mGreenSize, EGL10.EGL_BLUE_SIZE, this.mBlueSize, EGL10.EGL_ALPHA_SIZE, this.mAlphaSize, EGL10.EGL_DEPTH_SIZE, this.mDepthSize, EGL10.EGL_STENCIL_SIZE, this.mStencilSize, EGL_RENDERABLE_TYPE, RenderableType, EGL10.EGL_SURFACE_TYPE, EGL10.EGL_WINDOW_BIT, EGL10.EGL_NONE};
        int[] num_configs = new int[1];
        if (!egl.eglChooseConfig(display, configParams, null, 0, num_configs)) {
            return null;
        }
        int iConfigCount = num_configs[0];
        EGLConfig[] configs = new EGLConfig[iConfigCount];
        if (egl.eglChooseConfig(display, configParams, configs, iConfigCount, null)) {
            return chooseConfigFromList(egl, display, configs);
        }
        return null;
    }

    private int findConfigAttrib(EGL10 egl, EGLDisplay display, EGLConfig config, int attribute, int defaultValue) {
        if (egl.eglGetConfigAttrib(display, config, attribute, this.mValue)) {
            int defaultValue2 = this.mValue[0];
            return defaultValue2;
        }
        return defaultValue;
    }
}
