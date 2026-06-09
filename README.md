# Flow HUD: AI-Integrated Desktop Search Widget & System Engine

Flow HUD is an ultra-fast, multi-threaded, keyboard-driven desktop productivity launcher and overlay ecosystem built using Python and PyQt6. Running completely decoupled from standard shell constraints, it brings localized artificial intelligence, raw hardware metric telemetry, system-level automation hooks, and deep application protocol routing into a singular unified command interface triggered globally.

---

## 🗺️ Architectural Priority Matrix

The interface doesn't just display results sequentially—it uses a strict **Hierarchical Priority Matrix** via an insertion-sort layer inside the input engine. When you query the launcher, tasks are evaluated, executed across asynchronous background threads, and organized visually by category weight:

| Priority Class | Weight | Visual Sorting Tier | Example Components |
| :--- | :---: | :--- | :--- |
| **Priority 0** | Top | Immediate Eye-Line | Local LLM text streams, AI "thinking" micro-animations, text-to-clipboard actions. |
| **Priority 1** | Middle | Core Workspace Utilities | Native app shortcuts (`.lnk`), multi-threaded disk utilities, Windows control panel hooks, custom HUD monitors, countdown timers. |
| **Priority 2** | Bottom | Ambient / Cloud Fallbacks | Remote URL navigation, raw Google lookups, deep web links. |

---

## ⚡ Core Functional Deep-Dive

### 1. 🤖 Asynchronous Local LLM Engine
* **How it Works**: Driven by an independent execution thread (`OllamaWorker`), the widget bypasses cloud APIs entirely by opening an explicit HTTP pipe to your local loopback address (`http://localhost:11434`). It feeds instructions to the model with highly specialized hyper-parameters optimized for rapid, direct desktop responses.
* **Stream Optimization**: Constrains generation lengths via `num_predict: 50` and tempers creativity via `temperature: 0.6` to guarantee snappy, 1-to-2 sentence conversational responses without locking the UI thread.
* **Built-in Fast Replies**: Intercepts classic conversational pleasantries via native Regular Expressions before triggering the LLM, eliminating computing overhead for routine greetings (`hi`, `bye`, `thanks`, etc.).

### 2. 🎵 Dynamic Environment & Registry-Aware Spotify Router
* **How it Works**: The script runs an advanced environment check before spinning up music commands:
  1. It performs an initial lookup inside the active start menu shortcut map.
  2. It attempts to open the local Windows Registry path `HKEY_CLASSES_ROOT\spotify`.
  3. It explicitly tests file visibility for standalone configurations inside path directories (`%APPDATA%\Spotify\Spotify.exe` and `%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe`).
* **Result Routing**: If the native app is verified, the command wraps your text query into a URI format and executes `os.startfile(spotify:search:...)` to directly control your local desktop player application. If absent, it gracefully switches to a secure, modern web browser player instance.

### 3. 📊 High-Performance Transparent HUD Elements
* **Real-time FPS & Latency Display**: When toggled, an unbordered, fully alpha-transparent `FPSPingWidget` anchors to your desktop context. Frame rates are calculated precisely using raw monotonic clock offsets (`time.perf_counter()`), while internet latency issues non-blocking ICMP echo payloads to Google's primary DNS cluster (`8.8.8.8`) over low-level subprocess channels (`0x08000000` creation flags to hide console popups completely).
* **System Resource Monitors**: Tracks real-time, instantaneous processor utilization metrics and global physical memory load updates using a decoupled hardware telemetry daemon.

### 4. 📁 Non-Blocking Disk Operation Framework
* **How it Works**: Disk queries use an explicit multi-threaded crawler (`SearchWorker`). Instead of locking up your display during deep directory traversal, it handles drive walks via background processes, pushing real-time UI updates to your launcher window using a safe Qt event bus (`pyqtSignal`). It supports absolute path mappings as well as logical root queries (e.g., `D drive`).

---

## ⌨️ Global Keybindings & Controls

* **`Alt + Q`** (Global Hotkey): Toggles the entire environment. Fades the interface in or out smoothly using a 200ms `OutCubic` opacity transform curve.
* **`Arrow Up` / `Arrow Down`**: Cycles focus through the auto-sorted recommendation list items.
* **`Mouse Hover`**: Dynamically shifts active focus directly to the item beneath your cursor.
* **`Enter` / `Mouse Click`**: Executes the currently selected action and triggers an automated `OutExpo` window collapse, moving the launcher cleanly to the background.

---

## 📋 Comprehensive Command Reference Guide

Type these exact syntax patterns into the search bar to run any system macro instantly:

### ⚙️ Windows Environment & Settings Macros
| Command Query Intent | Exact Syntax / Pattern Examples | Underlying API Call / Action |
| :--- | :--- | :--- |
| **Audio Control** | `mute`, `unmute`, `volume up`, `volume down` | Emulates native VK hardware keys (`0xAD`, `0xAF`, `0xAE`) |
| **System Theme** | `turn on dark mode`, `set theme to light` | Edits Registry values directly under `...\Themes\Personalize` |
| **Display Brightness** | `set brightness to 80` | Evaluates via PowerShell WMI monitor classes |
| **Desktop Workspace** | `set wallpaper to C:\path\to\image.jpg` | Forces system redraw using Win32 `SystemParametersInfoW` |
| **Display Timeout** | `set screen timeout to 10` | Modifies AC power architecture configuration using `powercfg` |
| **System Standby** | `set sleep timeout to 30` | Modifies AC standby parameters using `powercfg` |
| **Peripheral Control** | `set mouse speed to max`, `set mouse speed to 10` | Adjusts underlying registry sensitivities via `User32.dll` |
| **Deep Link Settings** | `open wifi settings`, `bluetooth settings`, `display settings`, `windows update settings`, `sound settings`, `apps settings`, `storage settings` | Launches native Windows configuration pages via `ms-settings:` URI schemes |

### 📁 Threaded File Operations
| Operation | Command Syntax Examples | Target Paths / Resolution |
| :--- | :--- | :--- |
| **Create Folder** | `create folder Dev inside D drive`<br>`add directory Workspace` | Targeted directory or automatic fallback to the local user Desktop path |
| **Create File** | `create file log.txt inside C:\`<br>`add document report.docx` | Creates empty item structure and reveals it inside a new File Explorer tab |
| **Delete File** | `delete file test.tmp`<br>`remove document notes.txt` | Deep scans active storage drives to find matching asset targets and wipes them |
| **Delete Folder**| `delete folder Legacy inside E:\`<br>`remove directory Target` | Recursively drops all child trees using non-blocking structural standard calls |
| **Rename Asset**| `rename file old.txt to new.txt`<br>`edit folder Assets to Data inside D:\` | Maps explicit paths or dynamically parses drive roots to find and rename structures |

### 🛠️ Media, Overlays, Utility & Calculation Anchors
| Target Utility | Syntax Examples | Execution Result |
| :--- | :--- | :--- |
| **Spotify Control** | `play After Hours`<br>`spotify Interstellar Soundtrack`<br>`listen to lo-fi` | Runs systemic application analysis; spawns local client app context or web fallback player |
| **Performance HUD** | `fps`, `show ping`, `fps counter` | Toggles transparent hardware overlay anchored to top-right screen space |
| **System Statistics**| `system stats`, `show me my system stats` | Spawns real-time CPU/RAM consumption widget on bottom-left screen edge |
| **Countdown Timer** | `timer for 45s`<br>`set a timer for 10 mins`<br>`timer 2 hours` | Launches standalone vintage layout countdown clock; rings system chime on expiration |
| **Weather Engine** | `weather in Baku`<br>`weather forecast in London` | Parses weather conditions or full 7-day outlook maps using `wttr.in` endpoints |
| **Unit Converter** | `180 cm in inches`<br>`50 lbs in kg`<br>`12 inches in cm` | Displays metric/imperial conversions instantly using regex validation maps |
| **Web Navigation** | `open github`, `open youtube` | Appends secure top-level domain routes and spins up your default browser |
| **Global Search** | `google raw text queries here` | Forcibly triggers your default browser to launch an online search engine page |

---

## 🛠️ Step-by-Step Environment Deployment

### 1. Engine Dependency Installation
Your application leverages specialized operating system bindings. Install the explicit requirements via your terminal instance:
```bash
pip install PyQt6 keyboard psutil
