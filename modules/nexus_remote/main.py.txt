"""
Nexus Remote & Telemetry Bridge
Wireless PC Trackpad, Media Controller, Presentation Remote, Remote Typing & Live Sensor Coprocessor.
"""
import os
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
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
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
        self.pc_ip = "127.0.0.1"
        self.pc_port = 8080
        self.mode = "trackpad"
        self.telemetry_active = False
        self.telemetry_clock = None

        self.load_config()

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

        status_text = f"PC: {self.pc_ip}:{self.pc_port}" if self.pc_ip != "127.0.0.1" else "PC: Auto-Discovering..."
        self.btn_status = Button(
            text=status_text,
            font_size="11sp",
            bold=True,
            background_normal="",
            background_color=(0.12, 0.20, 0.30, 0.95),
            color=(0.02, 0.71, 0.83, 1),
            size_hint_x=None,
            width=dp(160),
            always_release=True
        )
        self.btn_status.bind(on_release=self.show_ip_dialog)
        header.add_widget(self.btn_status)
        self.add_widget(header)

        # Trigger automatic background LAN discovery probe immediately on launch
        Clock.schedule_once(lambda dt: self.auto_discover_server(quiet=True), 0.3)

        # 2. Mode Selector Bar (TRACKPAD | MEDIA | TYPING | SENSORS | ACE)
        mode_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(38), spacing=dp(4))
        self.mode_btns = {}
        modes = [("trackpad", "🖱️ MOUSE"), ("media", "⏯️ MEDIA"), ("type", "⌨️ TYPE"), ("telemetry", "📡 SENSORS"), ("agent", "🧠 ACE")]
        for m_id, label in modes:
            b = Button(
                text=label,
                background_normal="",
                background_color=(0.02, 0.71, 0.83, 1) if m_id == "trackpad" else (0.15, 0.16, 0.24, 1),
                color=(0.05, 0.05, 0.08, 1) if m_id == "trackpad" else (0.8, 0.8, 0.9, 1),
                bold=True,
                font_size="10sp",
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

    def _apply_host_str(self, host_str):
        if not host_str:
            return
        if ":" in host_str:
            parts = host_str.split(":")
            self.pc_ip = parts[0].strip()
            try:
                self.pc_port = int(parts[1].strip())
            except ValueError:
                self.pc_port = 8080
        else:
            self.pc_ip = host_str.strip()
            self.pc_port = 8080
        if hasattr(self, 'btn_status'):
            self.btn_status.text = f"PC: {self.pc_ip}:{self.pc_port}"

    def auto_discover_server(self, quiet=False):
        try:
            from core.discovery import discover_server
            def _found(disc):
                if disc:
                    self._apply_host_str(disc)
                    self.save_config(disc)
                elif not quiet and hasattr(self, 'btn_status'):
                    self.btn_status.text = "⚠️ No PC on LAN"
            discover_server(timeout=1.5, callback=_found)
        except Exception as e:
            if not quiet and hasattr(self, 'btn_status'):
                self.btn_status.text = f"❌ {e}"

    def load_config(self):
        if self.host and hasattr(self.host, 'get_server_host'):
            try:
                h = self.host.get_server_host()
                if h:
                    self._apply_host_str(h)
                    return
            except Exception:
                pass

        search_dirs = [
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            os.getcwd(),
            os.path.dirname(os.path.abspath(__file__))
        ]
        for d in search_dirs:
            s_file = os.path.join(d, "settings.json")
            if os.path.exists(s_file):
                try:
                    with open(s_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        h = data.get("server_host", "")
                        if h:
                            self._apply_host_str(h)
                            return
                except Exception:
                    pass

    def save_config(self, host_str):
        self._apply_host_str(host_str)
        if self.host and hasattr(self.host, 'save_server_host'):
            try:
                self.host.save_server_host(f"{self.pc_ip}:{self.pc_port}")
            except Exception:
                pass

        search_dirs = [
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            os.getcwd(),
            os.path.dirname(os.path.abspath(__file__))
        ]
        for d in search_dirs:
            s_file = os.path.join(d, "settings.json")
            if os.path.exists(s_file):
                try:
                    data = {}
                    with open(s_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["server_host"] = f"{self.pc_ip}:{self.pc_port}"
                    with open(s_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                except Exception:
                    pass

    def show_ip_dialog(self, *args):
        modal = ModalView(size_hint=(0.88, 0.52), auto_dismiss=True)
        box = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        
        with box.canvas.before:
            Color(0.10, 0.11, 0.17, 0.98)
            bg = RoundedRectangle(size=box.size, pos=box.pos, radius=[dp(14)])
            Color(0.02, 0.71, 0.83, 0.8)
            bdr = Line(rounded_rectangle=(box.x, box.y, box.width, box.height, dp(14)), width=1.5)
        box.bind(size=lambda inst, val: setattr(bg, 'pos', inst.pos) or setattr(bg, 'size', inst.size) or setattr(bdr, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(14))))

        lbl = Label(
            text="⚙️ SET PC ADDRESS (IP:PORT)",
            font_size="15sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            size_hint_y=None,
            height=dp(28)
        )
        box.add_widget(lbl)

        txt = TextInput(
            text=f"{self.pc_ip}:{self.pc_port}",
            multiline=False,
            font_size="15sp",
            size_hint_y=None,
            height=dp(44),
            background_color=(0.06, 0.07, 0.11, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.02, 0.71, 0.83, 1)
        )
        box.add_widget(txt)

        def do_discover(inst):
            lbl.text = "🔍 Searching Wi-Fi/Hotspot..."
            try:
                from core.discovery import discover_server
                def _found(disc):
                    if disc:
                        txt.text = disc
                        lbl.text = f"✅ Found: {disc}"
                    else:
                        lbl.text = "⚠️ No PC found. Run server.sh"
                discover_server(timeout=1.5, callback=_found)
            except Exception as e:
                lbl.text = f"❌ Error: {e}"

        btn_auto = Button(
            text="📡 AUTO-DISCOVER PC ON LAN",
            background_normal="",
            background_color=(0.14, 0.20, 0.32, 1.0),
            color=(0.02, 0.71, 0.83, 1.0),
            bold=True,
            font_size="12sp",
            size_hint_y=None,
            height=dp(38),
            always_release=True
        )
        btn_auto.bind(on_release=do_discover)
        box.add_widget(btn_auto)

        btn_row = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(44))
        
        btn_cancel = Button(text="CANCEL", background_normal="", background_color=(0.2, 0.22, 0.3, 1), bold=True, font_size="13sp", always_release=True)
        btn_cancel.bind(on_release=lambda x: modal.dismiss())
        btn_row.add_widget(btn_cancel)

        def save_and_dismiss(inst):
            new_val = txt.text.strip()
            if new_val:
                self.save_config(new_val)
            modal.dismiss()

        btn_save = Button(text="SAVE & CONNECT", background_normal="", background_color=(0.15, 0.68, 0.38, 1), bold=True, font_size="13sp", always_release=True)
        btn_save.bind(on_release=save_and_dismiss)
        btn_row.add_widget(btn_save)

        box.add_widget(btn_row)
        modal.add_widget(box)
        modal.open()

    def on_load(self, host_api):
        self.host = host_api
        self.load_config()

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
        elif new_mode == "agent":
            self.build_agent_view()

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

    # --- VIEW 5: ACE-OS COGNITIVE AGENT BRIDGE ---
    def build_agent_view(self):
        box = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8), size_hint_y=1.0)

        # Header with connection & active layer
        top_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(32), spacing=dp(6))
        self.lbl_agent_header = Label(
            text="🧠 ACE LAYER:",
            font_size="11sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            size_hint_x=None,
            width=dp(90),
            halign='left',
            valign='middle'
        )
        self.lbl_agent_header.bind(size=self.lbl_agent_header.setter('text_size'))
        top_row.add_widget(self.lbl_agent_header)

        self.remote_layer_btns = {}
        for lc, lbl, col in [("L1", "L1 VISION", (0.54, 0.36, 0.96, 0.9)), ("L2", "L2 STRATEGY", (0.95, 0.65, 0.15, 0.9)), ("L6", "L6 EXECUTE", (0.15, 0.68, 0.38, 0.9))]:
            btn = Button(
                text=lbl,
                font_size="10sp",
                bold=True,
                background_normal="",
                background_color=(0.18, 0.20, 0.30, 0.9),
                color=(0.85, 0.85, 0.95, 1),
                always_release=True
            )
            btn.bind(on_release=lambda inst, code=lc: self.shift_agent_layer(code))
            self.remote_layer_btns[lc] = (btn, col)
            top_row.add_widget(btn)
        box.add_widget(top_row)

        # Quick Actions Row
        q_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(34), spacing=dp(6))
        btn_tele_ask = Button(
            text="📡 INJECT SENSORS",
            font_size="10sp",
            bold=True,
            background_normal="",
            background_color=(0.12, 0.25, 0.35, 1),
            color=(0.02, 0.71, 0.83, 1),
            always_release=True
        )
        btn_tele_ask.bind(on_release=lambda x: self.send_agent_prompt("Analyze my phone's current physical orientation, ambient light, and acoustic environment."))
        q_row.add_widget(btn_tele_ask)

        btn_tools_ask = Button(
            text="📦 LIST MODULES",
            font_size="10sp",
            bold=True,
            background_normal="",
            background_color=(0.20, 0.15, 0.35, 1),
            color=(0.85, 0.65, 0.95, 1),
            always_release=True
        )
        btn_tools_ask.bind(on_release=lambda x: self.send_agent_prompt("List all installed OpenHub modules and their categories."))
        q_row.add_widget(btn_tools_ask)
        box.add_widget(q_row)

        # Input Row
        inp_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(44), spacing=dp(6))
        self.txt_remote_agent = TextInput(
            hint_text="Ask ACE OS or command task...",
            multiline=False,
            font_size="13sp",
            background_color=(0.08, 0.09, 0.14, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.02, 0.71, 0.83, 1),
            padding=[dp(8), dp(8), dp(8), dp(8)]
        )
        self.txt_remote_agent.bind(on_text_validate=lambda x: self.send_agent_prompt())
        inp_row.add_widget(self.txt_remote_agent)

        btn_send_remote = Button(
            text="SEND",
            size_hint_x=None,
            width=dp(65),
            font_size="11sp",
            bold=True,
            background_normal="",
            background_color=(0.02, 0.71, 0.83, 1),
            color=(0.05, 0.05, 0.08, 1),
            always_release=True
        )
        btn_send_remote.bind(on_release=lambda x: self.send_agent_prompt())
        inp_row.add_widget(btn_send_remote)
        box.add_widget(inp_row)

        # Response Scroll Container
        scroll = ScrollView(size_hint_y=1.0)
        self.lbl_agent_resp = Label(
            text="🤖 ACE OS SimpleAgent Ready.\nTap a quick action above or enter a directive.",
            font_size="13sp",
            color=(0.90, 0.90, 0.95, 1),
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        self.lbl_agent_resp.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        self.lbl_agent_resp.bind(texture_size=lambda inst, val: setattr(inst, 'height', max(val[1], dp(120))))
        scroll.add_widget(self.lbl_agent_resp)
        box.add_widget(scroll)

        self.workspace.add_widget(box)
        Clock.schedule_once(lambda dt: self.fetch_agent_layer(), 0.1)

    def fetch_agent_layer(self):
        def _get():
            try:
                url = f"http://{self.pc_ip}:{self.pc_port}/api/simple_agent/layer"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    layer = data.get("active_layer", "L6_Prosecution")
                    Clock.schedule_once(lambda dt: self.update_remote_layer_ui(layer), 0)
            except Exception:
                pass
        threading.Thread(target=_get, daemon=True).start()

    def shift_agent_layer(self, layer_code):
        def _shift():
            try:
                url = f"http://{self.pc_ip}:{self.pc_port}/api/simple_agent/layer"
                payload = json.dumps({"layer": layer_code}).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    layer = data.get("active_layer", layer_code)
                    Clock.schedule_once(lambda dt: self.update_remote_layer_ui(layer), 0)
            except Exception:
                pass
        threading.Thread(target=_shift, daemon=True).start()

    def update_remote_layer_ui(self, active_layer="L6"):
        if not hasattr(self, 'remote_layer_btns'):
            return
        for lc, (btn, act_col) in self.remote_layer_btns.items():
            if lc in active_layer:
                btn.background_color = act_col
                btn.color = (1, 1, 1, 1)
            else:
                btn.background_color = (0.18, 0.20, 0.30, 0.9)
                btn.color = (0.7, 0.7, 0.8, 1)

    def send_agent_prompt(self, override_text=None):
        prompt = override_text or (self.txt_remote_agent.text.strip() if hasattr(self, 'txt_remote_agent') else "")
        if not prompt:
            return
        if hasattr(self, 'txt_remote_agent') and not override_text:
            self.txt_remote_agent.text = ""

        if hasattr(self, 'lbl_agent_resp'):
            self.lbl_agent_resp.text = f"⏳ Sending to ACE OS SimpleAgent ({self.pc_ip}:{self.pc_port})...\nPrompt: {prompt}"

        # Capture phone sensors
        sensor_ctx = ""
        if self.host and self.host.hardware:
            try:
                p, r, _ = self.host.hardware.get_orientation_angles()
                h, _ = self.host.hardware.get_compass_heading()
                lux, _ = self.host.hardware.get_lux()
                db = self.host.hardware.get_audio_level_db()
                sensor_ctx = f"Heading={h:.1f}°, Pitch={p:.1f}°, Roll={r:.1f}°, Lux={lux:.0f} lx, Mic={db:.0f} dB"
            except Exception:
                pass

        def _do_query():
            try:
                url = f"http://{self.pc_ip}:{self.pc_port}/api/simple_agent/chat"
                payload = json.dumps({
                    "prompt": prompt,
                    "sensor_context": sensor_ctx,
                    "model": "gemma4:e4b"
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=45.0) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    reply = data.get("response", "(No response)")
                    tools = data.get("tools_executed", [])
                    layer = data.get("active_layer", "")
                    
                    full_display = ""
                    if layer:
                        full_display += f"🧠 [{layer}]\n"
                    if tools:
                        tools_str = ", ".join([t.get("name", "tool") for t in tools])
                        full_display += f"🔧 [Executed Tools: {tools_str}]\n\n"
                    full_display += reply

                    def _update_ui(dt):
                        if hasattr(self, 'lbl_agent_resp'):
                            self.lbl_agent_resp.text = full_display
                        if layer:
                            self.update_remote_layer_ui(layer)
                    Clock.schedule_once(_update_ui, 0)
            except Exception as e:
                def _update_err(dt):
                    if hasattr(self, 'lbl_agent_resp'):
                        self.lbl_agent_resp.text = f"❌ Error querying agent: {e}"
                Clock.schedule_once(_update_err, 0)

        threading.Thread(target=_do_query, daemon=True).start()

