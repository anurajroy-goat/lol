package com.practiwice.timer;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;
import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import java.io.IOException;

public class TimerNotificationService extends Service {
    private static final String CHANNEL_ID = "timer_notification_channel";
    private static final int NOTIFICATION_ID = 1001;
    
    private MediaPlayer mediaPlayer;
    private PowerManager.WakeLock wakeLock;
    private String soundPath;
    private boolean autoRestart;
    private int timerDurationSeconds;
    
    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        
        PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "PracTwice::TimerWakeLock"
        );
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getAction();
            if (action != null) {
                switch (action) {
                    case "START_TIMER_SERVICE":
                        soundPath = intent.getStringExtra("sound_path");
                        autoRestart = intent.getBooleanExtra("auto_restart", false);
                        timerDurationSeconds = intent.getIntExtra("duration_seconds", 180);
                        startForeground(NOTIFICATION_ID, createNotification("Timer Running"));
                        break;
                    case "TIMER_COMPLETE":
                        handleTimerComplete();
                        break;
                    case "STOP_SERVICE":
                        stopTimerService();
                        break;
                }
            }
        }
        
        return START_STICKY;
    }
    
    private void handleTimerComplete() {
        NotificationManager notificationManager = 
            (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        notificationManager.notify(
            NOTIFICATION_ID, 
            createNotification("Timer Complete!")
        );
        
        if (soundPath != null && !soundPath.isEmpty()) {
            playNotificationSound();
        }
        
        vibrate();
        
        if (autoRestart) {
            // Restart logic would communicate back to Flutter
        }
    }
    
    private void playNotificationSound() {
        try {
            if (mediaPlayer != null) {
                if (mediaPlayer.isPlaying()) {
                    mediaPlayer.stop();
                }
                mediaPlayer.release();
            }
            
            mediaPlayer = new MediaPlayer();
            
            if (soundPath.startsWith("asset://")) {
                String assetPath = soundPath.substring(8);
                // Requires Flutter asset handling
            } else {
                mediaPlayer.setDataSource(this, Uri.parse(soundPath));
            }
            
            mediaPlayer.setAudioAttributes(
                new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build()
            );
            
            mediaPlayer.setLooping(false);
            mediaPlayer.prepare();
            mediaPlayer.start();
            
            if (!wakeLock.isHeld()) {
                wakeLock.acquire(60*1000);
            }
            
            mediaPlayer.setOnCompletionListener(mp -> {
                if (wakeLock.isHeld()) {
                    wakeLock.release();
                }
            });
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    private void vibrate() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            VibratorManager vibratorManager = 
                (VibratorManager) getSystemService(Context.VIBRATOR_MANAGER_SERVICE);
            if (vibratorManager != null) {
                Vibrator vibrator = vibratorManager.getDefaultVibrator();
                vibrator.vibrate(
                    VibrationEffect.createOneShot(1000, VibrationEffect.DEFAULT_AMPLITUDE)
                );
            }
        } else {
            Vibrator vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (vibrator != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(
                        VibrationEffect.createOneShot(1000, VibrationEffect.DEFAULT_AMPLITUDE)
                    );
                } else {
                    vibrator.vibrate(1000);
                }
            }
        }
    }
    
    private void stopTimerService() {
        if (mediaPlayer != null) {
            if (mediaPlayer.isPlaying()) {
                mediaPlayer.stop();
            }
            mediaPlayer.release();
            mediaPlayer = null;
        }
        
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
        
        stopForeground(true);
        stopSelf();
    }
    
    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Timer Notifications",
                NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("Notifications for timer completion");
            channel.enableLights(true);
            channel.setLightColor(Color.BLUE);
            channel.setVibrationPattern(new long[]{0, 1000});
            channel.enableVibration(true);
            
            NotificationManager notificationManager = getSystemService(NotificationManager.class);
           vérification notificationManager.createNotificationChannel(channel);
        }
    }
    
    private Notification createNotification(String contentText) {
        Intent intent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_IMMUTABLE
        );
        
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_timer)
            .setContentTitle("PracTwice Timer")
            .setContentText(contentText)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true);
        
        if (contentText.equals("Timer Complete!")) {
            Intent stopIntent = new Intent(this, TimerNotificationService.class);
            stopIntent.setAction("STOP_SERVICE");
            PendingIntent stopPendingIntent = PendingIntent.getService(
                this, 0, stopIntent, PendingIntent.FLAG_IMMUTABLE
            );
            
            builder.addAction(
                R.drawable.ic_stop,
                "Stop",
                stopPendingIntent
            );
            
            if (autoRestart) {
                Intent restartIntent = new Intent(this, TimerNotificationService.class);
                restartIntent.setAction("RESTART_TIMER");
                PendingIntent restartPendingIntent = PendingIntent.getService(
                    this, 0, restartIntent, PendingIntent.FLAG_IMMUTABLE
                );
                
                builder.addAction(
                    R.drawable.ic_restart,
                    "Restart Now",
                    restartPendingIntent
                );
            }
        }
        
        return builder.build();
    }
    
    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        
        if (mediaPlayer != null) {
            mediaPlayer.release();
            mediaPlayer = null;
        }
        
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
    }
}