"""
Nexus Remote & Telemetry Bridge
Wireless PC Trackpad, Media Controller, Presentation Remote, Remote Typing & Live Sensor Coprocessor.
"""
import time
import json
import urllib.request
import threading
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
from kivy.metrics import dp, sp
from kivy.clock import Clock

class Trackpad(Widget):
    def __init__(self, host_module, **kwargs):
        super().__init__(**kwargs)
        self.host_module = host_module
        self.last_touch_x = None
        self.last_touch_y = None
        self.touch_start_time = 0
        self.total_movement = 0
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Trackpad Glass Surface
            Color(0.10, 0.11, 0.17, 1.0)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
            # Cyan Border
            Color(0.02, 0.71, 0.83, 0.4)
            Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(16)), width=1.5)
            # Center subtle grid
            Color(0.18, 0.20, 0.30, 0.4)
            Line(points=[self.center_x, self.y + dp(20), self.center_x, self.top - dp(20)], width=1.0)
            Line(points=[self.x + dp(20), self.center_y, self.right - dp(20), self.center_y], width=1.0)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        touch.grab(self)
        self.last_touch_x = touch.x
        self.last_touch_y = touch.y
        self.touch_start_time = time.perf_counter()
        self.total_movement = 0
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        if self.last_touch_x is not None and self.last_touch_y is not None:
            dx = (touch.x - self.last_touch_x) * 1.8
            dy = (self.last_touch_y - touch.y) * 1.8  # Invert Y for screen coordinates
            self.total_movement += abs(dx) + abs(dy)
            
            if abs(dx) > 0.5 or abs(dy) > 0.5:
                self.host_module.send_remote_action({"type": "mouse_move", "dx": int(dx), "dy": int(dy)})

        self.last_touch_x = touch.x
        self.last_touch_y = touch.y
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            duration = time.perf_counter() - self.touch_start_time
            # Tap detection (short tap with minimal motion = click)
            if duration < 0.25 and self.total_movement < dp(15):
                self.host_module.send_remote_action({"type": "click", "button": 1})
                if self.host_module.host and self.host_module.host.hardware:
                    self.host_module.host.hardware.vibrate(20)

            self.last_touch_x = None
            self.last_touch_y = None
            return True
        return super().on_touch_up(touch)


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(8), **kwargs)
        self.host = None
        self.pc_ip = "10.62.206.29"
        self.pc_port = 8080
        self.mode = "trackpad"
        self.telemetry_active = False
        self.telemetry_clock = None

        # 1. Header & PC Connection Status
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(38), spacing=dp(8))
        self.lbl_title = Label(
            text="🌐 NEXUS PC BRIDGE",
            font_size="16sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        header.add_widget(self.lbl_title)

        self.lbl_status = Label(
            text=f"PC: {self.pc_ip}",
            font_size="12sp",
            color=(0.6, 0.9, 0.7, 1),
            size_hint_x=None,
            width=dp(140),
            halign='right',
            valign='middle'
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        header.add_widget(self.lbl_status)
        self.add_widget(header)

        # 2. Mode Selector Bar (TRACKPAD | MEDIA | TYPING | SENSORS)
        mode_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(38), spacing=dp(6))
        self.mode_btns = {}
        modes = [("trackpad", "🖱️ MOUSE"), ("media", "⏯️ MEDIA"), ("type", "⌨️ TYPE"), ("telemetry", "📡 3D SENSORS")]
        for m_id, label in modes:
            b = Button(
                text=label,
                background_normal="",
                background_color=(0.02, 0.71, 0.83, 1) if m_id == "trackpad" else (0.15, 0.16, 0.24, 1),
                color=(0.05, 0.05, 0.08, 1) if m_id == "trackpad" else (0.8, 0.8, 0.9, 1),
                bold=True,
                font_size="11sp",
                always_release=True
            )
            b.bind(on_release=lambda inst, m=m_id: self.switch_mode(m))
            self.mode_btns[m_id] = b
            mode_bar.add_widget(b)
        self.add_widget(mode_bar)

        # 3. Dynamic Center Workspace Container
        self.workspace = BoxLayout(orientation='vertical', size_hint_y=1.0)
        self.add_widget(self.workspace)

        # Build initial Trackpad view
        self.build_trackpad_view()

    def on_load(self, host_api):
        self.host = host_api

    def on_resume(self):
        pass

    def on_pause(self):
        if self.telemetry_clock:
            self.telemetry_clock.cancel()
            self.telemetry_clock = None

    def switch_mode(self, new_mode):
        self.mode = new_mode
        for m_id, btn in self.mode_btns.items():
            if m_id == new_mode:
                btn.background_color = (0.02, 0.71, 0.83, 1)
                btn.color = (0.05, 0.05, 0.08, 1)
            else:
                btn.background_color = (0.15, 0.16, 0.24, 1)
                btn.color = (0.8, 0.8, 0.9, 1)

        self.workspace.clear_widgets()
        if new_mode == "trackpad":
            self.build_trackpad_view()
        elif new_mode == "media":
            self.build_media_view()
        elif new_mode == "type":
            self.build_typing_view()
        elif new_mode == "telemetry":
            self.build_telemetry_view()

    # --- VIEW 1: TRACKPAD & MOUSE BUTTONS ---
    def build_trackpad_view(self):
        # Interactive Touch Trackpad
        tp = Trackpad(self, size_hint_y=1.0)
        self.workspace.add_widget(tp)

        # Click Buttons Row (Left Click, Scroll Up, Scroll Down, Right Click)
        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        
        btn_lclick = Button(
            text="LEFT CLICK",
            size_hint_x=0.4,
            background_normal="",
            background_color=(0.18, 0.20, 0.30, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_lclick.bind(on_release=lambda x: self.send_remote_action({"type": "click", "button": 1}))
        btn_row.add_widget(btn_lclick)

        btn_scroll_up = Button(
            text="▲ SCROLL",
            size_hint_x=0.2,
            background_normal="",
            background_color=(0.14, 0.15, 0.22, 1),
            color=(0.02, 0.71, 0.83, 1),
            bold=True,
            font_size="11sp",
            always_release=True
        )
        btn_scroll_up.bind(on_release=lambda x: self.send_remote_action({"type": "click", "button": 4}))
        btn_row.add_widget(btn_scroll_up)

        btn_scroll_dn = Button(
            text="▼ SCROLL",
            size_hint_x=0.2,
            background_normal="",
            background_color=(0.14, 0.15, 0.22, 1),
            color=(0.02, 0.71, 0.83, 1),
            bold=True,
            font_size="11sp",
            always_release=True
        )
        btn_scroll_dn.bind(on_release=lambda x: self.send_remote_action({"type": "click", "button": 5}))
        btn_row.add_widget(btn_scroll_dn)

        btn_rclick = Button(
            text="RIGHT CLICK",
            size_hint_x=0.4,
            background_normal="",
            background_color=(0.18, 0.20, 0.30, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_rclick.bind(on_release=lambda x: self.send_remote_action({"type": "click", "button": 3}))
        btn_row.add_widget(btn_rclick)

        self.workspace.add_widget(btn_row)

    # --- VIEW 2: MEDIA & PRESENTATION CONTROLLER ---
    def build_media_view(self):
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=1.0, padding=dp(8))
        
        controls = [
            ("⏯️ PLAY / PAUSE", "space"),
            ("🔇 MUTE / UNMUTE", "XF86AudioMute"),
            ("🔊 VOLUME UP (+)", "XF86AudioRaiseVolume"),
            ("🔉 VOLUME DOWN (-)", "XF86AudioLowerVolume"),
            ("⏮️ PREV TRACK", "XF86AudioPrev"),
            ("⏭️ NEXT TRACK", "XF86AudioNext"),
            ("◀ PREV SLIDE", "Left"),
            ("▶ NEXT SLIDE", "Right"),
            ("🖥️ FULLSCREEN", "F11"),
            ("❌ ESCAPE", "Escape")
        ]

        for label, key in controls:
            b = Button(
                text=label,
                background_normal="",
                background_color=(0.14, 0.16, 0.25, 1),
                color=(0.95, 0.95, 1, 1),
                bold=True,
                font_size="13sp",
                always_release=True
            )
            b.bind(on_release=lambda inst, k=key: self.send_key(k))
            grid.add_widget(b)

        self.workspace.add_widget(grid)

    # --- VIEW 3: REMOTE TYPING KEYPAD ---
    def build_typing_view(self):
        box = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(12), size_hint_y=1.0)
        
        lbl_hint = Label(
            text="Type text below to beam directly into active PC window:",
            font_size="13sp",
            color=(0.7, 0.7, 0.8, 1),
            size_hint_y=None,
            height=dp(28)
        )
        box.add_widget(lbl_hint)

        self.txt_remote = TextInput(
            hint_text="Enter text to type on PC...",
            size_hint_y=0.4,
            background_color=(0.08, 0.09, 0.14, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.02, 0.71, 0.83, 1),
            font_size="15sp",
            padding=[dp(12), dp(12)]
        )
        box.add_widget(self.txt_remote)

        btn_send_type = Button(
            text="🚀 BEAM TEXT TO PC",
            size_hint_y=None,
            height=dp(52),
            background_normal="",
            background_color=(0.02, 0.71, 0.83, 1),
            color=(0.05, 0.05, 0.08, 1),
            bold=True,
            font_size="15sp",
            always_release=True
        )
        btn_send_type.bind(on_release=self.on_beam_text)
        box.add_widget(btn_send_type)

        # Quick Key Row
        q_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(46), spacing=dp(8))
        for k_lbl, k_val in [("ENTER ↵", "Return"), ("BACKSPACE ⌫", "BackSpace"), ("TAB ⇥", "Tab"), ("CTRL+C", "ctrl+c")]:
            b = Button(
                text=k_lbl,
                background_normal="",
                background_color=(0.18, 0.20, 0.30, 1),
                color=(1, 1, 1, 1),
                bold=True,
                font_size="12sp",
                always_release=True
            )
            b.bind(on_release=lambda inst, k=k_val: self.send_key(k))
            q_row.add_widget(b)
        box.add_widget(q_row)

        self.workspace.add_widget(box)

    # --- VIEW 4: LIVE 3D TELEMETRY COPROCESSOR ---
    def build_telemetry_view(self):
        box = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(12), size_hint_y=1.0)
        
        self.lbl_tele_info = Label(
            text="📡 Telemetry Stream: INACTIVE",
            font_size="16sp",
            bold=True,
            color=(0.95, 0.75, 0.1, 1),
            size_hint_y=None,
            height=dp(36)
        )
        box.add_widget(self.lbl_tele_info)

        self.lbl_tele_readings = Label(
            text="Pitch: 0.0° | Roll: 0.0°\nHeading: 0.0° | Lux: 0 lx",
            font_size="16sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=0.5,
            halign='center'
        )
        box.add_widget(self.lbl_tele_readings)

        self.btn_tele_toggle = Button(
            text="▶ START 30Hz TELEMETRY STREAM",
            size_hint_y=None,
            height=dp(56),
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="15sp",
            always_release=True
        )
        self.btn_tele_toggle.bind(on_release=self.toggle_telemetry)
        box.add_widget(self.btn_tele_toggle)

        self.workspace.add_widget(box)

    def on_beam_text(self, *args):
        text = self.txt_remote.text
        if text:
            self.send_remote_action({"type": "type", "text": text})
            self.txt_remote.text = ""
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(30)

    def send_key(self, key_name):
        self.send_remote_action({"type": "key", "key": key_name})
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(25)

    def send_remote_action(self, payload):
        def _post():
            try:
                url = f"http://{self.pc_ip}:{self.pc_port}/api/remote/action"
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    pass
            except Exception:
                pass
        threading.Thread(target=_post, daemon=True).start()

    def toggle_telemetry(self, *args):
        if not self.telemetry_active:
            self.telemetry_active = True
            self.lbl_tele_info.text = "📡 Telemetry Stream: LIVE (30Hz)"
            self.lbl_tele_info.color = (0.15, 0.85, 0.4, 1)
            self.btn_tele_toggle.text = "⏹ STOP TELEMETRY STREAM"
            self.btn_tele_toggle.background_color = (0.85, 0.20, 0.20, 1)
            self.telemetry_clock = Clock.schedule_interval(self._send_telemetry_tick, 1.0 / 30.0)
        else:
            self.telemetry_active = False
            self.lbl_tele_info.text = "📡 Telemetry Stream: INACTIVE"
            self.lbl_tele_info.color = (0.95, 0.75, 0.1, 1)
            self.btn_tele_toggle.text = "▶ START 30Hz TELEMETRY STREAM"
            self.btn_tele_toggle.background_color = (0.15, 0.68, 0.38, 1)
            if self.telemetry_clock:
                self.telemetry_clock.cancel()
                self.telemetry_clock = None

    def _send_telemetry_tick(self, dt):
        if not self.host or not self.host.hardware:
            return
        
        p, r, _ = self.host.hardware.get_orientation_angles()
        h, _ = self.host.hardware.get_compass_heading()
        lux, _ = self.host.hardware.get_lux()
        db = self.host.hardware.get_audio_level_db()

        self.lbl_tele_readings.text = f"Pitch: {p:.1f}° | Roll: {r:.1f}°\nHeading: {h:.1f}° | Lux: {lux:.0f} lx | Mic: {db:.0f} dB"

        def _post_tele():
            try:
                payload = {"pitch": p, "roll": r, "heading": h, "lux": lux, "db": db, "timestamp": time.time()}
                url = f"http://{self.pc_ip}:{self.pc_port}/api/remote/telemetry"
                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=0.2) as resp:
                    pass
            except Exception:
                pass

        threading.Thread(target=_post_tele, daemon=True).start()
