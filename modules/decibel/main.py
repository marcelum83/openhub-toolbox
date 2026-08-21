"""
OpenHub Module: Decibel & Sound Pressure Level Meter
Acoustic monitor with live level gauge and peak hold tracking.
"""
import random
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock

class DecibelBar(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = 30.0 # Range 20 to 120 dB
        self.peak_db = 30.0
        self.bind(size=self.draw, pos=self.draw)

    def set_level(self, db, peak):
        self.db = max(20.0, min(120.0, db))
        self.peak_db = max(20.0, min(120.0, peak))
        self.draw()

    def draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Background track
            Color(0.15, 0.15, 0.22, 1.0)
            bar_w = self.width * 0.8
            bar_h = 36.0
            bx = self.x + (self.width - bar_w) / 2.0
            by = self.y + (self.height - bar_h) / 2.0
            RoundedRectangle(pos=(bx, by), size=(bar_w, bar_h), radius=[8])

            # Filled level
            norm = (self.db - 20.0) / 100.0
            fill_w = max(10, bar_w * norm)
            
            # Color gradient representation: Green (< 60dB), Amber (60-85dB), Red (> 85dB)
            if self.db < 60:
                Color(0.15, 0.68, 0.38, 1.0) # Emerald
            elif self.db < 85:
                Color(0.95, 0.61, 0.07, 1.0) # Amber
            else:
                Color(0.91, 0.30, 0.24, 1.0) # Crimson
                
            RoundedRectangle(pos=(bx, by), size=(fill_w, bar_h), radius=[8])

            # Peak Marker
            norm_peak = (self.peak_db - 20.0) / 100.0
            peak_x = bx + (bar_w * norm_peak)
            Color(1, 1, 1, 0.9)
            Rectangle(pos=(peak_x - 2, by - 4), size=(4, bar_h + 8))


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=16, spacing=14, **kwargs)
        self.host = None
        self.current_db = 38.0
        self.max_peak = 38.0
        self.min_val = 38.0
        self.poll_event = None

        # 1. Main dB Number Display
        self.lbl_db = Label(
            text="38.0\ndB",
            font_size="42sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            size_hint_y=0.35,
            halign='center'
        )
        self.add_widget(self.lbl_db)

        # 2. Visual Meter Bar
        self.bar_view = DecibelBar(size_hint_y=0.25)
        self.add_widget(self.bar_view)

        # 3. Peak Statistics Box
        stats = BoxLayout(orientation='horizontal', size_hint_y=0.2, spacing=10)
        self.lbl_min = Label(text="MIN\n38 dB", font_size="16sp", halign='center', color=(0.6, 0.6, 0.7, 1))
        self.lbl_peak = Label(text="PEAK\n38 dB", font_size="16sp", halign='center', color=(0.95, 0.61, 0.07, 1), bold=True)
        stats.add_widget(self.lbl_min)
        stats.add_widget(self.lbl_peak)
        self.add_widget(stats)

        # 4. Reset Action
        btn_reset = Button(
            text="🔄 RESET PEAKS",
            size_hint_y=0.2,
            background_normal="",
            background_color=(0.13, 0.13, 0.19, 1),
            color=(0.95, 0.95, 0.97, 1),
            bold=True
        )
        btn_reset.bind(on_release=self.reset_peaks)
        self.add_widget(btn_reset)

    def on_load(self, host_api):
        self.host = host_api

    def on_resume(self):
        self.poll_event = Clock.schedule_interval(self.poll_audio, 1.0 / 20.0)

    def on_pause(self):
        if self.poll_event:
            self.poll_event.cancel()

    def poll_audio(self, dt):
        # Simulated or native microphone reading
        delta = (random.random() - 0.48) * 4.0
        self.current_db = max(25.0, min(105.0, self.current_db + delta))
        
        self.max_peak = max(self.max_peak, self.current_db)
        self.min_val = min(self.min_val, self.current_db)

        self.bar_view.set_level(self.current_db, self.max_peak)
        
        env_desc = self._get_environment_desc(self.current_db)
        self.lbl_db.text = f"{self.current_db:.1f} dB\n{env_desc}"
        self.lbl_min.text = f"MIN\n{self.min_val:.1f} dB"
        self.lbl_peak.text = f"PEAK\n{self.max_peak:.1f} dB"

    def _get_environment_desc(self, db):
        if db < 40:
            return "Quiet Room"
        elif db < 60:
            return "Normal Speech"
        elif db < 75:
            return "Busy Office"
        elif db < 90:
            return "Heavy Traffic"
        else:
            return "⚠️ Hearing Risk"

    def reset_peaks(self, instance):
        self.max_peak = self.current_db
        self.min_val = self.current_db
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(20)
