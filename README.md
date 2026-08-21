# 🌌 OpenHub

> **Programmable Physical Toolbox & Dynamic Module Host for Google Pixel 7a & Linux.**

OpenHub is a lightweight mobile host environment built on Python and Kivy/KivyMD. Instead of compiling a sealed application every time you create or tweak a tool, the OpenHub host is compiled once to your device. All capabilities are dynamic, interpreted **modules** that can be created on the fly, edited in-app, or pulled from GitHub.

---

## 🛠️ The 2 Cores

### 1. The Deck (Toolbox Launcher)
* Dynamically scans and renders all tools in `modules/`.
* Category filters: `Tools`, `Field`, `Agents`, `Experiments`, `Scratch`.
* Search bar & instant launch into a sandboxed host viewport with `[◀ BACK]` navigation.

### 2. The Forge (In-App Studio & Agentic Self-Mutator)
* **Pydroid-like Live Editor:** Write and tweak Python/Kivy code directly on your Pixel 7a.
* **`[▶ RUN LIVE]`:** Instantly mounts and tests your script.
* **Agentic Chat & Mutation:** Prompt Gemini or local Ollama (*"Make me a water tank volume calculator with sliders for radius and height"*), which generates verified Kivy code and hot-reloads it.
* **`[💾 SAVE TO TOOLBOX]`:** Automatically packages the active script into a permanent module with `manifest.json`.

---

## 📦 Foundational Physical Tools Included

1. **🟢 Spirit Level (`modules/level/`):** 2-axis visual bubble level with pitch/roll degree meters, zero-calibration, and haptic level lock.
2. **⏱️ Haptic Metronome (`modules/metronome/`):** BPM slider, tap tempo, time signatures (2/4, 3/4, 4/4, 6/8), visual beat dots, and heavy/light haptic pulses.
3. **📐 Universal Unit Converter (`modules/converter/`):** Multi-dimensional matrix covering Length, Mass/Lunar Weight, Volume, Pressure, and Temperature.
4. **🧭 Digital Compass (`modules/compass/`):** Magnetometer azimuth degrees with cardinal orientation pointers.
5. **⏱️ Precision Stopwatch (`modules/stopwatch/`):** Millisecond timer with split lap tracking.
6. **🔊 Sound Level Meter (`modules/decibel/`):** Acoustic sound pressure (dB) meter with visual gauge and peak hold tracking.

---

## 🖥️ Running on Linux Desktop

```bash
cd /home/mike/Documents/pixel
bash run.sh
```

All sensor tools automatically run in **Desktop Simulation Mode** when hardware sensors are absent, allowing instant desktop testing with mouse and keyboard.

---

## 📱 Compiling for Google Pixel 7a (Android)

Plug in your Pixel 7a via USB, enable **USB Debugging** in Developer Options, and run:

```bash
buildozer android debug run
```

To watch live logs from the phone:
```bash
buildozer android logcat
```

---

## 🧩 Creating a New Module

Every module lives in `modules/<module_name>/`:

```text
modules/my_tool/
├── manifest.json
└── main.py
```

### `manifest.json`
```json
{
  "id": "my_tool",
  "name": "My Tool",
  "version": "1.0.0",
  "author": "mike",
  "category": "Tools",
  "description": "My custom utility tool.",
  "entrypoint": "main.py",
  "trust_level": "trusted"
}
```

### `main.py`
```python
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.add_widget(Label(text="Hello from My Custom Tool!"))

    def on_load(self, host_api):
        self.host = host_api
        self.host.log("Module loaded!")
```
