package com.popcap.SexyAppFramework;

import android.util.Log;
import android.view.SurfaceHolder;
import javax.microedition.khronos.egl.EGL10;
import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.egl.EGLContext;
import javax.microedition.khronos.egl.EGLDisplay;
import javax.microedition.khronos.egl.EGLSurface;

// Recovered from the NA 1.6.257161 DEX and checked against Iris Smali.
public abstract class GLESRenderer {
    protected EGL10 mEgl;
    protected EGLConfig mEglConfig;
    protected AndroidSurfaceView mGLView;
    protected EGLDisplay mEglDisplay = EGL10.EGL_NO_DISPLAY;
    protected EGLSurface mEglSurface = EGL10.EGL_NO_SURFACE;
    protected EGLContext mEglContext = EGL10.EGL_NO_CONTEXT;
    protected EGLContext mLoadingContext = EGL10.EGL_NO_CONTEXT;

    public abstract int getGLESVersion();

    public abstract int getSysFBO();

    public abstract boolean resizeFromLayer();

    public abstract boolean setCurrentContext();

    public abstract boolean setLoadingContext();

    public void Init(AndroidSurfaceView InView, EGL10 InEgl, EGLDisplay InDisplay) {
        this.mGLView = InView;
        this.mEgl = InEgl;
        this.mEglDisplay = InDisplay;
    }

    public boolean Startup() {
        return true;
    }

    public void Shutdown() {
        synchronized (this) {
            DestroySurface();
            DestroyEglContext(this.mLoadingContext);
            this.mLoadingContext = EGL10.EGL_NO_CONTEXT;
            DestroyEglContext(this.mEglContext);
            this.mEglContext = EGL10.EGL_NO_CONTEXT;
        }
    }

    public void LostFocus() {
        DestroySurface();
    }

    public void GotFocus() {
        if (this.mEglContext == EGL10.EGL_NO_CONTEXT) {
            Startup();
        }
    }

    public void LostContext() {
        Shutdown();
    }

    public void CreateSurface(SurfaceHolder holder) {
        if (this.mEglSurface != EGL10.EGL_NO_SURFACE) {
            DestroySurface();
        }
        try {
            this.mEglSurface = this.mEgl.eglCreateWindowSurface(this.mEglDisplay, this.mEglConfig, holder, null);
        } catch (Exception ex) {
            Log.e("EGL", ex.toString());
        }
    }

    public void DestroySurface() {
        if (this.mEglSurface != EGL10.EGL_NO_SURFACE) {
            this.mEgl.eglMakeCurrent(this.mEglDisplay, EGL10.EGL_NO_SURFACE, EGL10.EGL_NO_SURFACE, EGL10.EGL_NO_CONTEXT);
            this.mEgl.eglDestroySurface(this.mEglDisplay, this.mEglSurface);
            this.mEglSurface = EGL10.EGL_NO_SURFACE;
        }
    }

    private void DestroyEglContext(EGLContext deadContext) {
        if (deadContext != EGL10.EGL_NO_CONTEXT) {
            this.mEgl.eglDestroyContext(this.mEglDisplay, deadContext);
        }
    }
}
