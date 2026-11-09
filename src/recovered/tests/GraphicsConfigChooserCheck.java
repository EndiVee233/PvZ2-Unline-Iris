package com.popcap.SexyAppFramework;

import java.lang.reflect.Proxy;
import java.util.Arrays;
import javax.microedition.khronos.egl.EGL10;
import javax.microedition.khronos.egl.EGLConfig;

public final class GraphicsConfigChooserCheck {
    private static final int[] ATTRIBUTES = {
        EGL10.EGL_RED_SIZE, EGL10.EGL_GREEN_SIZE, EGL10.EGL_BLUE_SIZE,
        EGL10.EGL_ALPHA_SIZE, EGL10.EGL_DEPTH_SIZE, EGL10.EGL_STENCIL_SIZE
    };
    private static final int[] TARGET = {8, 8, 8, 0, 24, 8};
    private static final EGLConfig LOW = new EGLConfig();
    private static final EGLConfig BEST = new EGLConfig();
    private static final EGLConfig TIE = new EGLConfig();
    private static final EGLConfig[] CANDIDATES = {LOW, BEST, TIE};

    private static void expect(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static void check(int glesVersion, int renderable, int failureCall) {
        int[] calls = {0};
        int[] filter = {
            EGL10.EGL_RED_SIZE, 8, EGL10.EGL_GREEN_SIZE, 8, EGL10.EGL_BLUE_SIZE, 8,
            EGL10.EGL_ALPHA_SIZE, 0, EGL10.EGL_DEPTH_SIZE, 24, EGL10.EGL_STENCIL_SIZE, 8,
            0x3040, renderable, EGL10.EGL_SURFACE_TYPE, EGL10.EGL_WINDOW_BIT, EGL10.EGL_NONE
        };
        EGL10 egl = (EGL10) Proxy.newProxyInstance(EGL10.class.getClassLoader(), new Class<?>[]{EGL10.class},
            (proxy, method, args) -> {
                if ("eglChooseConfig".equals(method.getName())) {
                    expect(Arrays.equals(filter, (int[]) args[1]), "EGL filter");
                    calls[0]++;
                    if (calls[0] == 1) {
                        expect(args[2] == null && (int) args[3] == 0, "count pass");
                        ((int[]) args[4])[0] = CANDIDATES.length;
                    } else {
                        expect((int) args[3] == CANDIDATES.length && args[4] == null, "list pass");
                        System.arraycopy(CANDIDATES, 0, args[2], 0, CANDIDATES.length);
                    }
                    return calls[0] != failureCall;
                }
                expect("eglGetConfigAttrib".equals(method.getName()), "unexpected EGL call");
                int index = 0;
                while (ATTRIBUTES[index] != (int) args[2]) {
                    index++;
                }
                // Unknown alpha must fall back to zero; equal scores retain the earlier match.
                if (args[1] == TIE && index == 3) {
                    return false;
                }
                ((int[]) args[3])[0] = args[1] == LOW && index == 0 ? 5 : TARGET[index];
                return true;
            });

        GraphicsConfigChooser chooser = new GraphicsConfigChooser(8, 8, 8, 0, 24, 8, glesVersion);
        expect(chooser.chooseConfig(egl, null) == (failureCall == 0 ? BEST : null), "best config or EGL failure");
        expect(calls[0] == (failureCall == 1 ? 1 : 2), "call count");
        expect(chooser.chooseConfigFromList(egl, null, new EGLConfig[0]) == null, "empty list");
    }

    public static void main(String[] args) {
        check(1, 1, 0);
        check(2, 4, 0);
        check(3, -1, 0);
        check(2, 4, 1);
        check(2, 4, 2);
        System.out.println("EGL filters, candidate ordering, and failure paths passed");
    }
}
