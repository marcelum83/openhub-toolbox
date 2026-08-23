"""
OpenHub Module: Ambient Light (Lux) Meter
Measures ambient illuminance, classifies environment lighting standards, and logs min/max peaks.
"""
import math
import random
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
from kivy.clock import Clock
from kivy.metrics import dp, sp

def classify_lux(lux):
    """Returns (category_name, icon, recommendation_text)."""
    if lux < 5:
        return "NIGHT / DARK", "🌑", "Moonlight / Deep Shadows (< 5 Lux)"
    elif lux < 50:
        return "DIM INTERIOR", "🕯️", "Mood Lighting / Nightlight (10 - 50 Lux)"
    elif lux < 200:
        return "LIVING ROOM", "🛋️", "Normal Home Environment (50 - 200 Lux)"
    elif lux < 500:
        return "OFFICE / STUDY", "💻", "Standard Workstation & Reading (200 - 500 Lux)"
    elif lux < 1000:
        return "PRECISION WORK", "🔬", "Lab / Drafting / Retail (500 - 1,000 Lux)"
    elif lux < 10000:
        return "OVERCAST DAYLIGHT", "⛅", "Outdoor Overcast / Shaded Sun (1,000 - 10,000 Lux)"
    else:
        return "DIRECT SUNLIGHT", "☀️", "Bright Direct Sun (> 10,000 Lux)"


class LuxOrbVisualizer(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lux = 350.0
        self.bind(size=self.draw, pos=self.draw)

    def set_lux(self, lux):
        self.lux = max(0.0, float(lux))
        self.draw()

    def draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            cx = self.x + self.width / 2.0
            cy = self.y + self.height / 2.0
            radius = min(self.width, self.height) * 0.38
            
            # Logarithmic normalization for 0 to 50,000 Lux
            log_val = math.log10(max(1.0, self.lux)) / 4.7 # 0 to ~1.0
            norm = min(1.0, max(0.05, log_val))
            
            # Outer diffuse glow halo
            Color(1.0, 0.85, 0.2, norm * 0.4)
            Ellipse(pos=(cx - radius * 1.3, cy - radius * 1.3), size=(radius * 2.6, radius * 2.6))
            
            # Outer Ring
            Color(0.2, 0.2, 0.28, 1.0)
            Line(circle=(cx, cy, radius), width=dp(2.5))
            
            # Sun / Photon Core
            core_r = radius * (0.3 + norm * 0.6)
            Color(1.0, 0.9 - norm * 0.2, 0.1 + (1.0 - norm) * 0.4, 0.9)
            Ellipse(pos=(cx - core_r, cy - core_r), size=(core_r * 2, core_r * 2))
            
            # Inner brilliance
            Color(1, 1, 1, 0.95 * norm)
            Ellipse(pos=(cx - core_r * 0.5, cy - core_r * 0.5), size=(core_r, core_r))


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(12), **kwargs)
        self.host = None
        self.current_lux = 350.0
        self.min_lux = 350.0
        self.max_lux = 350.0
        self.is_monitoring = True
        
        # 1. Main Lux Display Card
        top_card = BoxLayout(orientation='vertical', size_hint_y=0.45, padding=dp(10), spacing=dp(6))
        with top_card.canvas.before:
            Color(0.09, 0.09, 0.13, 1.0)
            self.bg_card = RoundedRectangle(size=top_card.size, pos=top_card.pos, radius=[dp(16)])
            Color(0.95, 0.61, 0.07, 0.5)
            self.border_card = Line(rounded_rectangle=(top_card.x, top_card.y, top_card.width, top_card.height, dp(16)), width=1.0)
        top_card.bind(size=self._update_top_card, pos=self._update_top_card)

        self.lbl_lux_value = Label(
            text="350",
            font_size="52sp",
            bold=True,
            color=(0.95, 0.61, 0.07, 1.0),
            size_hint_y=0.55,
            halign='center'
        )
        self.lbl_lux_value.bind(size=self.lbl_lux_value.setter('text_size'))
        top_card.add_widget(self.lbl_lux_value)

        self.lbl_unit = Label(
            text="LUX (LUMENS / m²)",
            font_size="13sp",
            bold=True,
            color=(0.6, 0.6, 0.7, 1.0),
            size_hint_y=0.15,
            halign='center'
        )
        self.lbl_unit.bind(size=self.lbl_unit.setter('text_size'))
        top_card.add_widget(self.lbl_unit)

        self.lbl_category = Label(
            text="💻 OFFICE / STUDY",
            font_size="18sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0),
            size_hint_y=0.30,
            halign='center'
        )
        self.lbl_category.bind(size=self.lbl_category.setter('text_size'))
        top_card.add_widget(self.lbl_category)
        self.add_widget(top_card)

        # 2. Glowing Lux Orb Visualizer
        self.orb_view = LuxOrbVisualizer(size_hint_y=0.35)
        self.add_widget(self.orb_view)

        # 3. Stats Row (Min / Max / Rec)
        stats_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        
        self.lbl_min = Label(
            text="Min: 350 lx",
            font_size="14sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0)
        )
        stats_box.add_widget(self.lbl_min)

        self.lbl_max = Label(
            text="Max: 350 lx",
            font_size="14sp",
            bold=True,
            color=(0.91, 0.30, 0.24, 1.0)
        )
        stats_box.add_widget(self.lbl_max)

        btn_reset = Button(
            text="🔄 RESET",
            size_hint_x=None,
            width=dp(95),
            background_normal="",
            background_color=(0.13, 0.13, 0.19, 1.0),
            color=(0.95, 0.95, 0.97, 1.0),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_reset.bind(on_release=self.reset_stats)
        stats_box.add_widget(btn_reset)
        self.add_widget(stats_box)

    def _update_top_card(self, instance, value):
        self.bg_card.pos = instance.pos
        self.bg_card.size = instance.size
        self.border_card.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, dp(16))

    def on_load(self, host_api):
        self.host = host_api

    def on_resume(self):
        self.is_monitoring = True
        if self.host and self.host.hardware:
            self.host.hardware.start_sensors()
        self.poll_event = Clock.schedule_interval(self.poll_lux, 1.0 / 15.0)

    def on_pause(self):
        if hasattr(self, 'poll_event') and self.poll_event:
            self.poll_event.cancel()
            self.poll_event = None
        self.is_monitoring = False
        if self.host and self.host.hardware:
            self.host.hardware.stop_sensors()

    def reset_stats(self, *args):
        self.min_lux = self.current_lux
        self.max_lux = self.current_lux
        self.lbl_min.text = f"Min: {int(self.min_lux)} lx"
        self.lbl_max.text = f"Max: {int(self.max_lux)} lx"
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(25)

    def poll_lux(self, dt):
        if not self.is_monitoring:
            return
        
        lux_val, sim = 350.0, True
        if self.host and self.host.hardware:
            lux_val, sim = self.host.hardware.get_lux()
        
        # Subtle drift simulation for desktop testing
        if sim:
            drift = (random.random() - 0.5) * 12.0
            self.current_lux = max(1.0, self.current_lux + drift)
        else:
            self.current_lux = float(lux_val)

        self.min_lux = min(self.min_lux, self.current_lux)
        self.max_lux = max(self.max_lux, self.current_lux)

        cat_title, cat_icon, cat_desc = classify_lux(self.current_lux)
        
        self.lbl_lux_value.text = f"{int(self.current_lux):,}"
        self.lbl_category.text = f"{cat_icon} {cat_title}"
        self.lbl_min.text = f"Min: {int(self.min_lux):,} lx"
        self.lbl_max.text = f"Max: {int(self.max_lux):,} lx"
        
        self.orb_view.set_lux(self.current_lux)
