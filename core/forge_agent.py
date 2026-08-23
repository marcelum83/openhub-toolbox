"""
OpenHub Forge Engine
Autonomous AI engineering backend that generates, mutates, fixes, and explains Kivy modules.
Works across Gemini API, local Ollama endpoints, or smart offline template synthesizers.
"""
import os
import re
import ast
import json
import threading
import urllib.request
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty

class ForgeEngine(EventDispatcher):
    is_working = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_forge_success')
        self.register_event_type('on_forge_error')
        self.gemini_api_key = self.load_api_key()
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

    def load_api_key(self):
        try:
            settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    key = data.get("gemini_api_key", "").strip()
                    if key:
                        return key
        except Exception:
            pass
        return os.getenv("GEMINI_API_KEY", "")

    def on_forge_success(self, action, code, explanation):
        pass

    def on_forge_error(self, action, error_message):
        pass

    # --- Core Public API ---

    def generate(self, prompt):
        """Generate a brand new Kivy tool from a natural language prompt."""
        self._dispatch_async("generate", prompt=prompt)

    def mutate(self, current_code, instruction):
        """Mutate and extend an existing Kivy code buffer with a new instruction."""
        self._dispatch_async("mutate", prompt=instruction, current_code=current_code)

    def fix(self, current_code, error_message):
        """Diagnose and fix a syntax or runtime error in the code."""
        prompt = f"Fix the following error in the Kivy application:\nError: {error_message}"
        self._dispatch_async("fix", prompt=prompt, current_code=current_code)

    # --- Internal Background Loop ---

    def _dispatch_async(self, action, prompt="", current_code=""):
        if self.is_working:
            return
        self.is_working = True
        t = threading.Thread(target=self._worker, args=(action, prompt, current_code))
        t.daemon = True
        t.start()

    def _worker(self, action, prompt, current_code):
        system_prompt = """You are an expert Kivy and Python developer embedded in OpenHub.
Your task is to write or modify a standalone, responsive Kivy widget or application.

RULES:
1. MANDATORY: Define `class OpenHubModule(BoxLayout):` as the root entrypoint.
2. FORBIDDEN: Never define `class ...App(App):` or call `App().run()`.
3. ANIMATIONS & CANVAS: Store state/velocity as instance variables (`self.vx`, `self.ball_x`), and redraw the canvas on each `Clock.schedule_interval` tick.
4. Use responsive metrics `dp()` and `sp()` from `kivy.metrics`.
5. Set `always_release=True` on buttons for smooth touchscreen activation.
6. Implement `on_load(self, host_api)` to access hardware if needed (`self.host.hardware.vibrate()`, etc.).
7. Return the complete, runnable Python code wrapped in ```python ... ``` without placeholders.

EXAMPLE TEMPLATE:
```python
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp, sp

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(12), **kwargs)
        self.host = None
        self.add_widget(Label(text="✨ Custom Tool", font_size="22sp", bold=True, size_hint_y=None, height=dp(40)))
        btn = Button(text="⚡ RUN", size_hint_y=None, height=dp(54), always_release=True, bold=True)
        btn.bind(on_release=self.on_btn)
        self.add_widget(btn)

    def on_load(self, host_api):
        self.host = host_api

    def on_btn(self, *args):
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(30)
```
Provide a short 1-sentence summary of what you created or changed.
"""
        user_message = f"Action: {action.upper()}\nInstruction: {prompt}"
        if current_code and current_code.strip():
            user_message += f"\n\nExisting Code:\n```python\n{current_code}\n```"

        full_prompt = f"{system_prompt}\n\n{user_message}"
        response_text = ""
        error_msg = ""

        # 1. Try Gemini API
        if self.gemini_api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
                payload = json.dumps({
                    "contents": [{"parts": [{"text": full_prompt}]}]
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=20) as res:
                    res_data = json.loads(res.read().decode('utf-8'))
                    response_text = res_data['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                error_msg = f"Gemini API error: {e}"

        # 2. Try Ollama
        if not response_text:
            try:
                payload = json.dumps({
                    "model": self.ollama_model,
                    "prompt": full_prompt,
                    "stream": False
                }).encode('utf-8')
                req = urllib.request.Request(self.ollama_url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as res:
                    res_data = json.loads(res.read().decode('utf-8'))
                    response_text = res_data.get("response", "")
            except Exception as e:
                if not error_msg:
                    error_msg = f"Ollama error: {e}"

        # 3. Fallback Synthesizer
        if not response_text:
            response_text = self._fallback_synthesizer(prompt, current_code)

        code = self._extract_code(response_text)
        explanation = self._extract_explanation(response_text)

        if not self._is_valid_python(code):
            Clock.schedule_once(lambda dt: self._deliver_error(action, "Generated code has syntax errors."), 0.1)
        else:
            Clock.schedule_once(lambda dt: self._deliver_success(action, code, explanation), 0.1)

    def _deliver_success(self, action, code, explanation):
        self.is_working = False
        self.dispatch('on_forge_success', action, code, explanation)

    def _deliver_error(self, action, error_message):
        self.is_working = False
        self.dispatch('on_forge_error', action, error_message)

    def _extract_code(self, text):
        match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
        raw = match.group(1).strip() if match else text.strip()
        try:
            from core.sanitizer import CodeSanitizer
            return CodeSanitizer.sanitize(raw)
        except Exception:
            return raw

    def _extract_explanation(self, text):
        cleaned = re.sub(r"```python\s*.*?\s*```", "", text, flags=re.DOTALL).strip()
        lines = [l for l in cleaned.split("\n") if l.strip()]
        return lines[0] if lines else "Operation completed successfully."

    def _is_valid_python(self, code):
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _fallback_synthesizer(self, prompt, current_code=""):
        return f"""Created interactive tool for: {prompt}

```python
import math
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=16, spacing=12, **kwargs)
        
        # Header
        self.add_widget(Label(
            text="{prompt.title()}",
            font_size="22sp",
            bold=True,
            size_hint_y=None,
            height=40,
            color=(0.02, 0.71, 0.83, 1)
        ))
        
        # Parameter 1: Diameter / Value A
        self.add_widget(Label(text="Primary Input (e.g. Dimension A):", size_hint_y=None, height=25, color=(0.7,0.7,0.8,1)))
        self.val_a = Slider(min=1, max=100, value=20, size_hint_y=None, height=40)
        self.val_a.bind(value=self.recalculate)
        self.add_widget(self.val_a)
        
        # Parameter 2: Height / Value B
        self.add_widget(Label(text="Secondary Input (e.g. Dimension B):", size_hint_y=None, height=25, color=(0.7,0.7,0.8,1)))
        self.val_b = Slider(min=1, max=100, value=50, size_hint_y=None, height=40)
        self.val_b.bind(value=self.recalculate)
        self.add_widget(self.val_b)
        
        # Output Readout Card
        self.lbl_result = Label(
            text="Result: Calculating...",
            font_size="24sp",
            bold=True,
            color=(0.15, 0.68, 0.38, 1),
            size_hint_y=0.4
        )
        self.add_widget(self.lbl_result)
        
        self.recalculate()

    def on_load(self, host_api):
        self.host = host_api

    def recalculate(self, *args):
        a = self.val_a.value
        b = self.val_b.value
        # Generic volumetric / ratio computation
        output = math.pi * ((a / 2.0) ** 2) * b
        litres = output * 0.001
        gallons = litres * 0.264172
        self.lbl_result.text = f"{{litres:.1f}} Litres\\n({{gallons:.1f}} Gallons)"
```
"""

# Backwards compatibility alias
ForgeAgent = ForgeEngine
