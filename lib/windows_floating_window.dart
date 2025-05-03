import 'package:flutter/services.dart';

class WindowsFloatingWindow {
  static const MethodChannel _channel = MethodChannel('com.practiwice.floating_window');

  static Future<bool> createFloatingWindow() async {
    return await _channel.invokeMethod('createFloatingWindow');
  }

  static Future<void> closeFloatingWindow() async {
    await _channel.invokeMethod('closeFloatingWindow');
  }

  static Future<void> updateFloatingWindowTime(String timeText) async {
    await _channel.invokeMethod('updateTime', {'time': timeText});
  }

  static Future<void> updateFloatingWindowPlayState(bool isRunning) async {
    await _channel.invokeMethod('updatePlayPauseButton', {'isRunning': isRunning});
  }
}