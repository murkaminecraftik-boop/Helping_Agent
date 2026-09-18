import sys
import os
import shutil
import webbrowser
import threading
import keyboard
import re
import ctypes
import urllib.request
import urllib.parse
import json
import psutil
import winreg
import subprocess
import time
import socket
import math
import base64
import hashlib
import uuid

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QListWidget, QListWidgetItem, QLabel, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QKeySequence, QShortcut, QFont


# --------------------------------------------------------------------------
# HIGH-PERFORMANCE DISK CRAWLER
# --------------------------------------------------------------------------
class SearchWorker(QObject):
    match_found = pyqtSignal(str, str)
    finished = pyqtSignal()

    EXCLUDE_DIRS = {
        '$recycle.bin', 'system volume information', 'windows', 'node_modules',
        '.git', '__pycache__', 'appdata', 'programdata', 'vendor'
    }

    def __init__(self, query, search_type="general", new_item=None, extra_item=None, is_file=False):
        super().__init__()
        self.query = query.lower()
        self.search_type = search_type
        self.new_item = new_item
        self.extra_item = extra_item
        self.is_file = is_file
        self._is_running = True

    def run(self):
        match_count = 0
        max_matches = 30  # Optimized for smaller UI

        user_home = os.path.expanduser("~")
        drives = [user_home] + [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                                if os.path.exists(f"{d}:\\") and not user_home.startswith(f"{d}:\\")]

        for root_dir in drives:
            if not self._is_running or match_count >= max_matches:
                break

            for root, dirs, files in os.walk(root_dir, topdown=True, onerror=lambda e: None):
                if not self._is_running or match_count >= max_matches:
                    break

                dirs[:] = [d for d in dirs if d.lower() not in self.EXCLUDE_DIRS and not d.startswith('.')]

                if self.search_type == "general":
                    for name in dirs + files:
                        if self.query in name.lower():
                            self.match_found.emit("file", os.path.join(root, name))
                            match_count += 1
                            if match_count >= max_matches: break

                elif self.search_type == "find_parent_dir":
                    for name in dirs:
                        if self.query == name.lower():
                            self.match_found.emit("parent_dir_match", os.path.join(root, name))
                            match_count += 1
                            if match_count >= max_matches: break

                elif self.search_type == "find_item_to_delete":
                    items_to_check = files if self.is_file else dirs
                    for name in items_to_check:
                        if self.query == name.lower():
                            self.match_found.emit("delete_match", os.path.join(root, name))
                            match_count += 1
                            if match_count >= max_matches: break

                elif self.search_type == "find_item_to_rename":
                    items_to_check = files if self.is_file else dirs
                    for name in items_to_check:
                        if self.query == name.lower():
                            self.match_found.emit("rename_match", os.path.join(root, name))
                            match_count += 1
                            if match_count >= max_matches: break

        self.finished.emit()

    def stop(self):
        self._is_running = False


# --------------------------------------------------------------------------
# WEATHER FETCHING WORKER
# --------------------------------------------------------------------------
class WeatherWorker(QObject):
    weather_found = pyqtSignal(str, list)

    def __init__(self, city, is_forecast=False):
        super().__init__()
        self.city = city
        self.is_forecast = is_forecast

    def run(self):
        try:
            url = f"https://wttr.in/{urllib.parse.quote(self.city)}?format=j1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                current = data['current_condition'][0]
                temp_c = current['temp_C']
                desc = current['weatherDesc'][0]['value']
                if not self.is_forecast:
                    self.weather_found.emit(f"🌤️ Weather in {self.city.title()}: {temp_c}°C, {desc}", [])
                else:
                    forecast_list = []
                    for day in data['weather']:
                        forecast_list.append(
                            f"📅 {day['date']}: {day['mintempC']}°C - {day['maxtempC']}°C ({day['hourly'][4]['weatherDesc'][0]['value']})")
                    self.weather_found.emit(f"🌤️ Weekly Forecast for {self.city.title()}:", forecast_list)
        except Exception:
            self.weather_found.emit("❌ Could not retrieve weather details.", [])


# --------------------------------------------------------------------------
# STREAMING GROQ CLOUD AI WORKER
# --------------------------------------------------------------------------
class FreeCloudAIWorker(QObject):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, prompt, api_key="YOUR_FREE_GROQ_API_KEY"):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key
        self._is_running = True

    def run(self):
        full_text = ""
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a fast desktop launcher assistant. Answer in 1 short sentence. Skip robotic greetings."},
                    {"role": "user", "content": self.prompt}
                ],
                "temperature": 0.5,
                "max_tokens": 80,
                "stream": True
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                for line in response:
                    if not self._is_running:
                        break
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_json = json.loads(data_str)
                            delta = chunk_json["choices"][0]["delta"]
                            if "content" in delta:
                                token = delta["content"]
                                full_text += token
                                self.chunk_received.emit(full_text)
                        except json.JSONDecodeError:
                            pass

            self.finished.emit(full_text.strip())
        except Exception as e:
            self.finished.emit("❌ Free AI temporarily unavailable. Check API key and connection.")

    def stop(self):
        self._is_running = False


# --------------------------------------------------------------------------
# ZERO-SUBPROCESS SOCKET PING WORKER
# --------------------------------------------------------------------------
class PingWorker(QObject):
    ping_updated = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def run(self):
        while self._is_running:
            start_time = time.perf_counter()
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.0)
                s.connect(("8.8.8.8", 53))
                s.close()
                latency = int((time.perf_counter() - start_time) * 1000)
                self.ping_updated.emit(latency)
            except Exception:
                self.ping_updated.emit(-1)

            for _ in range(15):
                if not self._is_running: break
                time.sleep(0.1)

    def stop(self):
        self._is_running = False


# --------------------------------------------------------------------------
# GLOBAL HOTKEY LISTENER
# --------------------------------------------------------------------------
class HotkeyListener(QObject):
    triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        keyboard.add_hotkey('alt+q', self.emit_trigger)

    def emit_trigger(self): self.triggered.emit()


# --------------------------------------------------------------------------
# ANIMATED BASE WIDGET
# --------------------------------------------------------------------------
class AnimatedWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(250)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def show_animated(self):
        self.setWindowOpacity(0.0)
        self.show()
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

    def hide_animated(self):
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.windowOpacity())
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.start()
        QTimer.singleShot(250, self.hide)


# --------------------------------------------------------------------------
# HUD & OVERLAY COMPONENTS (Minimalist Redesign)
# --------------------------------------------------------------------------
class FPSPingWidget(AnimatedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(180, 40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)

        self.hud_label = QLabel("FPS: --  •  PING: -- ms", self)
        self.hud_label.setStyleSheet(
            "font-size: 13px; font-family: 'Segoe UI', 'Roboto', Arial; color: #4ade80; background: rgba(24, 24, 27, 220); border-radius: 8px; font-weight: 600; padding: 6px 12px;")
        layout.addWidget(self.hud_label)

        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self.calculate_realtime_performance)
        self.last_time = time.perf_counter()
        self.frames = 0
        self.current_fps = 0
        self.ping_string = "--"

        self.ping_worker = None
        self.ping_thread = None
        self.position_window()

    def position_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 20)

    def showEvent(self, event):
        super().showEvent(event)
        self.last_time = time.perf_counter()
        self.frames = 0
        self.fps_timer.start(16)
        self.ping_worker = PingWorker()
        self.ping_thread = threading.Thread(target=self.ping_worker.run, daemon=True)
        self.ping_worker.ping_updated.connect(self.process_ping_payload)
        self.ping_thread.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.fps_timer.stop()
        if self.ping_worker:
            self.ping_worker.stop()

    def process_ping_payload(self, ms):
        self.ping_string = "ERR" if ms == -1 else f"{ms}ms"

    def calculate_realtime_performance(self):
        self.frames += 1
        now = time.perf_counter()
        delta = now - self.last_time
        if delta >= 0.5:
            self.current_fps = int(self.frames / delta)
            self.frames = 0
            self.last_time = now
        self.hud_label.setText(f"FPS: {self.current_fps}  •  PING: {self.ping_string}")
        self.update()


class TimerWidget(AnimatedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(160, 80)

        self.main_container = QWidget(self)
        self.main_container.setStyleSheet(
            "background-color: rgba(24, 24, 27, 230); border: 1px solid #3f3f46; border-radius: 12px;")

        layout = QVBoxLayout(self.main_container)
        layout.setContentsMargins(12, 8, 12, 12)

        top_layout = QHBoxLayout()
        self.title_label = QLabel("⏱️ Timer", self.main_container)
        self.title_label.setStyleSheet(
            "font-family: 'Segoe UI', Arial; font-weight: 600; font-size: 12px; color: #a1a1aa; border: none; background: transparent;")
        self.close_btn = QPushButton("✕", self.main_container)
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setStyleSheet(
            "background: transparent; color: #f87171; border: none; font-size: 12px; font-weight: bold;")
        self.close_btn.clicked.connect(self.hide_animated)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.close_btn)
        layout.addLayout(top_layout)

        self.time_label = QLabel("00:00", self.main_container)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet(
            "font-size: 28px; font-family: 'Segoe UI', Arial; font-weight: bold; color: #4ade80; border: none; background: transparent;")
        layout.addWidget(self.time_label)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.main_container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.remaining = 0
        self.position_window()

    def position_window(self):
        self.move(20, 20)

    def start_timer(self, seconds):
        self.remaining = seconds
        self.update_display()
        self.time_label.setStyleSheet(
            "font-size: 28px; font-family: 'Segoe UI', Arial; font-weight: bold; color: #4ade80; border: none; background: transparent;")
        self.timer.start(1000)
        self.show_animated()
        self.position_window()

    def update_time(self):
        if self.remaining > 0:
            self.remaining -= 1
            self.update_display()
        else:
            self.timer.stop()
            self.time_label.setText("00:00")
            self.time_label.setStyleSheet(
                "font-size: 28px; font-family: 'Segoe UI', Arial; font-weight: bold; color: #f87171; border: none; background: transparent;")
            ctypes.windll.user32.MessageBeep(0xFFFFFFFF)

    def update_display(self):
        m, s = divmod(self.remaining, 60)
        h, m = divmod(m, 60)
        self.time_label.setText(f"{h:02}:{m:02}:{s:02}" if h > 0 else f"{m:02}:{s:02}")


class StatsWidget(AnimatedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(200, 110)
        self.main_container = QWidget(self)
        self.main_container.setStyleSheet(
            "background-color: rgba(24, 24, 27, 230); color: #ececec; border: 1px solid #3f3f46; border-radius: 12px; font-family: 'Segoe UI', Arial;")
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(12, 10, 12, 12)
        top_layout = QHBoxLayout()
        self.title_label = QLabel("📊 System", self.main_container)
        self.title_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #a1a1aa; border: none; background: transparent;")
        self.close_btn = QPushButton("✕", self.main_container)
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setStyleSheet(
            "background: transparent; color: #f87171; border: none; font-size: 12px; font-weight: bold;")
        self.close_btn.clicked.connect(self.hide_animated)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.close_btn)
        container_layout.addLayout(top_layout)
        self.cpu_label = QLabel("CPU: 0%", self.main_container)
        self.cpu_label.setStyleSheet("font-size: 13px; font-weight: 500; border: none; background: transparent;")
        self.ram_label = QLabel("RAM: 0%", self.main_container)
        self.ram_label.setStyleSheet("font-size: 13px; font-weight: 500; border: none; background: transparent;")
        container_layout.addWidget(self.cpu_label)
        container_layout.addWidget(self.ram_label)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.main_container)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)
        self.position_window()

    def position_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(20, screen.height() - self.height() - 60)

    def update_stats(self):
        self.cpu_label.setText(f"CPU Utilization: {psutil.cpu_percent()}%")
        self.ram_label.setText(f"RAM Utilization: {psutil.virtual_memory().percent}%")


# --------------------------------------------------------------------------
# MAIN FLOW HUD LAUNCHER ENGINE (Minimalist Redesign)
# --------------------------------------------------------------------------
class FlowWidget(QWidget):

    def get_list_height(self):
        return self.results_list.height()

    def set_list_height(self, val):
        self.results_list.setFixedHeight(val)

    listHeight = pyqtProperty(int, fget=get_list_height, fset=set_list_height)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        self.layout.setSpacing(8)

        self.input_box = QLineEdit(self)
        self.input_box.setMinimumWidth(600)
        self.input_box.setStyleSheet("""
            QLineEdit {
                font-family: 'Segoe UI', 'Roboto', Arial;
                font-size: 20px;
                padding: 12px 18px;
                border-radius: 12px;
                background-color: rgba(24, 24, 27, 240);
                color: #f4f4f5;
                border: 1px solid #3f3f46;
            }
            QLineEdit:focus { border: 1px solid #52525b; }
        """)
        self.layout.addWidget(self.input_box)
        self.input_box.installEventFilter(self)

        self.results_list = QListWidget(self)
        self.results_list.setMinimumWidth(600)
        self.results_list.setFixedHeight(0)
        self.results_list.setMouseTracking(True)
        self.results_list.setStyleSheet("""
            QListWidget {
                font-family: 'Segoe UI', 'Roboto', Arial;
                font-size: 15px;
                background-color: rgba(24, 24, 27, 240);
                color: #e4e4e7;
                border-radius: 12px;
                border: 1px solid #3f3f46;
                padding: 6px;
                outline: none;
            }
            QListWidget::item { padding: 10px 12px; border-radius: 8px; margin-bottom: 2px; }
            QListWidget::item:hover { background-color: rgba(63, 63, 70, 150); }
            QListWidget::item:selected { background-color: rgba(82, 82, 91, 180); color: #ffffff; }
        """)
        self.results_list.hide()
        self.layout.addWidget(self.results_list)

        self.input_box.textChanged.connect(self.on_text_changed)
        self.input_box.returnPressed.connect(self.execute_top_result)
        self.results_list.itemClicked.connect(self.execute_clicked_item)
        self.results_list.entered.connect(self.on_item_hovered)

        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_selected_to_clipboard)

        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(200)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.list_anim = QPropertyAnimation(self, b"listHeight")
        self.list_anim.setDuration(300)
        self.list_anim.setEasingCurve(QEasingCurve.Type.OutExpo)

        self.search_worker = None
        self.search_thread = None
        self.weather_worker = None
        self.weather_thread = None
        self.ai_worker = None
        self.ai_thread = None

        self.ai_debounce_timer = QTimer(self)
        self.ai_debounce_timer.setSingleShot(True)
        self.ai_debounce_timer.timeout.connect(self.execute_ai_query)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_ai_loading_animation)
        self.ai_dot_count = 0

        self.installed_apps = {}
        self.stats_widget = StatsWidget()
        self.timer_widget = TimerWidget()
        self.fps_widget = FPSPingWidget()

        self.win_settings_map = {
            "bluetooth": "bluetooth", "wifi": "network-wifi", "network": "network-status",
            "display": "display", "sound": "sound", "audio": "sound", "update": "windowsupdate",
            "privacy": "privacy", "apps": "appsfeatures", "power": "powersleep",
            "battery": "batterysaver", "personalization": "personalization-background",
            "accounts": "accounts", "time": "dateandtime", "language": "regionlanguage",
            "storage": "storagesense", "mouse": "mousetouchpad", "keyboard": "keyboard"
        }

        self.fast_ai_replies = {
            r"^(hello|hi|hey|greetings)(?:\s+there)?[\!\.\?]*$": "Hello! How can I assist you today?",
            r"^(bye|goodbye|cya|see ya)[\!\.\?]*$": "Goodbye! Have a productive day!",
            r"^how (are you|was your day)[\!\.\?]*$": "I'm running smoothly! Ready to help you get things done.",
            r"^(thanks|thank you)[\!\.\?]*$": "You're very welcome!",
            r"^who are you[\!\.\?]*$": "I am your fast, local desktop assistant.",
            r"^(good morning|good afternoon|good evening)[\!\.\?]*$": "Greetings! What's on the agenda?",
            r"^(ok|okay|cool|awesome|great)[\!\.\?]*$": "Got it! Let me know if you need anything else."
        }

        self.index_apps()
        self.center_window()
        self.hotkey_listener = HotkeyListener()
        self.hotkey_listener.triggered.connect(self.toggle_visibility)

    def is_spotify_installed(self):
        if any("spotify" in k for k in self.installed_apps.keys()):
            return True
        try:
            key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "spotify")
            winreg.CloseKey(key)
            return True
        except Exception:
            pass
        paths = [
            os.path.join(os.environ.get("APPDATA", ""), "Spotify", "Spotify.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", "Spotify.exe")
        ]
        return any(os.path.exists(p) for p in paths)

    def get_action_priority(self, action_data):
        if not action_data:
            return 2
        if action_data.startswith("copy_text:") or action_data == "info:ai_thinking":
            return 0
        if (action_data.startswith("info:") or action_data.startswith("action:") or
                action_data.startswith("winsettings:") or action_data.startswith("app:") or
                action_data.startswith("web:") or
                action_data.startswith("create_") or action_data.startswith("delete_") or
                action_data.startswith("rename_") or action_data.startswith("sys:") or
                action_data.startswith("dev:")):
            return 1
        return 2

    def add_result(self, display_text, action_data):
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, action_data)

        target_priority = self.get_action_priority(action_data)
        insertion_index = self.results_list.count()

        for i in range(self.results_list.count()):
            existing_action = self.results_list.item(i).data(Qt.ItemDataRole.UserRole)
            if target_priority < self.get_action_priority(existing_action):
                insertion_index = i
                break

        self.results_list.insertItem(insertion_index, item)
        if self.results_list.currentRow() == -1 and self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def copy_selected_to_clipboard(self):
        item = self.results_list.currentItem()
        if item:
            action_data = item.data(Qt.ItemDataRole.UserRole) or ""
            text_to_copy = item.text()
            if action_data.startswith("copy_text:"):
                text_to_copy = action_data[10:]
            elif action_data.startswith("file:"):
                text_to_copy = action_data[5:]
            QApplication.clipboard().setText(text_to_copy)

    # --------------------------------------------------------------------------
    # COMMAND & PARSER EXTENSIONS
    # --------------------------------------------------------------------------
    def parse_math_command(self, text):
        clean_text = text.strip().lower()
        pct_match = re.search(r"^(\d+(?:\.\d+)?)\%\s+of\s+(\d+(?:\.\d+)?)$", clean_text)
        if pct_match:
            pct, val = float(pct_match.group(1)), float(pct_match.group(2))
            res = (pct / 100.0) * val
            return f"🧮 {pct}% of {val} = {res:g}"
        if re.match(r"^[\d\.\+\-\*\/\(\)\^\s\%]+$", clean_text) and any(op in clean_text for op in "+-*/^"):
            try:
                expr = clean_text.replace("^", "**")
                allowed_names = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "pi": math.pi,
                                 "e": math.e}
                result = eval(expr, {"__builtins__": None}, allowed_names)
                return f"🧮 {clean_text} = {result:g}"
            except Exception:
                pass
        return None

    def parse_dev_command(self, text):
        clean = text.strip()
        low = clean.lower()
        if low == "uuid":
            new_id = str(uuid.uuid4())
            return (f"🔑 Generated UUID: {new_id}", f"copy_text:{new_id}")
        elif low.startswith("b64enc "):
            encoded = base64.b64encode(clean[7:].encode()).decode()
            return (f"🔐 Base64 Encoded: {encoded}", f"copy_text:{encoded}")
        elif low.startswith("b64dec "):
            try:
                decoded = base64.b64decode(clean[7:].encode()).decode()
                return (f"🔓 Base64 Decoded: {decoded}", f"copy_text:{decoded}")
            except Exception:
                return ("❌ Invalid Base64 String", "info:error")
        elif low.startswith("hash "):
            val = clean[5:]
            md5_val = hashlib.md5(val.encode()).hexdigest()
            return (f"🔑 MD5: {md5_val}", f"copy_text:{md5_val}")
        return None

    def parse_timer_command(self, text):
        match = re.search(
            r"(?:set\s+(?:a\s+)?)?timer\s+(?:for\s+)?(\d+(?:\.\d+)?)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours)",
            text.lower())
        if match:
            val = float(match.group(1))
            unit = match.group(2)
            if unit.startswith('s'):
                return int(val)
            elif unit.startswith('m'):
                return int(val * 60)
            elif unit.startswith('h'):
                return int(val * 3600)
        return None

    def parse_file_op_command(self, text):
        text_lower = text.lower().strip()
        op = None
        cmd = ""
        if text_lower.startswith("create ") or text_lower.startswith("add "):
            op = "create"
            cmd = text[7:].strip() if text_lower.startswith("create ") else text[4:].strip()
        elif text_lower.startswith("delete ") or text_lower.startswith("remove "):
            op = "delete"
            cmd = text[7:].strip() if text_lower.startswith("delete ") else text[7:].strip()
        elif text_lower.startswith("rename ") or text_lower.startswith("edit "):
            op = "rename"
            cmd = text[7:].strip() if text_lower.startswith("rename ") else text[5:].strip()

        if not op: return None

        target = None
        match_target = re.search(r"\s+(?:in|inside\s+of|inside|from)\s+(.+)$", cmd, re.IGNORECASE)
        if match_target:
            target = match_target.group(1).strip()
            cmd = cmd[:match_target.start()].strip()

        if op == "rename":
            to_match = re.search(r"\s+to\s+(.+)$", cmd, re.IGNORECASE)
            if not to_match: return None
            old_part = cmd[:to_match.start()].strip()
            new_part = to_match.group(1).strip()
            is_file = "file" in old_part.lower() or "file" in new_part.lower() or "." in old_part or "." in new_part
            old_name = re.sub(r"^(?:a\s+)?(?:folder|file|directory|document)\s+(?:named\s+|called\s+)?", "", old_part,
                              flags=re.IGNORECASE).strip()
            old_name = re.sub(r"\s+(?:folder|file|directory|document)$", "", old_name, flags=re.IGNORECASE).strip()
            new_name = re.sub(r"^(?:a\s+)?(?:folder|file|directory|document)\s+(?:named\s+|called\s+)?", "", new_part,
                              flags=re.IGNORECASE).strip()
            new_name = re.sub(r"\s+(?:folder|file|directory|document)$", "", new_name, flags=re.IGNORECASE).strip()
            return (op, old_name, new_name, target, is_file)
        else:
            is_file = "file" in cmd.lower() or "document" in cmd.lower() or "." in cmd
            item_name = re.sub(r"^(?:a\s+)?(?:folder|file|directory|document)\s+(?:named\s+|called\s+)?", "", cmd,
                               flags=re.IGNORECASE).strip()
            item_name = re.sub(r"\s+(?:folder|file|directory|document)$", "", item_name, flags=re.IGNORECASE).strip()
            if not item_name: item_name = "New File.txt" if is_file else "New Folder"
            return (op, item_name, None, target, is_file)

    def normalize_target(self, target):
        if not target: return None
        t_low = target.lower().strip()
        drive_match = re.match(r"^([a-z])\s*drive$", t_low, re.IGNORECASE)
        if drive_match: return f"{drive_match.group(1).upper()}:\\"
        drive_match2 = re.match(r"^drive\s+([a-z])$", t_low, re.IGNORECASE)
        if drive_match2: return f"{drive_match2.group(1).upper()}:\\"
        if len(t_low) == 1 and t_low.isalpha(): return f"{t_low.upper()}:\\"
        if t_low.endswith(":") and len(t_low) == 2: return f"{t_low.upper()}\\"
        if os.path.isabs(target) and os.path.exists(target): return target
        return target

    def parse_conversion_command(self, text):
        match = re.search(r"^(\d+(?:\.\d+)?)\s*(inch|inches|cm|m|mm|lbs|kg)\s+in\s+(inch|inches|cm|m|mm|lbs|kg)$",
                          text.strip().lower())
        if match:
            v, f_u, t_u = float(match.group(1)), match.group(2), match.group(3)
            if f_u in ("inch", "inches") and t_u == "cm": return f"📐 {v} inches = {v * 2.54:.2f} cm"
            if f_u == "cm" and t_u in ("inch", "inches"): return f"📐 {v} cm = {v / 2.54:.2f} inches"
            if f_u == "lbs" and t_u == "kg": return f"📐 {v} lbs = {v * 0.45359237:.2f} kg"
            if f_u == "kg" and t_u == "lbs": return f"📐 {v} kg = {v / 0.45359237:.2f} lbs"
            if f_u == "m" and t_u == "cm": return f"📐 {v} m = {v * 100:.2f} cm"
            if f_u == "cm" and t_u == "m": return f"📐 {v} cm = {v / 100:.4f} m"
            if f_u == "mm" and t_u == "cm": return f"📐 {v} mm = {v / 10:.2f} cm"
            if f_u == "cm" and t_u == "mm": return f"📐 {v} cm = {v * 10:.2f} mm"
        return None

    def eventFilter(self, obj, event):
        if obj == self.input_box and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                if self.input_box.text():
                    self.input_box.clear()
                else:
                    self.hide_main_window()
                return True
            elif event.key() == Qt.Key.Key_Tab:
                if self.results_list.currentItem():
                    txt = self.results_list.currentItem().text()
                    txt = re.sub(r"^[^\w\s]+", "", txt).strip()
                    self.input_box.setText(txt)
                return True
            elif event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                self.results_list.keyPressEvent(event)
                return True
        return super().eventFilter(obj, event)

    def on_item_hovered(self, index):
        self.results_list.setCurrentRow(index.row())

    def index_apps(self):
        search_paths = [path for path in [
            os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop'),
            os.path.join(os.environ.get('PUBLIC', ''), 'Desktop')
        ] if os.path.exists(path)]

        for path in search_paths:
            for root, _, files in os.walk(path):
                for f in files:  # This loop was missing
                    if f.endswith('.lnk'):
                        self.installed_apps[f[:-4].lower()] = os.path.join(root, f)

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 630) // 2, (screen.height() - 400) // 4)

    def toggle_visibility(self):
        if self.isVisible() and self.windowOpacity() > 0:
            self.opacity_anim.stop()
            self.opacity_anim.setStartValue(self.windowOpacity())
            self.opacity_anim.setEndValue(0.0)
            self.opacity_anim.start()
            QTimer.singleShot(200, self.hide)
        else:
            self.setWindowOpacity(0.0)
            self.show()
            self.activateWindow()
            self.input_box.setFocus()
            self.input_box.selectAll()
            self.opacity_anim.stop()
            self.opacity_anim.setStartValue(0.0)
            self.opacity_anim.setEndValue(1.0)
            self.opacity_anim.start()

    def hide_main_window(self):
        self.opacity_anim.stop()
        self.opacity_anim.setStartValue(self.windowOpacity())
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.start()
        QTimer.singleShot(200, self.hide)

    def hide_list_if_empty(self):
        if self.results_list.height() == 0:
            self.results_list.hide()

    def on_text_changed(self, text):
        self.results_list.clear()
        self.ai_debounce_timer.stop()
        self.animation_timer.stop()

        if self.search_worker: self.search_worker.stop()
        if self.ai_worker: self.ai_worker.stop()

        if not text.strip():
            self.list_anim.stop()
            self.list_anim.setStartValue(self.results_list.height())
            self.list_anim.setEndValue(0)
            self.list_anim.start()
            QTimer.singleShot(300, self.hide_list_if_empty)
            return

        if self.results_list.isHidden() or self.results_list.height() == 0:
            self.results_list.show()
            self.list_anim.stop()
            self.list_anim.setStartValue(self.results_list.height())
            self.list_anim.setEndValue(320)
            self.list_anim.start()

        text_lower = text.lower().strip()

        if text_lower in ("lock", "lock pc"):
            self.add_result("🔒 Lock Workstation", "sys:lock");
            return
        elif text_lower in ("empty trash", "empty recycle bin", "clean trash"):
            self.add_result("🗑️ Empty Recycle Bin", "sys:empty_bin");
            return
        elif text_lower in ("sleep", "suspend"):
            self.add_result("💤 Sleep Computer", "sys:sleep");
            return
        elif text_lower in ("ip", "my ip", "ipconfig"):
            self.add_result(f"🌐 Local IP: {socket.gethostbyname(socket.gethostname())}",
                            "copy_text:" + socket.gethostbyname(socket.gethostname()));
            return

        if text_lower.startswith("kill "):
            self.add_result(f"🚫 Terminate process: '{text_lower[5:].strip()}'", f"sys:kill:{text_lower[5:].strip()}");
            return

        dev_res = self.parse_dev_command(text)
        if dev_res: self.add_result(dev_res[0], dev_res[1]); return

        math_res = self.parse_math_command(text)
        if math_res: self.add_result(math_res, f"copy_text:{math_res.split('=')[-1].strip()}"); return

        if text_lower.startswith("yt "):
            self.add_result(f"▶️ Search YouTube: '{text[3:].strip()}'",
                            f"web:https://www.youtube.com/results?search_query={urllib.parse.quote(text[3:].strip())}"); return
        elif text_lower.startswith("gh "):
            self.add_result(f"🐙 Search GitHub: '{text[3:].strip()}'",
                            f"web:https://github.com/search?q={urllib.parse.quote(text[3:].strip())}"); return
        elif text_lower.startswith("wiki "):
            self.add_result(f"📖 Search Wikipedia: '{text[5:].strip()}'",
                            f"web:https://en.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote(text[5:].strip())}"); return
        elif text_lower.startswith("r/"):
            self.add_result(f"👽 Open Subreddit: 'r/{text[2:].strip()}'",
                            f"web:https://www.reddit.com/r/{text[2:].strip()}"); return
        elif text_lower.startswith("map "):
            self.add_result(f"🗺️ Search Maps for '{text[4:].strip()}'",
                            f"web:https://www.google.com/maps/search/{urllib.parse.quote(text[4:].strip())}"); return

        timer_secs = self.parse_timer_command(text)
        if timer_secs is not None: self.add_result(f"⏱️ Start Timer for {timer_secs} seconds",
                                                   f"action:timer:{timer_secs}"); return

        if text_lower in ("show fps", "fps", "show ping", "ping", "fps counter"):
            self.add_result(f"📊 {'Close' if self.fps_widget.isVisible() else 'Open'} Live FPS & Ping HUD",
                            "action:fps_counter");
            return

        match_music = re.search(r"^(?:play|spotify|listen\s+to)\s+(.+)$", text_lower)
        if match_music: self.add_result(f"🎵 Search Spotify for '{text[match_music.start(1):].strip()}'",
                                        f"action:spotify:{text[match_music.start(1):].strip()}"); return

        if text_lower.startswith("google "):
            if text[7:].strip(): self.add_result(f"🔍 Google Search: '{text[7:].strip()}'", f"google:{text[7:].strip()}")
            return

        if text_lower in ("show me my system stats", "system stats", "stats"):
            self.add_result("📊 Open System Hardware Monitor", "action:stats");
            return

        if text_lower.startswith("weather forecast in ") and text[20:].strip():
            self.add_result(f"🔍 Fetching weekly forecast for {text[20:].strip().title()}...", "info:searching")
            self.start_weather_search(text[20:].strip(), is_forecast=True);
            return
        elif text_lower.startswith("weather in ") and text[11:].strip():
            self.add_result(f"🔍 Fetching current weather for {text[11:].strip().title()}...", "info:searching")
            self.start_weather_search(text[11:].strip(), is_forecast=False);
            return

        conversion_res = self.parse_conversion_command(text)
        if conversion_res: self.add_result(conversion_res, "info:conversion"); return

        for key, uri in self.win_settings_map.items():
            if f"{key} settings" in text_lower or f"open {key}" in text_lower:
                self.add_result(f"⚙️ Open Windows {key.title()} Settings", f"winsettings:{uri}");
                return

        if text_lower.startswith("set ") or text_lower.endswith("volume") or text_lower.startswith(
                "mute") or text_lower.startswith("unmute") or text_lower.startswith("turn "):
            match = re.search(r"set\s+(?:my\s+)?mouse\s+speed\s+to\s+(.+)", text_lower)
            if match:
                val = match.group(1).strip()
                speed = 20 if val in ("max", "maximum", "fastest") else 1 if val in ("min", "minimum",
                                                                                     "slowest") else 10 if val in (
                    "medium", "default", "normal") else max(1, min(int(val), 20)) if val.isdigit() else None
                if speed: self.add_result(f"⚙️ Set Mouse Speed to {speed}", f"setting:mousespeed:{speed}"); return
            match = re.search(r"(?:set\s+theme\s+to|turn\s+on)\s+(dark|light)(?:\s+mode)?", text_lower)
            if match: self.add_result(f"🌗 Change System Theme to {match.group(1).title()} Mode",
                                      f"setting:theme:{match.group(1)}"); return
            match = re.search(r"set\s+(?:screen\s+)?brightness\s+to\s+(\d+)", text_lower)
            if match: self.add_result(f"☀️ Set Brightness to {max(0, min(int(match.group(1)), 100))}%",
                                      f"setting:brightness:{max(0, min(int(match.group(1)), 100))}"); return
            match = re.search(r"set\s+wallpaper\s+to\s+(.+)", text, re.IGNORECASE)
            if match: self.add_result(f"🖼️ Set Desktop Wallpaper to '{match.group(1).strip()}'",
                                      f"setting:wallpaper:{match.group(1).strip()}"); return
            if "mute volume" in text_lower or text_lower == "mute":
                self.add_result("🔇 Mute Volume", "setting:volume:mute"); return
            elif "unmute volume" in text_lower or text_lower == "unmute":
                self.add_result("🔊 Unmute Volume", "setting:volume:unmute"); return

        file_op = self.parse_file_op_command(text)
        if file_op:
            op, item_name, new_name, target, is_file = file_op
            norm_target = self.normalize_target(target) if target else None
            is_target_ready = norm_target and os.path.isabs(norm_target) and (
                        os.path.exists(norm_target) or re.match(r"^[A-Z]:\\$", norm_target))

            if op == "create":
                action = "create_file" if is_file else "create_dir"
                if is_target_ready:
                    self.add_result(f"✨ Create {'File' if is_file else 'Folder'} '{item_name}' in {norm_target}",
                                    f"{action}:{os.path.join(norm_target, item_name)}")
                elif target:
                    self.add_result(f"🔍 Searching drives for parent directory '{target}'...", "info:searching")
                    self.start_custom_search(target, search_type="find_parent_dir", new_item=item_name,
                                             extra_item="create", is_file=is_file)
                else:
                    default_path = os.path.join(os.path.expanduser("~"), "Desktop")
                    if not os.path.exists(default_path): default_path = "C:\\"
                    self.add_result(f"✨ Create {'File' if is_file else 'Folder'} '{item_name}' on Desktop",
                                    f"{action}:{os.path.join(default_path, item_name)}")
                return
            elif op == "delete":
                action = "delete_file" if is_file else "delete_dir"
                if is_target_ready:
                    self.add_result(f"❌ Delete {'File' if is_file else 'Folder'} '{item_name}' from {norm_target}",
                                    f"{action}:{os.path.join(norm_target, item_name)}")
                elif target:
                    self.add_result(f"🔍 Searching for folder '{target}' containing '{item_name}'...", "info:searching")
                    self.start_custom_search(target, search_type="find_parent_dir", new_item=item_name,
                                             extra_item="delete", is_file=is_file)
                else:
                    self.add_result(f"🔍 Searching all drives for '{item_name}' to delete...", "info:searching")
                    self.start_custom_search(item_name, search_type="find_item_to_delete", is_file=is_file)
                return
            elif op == "rename":
                action = "rename_file" if is_file else "rename_dir"
                if is_target_ready:
                    self.add_result(f"📝 Rename '{item_name}' to '{new_name}' in {norm_target}",
                                    f"{action}:{os.path.join(norm_target, item_name)}||{os.path.join(norm_target, new_name)}")
                elif target:
                    self.add_result(f"🔍 Searching for folder '{target}' to rename '{item_name}'...", "info:searching")
                    self.start_custom_search(target, search_type="find_parent_dir", new_item=item_name,
                                             extra_item=f"rename||{new_name}", is_file=is_file)
                else:
                    self.add_result(f"🔍 Searching all drives for '{item_name}' to rename...", "info:searching")
                    self.start_custom_search(item_name, search_type="find_item_to_rename", new_item=new_name,
                                             is_file=is_file)
                return

        clean_text = text.strip()
        target_search = clean_text[5:].strip() if text_lower.startswith("open ") else clean_text

        known_websites = {
            "youtube": "youtube.com", "github": "github.com", "twitch": "twitch.tv",
            "reddit": "reddit.com", "netflix": "netflix.com", "amazon": "amazon.com",
            "twitter": "twitter.com", "x": "x.com", "instagram": "instagram.com",
            "discord": "discord.com", "chatgpt": "chatgpt.com", "claude": "claude.ai",
            "facebook": "facebook.com", "wikipedia": "wikipedia.org"
        }

        is_url_or_site = False
        url_match = re.match(r"^([a-z0-9\-]+\.)+[a-z]{2,}(/.*)?$", target_search)

        if text_lower.startswith("open "):
            if target_search:
                for shortcut in [k for k in self.installed_apps if target_search in k]:
                    self.add_result(f"🚀 Launch {shortcut.title()} (App)", f"app:{self.installed_apps[shortcut]}")

                if url_match:
                    self.add_result(f"🌐 Open {target_search}", f"web:https://{target_search}")
                elif target_search in known_websites:
                    self.add_result(f"🌐 Open {known_websites[target_search]}",
                                    f"web:https://www.{known_websites[target_search]}")
                else:
                    self.add_result(f"🌐 Open {target_search}.com (Website)", f"web:https://www.{target_search}.com")
            return
        else:
            for shortcut in [k for k in self.installed_apps if text_lower in k]:
                self.add_result(f"🚀 Launch {shortcut.title()} (App)", f"app:{self.installed_apps[shortcut]}")

            if url_match:
                self.add_result(f"🌐 Open {target_search}", f"web:https://{target_search}")
                is_url_or_site = True
            elif target_search in known_websites:
                self.add_result(f"🌐 Open {known_websites[target_search]}",
                                f"web:https://www.{known_websites[target_search]}")
                is_url_or_site = True

        # Only fallback to Spotify if the input does NOT resemble a web domain or a known website platform
        if not is_url_or_site:
            self.add_result(f"🎵 Play '{clean_text}' on Spotify", f"action:spotify:{clean_text}")

        if text_lower.startswith("search ") and text[7:].strip():
            self.add_result(f"🔍 Searching drives for '{text[7:].strip()}'...", "info:searching")
            self.start_custom_search(text[7:].strip(), search_type="general")
            return

        if not text_lower.startswith("google "):
            self.add_result(f"🔍 Search Google for '{clean_text}'", f"google:{clean_text}")

        for pattern, reply in self.fast_ai_replies.items():
            if re.match(pattern, text_lower):
                self.on_ai_match(reply)
                return

        self.add_result("✨ AI is thinking", "info:ai_thinking")
        self.ai_dot_count = 1
        self.ai_debounce_timer.start(350)

    def update_ai_loading_animation(self):
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == "info:ai_thinking":
                self.ai_dot_count = (self.ai_dot_count % 3) + 1
                item.setText(f"✨ AI is thinking{'.' * self.ai_dot_count}")
                break

    def execute_ai_query(self):
        if self.input_box.text().strip():
            self.animation_timer.start(400)
            self.ai_worker = FreeCloudAIWorker(self.input_box.text().strip())
            self.ai_thread = threading.Thread(target=self.ai_worker.run, daemon=True)
            self.ai_worker.chunk_received.connect(self.on_ai_chunk)
            self.ai_worker.finished.connect(self.on_ai_match)
            self.ai_thread.start()

    def on_ai_chunk(self, streamed_text):
        self.animation_timer.stop()
        found = False
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) in ("info:ai_thinking", "info:ai_streaming"):
                item.setText(f"✨ {streamed_text}")
                item.setData(Qt.ItemDataRole.UserRole, "info:ai_streaming")
                found = True
                break
        if not found:
            self.add_result(f"✨ {streamed_text}", "info:ai_streaming")

    def start_custom_search(self, query, search_type="general", new_item=None, extra_item=None, is_file=False):
        self.search_worker = SearchWorker(query, search_type=search_type, new_item=new_item, extra_item=extra_item,
                                          is_file=is_file)
        self.search_thread = threading.Thread(target=self.search_worker.run, daemon=True)
        self.search_worker.match_found.connect(self.on_search_match)
        self.search_thread.start()

    def start_weather_search(self, city, is_forecast=False):
        self.weather_worker = WeatherWorker(city, is_forecast)
        self.weather_thread = threading.Thread(target=self.weather_worker.run, daemon=True)
        self.weather_worker.weather_found.connect(self.on_weather_match)
        self.weather_thread.start()

    def on_search_match(self, match_type, path):
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == "info:searching":
                self.results_list.takeItem(i);
                break

        if match_type == "file":
            self.add_result(f"📁 {path}", f"file:{path}")
        elif match_type == "parent_dir_match":
            is_file = self.search_worker.is_file
            item_name = self.search_worker.new_item
            extra = self.search_worker.extra_item
            if extra == "create":
                self.add_result(f"✨ Create {'File' if is_file else 'Folder'} '{item_name}' in {path}",
                                f"{'create_file' if is_file else 'create_dir'}:{os.path.join(path, item_name)}")
            elif extra == "delete":
                self.add_result(f"❌ Delete '{item_name}' from {path}",
                                f"{'delete_file' if is_file else 'delete_dir'}:{os.path.join(path, item_name)}")
            elif extra and extra.startswith("rename||"):
                self.add_result(f"📝 Rename '{item_name}' to '{extra.split('||')[1]}' in {path}",
                                f"{'rename_file' if is_file else 'rename_dir'}:{os.path.join(path, item_name)}||{os.path.join(path, extra.split('||')[1])}")
        elif match_type == "delete_match":
            self.add_result(f"❌ Delete at {path}",
                            f"{'delete_file' if self.search_worker.is_file else 'delete_dir'}:{path}")
        elif match_type == "rename_match":
            self.add_result(f"📝 Rename '{os.path.basename(path)}' to '{self.search_worker.new_item}'",
                            f"{'rename_file' if self.search_worker.is_file else 'rename_dir'}:{path}||{os.path.join(os.path.dirname(path), self.search_worker.new_item)}")

    def on_weather_match(self, summary, lines):
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == "info:searching":
                self.results_list.takeItem(i);
                break
        self.add_result(summary, "info:weather")
        for line in lines: self.add_result(line, "info:weather")

    def on_ai_match(self, response_text):
        self.animation_timer.stop()
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) in ("info:ai_thinking", "info:ai_streaming"):
                self.results_list.takeItem(i);
                break
        for line in response_text.split('\n'):
            if line.strip(): self.add_result(f"✨ {line}", f"copy_text:{line}")

    def execute_top_result(self):
        if self.results_list.count() > 0:
            self.execute_action(
                (self.results_list.currentItem() or self.results_list.item(0)).data(Qt.ItemDataRole.UserRole))

    def execute_clicked_item(self, item):
        self.execute_action(item.data(Qt.ItemDataRole.UserRole))

    def execute_action(self, action_data):
        if not action_data or action_data.startswith("info:"): return
        if not action_data.startswith("copy_text:"): self.hide_main_window()

        if action_data == "sys:lock":
            ctypes.windll.user32.LockWorkStation()
        elif action_data == "sys:empty_bin":
            try:
                ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            except Exception:
                pass
        elif action_data == "sys:sleep":
            subprocess.run("powertoy /sleep", shell=True, creationflags=0x08000000)
        elif action_data.startswith("sys:kill:"):
            target = action_data[9:].lower()
            for proc in psutil.process_iter(['name']):
                try:
                    if target in proc.info['name'].lower(): proc.kill()
                except Exception:
                    pass
        elif action_data.startswith("google:"):
            webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(action_data[7:])}")
        elif action_data == "action:stats":
            self.stats_widget.show_animated();
            self.stats_widget.position_window()
        elif action_data == "action:fps_counter":
            if self.fps_widget.isVisible():
                self.fps_widget.hide_animated()
            else:
                self.fps_widget.show_animated(); self.fps_widget.position_window()
        elif action_data.startswith("action:spotify:"):
            query = action_data[15:]
            if self.is_spotify_installed():
                os.startfile(f"spotify:search:{urllib.parse.quote(query)}")
            else:
                webbrowser.open(f"https://open.spotify.com/search/{urllib.parse.quote(query)}")
        elif action_data.startswith("action:timer:"):
            self.timer_widget.start_timer(int(action_data.split(":")[2]))
        elif action_data.startswith("winsettings:"):
            os.system(f"start ms-settings:{action_data.split(':')[1]}")
        elif action_data.startswith("web:"):
            webbrowser.open(action_data[4:])
        elif action_data.startswith("app:"):
            os.startfile(action_data[4:])
        elif action_data.startswith("copy_text:"):
            QApplication.clipboard().setText(action_data[10:])
        elif action_data.startswith("file:"):
            path = action_data[5:]
            if os.path.exists(path): os.startfile(path if os.path.isdir(path) else os.path.dirname(path))
        elif action_data.startswith("create_dir:"):
            try:
                os.makedirs(action_data[11:], exist_ok=True); os.startfile(action_data[11:])
            except Exception:
                pass
        elif action_data.startswith("create_file:"):
            try:
                os.makedirs(os.path.dirname(action_data[12:]), exist_ok=True)
                with open(action_data[12:], "w") as f:
                    pass
                os.startfile(action_data[12:])
            except Exception:
                pass
        elif action_data.startswith("delete_file:"):
            try:
                if os.path.exists(action_data[12:]): os.remove(action_data[12:])
            except Exception:
                pass
        elif action_data.startswith("delete_dir:"):
            try:
                if os.path.exists(action_data[11:]): shutil.rmtree(action_data[11:])
            except Exception:
                pass
        elif action_data.startswith("rename_file:"):
            try:
                p = action_data[12:].split("||")
                if len(p) == 2 and os.path.exists(p[0]): os.rename(p[0], p[1])
            except Exception:
                pass
        elif action_data.startswith("rename_dir:"):
            try:
                p = action_data[11:].split("||")
                if len(p) == 2 and os.path.exists(p[0]): os.rename(p[0], p[1])
            except Exception:
                pass
        elif action_data.startswith("setting:"):
            parts = action_data.split(":")
            if parts[1] == "mousespeed":
                try:
                    ctypes.windll.user32.SystemParametersInfoW(0x0071, 0, int(parts[2]), 0)
                except Exception:
                    pass
            elif parts[1] == "theme":
                try:
                    reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                         r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 0,
                                         winreg.KEY_SET_VALUE)
                    val = 0 if parts[2] == "dark" else 1
                    winreg.SetValueEx(reg, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
                    winreg.SetValueEx(reg, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)
                    winreg.CloseKey(reg)
                    ctypes.windll.user32.SendMessageW(0xFFFF, 0x001A, 0, "Environment")
                except Exception:
                    pass
            elif parts[1] == "brightness":
                try:
                    subprocess.run(["powershell", "-Command",
                                    f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {int(parts[2])})"],
                                   capture_output=True, creationflags=0x08000000)
                except Exception:
                    pass
            elif parts[1] == "wallpaper":
                try:
                    ctypes.windll.user32.SystemParametersInfoW(20, 0, ":".join(parts[2:]), 3)
                except Exception:
                    pass
            elif parts[1] == "volume":
                if parts[2] in ("mute", "unmute"): ctypes.windll.user32.keybd_event(0xAD, 0, 0,
                                                                                    0); ctypes.windll.user32.keybd_event(
                    0xAD, 0, 2, 0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    widget = FlowWidget()
    sys.exit(app.exec())