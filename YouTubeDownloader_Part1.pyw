import sys
import os
import re
import urllib.request
import threading
import subprocess
import json
import platform
import psutil
import datetime
import time
import hashlib
import zipfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox, 
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, 
    QTextEdit, QMessageBox, QCheckBox, QDialog, QDialogButtonBox, 
    QMenuBar, QAction, QTimeEdit, QInputDialog, QFrame, QSystemTrayIcon, 
    QMenu, QFontComboBox, QSlider, QScrollArea
)
from PyQt6.QtGui import QPixmap, QImage, QColor, QPalette, QIcon, QFont, QDesktopServices
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QTime, QTranslator, QLocale
from PyQt6.QtMultimedia import QSound
import vlc
import requests
import matplotlib.pyplot as plt
import numpy as np
from cryptography.fernet import Fernet
import getpass
import socket
import logging
from logging.handlers import RotatingFileHandler
import json
import csv
import pandas as pd
import webbrowser
from datetime import datetime
import pyperclip
import pyautogui

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('youtube_downloader.log', maxBytes=1000000, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0
SUPPORTED_LANGUAGES = {
    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'zh': 'Chinese',
    'hi': 'Hindi', 'ar': 'Arabic', 'ru': 'Russian', 'ja': 'Japanese', 'pt': 'Portuguese'
}
ENCRYPTION_KEY = Fernet.generate_key()
CIPHER = Fernet(ENCRYPTION_KEY)

# Utility Functions
def encrypt_data(data):
    return CIPHER.encrypt(data.encode()).decode()

def decrypt_data(data):
    return CIPHER.decrypt(data.encode()).decode()

def send_email(subject, body, to_email, attachment_path=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = 'your_email@example.com'
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        if attachment_path:
            with open(attachment_path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('your_email@example.com', 'your_password')
            server.send_message(msg)
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")

def generate_report(data, format='csv', output_path='report'):
    if format == 'csv':
        df = pd.DataFrame(data)
        df.to_csv(f"{output_path}.csv", index=False)
    elif format == 'pdf':
        fig, ax = plt.subplots()
        ax.plot(data['time'], data['speed'])
        fig.savefig(f"{output_path}.pdf")
    logger.info(f"Report generated at {output_path}.{format}")

class InfoExtractor(QThread):
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    command_signal = pyqtSignal(str)
    
    def __init__(self, url, is_playlist=True, proxy=None):
        super().__init__()
        self.url = url
        self.is_playlist = is_playlist
        self.proxy = proxy
        self._is_running = True
        
    def stop(self):
        self._is_running = False
        self.terminate()
        self.wait()
        logger.info("InfoExtractor stopped")
        
    def run(self):
        if not self._is_running:
            return
        try:
            self.command_signal.emit("Starting video info extraction...")
            videos = []
            command_base = ["yt-dlp", "--flat-playlist" if self.is_playlist else "--dump-json", "--dump-json", self.url]
            if self.proxy:
                command_base.insert(1, f"--proxy={self.proxy}")
            command = command_base
            self.command_signal.emit(f"Executing command: {' '.join(command)}")
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                creationflags=CREATE_NO_WINDOW
            )
            if self.is_playlist:
                for line in process.stdout:
                    if not self._is_running:
                        process.terminate()
                        return
                    self.command_signal.emit(f"Output: {line.strip()}")
                    try:
                        video_info = json.loads(line)
                        video_data = {
                            'id': video_info.get('id', ''),
                            'title': video_info.get('title', 'Unknown Title'),
                            'thumbnail': self.get_best_thumbnail(video_info),
                            'url': f"https://www.youtube.com/watch?v={video_info.get('id', '')}",
                            'size': video_info.get('filesize', 0),
                            'duration': video_info.get('duration_string', 'N/A'),
                            'uploader': video_info.get('uploader', 'N/A'),
                            'upload_date': video_info.get('upload_date', 'N/A'),
                            'views': video_info.get('view_count', 0),
                            'likes': video_info.get('like_count', 0)
                        }
                        videos.append(video_data)
                    except json.JSONDecodeError:
                        self.command_signal.emit("Warning: Failed to parse JSON line, skipping...")
                        continue
            else:
                output, stderr = process.communicate()
                if stderr:
                    self.command_signal.emit(f"STDERR: {stderr}")
                if process.returncode != 0:
                    self.error_signal.emit(f"Failed to fetch video info: {stderr}")
                    return
                video_info = json.loads(output)
                videos = [{
                    'id': video_info.get('id', ''),
                    'title': video_info.get('title', 'Unknown Title'),
                    'thumbnail': self.get_best_thumbnail(video_info),
                    'url': self.url,
                    'size': video_info.get('filesize', 0),
                    'duration': video_info.get('duration_string', 'N/A'),
                    'uploader': video_info.get('uploader', 'N/A'),
                    'upload_date': video_info.get('upload_date', 'N/A'),
                    'views': video_info.get('view_count', 0),
                    'likes': video_info.get('like_count', 0)
                }]

            if self._is_running:
                self.finished_signal.emit(videos)
        except Exception as e:
            if self._is_running:
                self.error_signal.emit(f"Error fetching info: {str(e)}")
                self.command_signal.emit(f"Exception occurred: {str(e)}")
            logger.error(f"InfoExtractor error: {str(e)}")

    def get_best_thumbnail(self, video_info):
        thumbnails = video_info.get('thumbnails', [])
        if thumbnails:
            for thumb in thumbnails:
                url = thumb.get('url')
                if url and ('maxres' in url or 'sddefault' in url):
                    return url
            return thumbnails[0].get('url', '')
        video_id = video_info.get('id', '')
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

class VideoDownloader(QThread):
    progress_signal = pyqtSignal(str, int, str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    command_signal = pyqtSignal(str)
    
    def __init__(self, video_info, output_path, video_quality, audio_quality, index, audio_only, video_only, naming_template, 
                 speed_limit=None, threads=4, encrypt=False, password=None, proxy=None, start_time=None, end_time=None):
        super().__init__()
        self.video_info = video_info
        self.output_path = output_path
        self.video_quality = video_quality
        self.audio_quality = audio_quality
        self.index = index
        self.audio_only = audio_only
        self.video_only = video_only
        self.naming_template = naming_template
        self.speed_limit = speed_limit
        self.threads = threads
        self.encrypt = encrypt
        self.password = password
        self.proxy = proxy
        self.start_time = start_time
        self.end_time = end_time
        self._is_running = True
        self._is_paused = False
        self.process = None
        self.start_timestamp = time.time()
        
    def stop(self):
        self._is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except (psutil.NoSuchProcess, psutil.TimeoutExpired, subprocess.TimeoutExpired):
                pass
        self.terminate()
        self.wait()
        logger.info(f"VideoDownloader stopped for {self.video_info['title']}")
        
    def pause(self):
        self._is_paused = True
        logger.info(f"Download paused: {self.video_info['title']}")
        
    def resume(self):
        self._is_paused = False
        logger.info(f"Download resumed: {self.video_info['title']}")
        
    def run(self):
        if not self._is_running:
            return
        try:
            self.command_signal.emit("Starting video download process...")
            video_url = self.video_info['url']
            title = self.video_info['title']
            index_str = f"{self.index:02d}"
            safe_filename = re.sub(r'[\\/*?:"<>|]', '', title)
            filename = self.naming_template.replace("[index]", index_str).replace("[title]", safe_filename)
            
            if self.audio_only:
                format_str = f"bestaudio[abr<={self.audio_quality}]"
                output_ext = ".mp3"
            elif self.video_only:
                format_str = f"bestvideo[height<={self.video_quality}]"
                output_ext = ".mp4"
            else:
                format_str = f"bestvideo[height<={self.video_quality}]+bestaudio[abr<={self.audio_quality}]/best[height<={self.video_quality}]"
                output_ext = ".mp4"

            cmd = [
                "yt-dlp",
                "-f", format_str,
                "-o", os.path.join(self.output_path, f"{filename}{output_ext}"),
                "--no-playlist",
                "--progress",
                "--no-warnings",
                "--merge-output-format", "mp4",
                "--recode-video", "mp4",
                "--concurrent-fragments", str(self.threads)
            ]
            if self.proxy:
                cmd.extend(["--proxy", self.proxy])
            if self.speed_limit:
                cmd.extend(["--limit-rate", f"{self.speed_limit}M"])
            if self.start_time and self.end_time:
                cmd.extend(["--download-sections", f"*{self.start_time}-{self.end_time}"])
            cmd.append(video_url)
            
            cmd_str = " ".join(cmd)
            self.command_signal.emit(f"Executing download command: {cmd_str}")
            logger.info(f"Executing download command: {cmd_str}")
            
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=CREATE_NO_WINDOW
            )
            
            for line in self.process.stdout:
                if not self._is_running:
                    self.process.terminate()
                    return
                if self._is_paused:
                    self.process.stdout.flush()
                    while self._is_paused and self._is_running:
                        QThread.msleep(100)
                    continue
                self.command_signal.emit(f"Download Output: {line.strip()}")
                if "% of" in line:
                    try:
                        progress_str = line.strip().split()[1]
                        progress = float(progress_str.replace('%', ''))
                        if progress >= 100:
                            progress = 99
                        speed = ""
                        if "MiB/s" in line:
                            speed = line.strip().split()[-2] + " " + line.strip().split()[-1]
                        self.progress_signal.emit(title, int(progress), speed)
                    except (ValueError, IndexError):
                        self.command_signal.emit("Warning: Failed to parse progress, continuing...")
            
            stderr = self.process.stderr.read()
            if stderr:
                self.command_signal.emit(f"Download STDERR: {stderr}")
                logger.error(f"Download STDERR: {stderr}")
            
            return_code = self.process.wait()
            if return_code != 0:
                if self._is_running:
                    self.error_signal.emit(f"Failed to download {title}: {stderr}")
                return
                
            if self.encrypt:
                output_file = os.path.join(self.output_path, f"{filename}{output_ext}")
                encrypted_file = f"{output_file}.enc"
                with open(output_file, 'rb') as f:
                    data = f.read()
                encrypted_data = CIPHER.encrypt(data)
                with open(encrypted_file, 'wb') as f:
                    f.write(encrypted_data)
                os.remove(output_file)
                logger.info(f"File encrypted: {encrypted_file}")
            
            if self._is_running:
                self.progress_signal.emit(title, 100, "")
                self.finished_signal.emit(title)
                self.command_signal.emit(f"Download completed for: {title}")
                logger.info(f"Download completed for: {title}")
        except Exception as e:
            if self._is_running:
                self.error_signal.emit(f"Error downloading {title}: {str(e)}")
                self.command_signal.emit(f"Exception during download: {str(e)}")
            logger.error(f"VideoDownloader error: {str(e)}")
        finally:
            self.process = None

class PreviewDownloader(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, output_path, proxy=None):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.proxy = proxy
        self._is_running = True
        
    def stop(self):
        self._is_running = False
        self.terminate()
        self.wait()
        logger.info("PreviewDownloader stopped")
        
    def run(self):
        if not self._is_running:
            return
        try:
            cmd = ["yt-dlp", "-f", "bestvideo[height<=360]+bestaudio/best[height<=360]", "--no-playlist", "--get-url"]
            if self.proxy:
                cmd.extend(["--proxy", self.proxy])
            cmd.append(self.url)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=CREATE_NO_WINDOW
            )
            output, stderr = process.communicate()
            if process.returncode != 0:
                self.error_signal.emit(f"Failed to get preview URL: {stderr}")
                logger.error(f"PreviewDownloader error: {stderr}")
                return
            stream_url = output.strip()
            self.finished_signal.emit(stream_url)
        except Exception as e:
            self.error_signal.emit(f"Error fetching preview: {str(e)}")
            logger.error(f"PreviewDownloader error: {str(e)}")

class ClipboardDialog(QDialog):
    def __init__(self, url, parent=None, show_add_too=False, language='en'):
        super().__init__(parent)
        self.setWindowTitle("New YouTube Playlist Detected")
        self.url = url
        self.show_add_too = show_add_too
        self.language = language
        
        layout = QVBoxLayout()
        label = QLabel(f"Copied YouTube playlist:\n{url}\n\nUse this playlist or add it to the list?")
        layout.addWidget(label)
        
        buttons = QDialogButtonBox()
        self.use_button = buttons.addButton("Use This Playlist", QDialogButtonBox.AcceptRole)
        self.add_button = buttons.addButton("Add to List", QDialogButtonBox.ActionRole)
        if self.show_add_too:
            self.add_too_button = buttons.addButton("Add this Playlist too", QDialogButtonBox.ActionRole)
            self.add_too_button.clicked.connect(self.handle_add_too)
        self.cancel_button = buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        logger.info("ClipboardDialog opened")
        
    def handle_add_too(self):
        self.done(2)
        logger.info("Add this Playlist too selected")

class LogsDialog(QDialog):
    def __init__(self, logs, parent=None, language='en'):
        super().__init__(parent)
        self.setWindowTitle("Command Logs")
        self.setGeometry(150, 150, 600, 400)
        
        layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setText(logs)
        layout.addWidget(self.log_text)
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
        
        self.setLayout(layout)
        logger.info("LogsDialog opened")

class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.videos = []
        self.current_download_index = 0
        self.current_view_index = 0
        self.download_threads = []
        self.preview_threads = []
        self.current_downloader = None
        self.info_fetcher = None
        self.total_size = 0
        self.download_queue = []
        self.last_clipboard_text = ""
        self.dialog_open = False
        self.clipboard_timer = QTimer()
        self.clipboard_timer.setSingleShot(True)
        self.clipboard_timer.setInterval(500)
        self.clipboard_timer.timeout.connect(self.process_clipboard_change)
        self.command_logs = ""
        self.playlist_add_count = 0
        self.retry_buttons = {}
        self.scheduled_time = None
        self.schedule_timer = QTimer()
        self.schedule_timer.timeout.connect(self.check_schedule)
        self.vlc_instance = vlc.Instance()
        self.player = None
        self.download_history = []
        self.settings = {}
        self.language = 'en'
        self.translator = QTranslator()
        self.tray_icon = QSystemTrayIcon(self)
        self.performance_data = {'speed': [], 'time': [], 'cpu': [], 'memory': []}
        self.analytics_data = {'downloads': 0, 'errors': 0, 'total_size': 0}
        self.init_settings()
        self.init_ui()
        self.setup_clipboard_monitoring()
        self.check_dependencies()
        self.setup_tray()
        self.start_performance_monitoring()
        logger.info("YouTubeDownloader initialized")

    def init_settings(self):
        default_settings = {
            'theme': 'Dark',
            'font_size': 'medium',
            'language': 'en',
            'speed_limit': None,
            'threads': 4,
            'encrypt_downloads': False,
            'proxy': None,
            'auto_resume': True,
            'download_history': [],
            'custom_shortcuts': {},
            'notifications': True,
            'email_notifications': False,
            'email_address': '',
            'auto_update': True,
            'log_level': 'INFO'
        }
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = default_settings
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f)
        logger.info("Settings initialized")

    def setup_tray(self):
        self.tray_icon.setIcon(QIcon('icon.png'))
        tray_menu = QMenu()
        restore_action = QAction("Restore", self)
        restore_action.triggered.connect(self.show)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(restore_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        logger.info("System tray setup")

    def start_performance_monitoring(self):
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self.monitor_performance)
        self.performance_timer.start(60000)  # Every minute
        logger.info("Performance monitoring started")

    def monitor_performance(self):
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        self.performance_data['cpu'].append(cpu_usage)
        self.performance_data['memory'].append(memory_usage)
        self.performance_data['time'].append(datetime.now().strftime('%H:%M:%S'))
        if cpu_usage > 80 or memory_usage > 80:
            self.tray_icon.showMessage("Resource Alert", "High CPU or memory usage detected!")
        logger.info(f"Performance: CPU {cpu_usage}%, Memory {memory_usage}%")

    def setup_clipboard_monitoring(self):
        clipboard = QApplication.clipboard()
        clipboard.dataChanged.connect(self.on_clipboard_changed)
        logger.info("Clipboard monitoring setup")

    def on_clipboard_changed(self):
        if self.dialog_open:
            return
        self.clipboard_timer.start()

    def process_clipboard_change(self):
        if self.dialog_open:
            return
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text == self.last_clipboard_text:
            return
        
        youtube_regex = r"^(https?://(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|playlist\?list=|shorts/)[^\s]+)"
        playlist_regex = r"^(https?://(www\.)?youtube\.com/playlist\?list=[^\s]+)"
        individual_regex = r"^(https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[^\s]+)"

        if re.match(youtube_regex, text):
            self.last_clipboard_text = text
            if re.match(individual_regex, text) and not re.match(playlist_regex, text):
                self.individual_input.setText(text)
                self.add_individual_video()
            elif re.match(playlist_regex, text):
                self.dialog_open = True
                show_add_too = self.playlist_add_count > 0
                dialog = ClipboardDialog(text, self, show_add_too=show_add_too, language=self.language)
                dialog.add_button.clicked.connect(lambda: self.handle_add_to_list(text))
                result = dialog.exec_()
                if result == QDialog.Accepted:
                    self.url_input.setText(text)
                    self.playlist_add_count += 1
                elif result == 2:
                    self.handle_add_to_list(text)
                    self.playlist_add_count += 1
                self.dialog_open = False
            self.last_clipboard_text = ""
        logger.info(f"Clipboard processed: {text}")

    def handle_add_to_list(self, url):
        self.individual_input.setText(url)
        self.add_individual_video()
        logger.info(f"Added to list: {url}")

    def check_dependencies(self):
        missing = []
        try:
            subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append("yt-dlp")
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append("ffmpeg")
        
        if missing:
            reply = QMessageBox.question(self, "Missing Dependencies", 
                                        f"Missing: {', '.join(missing)}. Install now?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.install_dependencies(missing)
        logger.info(f"Dependencies checked, missing: {missing}")

    def install_dependencies(self, missing):
        self.statusbar.showMessage("Installing dependencies...")
        for dep in missing:
            try:
                if dep == "yt-dlp":
                    subprocess.run(["pip", "install", "yt-dlp"], check=True)
                elif dep == "ffmpeg":
                    if platform.system() == "Windows":
                        subprocess.run(["winget", "install", "ffmpeg"], check=True)
                    else:
                        subprocess.run(["sudo", "apt", "install", "ffmpeg"], check=True)
                self.statusbar.showMessage(f"{dep} installed successfully")
                logger.info(f"{dep} installed successfully")
            except subprocess.CalledProcessError as e:
                QMessageBox.warning(self, "Installation Failed", f"Failed to install {dep}: {str(e)}")
                self.statusbar.showMessage(f"Failed to install {dep}")
                logger.error(f"Failed to install {dep}: {str(e)}")
                return
        QMessageBox.information(self, "Success", "All dependencies installed successfully!")
        logger.info("All dependencies installed")

    def apply_theme(self, theme):
        if theme == "Dark":
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            QApplication.setPalette(palette)
        elif theme == "Light":
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(200, 200, 200))
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(180, 180, 180))
            palette.setColor(QPalette.ButtonText, Qt.black)
            QApplication.setPalette(palette)
        elif theme == "Custom":
            color, ok = QInputDialog.getText(self, "Custom Theme", "Enter background color (hex, e.g., #123456):")
            if ok and color:
                text_color = "#ffffff" if sum(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) < 384 else "#000000"
                self.setStyleSheet(f"""
                    QWidget {{ background-color: {color}; color: {text_color}; }}
                    QPushButton {{ background-color: {color}; color: {text_color}; }}
                    QLineEdit, QComboBox, QTextEdit {{ background-color: {color}; color: {text_color}; }}
                """)
        self.settings['theme'] = theme
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)
        self.statusbar.showMessage(f"Theme applied: {theme}")
        logger.info(f"Theme applied: {theme}")

    def change_language(self, lang_code):
        self.language = lang_code
        self.translator.load(f"translations_{lang_code}.qm")
        QApplication.instance().installTranslator(self.translator)
        self.retranslate_ui()
        self.settings['language'] = lang_code
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)
        logger.info(f"Language changed to: {lang_code}")

    def retranslate_ui(self):
        self.setWindowTitle(self.tr("YouTube Downloader"))
        # Retranslate all UI elements (to be implemented in init_ui)
        logger.info("UI retranslated")

    def init_ui(self):
        self.setWindowTitle(self.tr("YouTube Downloader"))
        self.setGeometry(100, 100, 900, 700)
        self.apply_theme(self.settings['theme'])
        self.change_language(self.settings['language'])
        # To be continued in Part 2
        # Continuing from Part 1 in init_ui
        menubar = self.menuBar()
        menu = menubar.addMenu(self.tr("Menu"))
        
        show_folder_action = QAction(self.tr("Show Download Folder"), self)
        show_folder_action.triggered.connect(self.show_download_folder)
        menu.addAction(show_folder_action)
        
        show_logs_action = QAction(self.tr("Show Logs"), self)
        show_logs_action.triggered.connect(self.show_logs)
        menu.addAction(show_logs_action)
        
        report_issue_action = QAction(self.tr("Report an Issue"), self)
        report_issue_action.triggered.connect(self.report_issue)
        menu.addAction(report_issue_action)
        
        about_action = QAction(self.tr("About"), self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        
        theme_menu = menu.addMenu(self.tr("Theme"))
        dark_action = QAction(self.tr("Dark"), self)
        dark_action.triggered.connect(lambda: self.apply_theme("Dark"))
        light_action = QAction(self.tr("Light"), self)
        light_action.triggered.connect(lambda: self.apply_theme("Light"))
        custom_action = QAction(self.tr("Custom"), self)
        custom_action.triggered.connect(lambda: self.apply_theme("Custom"))
        theme_menu.addAction(dark_action)
        theme_menu.addAction(light_action)
        theme_menu.addAction(custom_action)
        
        language_menu = menu.addMenu(self.tr("Language"))
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            lang_action = QAction(lang_name, self)
            lang_action.triggered.connect(lambda checked, lc=lang_code: self.change_language(lc))
            language_menu.addAction(lang_action)
        
        settings_menu = menu.addMenu(self.tr("Settings"))
        font_size_action = QAction(self.tr("Font Size"), self)
        font_size_action.triggered.connect(self.adjust_font_size)
        settings_menu.addAction(font_size_action)
        
        proxy_action = QAction(self.tr("Set Proxy"), self)
        proxy_action.triggered.connect(self.set_proxy)
        settings_menu.addAction(proxy_action)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Toolbar for quick actions
        toolbar_layout = QHBoxLayout()
        toolbar_download = QPushButton(self.tr("Quick Download"))
        toolbar_download.clicked.connect(self.start_download_all)
        toolbar_clear = QPushButton(self.tr("Quick Clear"))
        toolbar_clear.clicked.connect(self.clear_list)
        toolbar_layout.addWidget(toolbar_download)
        toolbar_layout.addWidget(toolbar_clear)
        main_layout.addLayout(toolbar_layout)
        
        # URL Input Section
        url_layout = QHBoxLayout()
        url_label = QLabel(self.tr("Playlist URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(self.tr("Enter YouTube Playlist URL"))
        self.url_input.textChanged.connect(self.load_info)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        
        # Individual Video Input Section
        individual_layout = QHBoxLayout()
        individual_label = QLabel(self.tr("Add Individual Video:"))
        self.individual_input = QLineEdit()
        self.individual_input.setPlaceholderText(self.tr("Enter YouTube Video URL"))
        self.add_individual_button = QPushButton(self.tr("Add Video"))
        self.add_individual_button.clicked.connect(self.add_individual_video)
        self.batch_import_button = QPushButton(self.tr("Import URLs from File"))
        self.batch_import_button.clicked.connect(self.batch_import_urls)
        individual_layout.addWidget(individual_label)
        individual_layout.addWidget(self.individual_input)
        individual_layout.addWidget(self.add_individual_button)
        individual_layout.addWidget(self.batch_import_button)
        
        # Output and Quality Settings
        folder_layout = QHBoxLayout()
        folder_label = QLabel(self.tr("Output Folder:"))
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText(self.tr("Select output folder"))
        self.browse_button = QPushButton(self.tr("Browse"))
        self.browse_button.clicked.connect(self.browse_folder)
        
        quality_label = QLabel(self.tr("Quality:"))
        self.quality_selector = QComboBox()
        self.quality_selector.addItems(["144", "240", "360", "480", "720", "Custom"])
        self.quality_selector.setCurrentText("480")
        self.quality_selector.currentTextChanged.connect(self.handle_custom_quality)
        
        audio_label = QLabel(self.tr("Audio (kbps):"))
        self.audio_selector = QComboBox()
        self.audio_selector.addItems(["64", "96", "124", "128", "192", "256"])
        self.audio_selector.setCurrentText("124")
        
        self.audio_only_checkbox = QCheckBox(self.tr("Audio Only"))
        self.video_only_checkbox = QCheckBox(self.tr("Video Only"))
        
        self.naming_template_input = QLineEdit()
        self.naming_template_input.setPlaceholderText(self.tr("e.g., [index]_[title]"))
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.browse_button)
        folder_layout.addWidget(quality_label)
        folder_layout.addWidget(self.quality_selector)
        folder_layout.addWidget(audio_label)
        folder_layout.addWidget(self.audio_selector)
        folder_layout.addWidget(self.audio_only_checkbox)
        folder_layout.addWidget(self.video_only_checkbox)
        folder_layout.addWidget(QLabel(self.tr("Naming Template:")))
        folder_layout.addWidget(self.naming_template_input)
        
        # Advanced Download Options
        advanced_layout = QHBoxLayout()
        speed_limit_label = QLabel(self.tr("Speed Limit (MB/s):"))
        self.speed_limit_input = QLineEdit()
        self.speed_limit_input.setPlaceholderText(self.tr("e.g., 1"))
        threads_label = QLabel(self.tr("Threads:"))
        self.threads_input = QLineEdit()
        self.threads_input.setText("4")
        self.encrypt_checkbox = QCheckBox(self.tr("Encrypt Downloads"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(self.tr("Encryption Password"))
        self.password_input.setEchoMode(QLineEdit.Password)
        advanced_layout.addWidget(speed_limit_label)
        advanced_layout.addWidget(self.speed_limit_input)
        advanced_layout.addWidget(threads_label)
        advanced_layout.addWidget(self.threads_input)
        advanced_layout.addWidget(self.encrypt_checkbox)
        advanced_layout.addWidget(self.password_input)
        
        # Schedule Download Section
        schedule_layout = QHBoxLayout()
        schedule_label = QLabel(self.tr("Schedule Download:"))
        self.schedule_time_edit = QTimeEdit()
        self.schedule_time_edit.setDisplayFormat("HH:mm")
        self.schedule_time_edit.setTime(QTime.currentTime())
        self.schedule_button = QPushButton(self.tr("Schedule"))
        self.schedule_button.clicked.connect(self.schedule_download)
        schedule_layout.addWidget(schedule_label)
        schedule_layout.addWidget(self.schedule_time_edit)
        schedule_layout.addWidget(self.schedule_button)
        
        # Current Download Section
        current_label = QLabel(self.tr("Currently Downloading:"))
        current_frame = QWidget()
        current_layout = QHBoxLayout(current_frame)
        
        current_left_layout = QVBoxLayout()
        self.current_thumbnail = QLabel()
        self.current_thumbnail.setFixedSize(240, 180)
        self.current_thumbnail.setScaledContents(True)
        
        nav_layout = QHBoxLayout()
        self.left_button = QPushButton("◄")
        self.left_button.clicked.connect(self.prev_video)
        self.right_button = QPushButton("►")
        self.right_button.clicked.connect(self.next_video)
        self.nav_counter = QLabel("0/0")
        self.preview_button = QPushButton(self.tr("Preview"))
        self.preview_button.clicked.connect(self.preview_video)
        nav_layout.addWidget(self.left_button)
        nav_layout.addWidget(self.nav_counter)
        nav_layout.addWidget(self.right_button)
        nav_layout.addWidget(self.preview_button)
        
        self.preview_frame = QFrame()
        self.preview_frame.setFixedSize(240, 180)
        self.preview_frame.hide()
        
        current_left_layout.addWidget(self.current_thumbnail)
        current_left_layout.addLayout(nav_layout)
        current_left_layout.addWidget(self.preview_frame)
        current_layout.addLayout(current_left_layout)
        
        current_right_layout = QVBoxLayout()
        self.current_title = QLabel()
        self.current_title.setWordWrap(True)
        self.progress_bar = QProgressBar()
        self.command_output = QTextEdit()
        self.command_output.setReadOnly(True)
        
        control_layout = QHBoxLayout()
        self.pause_resume_button = QPushButton(self.tr("Pause"))
        self.pause_resume_button.clicked.connect(self.toggle_pause_resume)
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.clicked.connect(self.cancel_download)
        control_layout.addWidget(self.pause_resume_button)
        control_layout.addWidget(self.cancel_button)
        
        current_right_layout.addWidget(self.current_title)
        current_right_layout.addWidget(self.progress_bar)
        current_right_layout.addWidget(self.command_output)
        current_right_layout.addLayout(control_layout)
        current_layout.addLayout(current_right_layout)
        
        # Video List Section
        playlist_label = QLabel(self.tr("Videos:"))
        self.videos_table = QTableWidget(0, 5)
        self.videos_table.setHorizontalHeaderLabels([self.tr("Index"), self.tr("Thumbnail"), self.tr("Title"), self.tr("Status"), self.tr("Actions")])
        self.videos_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.videos_table.setColumnWidth(0, 50)
        self.videos_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.videos_table.setColumnWidth(1, 120)
        self.videos_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.videos_table.setColumnWidth(3, 100)
        self.videos_table.setColumnWidth(4, 100)
        
        # Download Options
        self.download_button = QPushButton(self.tr("Download All"))
        self.download_button.clicked.connect(self.start_download_all)
        self.download_button.setEnabled(False)
        
        self.clear_button = QPushButton(self.tr("Clear List"))
        self.clear_button.clicked.connect(self.clear_list)
        
        download_options_layout = QHBoxLayout()
        
        specific_layout = QHBoxLayout()
        specific_label = QLabel(self.tr("Download Specific Video:"))
        self.specific_input = QLineEdit()
        self.specific_input.setPlaceholderText(self.tr("e.g., 16"))
        self.specific_download_button = QPushButton(self.tr("Download"))
        self.specific_download_button.clicked.connect(self.start_download_specific)
        self.specific_download_button.setEnabled(False)
        specific_layout.addWidget(specific_label)
        specific_layout.addWidget(self.specific_input)
        specific_layout.addWidget(self.specific_download_button)
        
        range_layout = QHBoxLayout()
        range_label = QLabel(self.tr("Download Range:"))
        self.range_start_input = QLineEdit()
        self.range_start_input.setPlaceholderText(self.tr("e.g., 1"))
        self.range_end_input = QLineEdit()
        self.range_end_input.setPlaceholderText(self.tr("e.g., 17"))
        self.range_download_button = QPushButton(self.tr("Download"))
        self.range_download_button.clicked.connect(self.start_download_range)
        self.range_download_button.setEnabled(False)
        range_layout.addWidget(range_label)
        range_layout.addWidget(self.range_start_input)
        range_layout.addWidget(QLabel(self.tr("to")))
        range_layout.addWidget(self.range_end_input)
        range_layout.addWidget(self.range_download_button)
        
        download_options_layout.addLayout(specific_layout)
        download_options_layout.addLayout(range_layout)
        
        # Analytics Dashboard
        analytics_label = QLabel(self.tr("Analytics Dashboard:"))
        analytics_layout = QHBoxLayout()
        self.download_stats_label = QLabel(self.tr("Downloads: 0 | Errors: 0 | Total Size: 0 MB"))
        self.speed_graph_button = QPushButton(self.tr("View Speed Graph"))
        self.speed_graph_button.clicked.connect(self.show_speed_graph)
        analytics_layout.addWidget(self.download_stats_label)
        analytics_layout.addWidget(self.speed_graph_button)
        
        self.statusbar = self.statusBar()
        
        main_layout.addLayout(url_layout)
        main_layout.addLayout(individual_layout)
        main_layout.addLayout(folder_layout)
        main_layout.addLayout(advanced_layout)
        main_layout.addLayout(schedule_layout)
        main_layout.addWidget(current_label)
        main_layout.addWidget(current_frame)
        main_layout.addWidget(playlist_label)
        main_layout.addWidget(self.videos_table)
        main_layout.addWidget(self.download_button)
        main_layout.addWidget(self.clear_button)
        main_layout.addLayout(download_options_layout)
        main_layout.addWidget(analytics_label)
        main_layout.addLayout(analytics_layout)
        
        self.setup_keyboard_shortcuts()
        self.load_settings()
        self.show()
        logger.info("UI initialized")

    def setup_keyboard_shortcuts(self):
        shortcuts = self.settings.get('custom_shortcuts', {
            'download_all': 'Ctrl+D',
            'clear_list': 'Ctrl+C',
            'pause_resume': 'Ctrl+P',
            'cancel': 'Ctrl+X'
        })
        # Implement shortcut handling (simplified for brevity)
        logger.info("Keyboard shortcuts setup")

    def load_settings(self):
        self.speed_limit_input.setText(str(self.settings.get('speed_limit', '')))
        self.threads_input.setText(str(self.settings.get('threads', 4)))
        self.encrypt_checkbox.setChecked(self.settings.get('encrypt_downloads', False))
        logger.info("Settings loaded")

    def handle_custom_quality(self, quality):
        if quality == "Custom":
            custom_res, ok = QInputDialog.getText(self, self.tr("Custom Resolution"), self.tr("Enter resolution (e.g., 800x600):"))
            if ok and custom_res:
                self.quality_selector.addItem(custom_res)
                self.quality_selector.setCurrentText(custom_res)
        logger.info(f"Quality set to: {quality}")

    def adjust_font_size(self):
        sizes = {'small': 8, 'medium': 10, 'large': 12}
        size, ok = QInputDialog.getItem(self, self.tr("Font Size"), self.tr("Select font size:"), list(sizes.keys()), 1, False)
        if ok:
            self.settings['font_size'] = size
            font = QFont()
            font.setPointSize(sizes[size])
            QApplication.setFont(font)
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f)
        logger.info(f"Font size adjusted to: {size}")

    def set_proxy(self):
        proxy, ok = QInputDialog.getText(self, self.tr("Set Proxy"), self.tr("Enter proxy (e.g., http://proxy:port):"))
        if ok:
            self.settings['proxy'] = proxy if proxy else None
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f)
        logger.info(f"Proxy set to: {proxy}")

    def show_download_folder(self):
        folder = self.folder_input.text().strip()
        if not folder:
            QMessageBox.warning(self, self.tr("Error"), self.tr("No output folder selected"))
            return
        if not os.path.exists(folder):
            QMessageBox.warning(self, self.tr("Error"), self.tr("Output folder does not exist"))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        logger.info("Download folder opened")

    def show_logs(self):
        dialog = LogsDialog(self.command_logs, self, language=self.language)
        dialog.exec_()

    def report_issue(self):
        email_url = "mailto:theswaraj@gmail.com?subject=Issue%20Report%20-%20YouTube%20Downloader"
        QDesktopServices.openUrl(QUrl(email_url))
        logger.info("Report issue email opened")

    def show_about(self):
        about_msg = QMessageBox(self)
        about_msg.setWindowTitle(self.tr("About"))
        about_msg.setText(self.tr("YouTube Downloader\nBuilt by ANURAJ RAI\nAll Rights Reserved 2025"))
        about_msg.exec_()
        logger.info("About dialog shown")

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("Select Output Folder"))
        if folder:
            self.folder_input.setText(folder)
        logger.info(f"Output folder selected: {folder}")

    def batch_import_urls(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select URL File"), "", "Text Files (*.txt)")
        if not file_path:
            return
        try:
            with open(file_path, 'r') as file:
                urls = file.readlines()
            for url in urls:
                url = url.strip()
                if url:
                    self.individual_input.setText(url)
                    self.add_individual_video()
            self.statusbar.showMessage(self.tr(f"Imported {len(urls)} URLs"))
            logger.info(f"Imported {len(urls)} URLs")
        except Exception as e:
            QMessageBox.warning(self, self.tr("Error"), self.tr(f"Failed to import URLs: {str(e)}"))
            logger.error(f"Failed to import URLs: {str(e)}")

    def schedule_download(self):
        self.scheduled_time = self.schedule_time_edit.time()
        self.schedule_timer.start(60000)
        self.statusbar.showMessage(self.tr(f"Download scheduled for {self.scheduled_time.toString('HH:mm')}"))
        logger.info(f"Download scheduled for {self.scheduled_time.toString('HH:mm')}")

    def check_schedule(self):
        current_time = QTime.currentTime()
        if self.scheduled_time and current_time >= self.scheduled_time:
            self.schedule_timer.stop()
            self.scheduled_time = None
            self.start_download_all()
            self.statusbar.showMessage(self.tr("Scheduled download started"))
            logger.info("Scheduled download started")

    def preview_video(self):
        if not self.videos or self.current_view_index >= len(self.videos):
            QMessageBox.warning(self, self.tr("Error"), self.tr("No video selected for preview"))
            return
        video = self.videos[self.current_view_index]
        self.current_thumbnail.hide()
        self.preview_frame.show()
        
        if self.player:
            self.player.stop()
        
        self.preview_downloader = PreviewDownloader(video['url'], self.folder_input.text().strip(), proxy=self.settings.get('proxy'))
        self.preview_downloader.finished_signal.connect(self.play_preview)
        self.preview_downloader.error_signal.connect(self.on_preview_error)
        self.preview_threads.append(self.preview_downloader)
        self.preview_downloader.start()
        logger.info(f"Preview started for: {video['title']}")

    def play_preview(self, stream_url):
        self.player = self.vlc_instance.media_player_new()
        media = self.vlc_instance.media_new(stream_url)
        media.add_option('start-time=0')
        media.add_option('stop-time=10')
        self.player.set_media(media)
        self.player.set_hwnd(self.preview_frame.winId())
        self.player.play()
        logger.info("Playing preview")

    def on_preview_error(self, error_message):
        QMessageBox.warning(self, self.tr("Preview Error"), error_message)
        self.current_thumbnail.show()
        self.preview_frame.hide()
        logger.error(f"Preview error: {error_message}")

    def clear_list(self):
        if self.player:
            self.player.stop()
        self.videos = []
        self.total_size = 0
        self.videos_table.setRowCount(0)
        self.current_view_index = 0
        self.retry_buttons.clear()
        self.download_button.setEnabled(False)
        self.specific_download_button.setEnabled(False)
        self.range_download_button.setEnabled(False)
        self.nav_counter.setText("0/0")
        self.current_thumbnail.clear()
        self.current_thumbnail.show()
        self.preview_frame.hide()
        self.current_title.clear()
        self.progress_bar.setValue(0)
        self.statusbar.showMessage(self.tr("Video list cleared"))
        self.update_navigation()
        logger.info("Video list cleared")

    def load_info(self):
        url = self.url_input.text().strip()
        if not url:
            self.clear_list()
            return
        if self.info_fetcher and self.info_fetcher.isRunning():
            self.info_fetcher.stop()
        self.videos = []
        self.total_size = 0
        self.current_view_index = 0
        self.videos_table.setRowCount(0)
        self.retry_buttons.clear()
        self.statusbar.showMessage(self.tr("Fetching info..."))
        self.download_button.setEnabled(False)
        self.specific_download_button.setEnabled(False)
        self.range_download_button.setEnabled(False)
        self.command_output.clear()
        
        self.info_fetcher = InfoExtractor(url, is_playlist=True, proxy=self.settings.get('proxy'))
        self.info_fetcher.finished_signal.connect(self.on_info_loaded)
        self.info_fetcher.error_signal.connect(self.on_error)
        self.info_fetcher.command_signal.connect(self.update_command_output)
        self.info_fetcher.start()
        logger.info(f"Loading info for URL: {url}")

    def add_individual_video(self):
        url = self.individual_input.text().strip()
        if not url:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Please enter a valid video URL"))
            return
        if self.info_fetcher and self.info_fetcher.isRunning():
            self.info_fetcher.stop()
        
        self.statusbar.showMessage(self.tr("Adding individual video..."))
        self.command_output.clear()
        
        self.info_fetcher = InfoExtractor(url, is_playlist=False, proxy=self.settings.get('proxy'))
        self.info_fetcher.finished_signal.connect(self.append_individual_video)
        self.info_fetcher.error_signal.connect(self.on_error)
        self.info_fetcher.command_signal.connect(self.update_command_output)
        self.info_fetcher.start()
        logger.info(f"Adding individual video: {url}")

    def append_individual_video(self, videos):
        for video in videos:
            if video['url'] in [v['url'] for v in self.videos]:
                continue  # Skip duplicates
            self.videos.append(video)
        
        self.videos_table.setRowCount(len(self.videos))
        
        for i, video in enumerate(self.videos):
            index_item = QTableWidgetItem(str(i + 1))
            index_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.videos_table.setItem(i, 0, index_item)
            
            thumbnail_label = QLabel()
            thumbnail_label.setFixedSize(120, 90)
            thumbnail_label.setScaledContents(True)
            threading.Thread(target=self.load_thumbnail, args=(video['thumbnail'], thumbnail_label)).start()
            self.videos_table.setCellWidget(i, 1, thumbnail_label)
            
            title_item = QTableWidgetItem(video['title'])
            title_item.setToolTip(self.tr(f"Duration: {video['duration']}\nUploader: {video['uploader']}\nUpload Date: {video['upload_date']}\nViews: {video['views']}\nLikes: {video['likes']}"))
            title_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.videos_table.setItem(i, 2, title_item)
            
            status_item = QTableWidgetItem(self.tr("Pending"))
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.videos_table.setItem(i, 3, status_item)
            
            actions_layout = QHBoxLayout()
            retry_button = QPushButton(self.tr("Retry"))
            retry_button.setVisible(False)
            retry_button.clicked.connect(lambda checked, idx=i: self.retry_download(idx))
            self.retry_buttons[i] = retry_button
            actions_layout.addWidget(retry_button)
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            self.videos_table.setCellWidget(i, 4, actions_widget)
            
            self.total_size += video.get('size', 0)
        
        total_size_mb = self.total_size / (1024 * 1024) if self.total_size else 0
        self.statusbar.showMessage(self.tr(f"Added video | Total {len(self.videos)} videos | Estimated total size: {total_size_mb:.2f} MB"))
        self.download_button.setEnabled(True)
        self.specific_download_button.setEnabled(True)
        self.range_download_button.setEnabled(True)
        self.current_view_index = 0
        self.update_navigation()
        self.individual_input.clear()
        logger.info(f"Individual video appended, total videos: {len(self.videos)}")

    def on_info_loaded(self, videos):
        for video in videos:
            if video['url'] in [v['url'] for v in self.videos]:
                continue  # Skip duplicates
            self.videos.append(video)
        
        self.videos_table.setRowCount(len(self.videos))
        
        for i, video in enumerate(self.videos):
            index_item = QTableWidgetItem(str(i + 1))
            index_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.videos_table.setItem(i, 0, index_item)
            
            thumbnail_label = QLabel()
            thumbnail_label.setFixedSize(120, 90)
            thumbnail_label.setScaledContents(True)
            threading.Thread(target=self.load_thumbnail, args=(video['thumbnail'], thumbnail_label)).start()
            self.videos_table.setCellWidget(i, 1, thumbnail_label)
            
            title_item = QTableWidgetItem(video['title'])
            title_item.setToolTip(self.tr(f"Duration: {video['duration']}\nUploader: {video['uploader']}\nUpload Date: {video['upload_date']}\nViews: {video['views']}\nLikes: {video['likes']}"))
            title_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.videos_table.setItem(i, 2, title_item)
            
            status_item = QTableWidgetItem(self.tr("Pending"))
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.videos_table.setItem(i, 3, status_item)
            
            actions_layout = QHBoxLayout()
            retry_button = QPushButton(self.tr("Retry"))
            retry_button.setVisible(False)
            retry_button.clicked.connect(lambda checked, idx=i: self.retry_download(idx))
            self.retry_buttons[i] = retry_button
            actions_layout.addWidget(retry_button)
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            self.videos_table.setCellWidget(i, 4, actions_widget)
            
            self.total_size += video.get('size', 0)
        
        total_size_mb = self.total_size / (1024 * 1024) if self.total_size else 0
        self.statusbar.showMessage(self.tr(f"Loaded {len(videos)} videos | Estimated total size: {total_size_mb:.2f} MB"))
        self.download_button.setEnabled(True)
        self.specific_download_button.setEnabled(True)
        self.range_download_button.setEnabled(True)
        self.current_view_index = 0
        self.update_navigation()
        logger.info(f"Info loaded, total videos: {len(self.videos)}")

    def load_thumbnail(self, url, label):
        if not url:
            label.setText(self.tr("No thumbnail"))
            return
        try:
            data = urllib.request.urlopen(url).read()
            image = QImage()
            image.loadFromData(data)
            label.setPixmap(QPixmap.fromImage(image))
        except Exception as e:
            label.setText(self.tr("Error"))
            logger.error(f"Failed to load thumbnail: {str(e)}")

    def update_navigation(self):
        if not self.videos:
            self.nav_counter.setText("0/0")
            self.current_thumbnail.clear()
            self.current_thumbnail.show()
            self.preview_frame.hide()
            self.left_button.setEnabled(False)
            self.right_button.setEnabled(False)
            return
        
        self.nav_counter.setText(f"{self.current_view_index + 1}/{len(self.videos)}")
        self.left_button.setEnabled(self.current_view_index > 0)
        self.right_button.setEnabled(self.current_view_index < len(self.videos) - 1)
        
        thumbnail_widget = self.videos_table.cellWidget(self.current_view_index, 1)
        if thumbnail_widget and thumbnail_widget.pixmap():
            self.current_thumbnail.setPixmap(thumbnail_widget.pixmap())
        else:
            self.current_thumbnail.setText(self.tr("No thumbnail"))
        logger.info(f"Navigation updated to index: {self.current_view_index}")

    def prev_video(self):
        if self.current_view_index > 0:
            self.current_view_index -= 1
            self.update_navigation()
            if self.player:
                self.player.stop()
                self.current_thumbnail.show()
                self.preview_frame.hide()
        logger.info("Navigated to previous video")

    def next_video(self):
        if self.current_view_index < len(self.videos) - 1:
            self.current_view_index += 1
            self.update_navigation()
            if self.player:
                self.player.stop()
                self.current_thumbnail.show()
                self.preview_frame.hide()
        logger.info("Navigated to next video")

    def retry_download(self, index):
        output_folder = self.folder_input.text().strip()
        if not output_folder:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Select an output folder"))
            return
        self.download_queue = [index]
        self.current_download_index = 0
        self.current_view_index = index
        self.videos_table.item(index, 3).setText(self.tr("Pending"))
        self.retry_buttons[index].setVisible(False)
        self.download_button.setEnabled(False)
        self.specific_download_button.setEnabled(False)
        self.range_download_button.setEnabled(False)
        self.download_next_video(output_folder)
        logger.info(f"Retrying download for index: {index}")

    def start_download_all(self):
        output_folder = self.folder_input.text().strip()
        if not output_folder:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Select an output folder"))
            return
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        if not self.videos:
            QMessageBox.warning(self, self.tr("Error"), self.tr("No videos to download"))
            return
        
        self.download_button.setEnabled(False)
        self.specific_download_button.setEnabled(False)
        self.range_download_button.setEnabled(False)
        self.download_queue = list(range(len(self.videos)))
        self.current_download_index = 0
        self.current_view_index = 0
        for i in range(self.videos_table.rowCount()):
            self.videos_table.item(i, 3).setText(self.tr("Pending"))
            self.retry_buttons[i].setVisible(False)
        self.download_next_video(output_folder)
        logger.info("Started downloading all videos")

    def start_download_specific(self):
        output_folder = self.folder_input.text().strip()
        if not output_folder:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Select an output folder"))
            return
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        if not self.videos:
            QMessageBox.warning(self, self.tr("Error"), self.tr("No videos to download"))
            return
        
        try:
            video_num = int(self.specific_input.text()) - 1
            if video_num < 0 or video_num >= len(self.videos):
                QMessageBox.warning(self, self.tr("Error"), self.tr(f"Video number must be between 1 and {len(self.videos)}"))
                return
            self.download_queue = [video_num]
            self.current_download_index = 0
            self.current_view_index = video_num
            for i in range(self.videos_table.rowCount()):
                self.videos_table.item(i, 3).setText(self.tr("Pending"))
                self.retry_buttons[i].setVisible(False)
            self.download_button.setEnabled(False)
            self.specific_download_button.setEnabled(False)
            self.range_download_button.setEnabled(False)
            self.download_next_video(output_folder)
            logger.info(f"Started downloading specific video: {video_num}")
        except ValueError:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Please enter a valid number"))
            logger.error("Invalid input for specific download")

    def start_download_range(self):
        output_folder = self.folder_input.text().strip()
        if not output_folder:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Select an output folder"))
            return
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        if not self.videos:
            QMessageBox.warning(self, self.tr("Error"), self.tr("No videos to download"))
            return
        
        try:
            start = int(self.range_start_input.text()) - 1
            end = int(self.range_end_input.text())
            if start < 0 or end > len(self.videos) or start >= end:
                QMessageBox.warning(self, self.tr("Error"), self.tr(f"Range must be between 1 and {len(self.videos)}, and start must be less than end"))
                return
            self.download_queue = list(range(start, end))
            self.current_download_index = 0
            self.current_view_index = start
            for i in range(self.videos_table.rowCount()):
                self.videos_table.item(i, 3).setText(self.tr("Pending"))
                self.retry_buttons[i].setVisible(False)
            self.download_button.setEnabled(False)
            self.specific_download_button.setEnabled(False)
            self.range_download_button.setEnabled(False)
            self.download_next_video(output_folder)
            logger.info(f"Started downloading range: {start} to {end}")
        except ValueError:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Please enter valid numbers"))
            logger.error("Invalid input for range download")

    def download_next_video(self, output_folder):
        if self.current_download_index >= len(self.download_queue):
            self.statusbar.showMessage(self.tr(f"All downloads completed! | Total size downloaded: {self.total_size / (1024 * 1024):.2f} MB"))
            self.download_button.setEnabled(True)
            self.specific_download_button.setEnabled(True)
            self.range_download_button.setEnabled(True)
            self.pause_resume_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            
            completion_msg = QMessageBox(self)
            completion_msg.setWindowTitle(self.tr("Download Complete"))
            completion_msg.setText(self.tr("All downloads have been completed successfully!"))
            if platform.system() == "Windows":
                QSound.play("C:/Windows/Media/tada.wav")
            completion_msg.exec_()
            
            self.analytics_data['downloads'] += len(self.download_queue)
            self.update_analytics()
            
            if self.settings.get('email_notifications'):
                send_email(
                    "Download Complete",
                    f"All downloads completed. Total size: {self.total_size / (1024 * 1024):.2f} MB",
                    self.settings.get('email_address')
                )
            return
        
        video_index = self.download_queue[self.current_download_index]
        video = self.videos[video_index]
        self.videos_table.item(video_index, 3).setText(self.tr("Downloading"))
        self.current_view_index = video_index
        self.update_navigation()
        
        self.current_title.setText(video['title'])
        self.progress_bar.setValue(0)
        self.command_output.clear()
        self.pause_resume_button.setText(self.tr("Pause"))
        self.pause_resume_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        
        naming_template = self.naming_template_input.text().strip() or "[index]_[title]"
        speed_limit = self.speed_limit_input.text().strip()
        speed_limit = float(speed_limit) if speed_limit else None
        threads = int(self.threads_input.text()) if self.threads_input.text() else 4
        encrypt = self.encrypt_checkbox.isChecked()
        password = self.password_input.text() if encrypt else None
        
        self.current_downloader = VideoDownloader(
            video, output_folder, self.quality_selector.currentText(), 
            self.audio_selector.currentText(), video_index + 1,
            self.audio_only_checkbox.isChecked(), self.video_only_checkbox.isChecked(),
            naming_template, speed_limit, threads, encrypt, password, self.settings.get('proxy')
        )
        self.current_downloader.progress_signal.connect(self.update_progress)
        self.current_downloader.finished_signal.connect(lambda _: self.on_video_completed(output_folder))
        self.current_downloader.error_signal.connect(self.on_error)
        self.current_downloader.command_signal.connect(self.update_command_output)
        self.download_threads.append(self.current_downloader)
        self.current_downloader.start()
        logger.info(f"Downloading video: {video['title']}")

    def update_progress(self, title, progress, speed=""):
        if title == self.current_title.text():
            self.progress_bar.setValue(progress)
            self.performance_data['speed'].append(float(speed.split()[0]) if speed else 0)
            self.statusbar.showMessage(self.tr(f"Downloading: {title} - {progress}% | Speed: {speed} | Total size: {self.total_size / (1024 * 1024):.2f} MB"))
            logger.info(f"Progress updated: {title} - {progress}%")

    def update_command_output(self, message):
        self.command_logs += message + "\n"
        self.command_output.append(message)
        self.command_output.verticalScrollBar().setValue(self.command_output.verticalScrollBar().maximum())
        logger.info(f"Command output: {message}")

    def on_video_completed(self, output_folder):
        video_index = self.download_queue[self.current_download_index]
        video = self.videos[video_index]
        self.videos_table.item(video_index, 3).setText(self.tr("Completed"))
        self.download_history.append({
            'title': video['title'],
            'url': video['url'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        self.current_download_index += 1
        self.download_next_video(output_folder)
        logger.info(f"Video completed: {video['title']}")

    def on_error(self, error_message):
        QMessageBox.warning(self, self.tr("Error"), error_message)
        self.statusbar.showMessage(self.tr(f"Error: {error_message} | Total size: {self.total_size / (1024 * 1024):.2f} MB"))
        self.download_button.setEnabled(True)
        self.specific_download_button.setEnabled(True)
        self.range_download_button.setEnabled(True)
        self.pause_resume_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.analytics_data['errors'] += 1
        self.update_analytics()
        if self.current_download_index < len(self.download_queue):
            video_index = self.download_queue[self.current_download_index]
            self.videos_table.item(video_index, 3).setText(self.tr("Failed"))
            self.retry_buttons[video_index].setVisible(True)
            self.current_download_index += 1
            self.download_next_video(self.folder_input.text())
        logger.error(f"Download error: {error_message}")

    def toggle_pause_resume(self):
        if self.current_downloader:
            if self.pause_resume_button.text() == self.tr("Pause"):
                self.current_downloader.pause()
                self.pause_resume_button.setText(self.tr("Resume"))
                self.statusbar.showMessage(self.tr(f"Download paused | Total size: {self.total_size / (1024 * 1024):.2f} MB"))
            else:
                self.current_downloader.resume()
                self.pause_resume_button.setText(self.tr("Pause"))
                self.statusbar.showMessage(self.tr(f"Download resumed | Total size: {self.total_size / (1024 * 1024):.2f} MB"))
            logger.info(f"Pause/Resume toggled")

    def cancel_download(self):
        if self.current_downloader:
            self.current_downloader.stop()
            video_index = self.download_queue[self.current_download_index]
            self.videos_table.item(video_index, 3).setText(self.tr("Cancelled"))
            self.current_download_index += 1
            self.download_next_video(self.folder_input.text())
            self.statusbar.showMessage(self.tr(f"Download cancelled | Total size: {self.total_size / (1024 * 1024):.2f} MB"))
            logger.info("Download cancelled")

    def show_speed_graph(self):
        plt.figure(figsize=(8, 6))
        plt.plot(self.performance_data['time'], self.performance_data['speed'], 'b-', label=self.tr('Download Speed (MB/s)'))
        plt.title(self.tr('Download Speed Over Time'))
        plt.xlabel(self.tr('Time'))
        plt.ylabel(self.tr('Speed (MB/s)'))
        plt.grid(True)
        plt.legend()
        plt.savefig('speed_graph.png')
        QDesktopServices.openUrl(QUrl.fromLocalFile('speed_graph.png'))
        logger.info("Speed graph displayed")

    def update_analytics(self):
        total_size_mb = self.analytics_data['total_size'] / (1024 * 1024)
        self.download_stats_label.setText(
            self.tr(f"Downloads: {self.analytics_data['downloads']} | Errors: {self.analytics_data['errors']} | Total Size: {total_size_mb:.2f} MB")
        )
        logger.info("Analytics updated")

    def closeEvent(self, event):
        if self.info_fetcher and self.info_fetcher.isRunning():
            self.info_fetcher.stop()
        for thread in self.download_threads:
            if thread.isRunning():
                thread.stop()
        for thread in self.preview_threads:
            if thread.isRunning():
                thread.stop()
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.name().lower() in ['ffmpeg.exe', 'yt-dlp.exe']:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        self.download_threads.clear()
        self.preview_threads.clear()
        if self.player:
            self.player.stop()
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)
        event.accept()
        logger.info("Application closed")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeDownloader()
    sys.exit(app.exec_())
