package com.popcap.SexyAppFramework;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.widget.ProgressBar;
import android.widget.RelativeLayout;

// Recovered from the NA 1.6.257161 DEX and checked against Iris Smali.
public class AndroidSplashScreen extends RelativeLayout {

    public static class SplashImage {
        private Rect mIntendedDisplayRect;
        private int mResourceID;

        SplashImage(int aResourceID, int aIntendedDisplayWidth, int aIntendedDisplayHeight) {
            this.mResourceID = aResourceID;
            this.mIntendedDisplayRect = new Rect(0, 0, aIntendedDisplayWidth, aIntendedDisplayHeight);
        }

        public int GetResourceID() {
            return this.mResourceID;
        }

        public Rect GetIntendedDisplayRect() {
            return this.mIntendedDisplayRect;
        }

        public Integer GetIntendedArea() {
            return Integer.valueOf(this.mIntendedDisplayRect.width() * this.mIntendedDisplayRect.height());
        }
    }

    public AndroidSplashScreen(Context context) {
        super(context);
        setVerticalGravity(Gravity.CENTER_VERTICAL);
        setHorizontalGravity(Gravity.CENTER_HORIZONTAL);
        View aSplashSurface = new AndroidSplashSurface(context);
        addView(aSplashSurface);
        ProgressBar aProgressBar = new ProgressBar(context);
        aProgressBar.setIndeterminate(true);
        RelativeLayout.LayoutParams lp = new RelativeLayout.LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT);
        lp.addRule(RelativeLayout.CENTER_IN_PARENT);
        addView(aProgressBar, lp);
    }

    private class AndroidSplashSurface extends SurfaceView implements SurfaceHolder.Callback {
        private Bitmap mBGBitmap;
        private int mHeight;
        private int mWidth;

        public AndroidSplashSurface(Context aContext) {
            super(aContext);
            getHolder().addCallback(this);
            getHolder().setFormat(PixelFormat.RGBA_8888);
            setWillNotDraw(false);
            setVisibility(View.VISIBLE);
            this.mBGBitmap = null;
            this.mWidth = -1;
            this.mHeight = -1;
        }

        @Override
        public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
            invalidate();
        }

        @Override
        public void surfaceCreated(SurfaceHolder holder) {
            invalidate();
        }

        @Override
        public void surfaceDestroyed(SurfaceHolder holder) {
        }

        @Override
        protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
            this.mWidth = View.MeasureSpec.getSize(widthMeasureSpec);
            this.mHeight = View.MeasureSpec.getSize(heightMeasureSpec);
            setMeasuredDimension(this.mWidth, this.mHeight);
            BitmapFactory.Options bfOptions = new BitmapFactory.Options();
            bfOptions.inScaled = false;
            this.mBGBitmap = BitmapFactory.decodeResource(getContext().getResources(), SexyAppFrameworkActivity.GetBestFitSplashImage(this.mWidth, this.mHeight), bfOptions);
            if (this.mBGBitmap != null) {
                this.mBGBitmap.setDensity(Bitmap.DENSITY_NONE);
            } else {
                Log.e("SexyAppFramework", String.format("Could not load splash resource for size: %dx%d", Integer.valueOf(this.mWidth), Integer.valueOf(this.mHeight)));
            }
        }

        @Override
        public void onDraw(Canvas canvas) {
            if (this.mBGBitmap != null) {
                canvas.drawColor(Color.BLACK);
                Paint paint = new Paint();
                paint.setAntiAlias(true);
                paint.setFilterBitmap(true);
                paint.setDither(true);
                int cx = (this.mWidth - this.mBGBitmap.getWidth()) / 2;
                int cy = 0;
                int cyWhitespace = ((int) (((double) this.mHeight) * 0.45d)) - this.mBGBitmap.getHeight();
                if (cyWhitespace > 0) {
                    cy = cyWhitespace / 2;
                }
                // The original draw call uses the default paint.
                canvas.drawBitmap(this.mBGBitmap, cx, cy, null);
            }
        }

        @Override
        public boolean onTouchEvent(MotionEvent InEvent) {
            return true;
        }
    }
}
