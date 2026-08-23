"""
OpenHub Module: Digital Compass
Magnetometer heading visualizer with cardinal orientations.
"""
import math
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Triangle
from kivy.clock import Clock

class CompassRose(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.heading = 0.0 # 0 = North, 90 = East, etc.
        self.bind(size=self.draw, pos=self.draw)

    def set_heading(self, heading):
        self.heading = heading % 360.0
        self.draw()

    def draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            cx = self.x + self.width / 2.0
            cy = self.y + self.height / 2.0
            radius = min(self.width, self.height) * 0.42
            
            # Outer Ring
            Color(0.15, 0.15, 0.22, 1.0)
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))
            
            Color(0.2, 0.2, 0.3, 0.8)
            Line(circle=(cx, cy, radius), width=2.0)
            Line(circle=(cx, cy, radius * 0.75), width=1.0)
            
            # Draw North Needle pointing towards (0 - heading)
            rad = math.radians(90 - self.heading)
            needle_len = radius * 0.85
            nx = cx + math.cos(rad) * needle_len
            ny = cy + math.sin(rad) * needle_len
            
            # Perpendicular base width for needle
            rad_perp = rad + math.pi / 2.0
            base_w = 16.0
            bx1 = cx + math.cos(rad_perp) * base_w
            by1 = cy + math.sin(rad_perp) * base_w
            bx2 = cx - math.cos(rad_perp) * base_w
            by2 = cy - math.sin(rad_perp) * base_w
            
            # North Pointer (Crimson Red)
            Color(0.91, 0.30, 0.24, 1.0)
            Triangle(points=[nx, ny, bx1, by1, bx2, by2])
            
            # South Pointer (White / Silver)
            sx = cx - math.cos(rad) * needle_len
            sy = cy - math.sin(rad) * needle_len
            Color(0.95, 0.95, 0.97, 0.8)
            Triangle(points=[sx, sy, bx1, by1, bx2, by2])
            
            # Center pin
            Color(0.02, 0.71, 0.83, 1.0)
            Ellipse(pos=(cx - 6, cy - 6), size=(12, 12))


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=16, spacing=14, **kwargs)
        self.host = None
        self.sim_heading = 0.0

        # Compass Visualizer
        self.compass_view = CompassRose(size_hint_y=0.7)
        self.add_widget(self.compass_view)

        # Readout Box
        self.lbl_heading = Label(
            text="000°\nNORTH",
            font_size="28sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            size_hint_y=0.3,
            halign='center'
        )
        self.add_widget(self.lbl_heading)

    def on_load(self, host_api):
        self.host = host_api

    def on_resume(self):
        if self.host and self.host.hardware:
            self.host.hardware.start_sensors()
        self.poll_event = Clock.schedule_interval(self.poll_heading, 1.0 / 25.0)

    def on_pause(self):
        if hasattr(self, 'poll_event'):
            self.poll_event.cancel()
        if self.host and self.host.hardware:
            self.host.hardware.stop_sensors()

    def poll_heading(self, dt):
        heading, sim = 0.0, True
        if self.host and self.host.hardware:
            heading, sim = self.host.hardware.get_compass_heading()
        
        # On desktop simulator, slowly rotate or respond
        if sim:
            self.sim_heading = (self.sim_heading + 0.5) % 360.0
            heading = self.sim_heading

        self.compass_view.set_heading(heading)
        
        cardinal = self._get_cardinal(heading)
        sim_text = " (Sim)" if sim else ""
        self.lbl_heading.text = f"{int(heading):03d}°\n{cardinal}{sim_text}"

    def _get_cardinal(self, h):
        dirs = ["NORTH", "NORTHEAST", "EAST", "SOUTHEAST", "SOUTH", "SOUTHWEST", "WEST", "NORTHWEST"]
        idx = int((h + 22.5) / 45.0) % 8
        return dirs[idx]
