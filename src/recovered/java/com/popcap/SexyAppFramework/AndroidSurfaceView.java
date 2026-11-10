package com.popcap.SexyAppFramework;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.PixelFormat;
import android.opengl.GLSurfaceView;
import android.text.InputType;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Display;
import android.view.GestureDetector;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.SurfaceHolder;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import java.util.BitSet;
import javax.microedition.khronos.egl.EGL10;
import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.egl.EGLContext;
import javax.microedition.khronos.egl.EGLDisplay;
import javax.microedition.khronos.opengles.GL;
import javax.microedition.khronos.opengles.GL10;

// Recovered from the NA 1.6.257161 DEX and checked against Iris Smali.
public class AndroidSurfaceView extends GLSurfaceView {
    public static final int DEBUG_CHECK_GL_ERROR = 1;
    public static final int DEBUG_LOG_GL_CALLS = 2;
    private boolean irisRightDown;
    private boolean irisMiddleDown;
    private final BitSet irisKeysDown = new BitSet();
    private AndroidRenderer mAndroidRenderer;
    private EGL10 mEgl;
    private int mGLESVersionSupported;
    private GestureDetector mGestureDetector;
    private EditInputConnection mInputConnection;
    private int mOrigAppHeight;
    private int mOrigAppWidth;
    GLESRenderer mRenderer;
    private ScaleGestureDetector mScaleGestureDetector;
    private AndroidUIEventManager mUIEventManager;
    private float mViewScaleFactor;
    private WindowManager mWindowManager;
    public boolean mbDrawingFrames;
    public boolean mbFocusState;
    private boolean mbIsInitialized;
    public Object mbNotifyOnDrawEventObject;
    static boolean DEBUG = false;
    static String LogTAG = "SexyEGL";

    public interface AndroidEGLConfigChooserInterface {
        EGLConfig chooseConfig(EGL10 egl10, EGLDisplay eGLDisplay);
    }

    public interface GLWrapper {
        GL wrap(GL gl);
    }

    private native void Native_onDrawFrame();

    private native void Native_onSurfaceChanged(int i, int i2);

    private native void Native_onSurfaceCreated();

    private boolean irisPointer(MotionEvent motionEvent) {
        AndroidUIEventManager androidUIEventManager = this.mUIEventManager;
        if (androidUIEventManager == null || !motionEvent.isFromSource(InputDevice.SOURCE_CLASS_POINTER)) {
            return false;
        }
        int buttonState = motionEvent.getButtonState();
        if ((buttonState & MotionEvent.BUTTON_TERTIARY) != 0) {
            if (!irisMiddleDown) {
                irisMiddleDown = true;
                androidUIEventManager.QueueIrisDesktop(AndroidUIEventManager.DESKTOP_PLANTFOOD_AT_POINTER,
                        motionEvent.getX(), motionEvent.getY());
            }
            return true;
        }
        if (irisMiddleDown) {
            irisMiddleDown = false;
            if (motionEvent.getActionMasked() == MotionEvent.ACTION_UP
                    || motionEvent.getActionMasked() == MotionEvent.ACTION_BUTTON_RELEASE) {
                return true;
            }
        }
        if ((buttonState & MotionEvent.BUTTON_SECONDARY) != 0) {
            if (this.irisRightDown) {
                return true;
            }
            this.irisRightDown = true;
            androidUIEventManager.QueueIrisDesktop(AndroidUIEventManager.DESKTOP_CANCEL, 0.0f, 0.0f);
            return true;
        }
        if (this.irisRightDown) {
            this.irisRightDown = false;
            int actionMasked = motionEvent.getActionMasked();
            if (actionMasked == MotionEvent.ACTION_UP || actionMasked == MotionEvent.ACTION_BUTTON_RELEASE) {
                return true;
            }
        }
        if (buttonState != 0 || motionEvent.getActionMasked() != MotionEvent.ACTION_HOVER_MOVE) {
            return false;
        }
        androidUIEventManager.QueueIrisDesktop(AndroidUIEventManager.DESKTOP_HOVER, motionEvent.getX(), motionEvent.getY());
        return true;
    }

    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent motionEvent) {
        return irisPointer(motionEvent) || super.dispatchGenericMotionEvent(motionEvent);
    }

    @Override
    public boolean onHoverEvent(MotionEvent motionEvent) {
        return irisPointer(motionEvent) || super.onHoverEvent(motionEvent);
    }

    @Override
    public boolean dispatchTouchEvent(MotionEvent motionEvent) {
        return irisPointer(motionEvent) || super.dispatchTouchEvent(motionEvent);
    }

    public AndroidSurfaceView(Context InContext) {
        super(InContext);
        this.mGLESVersionSupported = 0;
        this.mbDrawingFrames = false;
        this.mbFocusState = false;
        this.mViewScaleFactor = 0.5f;
    }

    public AndroidSurfaceView(Context InContext, WindowManager InWindowManager, AndroidUIEventManager InEventManager, int InGLESVersionSupported) {
        super(InContext);
        this.mGLESVersionSupported = 0;
        this.mbDrawingFrames = false;
        this.mbFocusState = false;
        this.mViewScaleFactor = 0.5f;
        this.mWindowManager = InWindowManager;
        this.mUIEventManager = InEventManager;
        this.mGLESVersionSupported = InGLESVersionSupported;
        this.mbIsInitialized = false;
        setFocusable(true);
        setFocusableInTouchMode(true);
        this.mOrigAppWidth = 0;
        this.mOrigAppHeight = 0;
        this.mGestureDetector = new GestureDetector(InContext, this.mUIEventManager);
        this.mGestureDetector.setIsLongpressEnabled(true);
        this.mScaleGestureDetector = new ScaleGestureDetector(InContext, this.mUIEventManager);
        setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                if (!SexyAppFrameworkActivity.instance().SplashScreenShowing()) {
                    boolean GestureDetected = AndroidSurfaceView.this.mScaleGestureDetector.onTouchEvent(event) | AndroidSurfaceView.this.mGestureDetector.onTouchEvent(event);
                    return AndroidSurfaceView.this.mUIEventManager.HandleTouchEvent(event) | GestureDetected;
                }
                return false;
            }
        });
    }

    public void init(int InRedBits, int InGreenBits, int InBlueBits, int InAlphaBits, int InDepthBits, int InStencilBits) {
        if (Graphics_IsOpenGLES20()) {
            this.mRenderer = new GLES20Renderer();
        }
        if (this.mRenderer == null) {
            this.mRenderer = new GLES11Renderer();
        }
        if (InAlphaBits > 0) {
            SurfaceHolder holder = getHolder();
            holder.setFormat(PixelFormat.TRANSLUCENT);
        }
        setEGLContextFactory(new AndroidEGLContextFactory(this));
        setEGLConfigChooser(new GraphicsConfigChooser(InRedBits, InGreenBits, InBlueBits, InAlphaBits, InDepthBits, InStencilBits, this.mGLESVersionSupported));
        this.mAndroidRenderer = new AndroidRenderer(this);
        setRenderer(this.mAndroidRenderer);
        this.mbIsInitialized = true;
    }

    private boolean EglContextIsValid() {
        EGLContext currentContext = this.mEgl.eglGetCurrentContext();
        return currentContext == this.mRenderer.mEglContext || this.mRenderer.setCurrentContext();
    }

    private int Graphics_GetGLViewSysFBO() {
        return this.mRenderer.getSysFBO();
    }

    public boolean Graphics_IsOpenGLES20() {
        return this.mGLESVersionSupported >= 2;
    }

    private float Graphics_GetGLViewScaleFactor() {
        return this.mViewScaleFactor;
    }

    private void Graphics_SetGLViewScaleFactor(float InScaleFactor) {
        this.mViewScaleFactor = InScaleFactor;
    }

    private boolean Graphics_CanSetGLViewScaleFactor() {
        return true;
    }

    private void Graphics_GetScreenSizeInPixels(int[] outWidthHeight) {
        synchronized (this) {
            outWidthHeight[0] = this.mOrigAppWidth;
            outWidthHeight[1] = this.mOrigAppHeight;
        }
    }

    public void SetScreenSizeInPixels(int width, int height) {
        this.mOrigAppWidth = width;
        this.mOrigAppHeight = height;
    }

    private void Graphics_GetScreenSizeInPoints(int[] outWidthHeight) {
        synchronized (this) {
            Display disp = this.mWindowManager.getDefaultDisplay();
            DisplayMetrics metrics = new DisplayMetrics();
            disp.getMetrics(metrics);
            float width = getWidth();
            float height = getHeight();
            outWidthHeight[0] = Math.round(width * 1.0f);
            outWidthHeight[1] = Math.round(height * 1.0f);
        }
    }

    private float Graphics_GetPointSizeInPixels() {
        float f;
        synchronized (this) {
            Display disp = this.mWindowManager.getDefaultDisplay();
            DisplayMetrics metrics = new DisplayMetrics();
            disp.getMetrics(metrics);
            f = metrics.density;
        }
        return f;
    }

    public final boolean IsInitailized() {
        return this.mbIsInitialized;
    }

    private static class AndroidEGLContextFactory implements GLSurfaceView.EGLContextFactory {
        private static int EGL_CONTEXT_CLIENT_VERSION = 12440;
        private AndroidSurfaceView mView;

        public AndroidEGLContextFactory(AndroidSurfaceView InView) {
            this.mView = null;
            this.mView = InView;
        }

        @Override
        public EGLContext createContext(EGL10 egl, EGLDisplay display, EGLConfig eglConfig) {
            int GLESVers = this.mView.mRenderer.getGLESVersion();
            int[] attrib_list = null;
            if (GLESVers > 0) {
                attrib_list = new int[]{EGL_CONTEXT_CLIENT_VERSION, GLESVers, EGL10.EGL_NONE};
            }
            checkEglError("Before eglCreateContext", egl);
            EGLContext newContext = egl.eglCreateContext(display, eglConfig, EGL10.EGL_NO_CONTEXT, attrib_list);
            if (newContext == EGL10.EGL_NO_CONTEXT) {
                checkEglError("After eglCreateContext", egl);
            }
            return newContext;
        }

        @Override
        public void destroyContext(EGL10 egl, EGLDisplay display, EGLContext deadContext) {
            if (deadContext != EGL10.EGL_NO_CONTEXT) {
                egl.eglDestroyContext(display, deadContext);
            }
        }

        private static void checkEglError(String prompt, EGL10 egl) {
            while (true) {
                int error = egl.eglGetError();
                if (error != EGL10.EGL_SUCCESS) {
                    Log.e(AndroidSurfaceView.LogTAG, String.format("%s: EGL error: 0x%x", prompt, Integer.valueOf(error)));
                } else {
                    return;
                }
            }
        }
    }

    @Override
    public boolean onKeyDown(int InKeyCode, KeyEvent InEvent) {
        switch (InKeyCode) {
            case KeyEvent.KEYCODE_1:
            case KeyEvent.KEYCODE_2:
            case KeyEvent.KEYCODE_3:
            case KeyEvent.KEYCODE_4:
            case KeyEvent.KEYCODE_A:
            case KeyEvent.KEYCODE_B:
            case KeyEvent.KEYCODE_D:
            case KeyEvent.KEYCODE_E:
            case KeyEvent.KEYCODE_F:
            case KeyEvent.KEYCODE_M:
            case KeyEvent.KEYCODE_N:
            case KeyEvent.KEYCODE_Q:
            case KeyEvent.KEYCODE_R:
            case KeyEvent.KEYCODE_V:
            case KeyEvent.KEYCODE_W:
            case KeyEvent.KEYCODE_X:
            case KeyEvent.KEYCODE_Z:
            case KeyEvent.KEYCODE_SPACE:
                if (InEvent.getRepeatCount() != 0) {
                    return irisKeysDown.get(InKeyCode) || super.onKeyDown(InKeyCode, InEvent);
                }
                irisKeysDown.clear(InKeyCode);
                SexyAppFrameworkActivity sexyAppFrameworkActivityInstance = SexyAppFrameworkActivity.instance();
                if (sexyAppFrameworkActivityInstance != null && !sexyAppFrameworkActivityInstance.irisKeyboardShowing() && InEvent.hasNoModifiers()) {
                    AndroidUIEventManager androidUIEventManager = this.mUIEventManager;
                    if (androidUIEventManager != null) {
                        androidUIEventManager.QueueIrisDesktop(InKeyCode, 0.0f, 0.0f);
                        irisKeysDown.set(InKeyCode);
                        return true;
                    }
                }
                break;
        }
        if (InKeyCode == KeyEvent.KEYCODE_MENU) {
            return true;
        }
        return super.onKeyDown(InKeyCode, InEvent);
    }

    @Override
    public boolean onKeyUp(int keyCode, KeyEvent event) {
        if (keyCode >= 0 && irisKeysDown.get(keyCode)) {
            irisKeysDown.clear(keyCode);
            return true;
        }
        return super.onKeyUp(keyCode, event);
    }

    @Override
    public void onWindowFocusChanged(boolean hasWindowFocus) {
        super.onWindowFocusChanged(hasWindowFocus);
        if (!hasWindowFocus) {
            irisKeysDown.clear();
            irisRightDown = irisMiddleDown = false;
        }
    }

    @Override
    protected void dispatchDraw(Canvas canvas) {
        super.dispatchDraw(canvas);
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
    }

    @Override
    protected void onDetachedFromWindow() {
        super.onDetachedFromWindow();
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        super.onMeasure(widthMeasureSpec, heightMeasureSpec);
    }

    @Override
    protected void onWindowVisibilityChanged(int visibility) {
        super.onWindowVisibilityChanged(visibility);
    }

    @Override
    public void onPause() {
        super.onPause();
        this.mAndroidRenderer.onPause();
    }

    public void SetFocusState(boolean inFocusState) {
        this.mbFocusState = inFocusState;
    }

    public boolean HasDrawnFirstFrame() {
        return !AndroidRenderer.mFirstDraw;
    }

    @Override
    public boolean onCheckIsTextEditor() {
        return true;
    }

    @Override
    public InputConnection onCreateInputConnection(EditorInfo outAttrs) {
        if (this.mInputConnection == null) {
            this.mInputConnection = new EditInputConnection(this, false, this.mUIEventManager);
        }
        outAttrs.actionLabel = null;
        outAttrs.inputType = InputType.TYPE_CLASS_TEXT;
        outAttrs.imeOptions = EditorInfo.IME_FLAG_NO_EXTRACT_UI;
        return this.mInputConnection;
    }

    @Override
    public boolean onKeyPreIme(int keyCode, KeyEvent event) {
        if (event.getKeyCode() == KeyEvent.KEYCODE_BACK) {
            if (event.getAction() == KeyEvent.ACTION_DOWN) {
                onKeyDown(keyCode, event);
            } else if (event.getAction() == KeyEvent.ACTION_UP) {
                onKeyUp(keyCode, event);
                SexyAppFrameworkActivity.instance().onKeyboardDismissedWithBackButton();
            }
            return false;
        }
        return super.onKeyPreIme(keyCode, event);
    }

    private static class AndroidRenderer implements GLSurfaceView.Renderer {
        static boolean mFirstDraw = true;
        AndroidSurfaceView mGLView;

        AndroidRenderer(AndroidSurfaceView InView) {
            this.mGLView = null;
            this.mGLView = InView;
        }

        @Override
        public void onDrawFrame(GL10 gl) {
            this.mGLView.mbDrawingFrames = true;
            if (this.mGLView.mbNotifyOnDrawEventObject != null) {
                synchronized (this.mGLView.mbNotifyOnDrawEventObject) {
                    this.mGLView.mbNotifyOnDrawEventObject.notifyAll();
                    this.mGLView.mbNotifyOnDrawEventObject = null;
                }
            } else if (!this.mGLView.mbFocusState) {
                return;
            }
            this.mGLView.Native_onDrawFrame();
            IrisSpeedFeedback.frame();
            if (mFirstDraw) {
                mFirstDraw = false;
                SexyAppFrameworkActivity.instance().RemoveSplashScreen();
            }
        }

        @Override
        public void onSurfaceCreated(GL10 gl, EGLConfig config) {
            Log.i("Surface", "surfaceCreated");
            this.mGLView.Native_onSurfaceCreated();
        }

        @Override
        public void onSurfaceChanged(GL10 gl, int width, int height) {
            Log.i("Surface", String.format("surfaceChanged %d %d", Integer.valueOf(width), Integer.valueOf(height)));
            this.mGLView.Native_onSurfaceChanged(width, height);
        }

        public void onPause() {
        }
    }
}
