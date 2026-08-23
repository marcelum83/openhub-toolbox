"""
OpenHub Module: Tactical Flashlight & Strobe Light
Physical LED camera torch control, high-speed variable strobe, emergency SOS Morse beacon, and screen lantern.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Ellipse, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp, sp

class FlashVisualizer(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_lit = False
        self.glow_color = (0.02, 0.71, 0.83, 1.0)
        self.bind(size=self.redraw, pos=self.redraw)

    def set_state(self, is_lit, color=(1.0, 0.9, 0.2, 1.0)):
        self.is_lit = is_lit
        self.glow_color = color
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            cx = self.x + self.width / 2.0
            cy = self.y + self.height / 2.0
            radius = min(self.width, self.height) * 0.38
            
            # Outer housing ring
            Color(0.12, 0.12, 0.18, 1.0)
            Ellipse(pos=(cx - radius - dp(12), cy - radius - dp(12)), size=((radius + dp(12)) * 2, (radius + dp(12)) * 2))
            
            if self.is_lit:
                # Glowing emitter
                Color(*self.glow_color)
                Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))
                Color(1, 1, 1, 0.8)
                Ellipse(pos=(cx - radius * 0.5, cy - radius * 0.5), size=(radius, radius))
            else:
                # Inactive reflector
                Color(0.2, 0.2, 0.28, 1.0)
                Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))
                Color(0.15, 0.15, 0.22, 1.0)
                Ellipse(pos=(cx - radius * 0.4, cy - radius * 0.4), size=(radius * 0.8, radius * 0.8))


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(12), **kwargs)
        self.host = None
        self.active_mode = "TORCH" # TORCH, STROBE, SOS, LANTERN
        self.is_active = False
        self.strobe_freq = 5.0 # Hz
        self.strobe_state = False
        self.strobe_event = None
        self.sos_step = 0
        self.sos_event = None
        self.lantern_color = (1.0, 1.0, 1.0, 1.0)

        # 1. Mode Switcher
        mode_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(44), spacing=dp(6))
        self.mode_btns = {}
        for m, label in [("TORCH", "🔦 TORCH"), ("STROBE", "⚡ STROBE"), ("SOS", "🆘 S.O.S."), ("LANTERN", "🏮 LANTERN")]:
            b = Button(
                text=label,
                background_normal="",
                background_color=(0.02, 0.71, 0.83, 1.0) if m == "TORCH" else (0.13, 0.13, 0.19, 1.0),
                color=(0.05, 0.05, 0.08, 1.0) if m == "TORCH" else (0.95, 0.95, 0.97, 1.0),
                bold=True,
                font_size="13sp",
                always_release=True
            )
            b.bind(on_release=lambda inst, mode=m: self.set_mode(mode))
            self.mode_btns[m] = b
            mode_box.add_widget(b)
        self.add_widget(mode_box)

        # 2. Main Center Display
        self.center_display = BoxLayout(orientation='vertical', spacing=dp(10))
        self.visualizer = FlashVisualizer(size_hint_y=0.65)
        self.center_display.add_widget(self.visualizer)

        self.lbl_status = Label(
            text="TORCH OFF",
            font_size="22sp",
            bold=True,
            color=(0.6, 0.6, 0.7, 1.0),
            size_hint_y=None,
            height=dp(36),
            halign='center'
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        self.center_display.add_widget(self.lbl_status)
        self.add_widget(self.center_display)

        # 3. Dynamic Controls Container
        self.ctrl_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(140), spacing=dp(8))
        self.add_widget(self.ctrl_box)
        
        self.build_torch_controls()

    def on_load(self, host_api):
        self.host = host_api

    def on_pause(self):
        self.stop_all()
        if self.host and self.host.hardware:
            self.host.hardware.set_torch(False)

    def on_resume(self):
        pass

    def stop_all(self):
        if self.strobe_event:
            self.strobe_event.cancel()
            self.strobe_event = None
        if self.sos_event:
            self.sos_event.cancel()
            self.sos_event = None
        self.is_active = False
        self.strobe_state = False
        if self.host and self.host.hardware:
            self.host.hardware.set_torch(False)
        self.visualizer.set_state(False)

    def set_mode(self, mode):
        self.stop_all()
        self.active_mode = mode
        for m, b in self.mode_btns.items():
            if m == mode:
                b.background_color = (0.02, 0.71, 0.83, 1.0)
                b.color = (0.05, 0.05, 0.08, 1.0)
            else:
                b.background_color = (0.13, 0.13, 0.19, 1.0)
                b.color = (0.95, 0.95, 0.97, 1.0)

        self.ctrl_box.clear_widgets()
        if mode == "TORCH":
            self.build_torch_controls()
            self.lbl_status.text = "TORCH READY"
        elif mode == "STROBE":
            self.build_strobe_controls()
            self.lbl_status.text = f"STROBE: {self.strobe_freq:.1f} Hz (IDLE)"
        elif mode == "SOS":
            self.build_sos_controls()
            self.lbl_status.text = "EMERGENCY S.O.S. (STANDBY)"
        elif mode == "LANTERN":
            self.build_lantern_controls()
            self.lbl_status.text = "SCREEN LANTERN"

    # --- TORCH MODE ---
    def build_torch_controls(self):
        self.btn_torch = Button(
            text="⚡ TOGGLE TORCH",
            font_size="18sp",
            bold=True,
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(64),
            always_release=True
        )
        self.btn_torch.bind(on_release=self.toggle_torch)
        self.ctrl_box.add_widget(self.btn_torch)

    def toggle_torch(self, *args):
        self.is_active = not self.is_active
        if self.host and self.host.hardware:
            self.host.hardware.set_torch(self.is_active)
            self.host.hardware.vibrate(30)
        
        self.visualizer.set_state(self.is_active, color=(1.0, 0.95, 0.4, 1.0))
        if self.is_active:
            self.lbl_status.text = "💡 TORCH ACTIVE (MAX POWER)"
            self.lbl_status.color = (0.15, 0.68, 0.38, 1.0)
            self.btn_torch.text = "🛑 TURN OFF"
            self.btn_torch.background_color = (0.91, 0.30, 0.24, 1.0)
        else:
            self.lbl_status.text = "TORCH OFF"
            self.lbl_status.color = (0.6, 0.6, 0.7, 1.0)
            self.btn_torch.text = "⚡ TURN ON"
            self.btn_torch.background_color = (0.15, 0.68, 0.38, 1.0)

    # --- STROBE MODE ---
    def build_strobe_controls(self):
        freq_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(10))
        self.lbl_freq = Label(text=f"Frequency: {self.strobe_freq:.1f} Hz", font_size="15sp", bold=True, size_hint_x=0.45)
        freq_row.add_widget(self.lbl_freq)
        
        slider = Slider(min=1.0, max=20.0, value=self.strobe_freq, size_hint_x=0.55)
        slider.bind(value=self.on_slider_freq)
        freq_row.add_widget(slider)
        self.ctrl_box.add_widget(freq_row)

        self.btn_strobe = Button(
            text="▶ START STROBE",
            font_size="17sp",
            bold=True,
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1.0),
            size_hint_y=None,
            height=dp(56),
            always_release=True
        )
        self.btn_strobe.bind(on_release=self.toggle_strobe)
        self.ctrl_box.add_widget(self.btn_strobe)

    def on_slider_freq(self, inst, val):
        self.strobe_freq = round(val, 1)
        if hasattr(self, 'lbl_freq'):
            self.lbl_freq.text = f"Frequency: {self.strobe_freq:.1f} Hz"
        if self.is_active:
            self.restart_strobe_timer()

    def toggle_strobe(self, *args):
        self.is_active = not self.is_active
        if self.is_active:
            self.btn_strobe.text = "🛑 STOP STROBE"
            self.btn_strobe.background_color = (0.91, 0.30, 0.24, 1.0)
            self.lbl_status.text = f"⚡ STROBE ACTIVE ({self.strobe_freq:.1f} Hz)"
            self.lbl_status.color = (0.54, 0.36, 0.96, 1.0)
            self.restart_strobe_timer()
        else:
            self.stop_all()
            self.btn_strobe.text = "▶ START STROBE"
            self.btn_strobe.background_color = (0.54, 0.36, 0.96, 1.0)
            self.lbl_status.text = "STROBE STOPPED"
            self.lbl_status.color = (0.6, 0.6, 0.7, 1.0)

    def restart_strobe_timer(self):
        if self.strobe_event:
            self.strobe_event.cancel()
        interval = 1.0 / (self.strobe_freq * 2.0)
        self.strobe_event = Clock.schedule_interval(self.strobe_tick, max(0.025, interval))

    def strobe_tick(self, dt):
        self.strobe_state = not self.strobe_state
        if self.host and self.host.hardware:
            self.host.hardware.set_torch(self.strobe_state)
        self.visualizer.set_state(self.strobe_state, color=(0.54, 0.36, 0.96, 1.0))

    # --- SOS MODE ---
    def build_sos_controls(self):
        lbl_info = Label(text="Emits international optical SOS: · · · — — — · · ·", font_size="13sp", color=(0.6, 0.6, 0.7, 1))
        self.ctrl_box.add_widget(lbl_info)

        self.btn_sos = Button(
            text="🆘 BROADCAST S.O.S.",
            font_size="17sp",
            bold=True,
            background_normal="",
            background_color=(0.91, 0.30, 0.24, 1.0),
            size_hint_y=None,
            height=dp(56),
            always_release=True
        )
        self.btn_sos.bind(on_release=self.toggle_sos)
        self.ctrl_box.add_widget(self.btn_sos)

    def toggle_sos(self, *args):
        self.is_active = not self.is_active
        if self.is_active:
            self.btn_sos.text = "🛑 CANCEL S.O.S."
            self.lbl_status.text = "🆘 BROADCASTING S.O.S."
            self.lbl_status.color = (0.91, 0.30, 0.24, 1.0)
            self.sos_step = 0
            # SOS timing: dot=0.2s, dash=0.6s, space=0.2s, letter_space=0.6s, word_space=1.4s
            self.sos_pattern = [
                (True, 0.2), (False, 0.2), (True, 0.2), (False, 0.2), (True, 0.2), (False, 0.6), # S (...)
                (True, 0.6), (False, 0.2), (True, 0.6), (False, 0.2), (True, 0.6), (False, 0.6), # O (---)
                (True, 0.2), (False, 0.2), (True, 0.2), (False, 0.2), (True, 0.2), (False, 1.2), # S (...)
            ]
            self.sos_next_tick(0)
        else:
            self.stop_all()
            self.btn_sos.text = "🆘 BROADCAST S.O.S."
            self.lbl_status.text = "S.O.S. STANDBY"
            self.lbl_status.color = (0.6, 0.6, 0.7, 1.0)

    def sos_next_tick(self, dt):
        if not self.is_active:
            return
        state, duration = self.sos_pattern[self.sos_step]
        if self.host and self.host.hardware:
            self.host.hardware.set_torch(state)
        self.visualizer.set_state(state, color=(0.91, 0.30, 0.24, 1.0))
        
        self.sos_step = (self.sos_step + 1) % len(self.sos_pattern)
        self.sos_event = Clock.schedule_once(self.sos_next_tick, duration)

    # --- LANTERN MODE ---
    def build_lantern_controls(self):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
        for col_name, rgb in [("WHITE", (1, 1, 1, 1)), ("WARM", (1, 0.85, 0.5, 1)), ("AMBER", (1, 0.6, 0.1, 1)), ("RED", (0.9, 0.2, 0.2, 1))]:
            b = Button(
                text=col_name,
                background_normal="",
                background_color=rgb,
                color=(0, 0, 0, 1) if col_name != "RED" else (1, 1, 1, 1),
                bold=True,
                font_size="13sp",
                always_release=True
            )
            b.bind(on_release=lambda inst, c=rgb, name=col_name: self.set_lantern_color(c, name))
            row.add_widget(b)
        self.ctrl_box.add_widget(row)

    def set_lantern_color(self, rgb, name):
        self.lantern_color = rgb
        self.visualizer.set_state(True, color=rgb)
        self.lbl_status.text = f"LANTERN: {name}"
        self.lbl_status.color = rgb
