"""
OpenHub Module: Spirit Level & Digital Inclinometer
Uses accelerometer/IMU to render a 2-axis visual bubble and pitch/roll degree meters.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.clock import Clock
import math

class LevelCanvas(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pitch = 0.0 # Forward/backward
        self.roll = 0.0  # Left/right
        self.is_level = False
        self.bind(size=self.draw, pos=self.draw)

    def update_angles(self, pitch, roll):
        self.pitch = pitch
        self.roll = roll
        self.is_level = abs(pitch) < 1.0 and abs(roll) < 1.0
        self.draw()

    def draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Background circular target
            cx = self.x + self.width / 2.0
            cy = self.y + self.height / 2.0
            radius = min(self.width, self.height) * 0.42
            
            # Outer ring
            Color(0.15, 0.15, 0.22, 1.0)
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))
            
            # Crosshairs
            Color(0.3, 0.3, 0.4, 0.8)
            Line(points=[cx - radius, cy, cx + radius, cy], width=1.5)
            Line(points=[cx, cy - radius, cx, cy + radius], width=1.5)
            
            # Center target bullseye
            target_r = radius * 0.2
            Color(0.02, 0.71, 0.83, 0.4)
            Line(circle=(cx, cy, target_r), width=2.0)
            
            # Calculate bubble position (clamped to radius)
            # 45 degrees max tilt for full radius displacement
            max_angle = 45.0
            norm_x = max(-1.0, min(1.0, self.roll / max_angle))
            norm_y = max(-1.0, min(1.0, self.pitch / max_angle))
            
            bubble_x = cx + (norm_x * (radius - 20))
            bubble_y = cy + (norm_y * (radius - 20))
            bubble_r = 18.0
            
            # Bubble Color: Neon Emerald when level (< 1.0 deg), Neon Amber otherwise
            if self.is_level:
                Color(0.15, 0.68, 0.38, 0.95) # Glowing green
            else:
                Color(0.95, 0.61, 0.07, 0.9)  # Glowing amber
                
            Ellipse(pos=(bubble_x - bubble_r, bubble_y - bubble_r), size=(bubble_r * 2, bubble_r * 2))
            Color(1, 1, 1, 0.9)
            Line(circle=(bubble_x, bubble_y, bubble_r), width=1.8)


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=16, spacing=12, **kwargs)
        self.host = None
        self.cal_pitch = 0.0
        self.cal_roll = 0.0
        self.was_level = False
        
        # Level canvas visualizer
        self.level_view = LevelCanvas(size_hint_y=0.65)
        self.add_widget(self.level_view)
        
        # Readout Card
        readouts = BoxLayout(orientation='horizontal', size_hint_y=0.2, spacing=10)
        
        # Pitch Box
        self.lbl_pitch = Label(
            text="PITCH\n0.0°",
            font_size="20sp",
            bold=True,
            color=(0.95, 0.95, 0.97, 1),
            halign='center'
        )
        readouts.add_widget(self.lbl_pitch)
        
        # Roll Box
        self.lbl_roll = Label(
            text="ROLL\n0.0°",
            font_size="20sp",
            bold=True,
            color=(0.95, 0.95, 0.97, 1),
            halign='center'
        )
        readouts.add_widget(self.lbl_roll)
        self.add_widget(readouts)
        
        # Calibration Action Bar
        actions = BoxLayout(orientation='horizontal', size_hint_y=0.15, spacing=10)
        btn_zero = Button(
            text="🎯 ZERO CALIBRATE",
            background_normal="",
            background_color=(0.02, 0.71, 0.83, 1),
            color=(0.05, 0.05, 0.08, 1),
            bold=True
        )
        btn_zero.bind(on_release=self.zero_calibrate)
        actions.add_widget(btn_zero)
        
        btn_reset = Button(
            text="RESET",
            size_hint_x=0.4,
            background_normal="",
            background_color=(0.13, 0.13, 0.19, 1),
            color=(0.95, 0.95, 0.97, 1),
            bold=True
        )
        btn_reset.bind(on_release=self.reset_calibrate)
        actions.add_widget(btn_reset)
        self.add_widget(actions)

    def on_load(self, host_api):
        self.host = host_api

    def on_resume(self):
        if self.host and self.host.hardware:
            self.host.hardware.start_sensors()
        self.poll_event = Clock.schedule_interval(self.poll_sensors, 1.0 / 30.0) # 30 FPS update

    def on_pause(self):
        if hasattr(self, 'poll_event'):
            self.poll_event.cancel()
        if self.host and self.host.hardware:
            self.host.hardware.stop_sensors()

    def poll_sensors(self, dt):
        pitch, roll, simulated = 0.0, 0.0, False
        if self.host and self.host.hardware:
            p, r, sim = self.host.hardware.get_orientation_angles()
            pitch = p - self.cal_pitch
            roll = r - self.cal_roll
            simulated = sim

        self.level_view.update_angles(pitch, roll)
        
        # Update text labels
        sim_tag = " (Sim)" if simulated else ""
        self.lbl_pitch.text = f"PITCH{sim_tag}\n{pitch:+.1f}°"
        self.lbl_roll.text = f"ROLL{sim_tag}\n{roll:+.1f}°"
        
        # Haptic trigger upon entering level
        is_level = abs(pitch) < 1.0 and abs(roll) < 1.0
        if is_level and not self.was_level:
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(30)
        self.was_level = is_level

    def zero_calibrate(self, instance):
        if self.host and self.host.hardware:
            p, r, _ = self.host.hardware.get_orientation_angles()
            self.cal_pitch = p
            self.cal_roll = r
            if self.host.hardware:
                self.host.hardware.vibrate(50)

    def reset_calibrate(self, instance):
        self.cal_pitch = 0.0
        self.cal_roll = 0.0
