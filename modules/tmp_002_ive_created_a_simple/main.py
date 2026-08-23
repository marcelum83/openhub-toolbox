"""
Bouncing Ball Module (Fixed & Optimized for OpenHub)
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.metrics import dp, sp
from kivy.clock import Clock

class BouncingBallArena(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ball_x = 200
        self.ball_y = 300
        self.radius = dp(28)
        self.vx = 400.0  # px/s
        self.vy = 500.0  # px/s
        self.host = None
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Arena background
            Color(0.08, 0.08, 0.12, 1.0)
            Rectangle(pos=self.pos, size=self.size)

            # Border
            Color(0.02, 0.71, 0.83, 0.5)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=1.5)

            # Glowing Ball Halo
            Color(1.0, 0.5, 0.1, 0.3)
            halo_r = self.radius * 1.5
            Ellipse(pos=(self.ball_x - halo_r, self.ball_y - halo_r), size=(halo_r * 2, halo_r * 2))

            # Core Ball
            Color(1.0, 0.55, 0.15, 1.0)
            Ellipse(pos=(self.ball_x - self.radius, self.ball_y - self.radius), size=(self.radius * 2, self.radius * 2))

            # Specular Reflection
            Color(1.0, 1.0, 1.0, 0.7)
            spec_r = self.radius * 0.35
            Ellipse(pos=(self.ball_x - self.radius * 0.4, self.ball_y + self.radius * 0.2), size=(spec_r, spec_r))

    def update(self, dt):
        if self.width <= 0 or self.height <= 0:
            return

        min_x = self.x + self.radius
        max_x = self.x + self.width - self.radius
        min_y = self.y + self.radius
        max_y = self.y + self.height - self.radius

        self.ball_x += self.vx * dt
        self.ball_y += self.vy * dt

        bounced = False

        if self.ball_x <= min_x:
            self.ball_x = min_x
            self.vx = abs(self.vx)
            bounced = True
        elif self.ball_x >= max_x:
            self.ball_x = max_x
            self.vx = -abs(self.vx)
            bounced = True

        if self.ball_y <= min_y:
            self.ball_y = min_y
            self.vy = abs(self.vy)
            bounced = True
        elif self.ball_y >= max_y:
            self.ball_y = max_y
            self.vy = -abs(self.vy)
            bounced = True

        if bounced and self.host and self.host.hardware:
            self.host.hardware.vibrate(20)

        self.redraw()


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(8), **kwargs)
        self.host = None
        self.event_clock = None

        # Title
        self.add_widget(Label(
            text="⚽ BOUNCING BALL",
            font_size="18sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            size_hint_y=None,
            height=dp(36)
        ))

        # Arena
        self.arena = BouncingBallArena(size_hint_y=1.0)
        self.add_widget(self.arena)

        # Control Row
        ctrl_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
        
        btn_boost = Button(
            text="⚡ SPEED BOOST",
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="14sp",
            always_release=True
        )
        btn_boost.bind(on_release=self.on_boost)
        ctrl_row.add_widget(btn_boost)

        btn_reset = Button(
            text="🔄 CENTER",
            background_normal="",
            background_color=(0.18, 0.18, 0.26, 1.0),
            color=(0.9, 0.9, 0.95, 1.0),
            bold=True,
            font_size="14sp",
            always_release=True
        )
        btn_reset.bind(on_release=self.on_reset)
        ctrl_row.add_widget(btn_reset)

        self.add_widget(ctrl_row)

    def on_load(self, host_api):
        self.host = host_api
        self.arena.host = host_api

    def on_resume(self):
        if not self.event_clock:
            self.event_clock = Clock.schedule_interval(self.arena.update, 1.0 / 60.0)

    def on_pause(self):
        if self.event_clock:
            self.event_clock.cancel()
            self.event_clock = None

    def on_boost(self, *args):
        self.arena.vx *= 1.35
        self.arena.vy *= 1.35
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(35)

    def on_reset(self, *args):
        self.arena.ball_x = self.arena.x + self.arena.width * 0.5
        self.arena.ball_y = self.arena.y + self.arena.height * 0.5
        self.arena.vx = 400.0
        self.arena.vy = 500.0
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(20)