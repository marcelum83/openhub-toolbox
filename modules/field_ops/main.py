"""
Field Operations & Client Job Terminal
Connects OpenHub Mobile directly to the Nexus Field Operations Gateway (:8001),
logging on-site sensor telemetry and triggering autonomous Google Workspace delivery.
"""
import json
import urllib.request
import threading
import time
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
        self.pc_ip = "127.0.0.1"
        self.gateway_port = 8001
        self.cloud_gateway_url = "https://nexus-backend-803890942321.europe-west2.run.app"
        self.use_cloud = True
        self.jobs = []
        self.selected_job = None
        self.sensor_clock = None

        # 1. Header Bar with Mode Toggle & Sync
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(38), spacing=dp(6))
        lbl_title = Label(
            text="⚡ FIELD OPS",
            font_size="15sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        header.add_widget(lbl_title)

        self.btn_gateway_mode = Button(
            text="☁️ CLOUD",
            size_hint_x=None,
            width=dp(95),
            background_normal="",
            background_color=(0.10, 0.16, 0.26, 1),
            color=(0.3, 0.8, 1, 1),
            bold=True,
            font_size="10sp",
            always_release=True
        )
        self.btn_gateway_mode.bind(on_release=self.toggle_gateway_mode)
        header.add_widget(self.btn_gateway_mode)

        self.btn_refresh = Button(
            text="🔄 SYNC",
            size_hint_x=None,
            width=dp(65),
            background_normal="",
            background_color=(0.14, 0.20, 0.32, 1),
            color=(0.02, 0.71, 0.83, 1),
            bold=True,
            font_size="10sp",
            always_release=True
        )
        self.btn_refresh.bind(on_release=lambda x: self.fetch_jobs())
        header.add_widget(self.btn_refresh)
        self.add_widget(header)

        # Trigger automatic background LAN discovery probe immediately on launch
        Clock.schedule_once(lambda dt: self.auto_discover_gateway(), 0.3)

        # 2. Live Telemetry Strip
        tele_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(52), padding=dp(6))
        with tele_box.canvas.before:
            Color(0.10, 0.11, 0.17, 0.95)
            self.tb_bg = RoundedRectangle(size=tele_box.size, pos=tele_box.pos, radius=[dp(8)])
            Color(0.02, 0.71, 0.83, 0.5)
            self.tb_border = Line(rounded_rectangle=(tele_box.x, tele_box.y, tele_box.width, tele_box.height, dp(8)), width=1.0)
        tele_box.bind(size=self._update_tb, pos=self._update_tb)

        self.lbl_telemetry = Label(
            text="📡 Telemetry: Pitch: 0.0° | Roll: 0.0° | Azimuth: 0° | Lux: 0 lx",
            font_size="11sp",
            color=(0.6, 0.85, 0.9, 1),
            halign='center'
        )
        tele_box.add_widget(self.lbl_telemetry)
        self.add_widget(tele_box)

        # 3. Work Order / Active Jobs Container
        self.lbl_job_header = Label(
            text="ACTIVE FIELD WORK ORDERS",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.6, 0.7, 1),
            size_hint_y=None,
            height=dp(20),
            halign='left'
        )
        self.lbl_job_header.bind(size=self.lbl_job_header.setter('text_size'))
        self.add_widget(self.lbl_job_header)

        self.scroll = ScrollView(size_hint_y=0.42, do_scroll_x=False)
        self.job_list = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.job_list.bind(minimum_height=self.job_list.setter('height'))
        self.scroll.add_widget(self.job_list)
        self.add_widget(self.scroll)

        # 4. Job Inspection & Completion Controls
        self.card_action = BoxLayout(orientation='vertical', size_hint_y=0.48, spacing=dp(6), padding=dp(8))
        with self.card_action.canvas.before:
            Color(0.08, 0.09, 0.14, 0.98)
            self.ca_bg = RoundedRectangle(size=self.card_action.size, pos=self.card_action.pos, radius=[dp(12)])
            Color(0.18, 0.20, 0.30, 0.8)
            self.ca_border = Line(rounded_rectangle=(self.card_action.x, self.card_action.y, self.card_action.width, self.card_action.height, dp(12)), width=1.2)
        self.card_action.bind(size=self._update_ca, pos=self._update_ca)

        self.lbl_active_job = Label(
            text="Select a Work Order from above",
            font_size="14sp",
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(24),
            halign='left'
        )
        self.lbl_active_job.bind(size=self.lbl_active_job.setter('text_size'))
        self.card_action.add_widget(self.lbl_active_job)

        self.txt_notes = TextInput(
            hint_text="Enter field notes, job results, or measurements...",
            size_hint_y=1.0,
            background_color=(0.05, 0.06, 0.10, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.02, 0.71, 0.83, 1),
            font_size="13sp",
            padding=[dp(8), dp(8)]
        )
        self.card_action.add_widget(self.txt_notes)

        self.btn_complete = Button(
            text="⚡ COMPLETE JOB & DELIVER INVOICE",
            size_hint_y=None,
            height=dp(50),
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp",
            disabled=True,
            always_release=True
        )
        self.btn_complete.bind(on_release=self.complete_selected_job)
        self.card_action.add_widget(self.btn_complete)

        self.add_widget(self.card_action)

    def _update_tb(self, inst, val):
        self.tb_bg.pos = inst.pos
        self.tb_bg.size = inst.size
        self.tb_border.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(8))

    def _update_ca(self, inst, val):
        self.ca_bg.pos = inst.pos
        self.ca_bg.size = inst.size
        self.ca_border.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(12))

    def toggle_gateway_mode(self, *args):
        self.use_cloud = not self.use_cloud
        if self.use_cloud:
            self.btn_gateway_mode.text = "☁️ CLOUD"
            self.btn_gateway_mode.background_color = (0.10, 0.16, 0.26, 1)
        else:
            self.btn_gateway_mode.text = f"🟢 LAN:{self.pc_ip.split('.')[-1]}"
            self.btn_gateway_mode.background_color = (0.12, 0.28, 0.22, 1)
        self.fetch_jobs()

    def auto_discover_gateway(self):
        try:
            from core.discovery import discover_server
            def _found(disc):
                if disc:
                    self.pc_ip = disc.split(":")[0]
                    self.use_cloud = False
                    self.btn_gateway_mode.text = f"🟢 LAN:{self.pc_ip.split('.')[-1]}"
                    self.btn_gateway_mode.background_color = (0.12, 0.28, 0.22, 1)
                    self.fetch_jobs()
            discover_server(timeout=1.2, callback=_found)
        except Exception:
            pass

    def get_gateway_url(self):
        if self.use_cloud or not self.pc_ip or self.pc_ip == "127.0.0.1":
            return self.cloud_gateway_url
        return f"http://{self.pc_ip}:{self.gateway_port}"

    def on_load(self, host_api):
        self.host = host_api
        if hasattr(host_api, 'get_server_host'):
            h = host_api.get_server_host()
            if h:
                self.pc_ip = h.split(":")[0]

    def on_resume(self):
        self.sensor_clock = Clock.schedule_interval(self._update_telemetry_tick, 0.5)
        self.fetch_jobs()

    def on_pause(self):
        if self.sensor_clock:
            self.sensor_clock.cancel()
            self.sensor_clock = None

    def _update_telemetry_tick(self, dt):
        if not self.host or not self.host.hardware:
            return
        p, r, _ = self.host.hardware.get_orientation_angles()
        h, _ = self.host.hardware.get_compass_heading()
        lux, _ = self.host.hardware.get_lux()
        db = self.host.hardware.get_audio_level_db()
        self.lbl_telemetry.text = f"📡 Telemetry: Pitch: {p:.1f}° | Roll: {r:.1f}° | Az: {h:.0f}° | {lux:.0f} lx | {db:.0f} dB"

    def fetch_jobs(self):
        self.lbl_job_header.text = "FETCHING JOBS FROM NEXUS GATEWAY..."
        def _worker():
            # 1. Try preferred gateway URL
            primary_url = f"{self.get_gateway_url()}/api/jobs"
            try:
                req = urllib.request.Request(primary_url, headers={"User-Agent": "OpenHub-Mobile"})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    jobs = data if isinstance(data, list) else data.get("jobs", [])
                    mode_label = "Cloud HQ" if self.use_cloud else f"LAN {self.pc_ip}"
                    Clock.schedule_once(lambda dt: self._populate_jobs(jobs, mode_label=mode_label), 0)
                    return
            except Exception:
                pass

            # 2. If LAN failed and we were not explicitly in Cloud mode, fallback to Cloud Run
            if not self.use_cloud:
                try:
                    fallback_url = f"{self.cloud_gateway_url}/api/jobs"
                    req = urllib.request.Request(fallback_url, headers={"User-Agent": "OpenHub-Mobile"})
                    with urllib.request.urlopen(req, timeout=4.0) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        jobs = data if isinstance(data, list) else data.get("jobs", [])
                        Clock.schedule_once(lambda dt: self._populate_jobs(jobs, mode_label="Cloud Fallback"), 0)
                        return
                except Exception:
                    pass

            # 3. Fallback to local sample jobs if offline completely
            sample_jobs = [
                {"id": "job_local_01", "client": "Apex Robotics Ltd", "type": "Sensor Calibration", "region": "London/M25", "price": 180, "status": "In Progress"},
                {"id": "job_local_02", "client": "Vortex Energy", "type": "Substation Acoustic Scan", "region": "Wales", "price": 320, "status": "Pending"}
            ]
            Clock.schedule_once(lambda dt: self._populate_jobs(sample_jobs, mode_label="Offline Simulation"), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_jobs(self, jobs, mode_label="Live HQ"):
        self.job_list.clear_widgets()
        self.lbl_job_header.text = f"ACTIVE WORK ORDERS ({len(jobs)}) — {mode_label}"
        self.jobs = jobs

        for job in jobs:
            j_id = job.get("id", "job_0")
            client = job.get("client") or job.get("client_name", "Client")
            j_type = job.get("type", "Field Inspection")
            price = job.get("price", 150)
            status = job.get("status", "ACTIVE")

            card = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(54), padding=dp(8), spacing=dp(8))
            with card.canvas.before:
                Color(0.12, 0.13, 0.20, 1)
                bg = RoundedRectangle(size=card.size, pos=card.pos, radius=[dp(8)])
                Color(0.02, 0.71, 0.83, 0.6) if self.selected_job == job else Color(0.2, 0.22, 0.32, 0.5)
                bdr = Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(8)), width=1.0)
            card.bind(size=lambda inst, val, b=bg, d=bdr: setattr(b, 'pos', inst.pos) or setattr(b, 'size', inst.size) or setattr(d, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(8))))

            info_box = BoxLayout(orientation='vertical')
            info_box.add_widget(Label(text=f"🏢 {client}", font_size="13sp", bold=True, color=(1, 1, 1, 1), halign='left'))
            info_box.add_widget(Label(text=f"{j_type} • £{price} • {status}", font_size="11sp", color=(0.7, 0.7, 0.8, 1), halign='left'))
            card.add_widget(info_box)

            btn_sel = Button(
                text="SELECT",
                size_hint_x=None,
                width=dp(70),
                background_normal="",
                background_color=(0.18, 0.22, 0.35, 1),
                color=(0.02, 0.71, 0.83, 1),
                bold=True,
                font_size="11sp",
                always_release=True
            )
            btn_sel.bind(on_release=lambda inst, j=job: self.select_job(j))
            card.add_widget(btn_sel)

            self.job_list.add_widget(card)

    def select_job(self, job):
        self.selected_job = job
        client = job.get("client") or job.get("client_name", "Client")
        j_type = job.get("type", "Work Order")
        price = job.get("price", 150)
        self.lbl_active_job.text = f"Selected: {client} (£{price}) - {j_type}"
        self.btn_complete.disabled = False
        self.btn_complete.text = f"⚡ COMPLETE & INVOICE (£{price})"
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(20)

    def complete_selected_job(self, *args):
        if not self.selected_job:
            return

        self.btn_complete.disabled = True
        self.btn_complete.text = "⏳ Processing Autonomous Delivery..."

        notes = self.txt_notes.text.strip()
        telemetry = self.lbl_telemetry.text

        def _worker():
            payload = json.dumps({
                "job_id": self.selected_job.get("id"),
                "notes": f"{notes}\nAttached Mobile Telemetry: {telemetry}",
                "timestamp": time.time()
            }).encode('utf-8')

            try:
                url = f"{self.get_gateway_url()}/api/complete_job"
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    pass
                Clock.schedule_once(lambda dt: self._on_complete_success(), 0)
            except Exception as e:
                # If LAN attempt failed, try cloud gateway as fallback
                if not self.use_cloud:
                    try:
                        url = f"{self.cloud_gateway_url}/api/complete_job"
                        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            pass
                        Clock.schedule_once(lambda dt: self._on_complete_success(), 0)
                        return
                    except Exception as ce:
                        Clock.schedule_once(lambda dt, err=str(ce): self._on_complete_finished(err), 0)
                        return
                Clock.schedule_once(lambda dt, err=str(e): self._on_complete_finished(err), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_complete_success(self):
        self.btn_complete.text = "✅ DELIVERED! (Doc & Sheet Updated)"
        self.btn_complete.background_color = (0.1, 0.8, 0.4, 1)
        self.txt_notes.text = ""
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(50)
        Clock.schedule_once(lambda dt: self.fetch_jobs(), 1.5)

    def _on_complete_finished(self, err_msg):
        self.btn_complete.text = f"⚠️ Finished: {err_msg[:24]}"
        self.btn_complete.background_color = (0.7, 0.4, 0.1, 1)
