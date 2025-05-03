import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:vibration/vibration.dart';
import 'dart:async';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import 'flutter_interaction.dart';
import 'platform_specifics.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize platform interaction
  await PlatformInteraction.initialize();

  // Initialize notifications
  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
      FlutterLocalNotificationsPlugin();
  const AndroidInitializationSettings initializationSettingsAndroid =
      AndroidInitializationSettings('@mipmap/ic_launcher');
  final InitializationSettings initializationSettings =
      InitializationSettings(android: initializationSettingsAndroid);
  await flutterLocalNotificationsPlugin.initialize(initializationSettings);

  // Load preferences
  final prefs = await SharedPreferences.getInstance();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => TimerSettings(prefs)),
      ],
      child: const PracTwiceApp(),
    ),
  );
}

class PracTwiceApp extends StatelessWidget {
  const PracTwiceApp({super.key});

  @override
  Widget build(BuildContext context) {
    final timerSettings = Provider.of<TimerSettings>(context);

    return MaterialApp(
      title: 'PracTwice',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
        textTheme: GoogleFonts.robotoTextTheme(
          Theme.of(context).textTheme,
        ),
      ),
      darkTheme: ThemeData.dark().copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.deepPurple,
          brightness: Brightness.dark,
        ),
      ),
      themeMode: timerSettings.isDarkMode ? ThemeMode.dark : ThemeMode.light,
      home: const TimerScreen(),
    );
  }
}

class TimerSettings extends ChangeNotifier {
  final SharedPreferences _prefs;

  Duration _timerDuration = const Duration(minutes: 3);
  bool _autoRestart = false;
  bool _playSoundOnComplete = true;
  String _selectedSoundPath = 'assets/sounds/timer_end.wav';
  String? _customSoundPath;
  String? _customWallpaperPath;
  bool _isFloatingMode = false;
  bool _isDarkMode = false;

  TimerSettings(this._prefs) {
    _loadSettings();
  }

  Duration get timerDuration => _timerDuration;
  bool get autoRestart => _autoRestart;
  bool get playSoundOnComplete => _playSoundOnComplete;
  String get soundPath => _customSoundPath ?? _selectedSoundPath;
  String? get wallpaperPath => _customWallpaperPath;
  bool get isFloatingMode => _isFloatingMode;
  bool get isDarkMode => _isDarkMode;

  Future<void> _loadSettings() async {
    _timerDuration = Duration(seconds: _prefs.getInt('timerSeconds') ?? 180);
    _autoRestart = _prefs.getBool('autoRestart') ?? false;
    _playSoundOnComplete = _prefs.getBool('playSoundOnComplete') ?? true;
    _selectedSoundPath =
        _prefs.getString('selectedSoundPath') ?? 'assets/sounds/timer_end.wav';
    _customSoundPath = _prefs.getString('customSoundPath');
    _customWallpaperPath = _prefs.getString('customWallpaperPath');
    _isDarkMode = _prefs.getBool('isDarkMode') ?? false;
    notifyListeners();
  }

  void setTimerDuration(Duration duration) {
    _timerDuration = duration;
    _prefs.setInt('timerSeconds', duration.inSeconds);
    notifyListeners();
  }

  void setAutoRestart(bool value) {
    _autoRestart = value;
    _prefs.setBool('autoRestart', value);
    notifyListeners();
  }

  void setPlaySoundOnComplete(bool value) {
    _playSoundOnComplete = value;
    _prefs.setBool('playSoundOnComplete', value);
    notifyListeners();
  }

  void setSelectedSound(String path) {
    _selectedSoundPath = path;
    _prefs.setString('selectedSoundPath', path);
    notifyListeners();
  }

  void setCustomSound(String? path) {
    _customSoundPath = path;
    if (path != null) {
      _prefs.setString('customSoundPath', path);
    } else {
      _prefs.remove('customSoundPath');
    }
    notifyListeners();
  }

  void setCustomWallpaper(String? path) {
    _customWallpaperPath = path;
    if (path != null) {
      _prefs.setString('customWallpaperPath', path);
    } else {
      _prefs.remove('customWallpaperPath');
    }
    notifyListeners();
  }

  void setFloatingMode(bool value) {
    _isFloatingMode = value;
    notifyListeners();
  }

  void setDarkMode(bool value) {
    _isDarkMode = value;
    _prefs.setBool('isDarkMode', value);
    notifyListeners();
  }
}

class TimerScreen extends StatefulWidget {
  const TimerScreen({super.key});

  @override
  State<TimerScreen> createState() => _TimerScreenState();
}

class _TimerScreenState extends State<TimerScreen> with WidgetsBindingObserver {
  final AudioPlayer _audioPlayer = AudioPlayer();
  Timer? _timer;
  Duration _remainingTime = const Duration(minutes: 3);
  bool _isRunning = false;
  final FlutterLocalNotificationsPlugin _notificationsPlugin =
      FlutterLocalNotificationsPlugin();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final settings = Provider.of<TimerSettings>(context, listen: false);
      setState(() {
        _remainingTime = settings.timerDuration;
      });
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _audioPlayer.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused && _isRunning) {
      PlatformInteraction.startTimerService(
        durationSeconds: _remainingTime.inSeconds,
        autoRestart:
            Provider.of<TimerSettings>(context, listen: false).autoRestart,
        soundPath: Provider.of<TimerSettings>(context, listen: false).soundPath,
        playSoundOnComplete: Provider.of<TimerSettings>(context, listen: false)
            .playSoundOnComplete,
      );
    }
  }

  void _startTimer() {
    if (_timer != null) {
      _timer!.cancel();
    }

    setState(() {
      _isRunning = true;
    });

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        if (_remainingTime.inSeconds > 0) {
          _remainingTime = _remainingTime - const Duration(seconds: 1);
          if (Provider.of<TimerSettings>(context, listen: false)
              .isFloatingMode) {
            FloatingWindowManager.updateFloatingWindowTime(
                _formatDuration(_remainingTime));
            PlatformInteraction.updateFloatingWindowPlayState(_isRunning);
          }
        } else {
          _onTimerComplete();
        }
      });
    });
  }

  void _pauseTimer() {
    if (_timer != null) {
      _timer!.cancel();
      _timer = null;
    }

    setState(() {
      _isRunning = false;
    });

    if (Provider.of<TimerSettings>(context, listen: false).isFloatingMode) {
      PlatformInteraction.updateFloatingWindowPlayState(_isRunning);
    }
  }

  void _resetTimer() {
    if (_timer != null) {
      _timer!.cancel();
      _timer = null;
    }

    final settings = Provider.of<TimerSettings>(context, listen: false);
    setState(() {
      _isRunning = false;
      _remainingTime = settings.timerDuration;
    });

    if (settings.isFloatingMode) {
      FloatingWindowManager.updateFloatingWindowTime(
          _formatDuration(_remainingTime));
      PlatformInteraction.updateFloatingWindowPlayState(_isRunning);
    }
  }

  void _onTimerComplete() {
    final settings = Provider.of<TimerSettings>(context, listen: false);

    if (settings.playSoundOnComplete && !settings.autoRestart) {
      _playCompletionSound();
    }

    Vibration.vibrate(duration: 1000);

    _showNotification();

    if (settings.autoRestart) {
      setState(() {
        _remainingTime = settings.timerDuration;
        _startTimer();
      });
    } else {
      setState(() {
        _isRunning = false;
        _timer?.cancel();
        _timer = null;
      });
    }
  }

  Future<void> _playCompletionSound() async {
    final settings = Provider.of<TimerSettings>(context, listen: false);
    final soundPath = settings.soundPath;

    try {
      if (soundPath.startsWith('assets/')) {
        await _audioPlayer
            .play(AssetSource(soundPath.replaceFirst('assets/', '')));
      } else {
        await _audioPlayer.play(DeviceFileSource(soundPath));
      }
    } catch (e) {
      await _audioPlayer.play(AssetSource('sounds/timer_end.wav'));
    }
  }

  void _showNotification() async {
    const AndroidNotificationDetails androidDetails =
        AndroidNotificationDetails(
      'timer_channel',
      'Timer Notifications',
      channelDescription: 'Notifications for timer completion',
      importance: Importance.high,
      priority: Priority.high,
      playSound: false,
    );

    const NotificationDetails platformDetails =
        NotificationDetails(android: androidDetails);

    await _notificationsPlugin.show(
      0,
      'Timer Complete',
      'Your timer has finished!',
      platformDetails,
    );
  }

  void _showTimerSetupBottomSheet() {
    final settings = Provider.of<TimerSettings>(context, listen: false);

    int minutes = settings.timerDuration.inMinutes;
    int seconds = settings.timerDuration.inSeconds % 60;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom,
                left: 16,
                right: 16,
                top: 16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Set Timer Duration',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 80,
                        child: TextField(
                          keyboardType: TextInputType.number,
                          textAlign: TextAlign.center,
                          decoration: const InputDecoration(
                            labelText: 'Minutes',
                            border: OutlineInputBorder(),
                          ),
                          controller:
                              TextEditingController(text: minutes.toString()),
                          onChanged: (value) {
                            minutes = int.tryParse(value) ?? 0;
                          },
                        ),
                      ),
                      const SizedBox(width: 20),
                      const Text(
                        ':',
                        style: TextStyle(
                            fontSize: 24, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(width: 20),
                      SizedBox(
                        width: 80,
                        child: TextField(
                          keyboardType: TextInputType.number,
                          textAlign: TextAlign.center,
                          decoration: const InputDecoration(
                            labelText: 'Seconds',
                            border: OutlineInputBorder(),
                          ),
                          controller:
                              TextEditingController(text: seconds.toString()),
                          onChanged: (value) {
                            seconds = int.tryParse(value) ?? 0;
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: () {
                      final totalSeconds = minutes * 60 + seconds;
                      final newDuration = Duration(seconds: totalSeconds);

                      settings.setTimerDuration(newDuration);
                      setState(() {
                        _remainingTime = newDuration;
                      });

                      Navigator.pop(context);
                    },
                    child: const Text('Set Timer'),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            );
          },
        );
      },
    );
  }

  String _formatDuration(Duration duration) {
    String twoDigits(int n) => n.toString().padLeft(2, '0');
    final minutes = twoDigits(duration.inMinutes);
    final seconds = twoDigits(duration.inSeconds.remainder(60));
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    final settings = Provider.of<TimerSettings>(context);

    return PlatformIntegrationWidget(
      onPlatformEvent: (event) {
        if (event == 'playPause') {
          _isRunning ? _pauseTimer() : _startTimer();
        } else if (event == 'reset') {
          _resetTimer();
        } else if (event == 'fullscreen') {
          settings.setFloatingMode(false);
          FloatingWindowManager.closeFloatingWindow();
        }
      },
      child: Scaffold(
        body: Container(
          decoration: BoxDecoration(
            image: settings.wallpaperPath != null
                ? DecorationImage(
                    image: FileImage(File(settings.wallpaperPath!)),
                    fit: BoxFit.cover,
                  )
                : null,
          ),
          child: SafeArea(
            child: settings.isFloatingMode
                ? _buildFloatingModeTimer()
                : _buildFullScreenTimer(settings),
          ),
        ),
        floatingActionButton: settings.isFloatingMode
            ? null
            : FloatingActionButton(
                onPressed: () async {
                  if (Platform.isAndroid) {
                    if (!await PlatformInteraction.hasOverlayPermission()) {
                      await PlatformInteraction.requestOverlayPermission();
                    }
                  }
                  if (await PlatformInteraction.isFloatingWindowSupported()) {
                    await FloatingWindowManager.createFloatingWindow();
                    settings.setFloatingMode(true);
                  }
                },
                tooltip: 'Enter Floating Mode',
                child: const Icon(Icons.picture_in_picture),
              ),
      ),
    );
  }

  Widget _buildFullScreenTimer(TimerSettings settings) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        AppBar(
          title: const Text('PracTwice'),
          actions: [
            IconButton(
              icon: Icon(
                  settings.isDarkMode ? Icons.light_mode : Icons.dark_mode),
              onPressed: () {
                settings.setDarkMode(!settings.isDarkMode);
              },
            ),
            IconButton(
              icon: const Icon(Icons.settings),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                      builder: (context) => const SettingsScreen()),
                );
              },
            ),
          ],
        ),
        Expanded(
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                GestureDetector(
                  onTap: _showTimerSetupBottomSheet,
                  child: Text(
                    _formatDuration(_remainingTime),
                    style: const TextStyle(
                      fontSize: 80,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(height: 40),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton(
                      onPressed: _isRunning ? _pauseTimer : _startTimer,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 32,
                          vertical: 16,
                        ),
                      ),
                      child: Text(_isRunning ? 'Pause' : 'Start'),
                    ),
                    const SizedBox(width: 20),
                    ElevatedButton(
                      onPressed: _resetTimer,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 32,
                          vertical: 16,
                        ),
                      ),
                      child: const Text('Reset'),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                SwitchListTile(
                  title: const Text('Auto Restarter'),
                  subtitle: const Text(
                      'Automatically restart timer after completion'),
                  value: settings.autoRestart,
                  onChanged: (value) {
                    settings.setAutoRestart(value);
                  },
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFloatingModeTimer() {
    return Align(
      alignment: Alignment.topRight,
      child: Container(
        width: 150,
        height: 100,
        margin: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface.withOpacity(0.9),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 10,
              spreadRadius: 1,
            ),
          ],
        ),
        child: Stack(
          children: [
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _formatDuration(_remainingTime),
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      IconButton(
                        icon: Icon(_isRunning ? Icons.pause : Icons.play_arrow),
                        onPressed: _isRunning ? _pauseTimer : _startTimer,
                        iconSize: 18,
                      ),
                      IconButton(
                        icon: const Icon(Icons.replay),
                        onPressed: _resetTimer,
                        iconSize: 18,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Positioned(
              top: 0,
              right: 0,
              child: IconButton(
                icon: const Icon(Icons.fullscreen),
                iconSize: 18,
                onPressed: () {
                  Provider.of<TimerSettings>(context, listen: false)
                      .setFloatingMode(false);
                  FloatingWindowManager.closeFloatingWindow();
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = Provider.of<TimerSettings>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          ListTile(
            title: const Text('Choose Background'),
            subtitle: const Text('Select a custom wallpaper'),
            leading: const Icon(Icons.wallpaper),
            onTap: () => _pickWallpaper(context),
          ),
          ListTile(
            title: const Text('Choose Sound'),
            subtitle: const Text('Select notification sound'),
            leading: const Icon(Icons.music_note),
            onTap: () => _showSoundPicker(context),
          ),
          SwitchListTile(
            title: const Text('Play Sound on Completion'),
            value: settings.playSoundOnComplete,
            onChanged: (value) {
              settings.setPlaySoundOnComplete(value);
            },
          ),
          SwitchListTile(
            title: const Text('Auto Restarter'),
            subtitle:
                const Text('Automatically restart timer after completion'),
            value: settings.autoRestart,
            onChanged: (value) {
              settings.setAutoRestart(value);
            },
          ),
          SwitchListTile(
            title: const Text('Dark Mode'),
            value: settings.isDarkMode,
            onChanged: (value) {
              settings.setDarkMode(value);
            },
          ),
          ListTile(
            title: const Text('Custom Duration'),
            subtitle: const Text('Set a custom timer duration'),
            leading: const Icon(Icons.timer),
            onTap: () {
              Navigator.pop(context);
              final timerScreenState =
                  context.findAncestorStateOfType<_TimerScreenState>();
              if (timerScreenState != null) {
                timerScreenState._showTimerSetupBottomSheet();
              }
            },
          ),
        ],
      ),
    );
  }

  Future<void> _pickWallpaper(BuildContext context) async {
    final settings = Provider.of<TimerSettings>(context, listen: false);

    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(source: ImageSource.gallery);

    if (pickedFile != null) {
      settings.setCustomWallpaper(pickedFile.path);
    }
  }

  void _showSoundPicker(BuildContext context) {
    final settings = Provider.of<TimerSettings>(context, listen: false);

    showModalBottomSheet(
      context: context,
      builder: (context) {
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('Default Sounds'),
              onTap: () {
                _showDefaultSoundsDialog(context);
              },
            ),
            ListTile(
              title: const Text('Choose Custom Sound'),
              onTap: () async {
                Navigator.pop(context);

                FilePickerResult? result = await FilePicker.platform.pickFiles(
                  type: FileType.audio,
                );

                if (result != null && result.files.single.path != null) {
                  settings.setCustomSound(result.files.single.path);
                }
              },
            ),
          ],
        );
      },
    );
  }

  void _showDefaultSoundsDialog(BuildContext context) {
    final settings = Provider.of<TimerSettings>(context, listen: false);

    Navigator.pop(context);

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Choose Default Sound'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildSoundOption(context, 'Timer End',
                    'assets/sounds/timer_end.wav', settings),
                _buildSoundOption(context, 'Childhood',
                    'assets/sounds/childhood.wav', settings),
                _buildSoundOption(
                    context, 'Morning', 'assets/sounds/morning.wav', settings),
                _buildSoundOption(
                    context, 'Melody', 'assets/sounds/melody.wav', settings),
                _buildSoundOption(context, 'Over the Horizon 2012',
                    'assets/sounds/over_the_horizon_2012.mp3', settings),
                _buildSoundOption(context, 'Over the Horizon 2017',
                    'assets/sounds/over_the_horizon_17.mp3', settings),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context);
              },
              child: const Text('Cancel'),
            ),
          ],
        );
      },
    );
  }

  Widget _buildSoundOption(
      BuildContext context, String name, String path, TimerSettings settings) {
    return ListTile(
      title: Text(name),
      trailing: IconButton(
        icon: const Icon(Icons.play_arrow),
        onPressed: () async {
          final player = AudioPlayer();
          await player.play(AssetSource(path.replaceFirst('assets/', '')));
        },
      ),
      onTap: () {
        settings.setSelectedSound(path);
        settings.setCustomSound(null);
        Navigator.pop(context);
      },
    );
  }
}
