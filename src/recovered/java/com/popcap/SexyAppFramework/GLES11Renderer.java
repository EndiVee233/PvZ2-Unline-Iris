package com.popcap.SexyAppFramework;

import android.opengl.GLES11Ext;
import android.util.Log;

// Recovered from the NA 1.6.257161 DEX and checked against Iris Smali.
public class GLES11Renderer extends GLESRenderer {
    private int colorRenderbuffer;
    private int defaultFramebuffer;

    @Override
    public int getGLESVersion() {
        return 1;
    }

    @Override
    public boolean Startup() {
        if (!super.Startup()) {
            return false;
        }
        this.defaultFramebuffer = -1;
        this.colorRenderbuffer = 0;
        if (this.defaultFramebuffer != -1) {
            GLES11Ext.glBindFramebufferOES(GLES11Ext.GL_FRAMEBUFFER_OES, this.defaultFramebuffer);
            GLES11Ext.glBindRenderbufferOES(GLES11Ext.GL_RENDERBUFFER_OES, this.colorRenderbuffer);
            GLES11Ext.glFramebufferRenderbufferOES(GLES11Ext.GL_FRAMEBUFFER_OES, GLES11Ext.GL_COLOR_ATTACHMENT0_OES, GLES11Ext.GL_RENDERBUFFER_OES, this.colorRenderbuffer);
        } else {
            GLES11Ext.glBindFramebufferOES(GLES11Ext.GL_FRAMEBUFFER_OES, 0);
        }
        resizeFromLayer();
        return true;
    }

    @Override
    public void Shutdown() {
        if (this.defaultFramebuffer != -1) {
            GLES11Ext.glDeleteFramebuffersOES(1, new int[]{this.defaultFramebuffer}, 0);
            this.defaultFramebuffer = -1;
        }
        if (this.colorRenderbuffer != 0) {
            GLES11Ext.glDeleteRenderbuffersOES(1, new int[]{this.colorRenderbuffer}, 0);
            this.colorRenderbuffer = 0;
        }
        super.Shutdown();
    }

    @Override
    public boolean resizeFromLayer() {
        GLES11Ext.glBindRenderbufferOES(GLES11Ext.GL_RENDERBUFFER_OES, this.colorRenderbuffer);
        int width = this.mGLView.getWidth();
        int height = this.mGLView.getHeight();
        GLES11Ext.glRenderbufferStorageOES(GLES11Ext.GL_RENDERBUFFER_OES, GLES11Ext.GL_RGB565_OES, width, height);
        if (GLES11Ext.glCheckFramebufferStatusOES(GLES11Ext.GL_FRAMEBUFFER_OES) == GLES11Ext.GL_FRAMEBUFFER_COMPLETE_OES) {
            return true;
        }
        Log.e("GLES11", String.format("Failed to make complete framebuffer object %x", Integer.valueOf(GLES11Ext.glCheckFramebufferStatusOES(GLES11Ext.GL_FRAMEBUFFER_OES))));
        return false;
    }

    @Override
    public int getSysFBO() {
        return this.defaultFramebuffer;
    }

    @Override
    public boolean setCurrentContext() {
        boolean success = this.mEgl.eglMakeCurrent(this.mEglDisplay, this.mEglSurface, this.mEglSurface, this.mEglContext);
        if (!success) {
            return false;
        }
        GLES11Ext.glBindFramebufferOES(GLES11Ext.GL_FRAMEBUFFER_OES, 0);
        return true;
    }

    @Override
    public boolean setLoadingContext() {
        boolean success = this.mEgl.eglMakeCurrent(this.mEglDisplay, this.mEglSurface, this.mEglSurface, this.mLoadingContext);
        return success;
    }
}
