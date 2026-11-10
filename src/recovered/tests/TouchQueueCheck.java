package com.popcap.SexyAppFramework;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

public final class TouchQueueCheck {
    private static final int TOUCH_BYTES = 48;
    private static final int HEADER_BYTES = 16;

    private static void expect(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static void touch(ByteBuffer out, int phase, int id, int x, int y, int oldX, int oldY) {
        expect(out.getInt() == 0, "touch tag");
        expect(out.getInt() == id, "pointer ID");
        expect(out.getInt() == x && out.getInt() == y, "current coordinates");
        expect(out.getInt() == oldX && out.getInt() == oldY, "previous coordinates");
        expect(out.getInt() == 1, "tap count");
        expect(Double.isFinite(out.getDouble()), "timestamp");
        expect(out.getInt() == phase, "phase");
        expect(out.getInt() == 0xDEADBEEF && out.getInt() == 0xDEADBEEF, "padding");
    }

    public static void main(String[] args) {
        AndroidUIEventManager manager = new AndroidUIEventManager();
        ByteBuffer out = ByteBuffer.allocate(HEADER_BYTES + TOUCH_BYTES);

        manager.QueueIrisDesktop(5, 8, 12);
        expect(!manager.ProcessEvents(out) && out.getInt(0) == 0, "ignored without focus");
        manager.HandleGotFocus();
        manager.QueueIrisDesktop(5, -12.8f, 34.9f);
        manager.QueueIrisDesktop(36, 999, 0);
        manager.HandleTextInputEvent(AndroidUIEventManager.TEXTINPUT_COMMIT, new byte[]{0x41, 0x42, 0x43});
        expect(!manager.ProcessEvents(null), "null buffer");

        ByteBuffer shortBuffer = ByteBuffer.allocate(HEADER_BYTES + TOUCH_BYTES - 1);
        expect(manager.ProcessEvents(shortBuffer), "overflow retains event");
        expect(shortBuffer.getInt(0) == 0 && shortBuffer.position() == HEADER_BYTES, "overflow rewinds");

        expect(manager.ProcessEvents(out), "command and text pending");
        expect(out.order() == ByteOrder.LITTLE_ENDIAN && out.getInt(0) == 1, "batch header");
        out.position(HEADER_BYTES);
        touch(out, 5, 0x7ffffffe, -12, 34, -12, 34);

        expect(manager.ProcessEvents(out) && out.getInt(0) == 1, "text pending");
        out.position(HEADER_BYTES);
        touch(out, 6, 0x7ffffffe, 36, 0, -12, 34);

        expect(!manager.ProcessEvents(out) && out.getInt(0) == 1, "text drained");
        out.position(HEADER_BYTES);
        expect(out.getInt() == 6 && out.getInt() == 0 && out.getInt() == 3, "text tag, action and length");
        expect(out.getInt() == 0x00434241, "UTF-8 bytes and alignment");

        manager.QueueIrisDesktop(AndroidUIEventManager.DESKTOP_PLANTFOOD_AT_POINTER, 110, 70);
        expect(!manager.ProcessEvents(out) && out.getInt(0) == 1, "middle-click command");
        out.position(HEADER_BYTES);
        touch(out, 6, 0x7ffffffe, 101, 0, 110, 70);

        AndroidUIEventManager.UITouchTracker tracker = manager.new UITouchTracker();
        tracker.mPointerId = 3;
        tracker.X = 18;
        tracker.Y = 19;
        manager.mTouches.put(tracker.mPointerId, tracker);
        manager.HandleLostFocus();
        expect(manager.mTouches.isEmpty(), "lost focus clears trackers");
        expect(!manager.ProcessEvents(out) && out.getInt(0) == 1, "cancel queued");
        out.position(HEADER_BYTES);
        touch(out, 4, 4, 18, 19, 18, 19);
        manager.HandleGotFocus();
        manager.QueueIrisDesktop(36, 0, 0);
        expect(!manager.ProcessEvents(out) && out.getInt(0) == 1, "command after regaining focus");
        out.position(HEADER_BYTES);
        touch(out, 6, 0x7ffffffe, 36, 0, -1, -1);
        System.out.println("Java touch queue, text, focus, and overflow checks passed");
    }
}
