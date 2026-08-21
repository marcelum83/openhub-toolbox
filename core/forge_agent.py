"""
OpenHub Forge Agent
Allows generating and self-mutating Kivy tools on the fly using Gemini API or local Ollama.
"""
import os
import re
import ast
import json
import threading
import urllib.request
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, StringProperty

class ForgeAgent(EventDispatcher):
    is_generating = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_agent_result')
        self.register_event_type('on_agent_error')
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

    def on_agent_result(self, code, explanation):
        pass

    def on_agent_error(self, error_message):
        pass

    def generate_or_mutate_tool(self, prompt, current_code=""):
        """Background thread generation loop."""
        if self.is_generating:
            return
        self.is_generating = True
        t = threading.Thread(target=self._run_loop, args=(prompt, current_code))
        t.daemon = True
        t.start()

    def _run_loop(self, prompt, current_code):
        system_prompt = """You are an expert Kivy and Python developer embedded in OpenHub.
Your task is to generate or mutate a standalone OpenHub module widget.

RULES:
1. Define a class named `OpenHubModule` that inherits from `BoxLayout` or another Kivy layout.
2. Implement `def on_load(self, host_api):` to store `self.host = host_api` if needed.
3. Keep the UI clean, modern, touch-friendly, and responsive for a mobile screen (9:16 or landscape).
4. Return the complete, runnable Python code wrapped in ```python ... ```.
5. Provide a short 1-2 sentence explanation of your design choices before or after the code block.
"""
        user_message = f"User Request: {prompt}"
        if current_code and current_code.strip():
            user_message += f"\n\nCurrent Working Code to mutate:\n```python\n{current_code}\n```"

        full_prompt = f"{system_prompt}\n\n{user_message}"
        response_text = ""
        error_msg = ""

        # Try Gemini API if key present
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

        # Fallback to local Ollama if Gemini not available or failed
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
                    error_msg = f"Ollama query failed: {e}"

        # If both fail, use smart template generator
        if not response_text:
            response_text = self._fallback_template(prompt)

        # Extract code and validate syntax
        code = self._extract_code(response_text)
        explanation = self._extract_explanation(response_text)

        if not self._is_valid_python(code):
            Clock.schedule_once(lambda dt: self.dispatch('on_agent_error', "Generated code failed Python syntax validation."), 0.1)
        else:
            Clock.schedule_once(lambda dt: self._deliver_result(code, explanation), 0.1)

    def _deliver_result(self, code, explanation):
        self.is_generating = False
        self.dispatch('on_agent_result', code, explanation)

    def _extract_code(self, text):
        match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
        return match.group(1).strip() if match else text.strip()

    def _extract_explanation(self, text):
        cleaned = re.sub(r"```python\s*.*?\s*```", "", text, flags=re.DOTALL).strip()
        lines = [l for l in cleaned.split("\n") if l.strip()]
        return "\n".join(lines[:3]) if lines else "Module created successfully."

    def _is_valid_python(self, code):
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _fallback_template(self, prompt):
        return f"""I have generated a starter interactive module based on "{prompt}".

```python
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.graphics import Color, RoundedRectangle

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=15, **kwargs)
        
        self.add_widget(Label(
            text="{prompt.title()}",
            font_size="24sp",
            size_hint_y=None,
            height=50,
            color=(0.02, 0.71, 0.83, 1)
        ))
        
        self.value_label = Label(
            text="Value: 50.0",
            font_size="18sp",
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.value_label)
        
        self.slider = Slider(min=0, max=100, value=50)
        self.slider.bind(value=self.on_slider_change)
        self.add_widget(self.slider)
        
        btn = Button(
            text="Execute Action",
            size_hint_y=None,
            height=55,
            background_color=(0.54, 0.36, 0.96, 1)
        )
        btn.bind(on_release=self.on_btn_click)
        self.add_widget(btn)

    def on_load(self, host_api):
        self.host = host_api
        if self.host:
            self.host.log("Custom module loaded.")

    def on_slider_change(self, instance, value):
        self.value_label.text = f"Value: {{value:.1f}}"

    def on_btn_click(self, instance):
        if hasattr(self, 'host') and self.host and self.host.hardware:
            self.host.hardware.vibrate(40)
        self.value_label.text = f"Action Triggered at {{self.slider.value:.1f}}!"
```
"""
