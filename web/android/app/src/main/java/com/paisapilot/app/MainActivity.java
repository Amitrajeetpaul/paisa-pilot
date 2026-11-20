package com.paisapilot.app;

import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebSettings;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(UsageAccessPlugin.class);
        super.onCreate(savedInstanceState);

        // Edge-to-edge full screen with matching status & navigation bar colours
        Window window = getWindow();
        WindowCompat.setDecorFitsSystemWindows(window, false);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            window.clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_STATUS);
            window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
            window.setStatusBarColor(Color.parseColor("#0F172A"));
            window.setNavigationBarColor(Color.parseColor("#14152E"));
        }

        WindowInsetsControllerCompat insetsController =
                WindowCompat.getInsetsController(window, window.getDecorView());
        if (insetsController != null) {
            insetsController.setAppearanceLightStatusBars(false);
            insetsController.setAppearanceLightNavigationBars(false);
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        lockWebViewSettings();
    }

    @Override
    public void onStart() {
        super.onStart();
        lockWebViewSettings();
    }

    /**
     * Locks the WebView text zoom strictly to 100%.
     * On Android, system-level font scaling (or OEM zoom) inflates the WebView's text,
     * causing lines to wrap onto a second line and distorting UI cards and buttons.
     */
    private void lockWebViewSettings() {
        if (getBridge() != null && getBridge().getWebView() != null) {
            WebSettings settings = getBridge().getWebView().getSettings();
            settings.setTextZoom(100);
            settings.setUseWideViewPort(true);
            settings.setLoadWithOverviewMode(true);
        }
    }
}
