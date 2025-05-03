package com.practiwice.timer;

import androidx.annotation.NonNull;
import io.flutter.embedding.android.FlutterActivity;
import io.flutter.embedding.engine.FlutterEngine;
import io.flutter.plugin.common.MethodChannel;
import android.content.Intent;
import android.net.Uri;
import android.provider.Settings;
import android.view.WindowManager;
import android.view.View;
import android.widget.TextView;
import android.view.LayoutInflater;
import android.graphics.PixelFormat;

public class MainActivity extends FlutterActivity {
    private static final String CHANNEL = "com.practiwice.timer/platform";
    private WindowManager windowManager;
    private View floatingView;

    @Override
    public void configureFlutterEngine(@NonNull FlutterEngine flutterEngine) {
        super.configureFlutterEngine(flutterEngine);
        new MethodChannel(flutterEngine.getDartExecutor().getBinaryMessenger(), CHANNEL)
            .setMethodCallHandler((call, result) -> {
                switch (call.method) {
                    case "isFloatingWindowSupported":
                        result.success(true);
                        break;
                    case "createFloatingWindow":
                        floatingView = LayoutInflater.from(this).inflate(R.layout.floating_timer, null);
                        WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                            WindowManager.LayoutParams.WRAP_CONTENT,
                            WindowManager.LayoutParams.WRAP_CONTENT,
                            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                            PixelFormat.TRANSLUCENT
                        );
                        params.gravity = android.view.Gravity.TOP | android.view.Gravity.START;
                        params.x = 0;
                        params.y = 100;
                        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
                        windowManager.addView(floatingView, params);
                        result.success(true);
                        break;
                    case "closeFloatingWindow":
                        if (floatingView != null) {
                            windowManager.removeView(floatingView);
                            floatingView = null;
                        }
                        result.success(true);
                        break;
                    case "updateFloatingWindowTime":
                        String time = call.argument("time");
                        if (floatingView != null) {
                            TextView timerText = floatingView.findViewById(R.id.timer_text);
                            if (timerText != null) {
                                timerText.setText(time);
                            }
                        }
                        result.success(null);
                        break;
                    case "updateFloatingWindowPlayState":
                        boolean isRunning = call.argument("isRunning");
                        // Update button state if needed
                        result.success(null);
                        break;
                    case "hasOverlayPermission":
                        result.success(Settings.canDrawOverlays(this));
                        break;
                    case "requestOverlayPermission":
                        Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                            Uri.parse("package:" + getPackageName()));
                        startActivity(intent);
                        result.success(true);
                        break;
                    case "startTimerService":
                        Intent serviceIntent = new Intent(this, TimerNotificationService.class);
                        serviceIntent.setAction("START_TIMER_SERVICE");
                        serviceIntent.putExtra("sound_path", call.argument("soundPath"));
                        serviceIntent.putExtra("auto_restart", call.argument("autoRestart"));
                        serviceIntent.putExtra("duration_seconds", call.argument("durationSeconds"));
                        startService(serviceIntent);
                        result.success(true);
                        break;
                    case "stopTimerService":
                        stopService(new Intent(this, TimerNotificationService.class));
                        result.success(true);
                        break;
                    case "notifyTimerComplete":
                        Intent completeIntent = new Intent(this, TimerNotificationService.class);
                        completeIntent.setAction("TIMER_COMPLETE");
                        startService(completeIntent);
                        result.success(null);
                        break;
                    default:
                        result.notImplemented();
                }
            });
    }
}