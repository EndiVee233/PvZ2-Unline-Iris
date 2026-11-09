package com.popcap.SexyAppFramework;

import android.os.Bundle;
import android.view.KeyEvent;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.CompletionInfo;
import android.view.inputmethod.CorrectionInfo;
import android.view.inputmethod.ExtractedText;
import android.view.inputmethod.ExtractedTextRequest;
import java.nio.charset.StandardCharsets;

import static com.popcap.SexyAppFramework.AndroidUIEventManager.*;

// Recovered from the NA 1.6.257161 DEX and checked against Iris Smali.
class EditInputConnection extends BaseInputConnection {
    private CharSequence mComposingText;
    private AndroidUIEventManager mUIEventManager;
    private AndroidSurfaceView mView;

    public EditInputConnection(AndroidSurfaceView targetView, boolean fullEditor, AndroidUIEventManager uiEventManager) {
        super(targetView, fullEditor);
        this.mView = targetView;
        this.mUIEventManager = uiEventManager;
    }

    private void sendEvent(CharSequence text, int action) {
        if (text != null) {
            byte[] textUTF8Bytes = text.toString().getBytes(StandardCharsets.UTF_8);
            this.mUIEventManager.HandleTextInputEvent(action, textUTF8Bytes);
        }
    }

    private boolean commitComposing(String commitText) {
        CharSequence composingText = this.mComposingText;
        this.mComposingText = null;
        if (composingText == null || !composingText.toString().equals(commitText)) {
            return false;
        }
        sendEvent("", TEXTINPUT_FINISH);
        return true;
    }

    @Override
    public boolean beginBatchEdit() {
        super.beginBatchEdit();
        return true;
    }

    @Override
    public boolean endBatchEdit() {
        super.endBatchEdit();
        return true;
    }

    @Override
    public boolean clearMetaKeyStates(int states) {
        super.clearMetaKeyStates(states);
        return true;
    }

    @Override
    public boolean commitCompletion(CompletionInfo completionInfo) {
        super.commitCompletion(completionInfo);
        return true;
    }

    @Override
    public boolean commitCorrection(CorrectionInfo correctionInfo) {
        super.commitCorrection(correctionInfo);
        return true;
    }

    @Override
    public boolean commitText(CharSequence text, int newCursorPosition) {
        super.commitText(text, newCursorPosition);
        if (!commitComposing(text.toString()) && text.length() > 0 && (text.length() != 1 || !Character.isDigit(text.charAt(0)))) {
            sendEvent(text, TEXTINPUT_COMMIT);
        }
        return true;
    }

    @Override
    public boolean deleteSurroundingText(int beforeLength, int afterLength) {
        super.deleteSurroundingText(beforeLength, afterLength);
        for (int i = 0; i < beforeLength; i++) {
            sendEvent("", TEXTINPUT_BACKSPACE);
        }
        return true;
    }

    @Override
    public boolean finishComposingText() {
        super.finishComposingText();
        if (this.mComposingText != null) {
            this.mComposingText = null;
            sendEvent("", TEXTINPUT_FINISH);
            return true;
        }
        return true;
    }

    @Override
    public int getCursorCapsMode(int reqModes) {
        int r = super.getCursorCapsMode(reqModes);
        return r;
    }

    @Override
    public ExtractedText getExtractedText(ExtractedTextRequest request, int flags) {
        ExtractedText r = super.getExtractedText(request, flags);
        return r;
    }

    @Override
    public CharSequence getSelectedText(int flags) {
        super.getSelectedText(flags);
        return null;
    }

    @Override
    public CharSequence getTextAfterCursor(int length, int flags) {
        super.getTextAfterCursor(length, flags);
        return "";
    }

    @Override
    public CharSequence getTextBeforeCursor(int length, int flags) {
        super.getTextBeforeCursor(length, flags);
        return "";
    }

    @Override
    public boolean performContextMenuAction(int id) {
        super.performContextMenuAction(id);
        return true;
    }

    @Override
    public boolean performEditorAction(int actionCode) {
        super.performEditorAction(actionCode);
        return true;
    }

    @Override
    public boolean performPrivateCommand(String action, Bundle data) {
        super.performPrivateCommand(action, data);
        return true;
    }

    @Override
    public boolean reportFullscreenMode(boolean enabled) {
        super.reportFullscreenMode(enabled);
        return true;
    }

    @Override
    public boolean sendKeyEvent(KeyEvent event) {
        super.sendKeyEvent(event);
        switch (event.getKeyCode()) {
            case KeyEvent.KEYCODE_0:
            case KeyEvent.KEYCODE_1:
            case KeyEvent.KEYCODE_2:
            case KeyEvent.KEYCODE_3:
            case KeyEvent.KEYCODE_4:
            case KeyEvent.KEYCODE_5:
            case KeyEvent.KEYCODE_6:
            case KeyEvent.KEYCODE_7:
            case KeyEvent.KEYCODE_8:
            case KeyEvent.KEYCODE_9:
                if (commitComposing(Character.toString((char) event.getUnicodeChar()))) {
                    return true;
                }
                break;
            case KeyEvent.KEYCODE_ENTER:
            case KeyEvent.KEYCODE_DEL:
                break;
            default:
                return true;
        }
        this.mUIEventManager.HandleKeyEvent(event);
        return true;
    }

    @Override
    public boolean setComposingRegion(int start, int end) {
        super.setComposingRegion(start, end);
        return true;
    }

    @Override
    public boolean setComposingText(CharSequence text, int newCursorPosition) {
        super.setComposingText(text, newCursorPosition);
        if (text.length() > 0) {
            this.mComposingText = text;
            sendEvent(text, TEXTINPUT_COMPOSE);
        } else {
            this.mComposingText = null;
            sendEvent("", TEXTINPUT_BACKSPACE);
        }
        return true;
    }

    @Override
    public boolean setSelection(int start, int end) {
        super.setSelection(start, end);
        return true;
    }
}
