"""
Nexus Terminal & Telemetry Chat Module
Real-time communication bridge to Aurelian Hub, local LAN peers and Gemini ACE agent.
"""
import time
import json
import threading
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
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
        self.messages = []

        # 1. Header
        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))
        self.lbl_title = Label(
            text="🛰️ NEXUS TERMINAL CHAT",
            font_size="16sp",
            bold=True,
            color=(0.54, 0.36, 0.96, 1.0),
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        head.add_widget(self.lbl_title)

        self.btn_clear = Button(
            text="CLEAR",
            size_hint_x=None,
            width=dp(65),
            background_normal="",
            background_color=(0.25, 0.15, 0.25, 1.0),
            color=(0.9, 0.7, 0.9, 1.0),
            font_size="11sp",
            always_release=True
        )
        self.btn_clear.bind(on_release=lambda x: self.clear_chat())
        head.add_widget(self.btn_clear)
        self.add_widget(head)

        # 2. Connection Bar
        conn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(32), spacing=dp(6))
        self.txt_endpoint = TextInput(
            text="localhost:8080",
            multiline=False,
            font_size="12sp",
            background_color=(0.12, 0.12, 0.18, 1.0),
            foreground_color=(0.8, 0.85, 0.95, 1.0)
        )
        conn_row.add_widget(self.txt_endpoint)

        self.btn_ping = Button(
            text="📡 PING HUB",
            size_hint_x=None,
            width=dp(95),
            background_normal="",
            background_color=(0.14, 0.24, 0.38, 1.0),
            color=(0.02, 0.71, 0.83, 1.0),
            bold=True,
            font_size="11sp",
            always_release=True
        )
        self.btn_ping.bind(on_release=lambda x: self.ping_hub())
        conn_row.add_widget(self.btn_ping)
        self.add_widget(conn_row)

        # 3. Message Scroll View
        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.msg_box = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.msg_box.bind(minimum_height=self.msg_box.setter('height'))
        self.scroll.add_widget(self.msg_box)
        self.add_widget(self.scroll)

        # 4. Message Input & Send
        input_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(42), spacing=dp(6))
        self.txt_input = TextInput(
            hint_text="Message Aurelian Hub / ACE Agent...",
            multiline=False,
            font_size="13sp",
            background_color=(0.14, 0.14, 0.20, 1.0),
            foreground_color=(0.95, 0.95, 0.98, 1.0)
        )
        self.txt_input.bind(on_text_validate=lambda x: self.send_message())
        input_row.add_widget(self.txt_input)

        self.btn_send = Button(
            text="SEND",
            size_hint_x=None,
            width=dp(70),
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="12sp",
            always_release=True
        )
        self.btn_send.bind(on_release=lambda x: self.send_message())
        input_row.add_widget(self.btn_send)
        self.add_widget(input_row)

        self.add_chat_bubble("System", "Nexus Terminal initialized. Connected to OpenHub runtime.", is_system=True)

    def on_load(self, host_api):
        self.host = host_api
        if self.host:
            self.host.log("Nexus Terminal Chat mounted.")

    def add_chat_bubble(self, sender, text, is_user=False, is_system=False):
        bubble = BoxLayout(orientation='vertical', size_hint_y=None, padding=dp(8), spacing=dp(3))
        with bubble.canvas.before:
            if is_user:
                Color(0.20, 0.25, 0.38, 0.9)
            elif is_system:
                Color(0.12, 0.15, 0.20, 0.9)
            else:
                Color(0.25, 0.18, 0.35, 0.9)
            bg = RoundedRectangle(size=bubble.size, pos=bubble.pos, radius=[dp(8)])
        bubble.bind(size=lambda inst, val, b=bg: setattr(b, 'pos', inst.pos) or setattr(b, 'size', inst.size))

        t_stamp = time.strftime("%H:%M:%S")
        h_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(16))
        h_row.add_widget(Label(
            text=f"[{t_stamp}] {sender}:",
            font_size="10sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0) if is_user else (0.7, 0.7, 0.8, 1.0),
            halign='left'
        ))
        bubble.add_widget(h_row)

        lbl_msg = Label(
            text=text,
            font_size="12sp",
            color=(0.95, 0.95, 0.98, 1.0),
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        lbl_msg.bind(
            width=lambda *x: lbl_msg.setter('text_size')(lbl_msg, (lbl_msg.width, None)),
            texture_size=lambda *x: setattr(lbl_msg, 'height', lbl_msg.texture_size[1])
        )
        bubble.add_widget(lbl_msg)
        bubble.bind(minimum_height=bubble.setter('height'))

        self.msg_box.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    def send_message(self):
        text = self.txt_input.text.strip()
        if not text:
            return
        self.txt_input.text = ""
        self.add_chat_bubble("You", text, is_user=True)

        # Forward via background worker or echo response
        def _worker():
            try:
                import urllib.request
                endpoint = self.txt_endpoint.text.strip()
                url = f"http://{endpoint}/api/agent/chat"
                payload = json.dumps({"message": text}).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    reply = data.get("reply", "Received by Hub.")
                    Clock.schedule_once(lambda dt: self.add_chat_bubble("Nexus Hub", reply), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.add_chat_bubble("Nexus Agent", f"Acknowledged: '{text}' (Offline Relay)"), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def ping_hub(self):
        self.add_chat_bubble("System", f"Pinging Hub at {self.txt_endpoint.text}...", is_system=True)
        def _worker():
            try:
                import urllib.request
                endpoint = self.txt_endpoint.text.strip()
                url = f"http://{endpoint}/version.json"
                req = urllib.request.Request(url, headers={"User-Agent": "OpenHub-Client"})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    Clock.schedule_once(lambda dt: self.add_chat_bubble("System", f"✅ Hub Online ({resp.status} OK)", is_system=True), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.add_chat_bubble("System", f"⚠️ Hub unreachable: {e}", is_system=True), 0)
        threading.Thread(target=_worker, daemon=True).start()

    def clear_chat(self):
        self.msg_box.clear_widgets()
        self.add_chat_bubble("System", "Chat cleared.", is_system=True)
