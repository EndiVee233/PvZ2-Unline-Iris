package com.popcap.SexyAppFramework;

import android.opengl.GLES20;
import android.util.Log;

// Recovered from the NA 1.6.257161 DEX and checked against Iris Smali.
class GLES20Renderer extends GLESRenderer {
    private int colorRenderbuffer;
    private int defaultFramebuffer;

    GLES20Renderer() {
    }

    @Override
    public int getGLESVersion() {
        return 2;
    }

    @Override
    public boolean Startup() {
        if (!super.Startup()) {
            return false;
        }
        this.defaultFramebuffer = -1;
        this.colorRenderbuffer = 0;
        if (this.defaultFramebuffer != -1) {
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, this.defaultFramebuffer);
            GLES20.glBindRenderbuffer(GLES20.GL_RENDERBUFFER, this.colorRenderbuffer);
            GLES20.glFramebufferRenderbuffer(GLES20.GL_FRAMEBUFFER, GLES20.GL_COLOR_ATTACHMENT0, GLES20.GL_RENDERBUFFER, this.colorRenderbuffer);
        } else {
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);
        }
        resizeFromLayer();
        return true;
    }

    @Override
    public void Shutdown() {
        if (this.defaultFramebuffer != -1) {
            GLES20.glDeleteFramebuffers(1, new int[]{this.defaultFramebuffer}, 0);
            this.defaultFramebuffer = -1;
        }
        if (this.colorRenderbuffer != 0) {
            GLES20.glDeleteRenderbuffers(1, new int[]{this.colorRenderbuffer}, 0);
            this.colorRenderbuffer = 0;
        }
        super.Shutdown();
    }

    @Override
    public boolean resizeFromLayer() {
        GLES20.glBindRenderbuffer(GLES20.GL_RENDERBUFFER, this.colorRenderbuffer);
        if (GLES20.glCheckFramebufferStatus(GLES20.GL_FRAMEBUFFER) == GLES20.GL_FRAMEBUFFER_COMPLETE) {
            return true;
        }
        Log.e("GLES20", String.format("Failed to make complete framebuffer object %x", Integer.valueOf(GLES20.glCheckFramebufferStatus(GLES20.GL_FRAMEBUFFER))));
        return false;
    }

    @Override
    public int getSysFBO() {
        return -1;
    }

    @Override
    public boolean setCurrentContext() {
        boolean success = this.mEgl.eglMakeCurrent(this.mEglDisplay, this.mEglSurface, this.mEglSurface, this.mEglContext);
        if (!success) {
            return false;
        }
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);
        return true;
    }

    @Override
    public boolean setLoadingContext() {
        boolean success = this.mEgl.eglMakeCurrent(this.mEglDisplay, this.mEglSurface, this.mEglSurface, this.mLoadingContext);
        return success;
    }
}
