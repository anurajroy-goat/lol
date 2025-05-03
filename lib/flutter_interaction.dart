import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// A class to handle platform-specific functionality through method channels
class PlatformInteraction {
  // Method channel for platform-specific code
  static const MethodChannel _channel = MethodChannel('com.practiwice.timer/platform');
  
  // Event channel for receiving events from native platforms
  static const EventChannel _eventChannel = EventChannel('com.practiwice.timer/events');
  
  // Stream controller for timer events
  static final StreamController<String> _eventController = StreamController<String>.broadcast();
  
  // Initialize platform interaction
  static Future<void> initialize() async {
    // Listen for platform events
    _eventChannel.receiveBroadcastStream().listen((event) {
      _eventController.add(event.toString());
    });
  }
  
  // Get stream of timer events from platform
  static Stream<String> get events => _eventController.stream;
  
  // Check if floating window is supported on this platform
  static Future<bool> isFloatingWindowSupported() async {
    try {
      if (Platform.isAndroid || Platform.isWindows) {
        return await _channel.invokeMethod('isFloatingWindowSupported');
      }
    } catch (e) {
      debugPrint('Error checking floating window support: $e');
    }
    return false;
  }
  
  // Create floating window
  static Future<bool> createFloatingWindow() async {
    try {
      if (Platform.isAndroid || Platform.isWindows) {
        return await _channel.invokeMethod('createFloatingWindow');
      }
    } catch (e) {
      debugPrint('Error creating floating window: $e');
    }
    return false;
  }
  
  // Close floating window
  static Future<bool> closeFloatingWindow() async {
    try {
      if (Platform.isAndroid || Platform.isWindows) {
        return await _channel.invokeMethod('closeFloatingWindow');
      }
    } catch (e) {
      debugPrint('Error closing floating window: $e');
    }
    return false;
  }
  
  // Update timer display in floating window
  static Future<void> updateFloatingWindowTime(String timeText) async {
    try {
      if (Platform.isAndroid || Platform.isWindows) {
        await _channel.invokeMethod('updateFloatingWindowTime', {'time': timeText});
      }
    } catch (e) {
      debugPrint('Error updating floating window time: $e');
    }
  }
  
  // Update play/pause state in floating window
  static Future<void> updateFloatingWindowPlayState(bool isRunning) async {
    try {
      if (Platform.isAndroid || Platform.isWindows) {
        await _channel.invokeMethod('updateFloatingWindowPlayState', {'isRunning': isRunning});
      }
    } catch (e) {
      debugPrint('Error updating floating window play state: $e');
    }
  }
  
  // Request permission for overlay (Android)
  static Future<bool> requestOverlayPermission() async {
    try {
      if (Platform.isAndroid) {
        return await _channel.invokeMethod('requestOverlayPermission');
      }
    } catch (e) {
      debugPrint('Error requesting overlay permission: $e');
    }
    return false;
  }
  
  // Check if overlay permission granted (Android)
  static Future<bool> hasOverlayPermission() async {
    try {
      if (Platform.isAndroid) {
        return await _channel.invokeMethod('hasOverlayPermission');
      }
    } catch (e) {
      debugPrint('Error checking overlay permission: $e');
    }
    return false;
  }
  
  // Start a foreground service for timer (Android)
  static Future<bool> startTimerService({
    required int durationSeconds,
    required bool autoRestart,
    required String soundPath,
    required bool playSoundOnComplete,
  }) async {
    try {
      if (Platform.isAndroid) {
        return await _channel.invokeMethod('startTimerService', {
          'durationSeconds': durationSeconds,
          'autoRestart': autoRestart,
          'soundPath': soundPath,
          'playSoundOnComplete': playSoundOnComplete,
        });
      }
    } catch (e) {
      debugPrint('Error starting timer service: $e');
    }
    return false;
  }
  
  // Stop the foreground service (Android)
  static Future<bool> stopTimerService() async {
    try {
      if (Platform.isAndroid) {
        return await _channel.invokeMethod('stopTimerService');
      }
    } catch (e) {
      debugPrint('Error stopping timer service: $e');
    }
    return false;
  }
  
  // Notify service that timer is complete (Android)
  static Future<void> notifyTimerComplete() async {
    try {
      if (Platform.isAndroid) {
        await _channel.invokeMethod('notifyTimerComplete');
      }
    } catch (e) {
      debugPrint('Error notifying timer complete: $e');
    }
  }
}

/// Widget to integrate with platform-specific components
class PlatformIntegrationWidget extends StatefulWidget {
  final Widget child;
  final Function(String) onPlatformEvent;
  
  const PlatformIntegrationWidget({
    Key? key,
    required this.child,
    required this.onPlatformEvent,
  }) : super(key: key);

  @override
  State<PlatformIntegrationWidget> createState() => _PlatformIntegrationWidgetState();
}

class _PlatformIntegrationWidgetState extends State<PlatformIntegrationWidget> {
  StreamSubscription? _eventSubscription;
  
  @override
  void initState() {
    super.initState();
    _setupEventListener();
  }
  
  void _setupEventListener() {
    _eventSubscription = PlatformInteraction.events.listen((event) {
      widget.onPlatformEvent(event);
    });
  }
  
  @override
  void dispose() {
    _eventSubscription?.cancel();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return widget.child;
  }
}