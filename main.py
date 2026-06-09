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
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFontDatabase 

class SearchWorker(QObject):
    match_found = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, query, search_type="general", new_item=None, extra_item=None, is_file=False):
        super().__init__()
        self.query = query.lower()
        self.search_type = search_type  
        self.new_item = new_item        
        self.extra_item = extra_item    
        self.is_file = is_file
        self._is_running = True

    def run(self):
        drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
        for drive in drives:
            for root, dirs, files in os.walk(drive, onerror=lambda e: None):
                if not self._is_running: return
                
                if self.search_type == "general":
                    for name in dirs + files:
                        if self.query in name.lower():
                            self.match_found.emit("file", os.path.join(root, name))
                            
                elif self.search_type == "find_parent_dir":
                    for name in dirs:
                        if self.query == name.lower():
                            self.match_found.emit("parent_dir_match", os.path.join(root, name))
                            
                elif self.search_type == "find_item_to_delete":
                    items_to_check = files if self.is_file else dirs
                    for name in items_to_check:
                        if self.query == name.lower():
                            self.match_found.emit("delete_match", os.path.join(root, name))
                            
                elif self.search_type == "find_item_to_rename":
                    items_to_check = files if self.is_file else dirs
                    for name in items_to_check:
                        if self.query == name.lower():
                            self.match_found.emit("rename_match", os.path.join(root, name))
        self.finished.emit()

    def stop(self):
        self._is_running = False

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
                        forecast_list.append(f"📅 {day['date']}: {day['mintempC']}°C - {day['maxtempC']}°C ({day['hourly'][4]['weatherDesc'][0]['value']})")
                    self.weather_found.emit(f"🌤️ Weekly Forecast for {self.city.title()}:", forecast_list)
        except Exception:
            self.weather_found.emit("❌ Could not retrieve weather details.", [])

class OllamaWorker(QObject):
    response_received = pyqtSignal(str)

    def __init__(self, prompt, model="llama3"):
        super().__init__()
        self.prompt = prompt
        self.model = model
        self._is_running = True

    def run(self):
        try:
            url = "http://localhost:11434/api/generate"
            system_instructions = (
                "You are a fast desktop assistant. Keep answers to 1 or 2 short sentences. "
                "Use a friendly, conversational tone—informal but direct. "
                "If the user enters a song title, track, or music query, identify it contextually. "
                "Do not use slang, and skip robotic greetings. Just answer directly."
            )
            payload = {
                "model": self.model,
                "prompt": self.prompt,
                "stream": False,
                "system": system_instructions,
                "options": { "num_predict": 50, "temperature": 0.6 }
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if not self._is_running: return
                self.response_received.emit(json.loads(response.read().decode()).get("response", "").strip())
        except Exception:
            self.response_received.emit(f"❌ Ollama Offline. Ensure Ollama is running with model '{self.model}'.")

    def stop(self):
        self._is_running = False

class HotkeyListener(QObject):
    triggered = pyqtSignal()
    def __init__(self):
        super().__init__()
        keyboard.add_hotkey('alt+q', self.emit_trigger)
    def emit_trigger(self): self.triggered.emit()

class PingWorker(QObject):
    ping_updated = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._is_running = True

    def run(self):
        while self._is_running:
            try:
                output = subprocess.check_output("ping -n 1 8.8.8.8", shell=True, creationflags=0x08000000).decode()
                match = re.search(r"time[=<](\d+)ms", output)
                if match:
                    self.ping_updated.emit(int(match.group(1)))
                else:
                    self.ping_updated.emit(-1)
            except Exception:
                self.ping_updated.emit(-1)
            
            for _ in range(15):
                if not self._is_running: break
                time.sleep(0.1)

    def stop(self):
        self._is_running = False

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

class FPSPingWidget(AnimatedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(220, 50)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.hud_label = QLabel("FPS: --  |  PING: -- ms", self)
        self.hud_label.setStyleSheet("font-size: 18px; font-family: 'Digital-7', 'Consolas'; color: #00ff00; background: transparent; font-weight: bold;")
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
            
        self.hud_label.setText(f"FPS: {self.current_fps}  |  PING: {self.ping_string}")
        self.update() 

class TimerWidget(AnimatedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(200, 100)
        
        self.main_container = QWidget(self)
        self.main_container.setStyleSheet("background-color: rgba(30, 30, 30, 220); border: 1px solid #333; border-radius: 10px;")
        
        layout = QVBoxLayout(self.main_container)
        layout.setContentsMargins(10, 5, 10, 10)
        
        top_layout = QHBoxLayout()
        self.title_label = QLabel("⏱️ Timer", self.main_container)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff; border: none; background: transparent;")
        self.close_btn = QPushButton("✕", self.main_container)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("background: transparent; color: #ff5555; border: none; font-size: 14px; font-weight: bold;")
        self.close_btn.clicked.connect(self.hide_animated)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.close_btn)
        layout.addLayout(top_layout)
        
        self.time_label = QLabel("00:00", self.main_container)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-size: 38px; font-family: 'Digital-7'; color: #00ff00; border: none; background: transparent;")
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
        self.time_label.setStyleSheet("font-size: 38px; font-family: 'Digital-7'; color: #00ff00; border: none; background: transparent;")
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
            self.time_label.setStyleSheet("font-size: 38px; font-family: 'Digital-7'; color: #ff0000; border: none; background: transparent;")
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
        self.resize(250, 130)
        self.main_container = QWidget(self)
        self.main_container.setStyleSheet("background-color: rgba(30, 30, 30, 220); color: #ffffff; border: 1px solid #333; border-radius: 10px;")
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        top_layout = QHBoxLayout()
        self.title_label = QLabel("📊 System Stats", self.main_container)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; border: none; background: transparent;")
        self.close_btn = QPushButton("✕", self.main_container)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("background: transparent; color: #ff5555; border: none; font-size: 14px; font-weight: bold;")
        self.close_btn.clicked.connect(self.hide_animated)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.close_btn)
        container_layout.addLayout(top_layout)
        self.cpu_label = QLabel("CPU: 0%", self.main_container)
        self.cpu_label.setStyleSheet("font-size: 13px; border: none; background: transparent;")
        self.ram_label = QLabel("RAM: 0%", self.main_container)
        self.ram_label.setStyleSheet("font-size: 13px; border: none; background: transparent;")
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
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize) 
        
        self.input_box = QLineEdit(self)
        self.input_box.setMinimumWidth(730) 
        self.input_box.setStyleSheet("font-size: 24px; padding: 15px; border-radius: 10px; background-color: #1e1e1e; color: #ffffff; border: 1px solid #333;")
        self.layout.addWidget(self.input_box)
        self.input_box.installEventFilter(self)
        
        self.results_list = QListWidget(self)
        self.results_list.setMinimumWidth(730)
        self.results_list.setFixedHeight(0) 
        self.results_list.setMouseTracking(True)
        self.results_list.setStyleSheet("""
            QListWidget { font-size: 16px; background-color: #1e1e1e; color: #ffffff; border-radius: 10px; border: 1px solid #333; padding: 5px; }
            QListWidget::item { padding: 10px; border-radius: 5px; }
            QListWidget::item:hover { background-color: #2d2d2d; }
            QListWidget::item:selected { background-color: #3d3d3d; }
        """)
        self.results_list.hide()
        self.layout.addWidget(self.results_list)
        
        self.input_box.textChanged.connect(self.on_text_changed)
        self.input_box.returnPressed.connect(self.execute_top_result)
        self.results_list.itemClicked.connect(self.execute_clicked_item)
        self.results_list.entered.connect(self.on_item_hovered)
        
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(200)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.list_anim = QPropertyAnimation(self, b"listHeight")
        self.list_anim.setDuration(350)
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
        """Probes shortcuts, standard paths, and native registry protocol maps to locate Spotify application."""
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
        """
        Calculates priority weights to group matching item classes:
        Priority 0: AI generation streams and system waiting indicators.
        Priority 1: Core OS utilities, custom automation tasks, and physical app shortcuts.
        Priority 2: Global lookup handlers and remote browser redirection fallbacks.
        """
        if not action_data:
            return 2
        if action_data.startswith("copy_text:") or action_data == "info:ai_thinking":
            return 0
        if (action_data.startswith("info:") or action_data.startswith("action:stats") or 
            action_data.startswith("action:timer") or action_data.startswith("action:fps") or 
            action_data.startswith("winsettings:") or action_data.startswith("app:") or 
            action_data.startswith("create_") or action_data.startswith("delete_") or 
            action_data.startswith("rename_")):
            return 1
        return 2

    def add_result(self, display_text, action_data):
        """Assembles suggestions utilizing a priority matrix insertion sort to keep AI at the top."""
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

    def parse_timer_command(self, text):
        match = re.search(r"(?:set\s+(?:a\s+)?)?timer\s+(?:for\s+)?(\d+(?:\.\d+)?)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours)", text.lower())
        if match:
            val = float(match.group(1))
            unit = match.group(2)
            if unit.startswith('s'): return int(val)
            elif unit.startswith('m'): return int(val * 60)
            elif unit.startswith('h'): return int(val * 3600)
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
            
        if not op:
            return None
            
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
            
            old_name = re.sub(r"^(?:a\s+)?(?:folder|file|directory|document)\s+(?:named\s+|called\s+)?", "", old_part, flags=re.IGNORECASE).strip()
            old_name = re.sub(r"\s+(?:folder|file|directory|document)$", "", old_name, flags=re.IGNORECASE).strip()
            
            new_name = re.sub(r"^(?:a\s+)?(?:folder|file|directory|document)\s+(?:named\s+|called\s+)?", "", new_part, flags=re.IGNORECASE).strip()
            new_name = re.sub(r"\s+(?:folder|file|directory|document)$", "", new_name, flags=re.IGNORECASE).strip()
            
            return (op, old_name, new_name, target, is_file)
        else:
            is_file = "file" in cmd.lower() or "document" in cmd.lower() or "." in cmd
            
            item_name = re.sub(r"^(?:a\s+)?(?:folder|file|directory|document)\s+(?:named\s+|called\s+)?", "", cmd, flags=re.IGNORECASE).strip()
            item_name = re.sub(r"\s+(?:folder|file|directory|document)$", "", item_name, flags=re.IGNORECASE).strip()
            
            if not item_name:
                item_name = "New File.txt" if is_file else "New Folder"
                
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
        match = re.search(r"^(\d+(?:\.\d+)?)\s*(inch|inches|cm|m|mm|lbs|kg)\s+in\s+(inch|inches|cm|m|mm|lbs|kg)$", text.strip().lower())
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
            if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
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
                for f in files:
                    if f.endswith('.lnk'): self.installed_apps[f[:-4].lower()] = os.path.join(root, f)

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 750) // 2, (screen.height() - 440) // 4)

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
            QTimer.singleShot(350, self.hide_list_if_empty)
            return
            
        if self.results_list.isHidden() or self.results_list.height() == 0:
            self.results_list.show()
            self.list_anim.stop()
            self.list_anim.setStartValue(self.results_list.height())
            self.list_anim.setEndValue(350)
            self.list_anim.start()
            
        text_lower = text.lower().strip()
        
        timer_secs = self.parse_timer_command(text)
        if timer_secs is not None:
            self.add_result(f"⏱️ Start Timer for {timer_secs} seconds", f"action:timer:{timer_secs}")
            return

        if text_lower in ("show fps", "fps", "show ping", "ping", "fps counter"):
            status_txt = "Close" if self.fps_widget.isVisible() else "Open"
            self.add_result(f"📊 {status_txt} Live Transparent FPS & Ping HUD Overlay", "action:fps_counter")
            return

        match_music = re.search(r"^(?:play|spotify|listen\s+to)\s+(.+)$", text_lower)
        if match_music:
            query = text[match_music.start(1):].strip()
            self.add_result(f"🎵 Search Spotify for '{query}'", f"action:spotify:{query}")
            return

        if text_lower.startswith("google "):
            if text[7:].strip(): self.add_result(f"🔍 Google Search: '{text[7:].strip()}'", f"google:{text[7:].strip()}")
            return
            
        if text_lower in ("show me my system stats", "system stats"):
            self.add_result("📊 Open System Hardware Monitor Overlay", "action:stats")
            return
            
        if text_lower.startswith("weather forecast in ") and text[20:].strip():
            self.add_result(f"🔍 Fetching weekly forecast for {text[20:].strip().title()}...", "info:searching")
            self.start_weather_search(text[20:].strip(), is_forecast=True)
            return
        elif text_lower.startswith("weather in ") and text[11:].strip():
            self.add_result(f"🔍 Fetching current weather for {text[11:].strip().title()}...", "info:searching")
            self.start_weather_search(text[11:].strip(), is_forecast=False)
            return
            
        conversion_res = self.parse_conversion_command(text)
        if conversion_res:
            self.add_result(conversion_res, "info:conversion")
            return

        for key, uri in self.win_settings_map.items():
            if f"{key} settings" in text_lower or f"open {key}" in text_lower:
                self.add_result(f"⚙️ Open Windows {key.title()} Settings", f"winsettings:{uri}")
                return

        if text_lower.startswith("set ") or text_lower.endswith("volume") or text_lower.startswith("mute") or text_lower.startswith("unmute") or text_lower.startswith("turn "):
            match = re.search(r"set\s+(?:my\s+)?mouse\s+speed\s+to\s+(.+)", text_lower)
            if match:
                val = match.group(1).strip()
                speed = 20 if val in ("max", "maximum", "fastest") else 1 if val in ("min", "minimum", "slowest") else 10 if val in ("medium", "default", "normal") else max(1, min(int(val), 20)) if val.isdigit() else None
                if speed: self.add_result(f"⚙️ Set Mouse Speed to {speed}", f"setting:mousespeed:{speed}"); return
            match = re.search(r"(?:set\s+theme\s+to|turn\s+on)\s+(dark|light)(?:\s+mode)?", text_lower)
            if match: self.add_result(f"🌗 Change System Theme to {match.group(1).title()} Mode", f"setting:theme:{match.group(1)}"); return
            match = re.search(r"set\s+(?:screen\s+)?brightness\s+to\s+(\d+)", text_lower)
            if match: self.add_result(f"☀️ Set Screen Brightness to {max(0, min(int(match.group(1)), 100))}%", f"setting:brightness:{max(0, min(int(match.group(1)), 100))}"); return
            match = re.search(r"set\s+wallpaper\s+to\s+(.+)", text, re.IGNORECASE)
            if match: self.add_result(f"🖼️ Set Desktop Wallpaper to '{match.group(1).strip()}'", f"setting:wallpaper:{match.group(1).strip()}"); return
            match = re.search(r"set\s+(?:screen|monitor)\s+timeout\s+to\s+(\d+)", text_lower)
            if match: self.add_result(f"🖥️ Set Screen Off Timeout to {int(match.group(1))} minutes", f"setting:timeout:monitor:{int(match.group(1))}"); return
            match = re.search(r"set\s+sleep\s+timeout\s+to\s+(\d+)", text_lower)
            if match: self.add_result(f"💤 Set System Sleep Timeout to {int(match.group(1))} minutes", f"setting:timeout:standby:{int(match.group(1))}"); return
            if "mute volume" in text_lower or text_lower == "mute": self.add_result("🔇 Mute Master Volume", "setting:volume:mute"); return
            elif "unmute volume" in text_lower or text_lower == "unmute": self.add_result("🔊 Unmute Master Volume", "setting:volume:unmute"); return
            elif "volume up" in text_lower or "turn up volume" in text_lower: self.add_result("🔊 Turn Up Volume", "setting:volume:up"); return
            elif "volume down" in text_lower or "turn down volume" in text_lower: self.add_result("🔉 Turn Down Volume", "setting:volume:down"); return
                
        file_op = self.parse_file_op_command(text)
        if file_op:
            op, item_name, new_name, target, is_file = file_op
            norm_target = self.normalize_target(target) if target else None
            is_target_ready = norm_target and os.path.isabs(norm_target) and (os.path.exists(norm_target) or re.match(r"^[A-Z]:\\$", norm_target))
            
            if op == "create":
                action = "create_file" if is_file else "create_dir"
                if is_target_ready:
                    self.add_result(f"✨ Create {'File' if is_file else 'Folder'} '{item_name}' inside {norm_target}", f"{action}:{os.path.join(norm_target, item_name)}")
                elif target:
                    self.add_result(f"🔍 Searching drives for parent directory '{target}'...", "info:searching")
                    self.start_custom_search(target, search_type="find_parent_dir", new_item=item_name, extra_item="create", is_file=is_file)
                else:
                    default_path = os.path.join(os.path.expanduser("~"), "Desktop")
                    if not os.path.exists(default_path): default_path = "C:\\"
                    self.add_result(f"✨ Create {'File' if is_file else 'Folder'} '{item_name}' on Desktop", f"{action}:{os.path.join(default_path, item_name)}")
                return
                
            elif op == "delete":
                action = "delete_file" if is_file else "delete_dir"
                if is_target_ready:
                    self.add_result(f"❌ Delete {'File' if is_file else 'Folder'} '{item_name}' from {norm_target}", f"{action}:{os.path.join(norm_target, item_name)}")
                elif target:
                    self.add_result(f"🔍 Searching for folder '{target}' containing '{item_name}'...", "info:searching")
                    self.start_custom_search(target, search_type="find_parent_dir", new_item=item_name, extra_item="delete", is_file=is_file)
                else:
                    self.add_result(f"🔍 Searching all drives for {'file' if is_file else 'folder'} '{item_name}' to delete...", "info:searching")
                    self.start_custom_search(item_name, search_type="find_item_to_delete", is_file=is_file)
                return
                
            elif op == "rename":
                action = "rename_file" if is_file else "rename_dir"
                if is_target_ready:
                    self.add_result(f"📝 Rename {'File' if is_file else 'Folder'} '{item_name}' to '{new_name}' in {norm_target}", f"{action}:{os.path.join(norm_target, item_name)}||{os.path.join(norm_target, new_name)}")
                elif target:
                    self.add_result(f"🔍 Searching for folder '{target}' to rename '{item_name}'...", "info:searching")
                    self.start_custom_search(target, search_type="find_parent_dir", new_item=item_name, extra_item=f"rename||{new_name}", is_file=is_file)
                else:
                    self.add_result(f"🔍 Searching all drives for {'file' if is_file else 'folder'} '{item_name}' to rename...", "info:searching")
                    self.start_custom_search(item_name, search_type="find_item_to_rename", new_item=new_name, is_file=is_file)
                return

        clean_text = text.strip()
        display_text = clean_text[5:].strip() if text_lower.startswith("open ") else clean_text
        
        # Standard Spotify query recommendation
        self.add_result(f"🎵 Open and Play '{display_text}' on Spotify", f"action:spotify:{display_text}")

        if text_lower.startswith("open "):
            target = text_lower[5:].strip()
            if target:
                for shortcut in [k for k in self.installed_apps if target in k]:
                    self.add_result(f"🚀 Launch {shortcut.title()} (App)", f"app:{self.installed_apps[shortcut]}")
                self.add_result(f"🌐 Open {target}.com (Website)", f"web:{target}")
                return
        else:
            for shortcut in [k for k in self.installed_apps if text_lower in k]:
                self.add_result(f"🚀 Launch {shortcut.title()} (App)", f"app:{self.installed_apps[shortcut]}")
                
        if text_lower.startswith("search ") and text[7:].strip():
            self.add_result(f"Searching drives for '{text[7:].strip()}'...", "info:searching")
            self.start_custom_search(text[7:].strip(), search_type="general")
            return

        if not text_lower.startswith("google "):
            self.add_result(f"🔍 Search Google for '{clean_text}'", f"google:{clean_text}")

        for pattern, reply in self.fast_ai_replies.items():
            if re.match(pattern, text_lower):
                self.on_ai_match(reply)
                return

        self.add_result("🤖 AI is thinking.", "info:ai_thinking")
        self.ai_dot_count = 1
        self.ai_debounce_timer.start(500)

    def update_ai_loading_animation(self):
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == "info:ai_thinking":
                self.ai_dot_count = (self.ai_dot_count % 3) + 1
                item.setText(f"🤖 AI is thinking{'.' * self.ai_dot_count}")
                break

    def execute_ai_query(self):
        if self.input_box.text().strip():
            self.animation_timer.start(450)
            self.ai_worker = OllamaWorker(self.input_box.text().strip(), model="llama3")
            self.ai_thread = threading.Thread(target=self.ai_worker.run, daemon=True)
            self.ai_worker.response_received.connect(self.on_ai_match)
            self.ai_thread.start()

    def start_custom_search(self, query, search_type="general", new_item=None, extra_item=None, is_file=False):
        self.search_worker = SearchWorker(query, search_type=search_type, new_item=new_item, extra_item=extra_item, is_file=is_file)
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
                self.results_list.takeItem(i); break
                
        if match_type == "file": 
            self.add_result(f"📁 {path}", f"file:{path}")
        elif match_type == "parent_dir_match":
            is_file = self.search_worker.is_file
            item_name = self.search_worker.new_item
            extra = self.search_worker.extra_item
            if extra == "create":
                self.add_result(f"✨ Create {'File' if is_file else 'Folder'} '{item_name}' in {path}", f"{'create_file' if is_file else 'create_dir'}:{os.path.join(path, item_name)}")
            elif extra == "delete":
                self.add_result(f"❌ Delete {'File' if is_file else 'Folder'} '{item_name}' from {path}", f"{'delete_file' if is_file else 'delete_dir'}:{os.path.join(path, item_name)}")
            elif extra.startswith("rename||"):
                n_name = extra.split("||")[1]
                self.add_result(f"📝 Rename {'File' if is_file else 'Folder'} '{item_name}' to '{n_name}' inside {path}", f"{'rename_file' if is_file else 'rename_dir'}:{os.path.join(path, item_name)}||{os.path.join(path, n_name)}")
        elif match_type == "delete_match":
            is_file = self.search_worker.is_file
            self.add_result(f"❌ Delete {'File' if is_file else 'Folder'} at {path}", f"{'delete_file' if is_file else 'delete_dir'}:{path}")
        elif match_type == "rename_match":
            is_file = self.search_worker.is_file
            n_name = self.search_worker.new_item
            self.add_result(f"📝 Rename {'File' if is_file else 'Folder'} '{os.path.basename(path)}' to '{n_name}' at {os.path.dirname(path)}", f"{'rename_file' if is_file else 'rename_dir'}:{path}||{os.path.join(os.path.dirname(path), n_name)}")

    def on_weather_match(self, summary, lines):
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == "info:searching":
                self.results_list.takeItem(i); break
        self.add_result(summary, "info:weather")
        for line in lines: self.add_result(line, "info:weather")

    def on_ai_match(self, response_text):
        self.animation_timer.stop()
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == "info:ai_thinking":
                self.results_list.takeItem(i); break
        for line in response_text.split('\n'):
            if line.strip(): self.add_result(f"🤖 {line}", f"copy_text:{line}")

    def execute_top_result(self):
        if self.results_list.count() > 0:
            self.execute_action((self.results_list.currentItem() or self.results_list.item(0)).data(Qt.ItemDataRole.UserRole))

    def execute_clicked_item(self, item):
        self.execute_action(item.data(Qt.ItemDataRole.UserRole))

    def execute_action(self, action_data):
        if not action_data or action_data.startswith("info:"): return
        if not action_data.startswith("copy_text:"): self.hide_main_window()
        
        if action_data.startswith("google:"): webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(action_data[7:])}")
        elif action_data == "action:stats": self.stats_widget.show_animated(); self.stats_widget.position_window()
        elif action_data == "action:fps_counter":
            if self.fps_widget.isVisible(): self.fps_widget.hide_animated()
            else: self.fps_widget.show_animated(); self.fps_widget.position_window()
        elif action_data.startswith("action:spotify:"):
            query = action_data[15:]
            if self.is_spotify_installed():
                # Hand over directly to native Spotify Desktop protocol handler
                os.startfile(f"spotify:search:{urllib.parse.quote(query)}")
            else:
                # Web fallback browser instance
                webbrowser.open(f"https://open.spotify.com/search/{urllib.parse.quote(query)}")
        elif action_data.startswith("action:timer:"): self.timer_widget.start_timer(int(action_data.split(":")[2]))
        elif action_data.startswith("winsettings:"): os.system(f"start ms-settings:{action_data.split(':')[1]}")
        elif action_data.startswith("web:"): webbrowser.open(f"https://www.{action_data[4:]}.com")
        elif action_data.startswith("app:"): os.startfile(action_data[4:])
        elif action_data.startswith("copy_text:"): QApplication.clipboard().setText(action_data[10:])
        elif action_data.startswith("file:"):
            path = action_data[5:]
            if os.path.exists(path): os.startfile(path if os.path.isdir(path) else os.path.dirname(path))
        elif action_data.startswith("create_dir:"):
            try: os.makedirs(action_data[11:], exist_ok=True); os.startfile(action_data[11:])
            except Exception: pass
        elif action_data.startswith("create_file:"):
            try:
                os.makedirs(os.path.dirname(action_data[12:]), exist_ok=True)
                with open(action_data[12:], "w") as f: pass
                os.startfile(action_data[12:])
            except Exception: pass
        elif action_data.startswith("delete_file:"):
            try:
                if os.path.exists(action_data[12:]): os.remove(action_data[12:])
            except Exception: pass
        elif action_data.startswith("delete_dir:"):
            try:
                if os.path.exists(action_data[11:]): shutil.rmtree(action_data[11:])
            except Exception: pass
        elif action_data.startswith("rename_file:"):
            try:
                p = action_data[12:].split("||")
                if len(p) == 2 and os.path.exists(p[0]): os.rename(p[0], p[1])
            except Exception: pass
        elif action_data.startswith("rename_dir:"):
            try:
                p = action_data[11:].split("||")
                if len(p) == 2 and os.path.exists(p[0]): os.rename(p[0], p[1])
            except Exception: pass
        elif action_data.startswith("setting:"):
            parts = action_data.split(":")
            if parts[1] == "mousespeed":
                try: ctypes.windll.user32.SystemParametersInfoW(0x0071, 0, int(parts[2]), 0)
                except Exception: pass
            elif parts[1] == "theme":
                try:
                    reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 0, winreg.KEY_SET_VALUE)
                    val = 0 if parts[2] == "dark" else 1
                    winreg.SetValueEx(reg, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
                    winreg.SetValueEx(reg, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)
                    winreg.CloseKey(reg)
                    ctypes.windll.user32.SendMessageW(0xFFFF, 0x001A, 0, "Environment")
                except Exception: pass
            elif parts[1] == "brightness":
                try: subprocess.run(["powershell", "-Command", f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {int(parts[2])})"], capture_output=True, creationflags=0x08000000)
                except Exception: pass
            elif parts[1] == "wallpaper":
                try: ctypes.windll.user32.SystemParametersInfoW(20, 0, ":".join(parts[2:]), 3)
                except Exception: pass
            elif parts[1] == "timeout":
                try: subprocess.run(f"powercfg /change {parts[2]}-timeout-ac {int(parts[3])}", shell=True, creationflags=0x08000000)
                except Exception: pass
            elif parts[1] == "volume":
                if parts[2] in ("mute", "unmute"):
                    ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0); ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
                elif parts[2] == "up":
                    for _ in range(5): ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0); ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
                elif parts[2] == "down":
                    for _ in range(5): ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0); ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    font_path = os.path.join(os.path.dirname(__file__), "digital-7.ttf") if "__file__" in locals() else "digital-7.ttf"
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)
    
    widget = FlowWidget()
    sys.exit(app.exec())