"""
OpenHub Conversational Agent Engine
Supports Local Workstation Ollama (qwen2.5-coder:7b, gemma4:e4b) and Gemini 1.5 Flash.
Manages conversation history, system context, sensor injection, and code artifact extraction.
"""
import os
import re
import json
import time
import threading
import urllib.request
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, StringProperty, ListProperty
from kivy.clock import Clock

DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"

AGENT_SYSTEM_PROMPT = """You are the OpenHub Agent, a brilliant embedded AI companion and physical tool architect for the Nexus mobile ecosystem.
You assist the user in two modes:
1. CONVERSATION & ANALYSIS: Answer questions thoughtfully, clearly, and concisely. If sensor data is provided, explain the readings.
2. TOOL CREATION: When the user asks for a new tool, app, game, or utility, generate a complete, beautiful, and fully working Kivy Python module wrapped in ```python ... ```.

### CRITICAL ARCHITECTURE RULES:
1. MANDATORY: ALWAYS define `class OpenHubModule(BoxLayout):` as the root entrypoint widget.
2. FORBIDDEN: NEVER define `class ...App(App):` or call `.run()`. OpenHub is an embedded modular runtime.
3. ANIMATIONS & CANVAS: When building animations, games, or physics (e.g. bouncing balls, cellular automata, dials):
   - Store positions/velocities on `self` (`self.vx`, `self.vy`, `self.ball_x`, `self.ball_y`), NEVER as local variables inside `update()`.
   - In your custom `Widget`, clear and redraw `self.canvas` in a `redraw()` method called on every frame tick (`Clock.schedule_interval(self.update, 1/60)`).
   - In `on_resume(self)` start your Clock interval, and in `on_pause(self)` cancel it.
4. TIMERS & TIMING TESTS:
   - Use `time.perf_counter()` to measure exact timestamps `(time.perf_counter() - start) * 1000`.
   - NEVER create recursive `Clock.schedule_once` loops that re-schedule themselves indefinitely without cancellation.
   - Store active `ClockEvent` objects and cancel them in `on_pause()`.
   - NEVER disable the action button when prompting the user to react.

### HARDWARE APIS AVAILABLE VIA `self.host.hardware`:
Inside `on_load(self, host_api)`: store `self.host = host_api`.
- `self.host.hardware.vibrate(duration_ms=35)`: triggers tactile haptic feedback.
- `self.host.hardware.get_compass_heading()`: returns `(heading_deg, is_sim)`.
- `self.host.hardware.get_orientation_angles()`: returns `(pitch_deg, roll_deg, is_sim)`.
- `self.host.hardware.get_lux()`: returns `(lux_float, is_sim)`.
- `self.host.hardware.set_torch(True/False)`: controls the physical LED flashlight.
- `self.host.hardware.get_audio_level_db()`: returns ambient decibels.

### CANONICAL MODULE STRUCTURE EXAMPLE:
```python
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.metrics import dp, sp
from kivy.clock import Clock

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(12), **kwargs)
        self.host = None
        self.count = 0

        # Title
        self.lbl_title = Label(
            text="✨ Module Title",
            font_size="22sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            size_hint_y=None,
            height=dp(40)
        )
        self.add_widget(self.lbl_title)

        # Primary Display
        self.lbl_display = Label(
            text="Ready",
            font_size="28sp",
            bold=True,
            color=(0.95, 0.95, 0.97, 1),
            size_hint_y=0.5
        )
        self.add_widget(self.lbl_display)

        # Interactive Button
        self.btn_action = Button(
            text="⚡ TRIGGER ACTION",
            size_hint_y=None,
            height=dp(56),
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="16sp",
            always_release=True
        )
        self.btn_action.bind(on_release=self.on_btn_pressed)
        self.add_widget(self.btn_action)

    def on_load(self, host_api):
        self.host = host_api

    def on_resume(self):
        pass

    def on_pause(self):
        pass

    def on_btn_pressed(self, *args):
        self.count += 1
        self.lbl_display.text = f"Count: {self.count}"
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(30)
```
Provide a short 1-sentence summary of what you created or changed. Always return the complete runnable code in ```python ... ``` without placeholders."""

class AgentChatEngine(EventDispatcher):
    is_busy = BooleanProperty(False)
    current_provider = StringProperty("ollama") # "ollama", "simple_agent", "firebase", or "gemini"
    current_model = StringProperty(DEFAULT_OLLAMA_MODEL)
    active_layer = StringProperty("L6_Prosecution")
    
    def __init__(self, host_bridge=None, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_agent_message')
        self.register_event_type('on_agent_error')
        self.host_bridge = host_bridge
        self.messages = [] # [{"role": "user"|"assistant", "content": str, "tool_code": str|None}]
        self.server_host = "10.112.214.29"
        self.ollama_port = "11434"
        self.gemini_api_key = ""
        self.active_conversation_id = None
        self.load_config()

    def on_agent_message(self, role, content, tool_code=None, tool_title="Custom Tool"):
        pass

    def on_agent_error(self, error_message):
        pass

    def load_config(self):
        try:
            settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    host_full = data.get("server_host", "10.112.214.29:8080")
                    self.server_host = host_full.split(":")[0]
                    self.gemini_api_key = data.get("gemini_api_key", "").strip()
                    self.current_provider = data.get("llm_provider", "ollama")
                    self.current_model = data.get("ollama_model", DEFAULT_OLLAMA_MODEL)
        except Exception as e:
            print(f"[AgentChatEngine] Config load error: {e}")

    def save_config(self, provider=None, model=None):
        if provider:
            self.current_provider = provider
        if model:
            self.current_model = model
        try:
            settings_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")
            data = {}
            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["llm_provider"] = self.current_provider
            data["ollama_model"] = self.current_model
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def send_user_message(self, user_text):
        if self.is_busy or not user_text.strip():
            return
        
        self.load_config()
        self.is_busy = True
        
        # Append user message to history
        msg_obj = {"role": "user", "content": user_text.strip(), "tool_code": None}
        self.messages.append(msg_obj)
        self.dispatch('on_agent_message', 'user', user_text.strip(), None, "")

        # Run query in worker thread
        t = threading.Thread(target=self._query_worker, args=(user_text,))
        t.daemon = True
        t.start()

    def _get_sensor_snapshot(self):
        if not self.host_bridge:
            return ""
        try:
            h, _ = self.host_bridge.get_compass_heading()
            p, r, _ = self.host_bridge.get_orientation_angles()
            lux, _ = self.host_bridge.get_lux()
            db = self.host_bridge.get_audio_level_db()
            return f"Compass Heading={h:.1f}°, Pitch={p:.1f}°, Roll={r:.1f}°, Ambient Lux={lux:.0f} lx, Mic={db:.0f} dB"
        except Exception:
            return ""

    def _query_worker(self, user_prompt):
        sensor_info = self._get_sensor_snapshot()
        sys_context = AGENT_SYSTEM_PROMPT + (f"\n[Live Device Sensor State: {sensor_info}]" if sensor_info else "")
        
        response_text = ""
        error_text = ""

        if self.current_provider == "simple_agent":
            response_text, error_text = self._query_simple_agent(user_prompt, sensor_info)
            if error_text:
                print(f"[AgentChatEngine] SimpleAgent error ({error_text}), falling back to Ollama...")
                response_text, error_text = self._query_ollama(user_prompt, sys_context)
        elif self.current_provider == "firebase":
            response_text, error_text = self._query_firebase_telepathy(user_prompt, sensor_info)
            if error_text:
                print(f"[AgentChatEngine] Firebase Telepathy error ({error_text}), falling back to Gemini...")
                response_text, error_text = self._query_gemini(user_prompt, sys_context)
        elif self.current_provider == "ollama":
            response_text, error_text = self._query_ollama(user_prompt, sys_context)
            # If Ollama fails, auto-fallback to Gemini if key exists
            if error_text and self.gemini_api_key:
                print(f"[AgentChatEngine] Ollama failed ({error_text}), falling back to Gemini Cloud...")
                response_text, error_text = self._query_gemini(user_prompt, sys_context)
        else:
            response_text, error_text = self._query_gemini(user_prompt, sys_context)
            if error_text:
                print(f"[AgentChatEngine] Gemini failed ({error_text}), falling back to local Ollama...")
                response_text, error_text = self._query_ollama(user_prompt, sys_context)

        Clock.schedule_once(lambda dt: self._on_worker_finished(response_text, error_text), 0)

    def _query_firebase_telepathy(self, user_prompt, sensor_info):
        url = "https://firestore.googleapis.com/v1/projects/nexus-ops-2026/databases/(default)/documents/agent_commands"
        payload = {
            "fields": {
                "target_app": {"stringValue": "simple_agent"},
                "action": {"stringValue": "prompt"},
                "status": {"stringValue": "PENDING"},
                "timestamp": {"integerValue": str(int(time.time() * 1000))},
                "payload": {
                    "mapValue": {
                        "fields": {
                            "text": {"stringValue": user_prompt},
                            "sensor_context": {"stringValue": sensor_info}
                        }
                    }
                }
            }
        }
        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                doc_path = data.get("name", "")
                doc_name = doc_path.split("/")[-1]

            # Poll for remote workstation response (up to 15 seconds)
            poll_url = f"https://firestore.googleapis.com/v1/{doc_path}"
            for _ in range(10):
                time.sleep(1.5)
                try:
                    p_req = urllib.request.Request(poll_url)
                    with urllib.request.urlopen(p_req, timeout=4) as p_resp:
                        p_data = json.loads(p_resp.read().decode('utf-8'))
                        fields = p_data.get("fields", {})
                        st = fields.get("status", {}).get("stringValue", "")
                        if st == "COMPLETED":
                            reply = fields.get("response", {}).get("stringValue", "")
                            if reply:
                                return reply, ""
                        elif st == "ERROR":
                            err = fields.get("error", {}).get("stringValue", "Remote agent execution failed.")
                            return "", err
                except Exception:
                    pass

            return f"📡 **Command Dispatched via Cloud Telepathy!**\nDoc: `{doc_name}`\nSimpleAgent on your workstation received this prompt. If SimpleAgent is running, it will complete shortly.", ""
        except Exception as e:
            return "", f"Firebase Telepathy error: {e}"

    def _query_simple_agent(self, user_prompt, sensor_info):
        url = f"http://{self.server_host}:8080/api/simple_agent/chat"
        # Format full conversation history (up to last 10 messages)
        history = []
        for m in self.messages[-10:]:
            history.append({"role": m["role"], "content": m["content"]})

        payload = json.dumps({
            "prompt": user_prompt,
            "history": history,
            "conversation_id": self.active_conversation_id,
            "sensor_context": sensor_info,
            "model": self.current_model
        }).encode('utf-8')
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if "conversation_id" in data and data["conversation_id"]:
                    self.active_conversation_id = data["conversation_id"]
                if "active_layer" in data and data["active_layer"]:
                    self.active_layer = data["active_layer"]

                resp_text = data.get("response", "")
                tools_run = data.get("tools_executed", [])
                if tools_run and not resp_text.startswith("🔧"):
                    summary = ", ".join([t.get("name", "tool") for t in tools_run])
                    resp_text = f"🔧 *[Tools executed: {summary}]*\n\n{resp_text}"
                return resp_text, ""
        except Exception as e:
            return "", f"SimpleAgent API error: {e}"

    def get_active_layer(self):
        url = f"http://{self.server_host}:8080/api/simple_agent/layer"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                layer = data.get("active_layer", "L6_Prosecution")
                self.active_layer = layer
                return layer
        except Exception:
            return getattr(self, "active_layer", "L6_Prosecution")

    def set_active_layer(self, layer_str):
        url = f"http://{self.server_host}:8080/api/simple_agent/layer"
        payload = json.dumps({"layer": layer_str}).encode('utf-8')
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                layer = data.get("active_layer", layer_str)
                self.active_layer = layer
                return layer
        except Exception:
            self.active_layer = layer_str
            return layer_str

    def _query_ollama(self, user_prompt, sys_prompt):
        url = f"http://{self.server_host}:{self.ollama_port}/api/chat"
        history = [{"role": "system", "content": sys_prompt}]
        for m in self.messages[-6:]:
            history.append({"role": m["role"], "content": m["content"]})
        
        payload = json.dumps({
            "model": self.current_model,
            "messages": history,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9
            }
        }).encode('utf-8')

        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get("message", {}).get("content", ""), ""
        except Exception as e:
            return "", f"Local Ollama error ({self.server_host}:{self.ollama_port}): {e}"

    def _query_gemini(self, user_prompt, sys_prompt):
        if not self.gemini_api_key:
            return "", "No Gemini API Key found in settings."
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        contents = []
        contents.append({"role": "user", "parts": [{"text": sys_prompt}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I am the OpenHub Assistant ready to chat and generate mobile tools."}]})
        for m in self.messages[-6:]:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        payload = json.dumps({"contents": contents}).encode('utf-8')
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['candidates'][0]['content']['parts'][0]['text'], ""
        except Exception as e:
            return "", f"Gemini API error: {e}"

    def _on_worker_finished(self, response_text, error_text):
        self.is_busy = False
        if error_text and not response_text:
            self.dispatch('on_agent_error', error_text)
            return

        # Extract code block if present
        tool_code = None
        tool_title = "Generated Tool"
        
        code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
        if code_match:
            raw_code = code_match.group(1)
            try:
                from core.sanitizer import CodeSanitizer
                tool_code = CodeSanitizer.sanitize(raw_code)
            except Exception:
                tool_code = raw_code

            # Try to infer a nice title
            for line in response_text.splitlines()[:5]:
                if any(kw in line.lower() for kw in ["tool", "app", "widget", "calculator", "game", "timer"]):
                    clean = re.sub(r'[^a-zA-Z0-9 ]', '', line).strip()
                    if clean:
                        tool_title = clean[:24]
                        break

        # Save assistant message
        self.messages.append({
            "role": "assistant",
            "content": response_text,
            "tool_code": tool_code
        })
        self.dispatch('on_agent_message', 'assistant', response_text, tool_code, tool_title)

    def clear_history(self):
        self.messages = []
        self.active_conversation_id = None
