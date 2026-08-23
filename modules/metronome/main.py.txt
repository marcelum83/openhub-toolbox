"""
OpenHub Module: Haptic Metronome
Audio-visual rhythm generator utilizing Pixel 7a haptics with tap tempo.
"""
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle
from kivy.clock import Clock

class BeatDisplay(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.num_beats = 4
        self.current_beat = 0
        self.is_running = False
        self.bind(size=self.draw, pos=self.draw)

    def set_meter(self, num_beats, current_beat, is_running):
        self.num_beats = num_beats
        self.current_beat = current_beat
        self.is_running = is_running
        self.draw()

    def draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            if self.num_beats <= 0:
                return
            
            spacing = 16
            dot_size = min(40, (self.width - (spacing * (self.num_beats + 1))) / self.num_beats)
            total_w = (self.num_beats * dot_size) + ((self.num_beats - 1) * spacing)
            start_x = self.x + (self.width - total_w) / 2.0
            center_y = self.y + self.height / 2.0

            for i in range(self.num_beats):
                dot_x = start_x + (i * (dot_size + spacing))
                dot_y = center_y - (dot_size / 2.0)
                
                if self.is_running and i == self.current_beat:
                    if i == 0:
                        Color(0.95, 0.61, 0.07, 1.0) # Accent Amber on beat 1
                    else:
                        Color(0.02, 0.71, 0.83, 1.0) # Cyan on sub-beats
                else:
                    Color(0.15, 0.15, 0.22, 1.0)     # Dim inactive

                Ellipse(pos=(dot_x, dot_y), size=(dot_size, dot_size))


from kivy.metrics import dp, sp

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(14), **kwargs)
        self.host = None
        self.bpm = 120
        self.beats_per_bar = 4
        self.current_beat = 0
        self.is_playing = False
        self.tap_times = []
        self.metronome_event = None

        # 1. Beat Visualizer
        self.beat_view = BeatDisplay(size_hint_y=0.25)
        self.add_widget(self.beat_view)

        # 2. Large BPM Readout
        self.lbl_bpm = Label(
            text="120\nBPM",
            font_size="36sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            size_hint_y=None,
            height=dp(80),
            halign='center'
        )
        self.add_widget(self.lbl_bpm)

        # 3. Slider & +/- Adjusters
        adj_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(56), spacing=dp(10))
        btn_minus = Button(text="-1", size_hint_x=0.2, background_color=(0.13, 0.13, 0.19, 1), font_size="18sp", bold=True)
        btn_minus.bind(on_release=lambda x: self.adjust_bpm(-1))
        adj_box.add_widget(btn_minus)

        self.slider = Slider(min=40, max=240, value=120, size_hint_x=0.6)
        self.slider.bind(value=self.on_slider_change)
        adj_box.add_widget(self.slider)

        btn_plus = Button(text="+1", size_hint_x=0.2, background_color=(0.13, 0.13, 0.19, 1), font_size="18sp", bold=True)
        btn_plus.bind(on_release=lambda x: self.adjust_bpm(1))
        adj_box.add_widget(btn_plus)
        self.add_widget(adj_box)

        # 4. Time Signature Selector (2/4, 3/4, 4/4, 6/8)
        sig_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        for sig, beats in [("2/4", 2), ("3/4", 3), ("4/4", 4), ("6/8", 6)]:
            b = Button(
                text=sig,
                background_color=(0.02, 0.71, 0.83, 1) if beats == 4 else (0.13, 0.13, 0.19, 1),
                color=(0.05, 0.05, 0.08, 1) if beats == 4 else (0.95, 0.95, 0.97, 1),
                bold=True,
                font_size="16sp"
            )
            b.bind(on_release=lambda inst, n=beats: self.set_signature(n))
            sig_box.add_widget(b)
        self.add_widget(sig_box)

        # 5. Play / Stop & Tap Tempo Actions
        ctrl_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(10))
        
        self.btn_play = Button(
            text="▶ START",
            size_hint_x=0.6,
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="18sp"
        )
        self.btn_play.bind(on_release=self.toggle_play)
        ctrl_box.add_widget(self.btn_play)

        btn_tap = Button(
            text="👆 TAP TEMPO",
            size_hint_x=0.4,
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="14sp"
        )
        btn_tap.bind(on_release=self.on_tap_tempo)
        ctrl_box.add_widget(btn_tap)

        self.add_widget(ctrl_box)

    def on_load(self, host_api):
        self.host = host_api

    def on_pause(self):
        self.stop_metronome()

    def toggle_play(self, instance):
        if self.is_playing:
            self.stop_metronome()
        else:
            self.start_metronome()

    def start_metronome(self):
        self.is_playing = True
        self.current_beat = 0
        self.btn_play.text = "⏹ STOP"
        self.btn_play.background_color = (0.91, 0.30, 0.24, 1)
        interval = 60.0 / self.bpm
        self.metronome_event = Clock.schedule_interval(self.on_tick, interval)
        self.on_tick(0) # First immediate pulse

    def stop_metronome(self):
        self.is_playing = False
        self.btn_play.text = "▶ START"
        self.btn_play.background_color = (0.15, 0.68, 0.38, 1)
        if self.metronome_event:
            self.metronome_event.cancel()
        self.beat_view.set_meter(self.beats_per_bar, 0, False)

    def on_tick(self, dt):
        self.beat_view.set_meter(self.beats_per_bar, self.current_beat, True)
        
        # Haptic Feedback: Heavy tick on beat 1, light on others
        if self.host and self.host.hardware:
            if self.current_beat == 0:
                self.host.hardware.vibrate(60)
            else:
                self.host.hardware.vibrate(25)

        self.current_beat = (self.current_beat + 1) % self.beats_per_bar

    def on_slider_change(self, instance, val):
        self.bpm = int(val)
        self.lbl_bpm.text = f"{self.bpm}\nBPM"
        if self.is_playing:
            self.stop_metronome()
            self.start_metronome()

    def adjust_bpm(self, delta):
        new_bpm = max(40, min(240, self.bpm + delta))
        self.slider.value = new_bpm

    def set_signature(self, beats):
        self.beats_per_bar = beats
        self.current_beat = 0
        self.beat_view.set_meter(self.beats_per_bar, 0, self.is_playing)

    def on_tap_tempo(self, instance):
        now = time.time()
        self.tap_times.append(now)
        # Keep only recent taps within 3 seconds
        self.tap_times = [t for t in self.tap_times if now - t < 3.0]
        
        if len(self.tap_times) >= 2:
            intervals = [self.tap_times[i] - self.tap_times[i - 1] for i in range(1, len(self.tap_times))]
            avg_interval = sum(intervals) / len(intervals)
            if avg_interval > 0:
                calculated_bpm = int(60.0 / avg_interval)
                self.slider.value = max(40, min(240, calculated_bpm))
        
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(20)
