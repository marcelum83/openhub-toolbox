"""
OpenHub Module: Precision Stopwatch
Millisecond timer with split lap tracking and lap time delta analysis.
"""
import time
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(14), **kwargs)
        self.host = None
        self.is_running = False
        self.elapsed = 0.0
        self.start_time = 0.0
        self.laps = []
        self.clock_event = None

        # 1. Main Time Readout
        self.lbl_time = Label(
            text="00:00.00",
            font_size="48sp",
            bold=True,
            color=(0.95, 0.95, 0.97, 1),
            size_hint_y=None,
            height=dp(120),
            halign='center'
        )
        self.add_widget(self.lbl_time)

        # 2. Control Buttons: [Start/Stop] [Lap/Reset] (Big touch targets)
        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(64), spacing=dp(12))
        
        self.btn_start = Button(
            text="▶ START",
            size_hint_x=0.5,
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="20sp"
        )
        self.btn_start.bind(on_release=self.toggle_start)
        btn_row.add_widget(self.btn_start)

        self.btn_lap = Button(
            text="⏱️ LAP",
            size_hint_x=0.5,
            background_normal="",
            background_color=(0.13, 0.13, 0.19, 1),
            color=(0.95, 0.95, 0.97, 1),
            bold=True,
            font_size="20sp"
        )
        self.btn_lap.bind(on_release=self.on_lap_or_reset)
        btn_row.add_widget(self.btn_lap)
        self.add_widget(btn_row)

        # 3. Lap History Table
        self.lap_scroll = ScrollView()
        self.lap_grid = GridLayout(cols=1, spacing=dp(8), size_hint_y=None, padding=[0, dp(8), 0, dp(8)])
        self.lap_grid.bind(minimum_height=self.lap_grid.setter('height'))
        self.lap_scroll.add_widget(self.lap_grid)
        self.add_widget(self.lap_scroll)

    def on_load(self, host_api):
        self.host = host_api

    def on_pause(self):
        # Keeps running in background unless explicitly stopped
        pass

    def toggle_start(self, instance):
        if self.is_running:
            # Stop
            self.is_running = False
            self.btn_start.text = "▶ START"
            self.btn_start.background_color = (0.15, 0.68, 0.38, 1)
            self.btn_lap.text = "🔄 RESET"
            if self.clock_event:
                self.clock_event.cancel()
        else:
            # Start
            self.is_running = True
            self.start_time = time.time() - self.elapsed
            self.btn_start.text = "⏹ STOP"
            self.btn_start.background_color = (0.91, 0.30, 0.24, 1)
            self.btn_lap.text = "⏱️ LAP"
            self.clock_event = Clock.schedule_interval(self.update_time, 1.0 / 30.0)
            
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(30)

    def on_lap_or_reset(self, instance):
        if self.is_running:
            # Record lap
            lap_time = self.elapsed
            self.laps.insert(0, lap_time)
            self.rebuild_laps()
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(40)
        else:
            # Reset
            self.elapsed = 0.0
            self.lbl_time.text = "00:00.00"
            self.laps = []
            self.lap_grid.clear_widgets()
            self.btn_lap.text = "⏱️ LAP"
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(20)

    def update_time(self, dt):
        if self.is_running:
            self.elapsed = time.time() - self.start_time
            self.lbl_time.text = self._format_time(self.elapsed)

    def rebuild_laps(self):
        self.lap_grid.clear_widgets()
        for idx, lap in enumerate(self.laps):
            lap_num = len(self.laps) - idx
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=36, padding=[10, 4, 10, 4])
            lbl_n = Label(text=f"Lap {lap_num:02d}", size_hint_x=0.5, halign='left', color=(0.6, 0.6, 0.7, 1))
            lbl_n.bind(size=lbl_n.setter('text_size'))
            row.add_widget(lbl_n)
            
            lbl_t = Label(text=self._format_time(lap), size_hint_x=0.5, halign='right', bold=True, color=(0.02, 0.71, 0.83, 1))
            lbl_t.bind(size=lbl_t.setter('text_size'))
            row.add_widget(lbl_t)
            self.lap_grid.add_widget(row)

    def _format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        centis = int((seconds * 100) % 100)
        return f"{mins:02d}:{secs:02d}.{centis:02d}"
