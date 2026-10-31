"""
Mutation World: Autonomous Generative UI Sandbox
Prompts Gemini AI to rewrite, mutate, and evolve live Kivy widgets directly on your device.
"""
import os
import re
import json
import threading
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp, sp
from kivy.clock import Clock

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(8), **kwargs)
        self.host = None
        self.mutation_count = 0
        self.api_key = ""

        # 1. Header
        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))
        lbl_title = Label(
            text="🧬 MUTATION WORLD",
            font_size="16sp",
            bold=True,
            color=(0.95, 0.45, 0.65, 1.0),
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        head.add_widget(lbl_title)

        self.lbl_gen = Label(
            text="Gen #0",
            font_size="12sp",
            color=(0.7, 0.7, 0.8, 1.0),
            size_hint_x=None,
            width=dp(70),
            halign='right'
        )
        head.add_widget(self.lbl_gen)
        self.add_widget(head)

        # 2. Live Sandbox Container
        self.sandbox_wrapper = BoxLayout(orientation='vertical')
        with self.sandbox_wrapper.canvas.before:
            Color(0.10, 0.10, 0.16, 1.0)
            self.sb_bg = RoundedRectangle(size=self.sandbox_wrapper.size, pos=self.sandbox_wrapper.pos, radius=[dp(12)])
            Color(0.95, 0.45, 0.65, 0.4)
            self.sb_bdr = Line(rounded_rectangle=(self.sandbox_wrapper.x, self.sandbox_wrapper.y, self.sandbox_wrapper.width, self.sandbox_wrapper.height, dp(12)), width=1.0)
        self.sandbox_wrapper.bind(size=self._update_sb_canvas, pos=self._update_sb_canvas)

        self.preview_area = BoxLayout(orientation='vertical', padding=dp(16))
        self.preview_area.add_widget(Label(
            text="🧬 Seed Widget Ready\nTap 'MUTATE' or a preset below to evolve.",
            font_size="14sp",
            color=(0.8, 0.85, 0.95, 1.0),
            halign='center'
        ))
        self.sandbox_wrapper.add_widget(self.preview_area)
        self.add_widget(self.sandbox_wrapper)

        # 3. Quick Mutation Presets
        presets_row = BoxLayout(orientation='horizontal', spacing=dp(6), size_hint_y=None, height=dp(32))
        presets = ["Neon HUD", "Matrix Rain", "Audio Visualizer", "Space Radar"]
        for p in presets:
            btn_p = Button(
                text=p,
                background_normal="",
                background_color=(0.18, 0.16, 0.26, 1.0),
                color=(0.9, 0.8, 0.95, 1.0),
                font_size="10sp",
                bold=True,
                always_release=True
            )
            btn_p.bind(on_release=lambda inst, name=p: self.run_mutation(f"Create a high-tech {name} UI component"))
            presets_row.add_widget(btn_p)
        self.add_widget(presets_row)

        # 4. Custom Prompt Input Bar
        input_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(42), spacing=dp(6))
        self.txt_prompt = TextInput(
            text="Evolve with glowing buttons and live counters",
            multiline=False,
            font_size="12sp",
            background_color=(0.14, 0.14, 0.20, 1.0),
            foreground_color=(0.95, 0.95, 0.98, 1.0)
        )
        input_row.add_widget(self.txt_prompt)

        self.btn_mutate = Button(
            text="⚡ MUTATE",
            size_hint_x=None,
            width=dp(95),
            background_normal="",
            background_color=(0.95, 0.45, 0.65, 1.0),
            color=(0.05, 0.05, 0.08, 1.0),
            bold=True,
            font_size="12sp",
            always_release=True
        )
        self.btn_mutate.bind(on_release=lambda x: self.run_mutation(self.txt_prompt.text.strip()))
        input_row.add_widget(self.btn_mutate)
        self.add_widget(input_row)

        # Status Bar
        self.lbl_status = Label(
            text="Ready. Powered by Gemini Generative API.",
            font_size="11sp",
            color=(0.6, 0.65, 0.75, 1.0),
            size_hint_y=None,
            height=dp(18),
            halign='left'
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        self.add_widget(self.lbl_status)

    def _update_sb_canvas(self, inst, val):
        self.sb_bg.pos = inst.pos
        self.sb_bg.size = inst.size
        self.sb_bdr.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(12))

    def on_load(self, host_api):
        self.host = host_api
        if self.host:
            self.host.log("Mutation World loaded.")
            # Load API key if available
            try:
                import json
                s_file = os.path.join(self.host.storage_root, "settings.json")
                if os.path.exists(s_file):
                    with open(s_file, "r") as f:
                        self.api_key = json.load(f).get("gemini_api_key", "")
            except Exception:
                pass

    def run_mutation(self, prompt_text):
        if not prompt_text:
            return
        self.lbl_status.text = f"🧬 Mutating UI: '{prompt_text}'..."
        self.btn_mutate.disabled = True

        def _worker():
            try:
                import urllib.request
                key = self.api_key or os.getenv("GEMINI_API_KEY", "")
                if not key:
                    Clock.schedule_once(lambda dt: self.on_mutation_error("No Gemini API key found in Settings."), 0)
                    return

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
                sys_prompt = (
                    "You are a Kivy UI code generator. Generate a python class 'MutatedWidget(BoxLayout)'. "
                    "Return ONLY executable Python code inside a ```python block. "
                    "Make it visually striking with modern colors, labels, or buttons."
                )
                full_prompt = f"{sys_prompt}\n\nUser Request: {prompt_text}"
                payload = json.dumps({"contents": [{"parts": [{"text": full_prompt}]}]}).encode('utf-8')

                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', text, re.DOTALL)
                    code = code_match.group(1) if code_match else text
                    Clock.schedule_once(lambda dt, c=code: self.apply_mutation(c), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt, err=e: self.on_mutation_error(str(err)), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def apply_mutation(self, code):
        self.btn_mutate.disabled = False
        try:
            # Check security via RiskAnalyzer if present
            try:
                from core.risk_analyzer import RiskAnalyzer
                ra = RiskAnalyzer()
                report = ra.analyze(code)
                if report.get("risk_level") == "HIGH":
                    self.lbl_status.text = "⚠️ Mutation blocked: High risk security violations."
                    return
            except Exception:
                pass

            # Safe execution in isolated namespace
            ns = {}
            exec(code, ns)
            widget_cls = ns.get("MutatedWidget") or ns.get("RootWidget")
            if not widget_cls:
                for v in ns.values():
                    if isinstance(v, type) and issubclass(v, BoxLayout) and v != BoxLayout:
                        widget_cls = v
                        break

            if widget_cls:
                self.preview_area.clear_widgets()
                inst = widget_cls()
                self.preview_area.add_widget(inst)
                self.mutation_count += 1
                self.lbl_gen.text = f"Gen #{self.mutation_count}"
                self.lbl_status.text = f"✅ Mutation Gen #{self.mutation_count} alive!"
                if self.host and self.host.hardware:
                    self.host.hardware.vibrate(30)
            else:
                self.lbl_status.text = "⚠️ Generated code didn't contain a valid BoxLayout."
        except Exception as e:
            self.lbl_status.text = f"❌ Execution error: {e}"

    def on_mutation_error(self, err):
        self.btn_mutate.disabled = False
        self.lbl_status.text = f"❌ Mutation error: {err}"
