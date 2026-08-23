"""
Kinetic Physics & Gravity Ball Sandbox
Interactive 2D multi-body physics with IMU tilt steering, touch throwing, elasticity controls and haptic impacts.
"""
import random
import math
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.metrics import dp, sp
from kivy.clock import Clock

class Ball:
    def __init__(self, x, y, vx=0.0, vy=0.0, radius=24, color=(0.02, 0.71, 0.83, 1.0)):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = radius
        self.color = color
        self.is_dragged = False
        self.trail = []

class PhysicsArena(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.balls = []
        self.gravity_y = -980.0 # px/s^2
        self.gravity_x = 0.0
        self.elasticity = 0.78  # Bounciness
        self.friction = 0.992   # Air drag
        self.active_ball = None
        self.touch_prev_pos = None
        self.touch_time = 0
        self.host = None
        self.last_haptic_time = 0

        self.bind(pos=self.redraw, size=self.redraw)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        tx, ty = touch.pos
        # Check if touching an existing ball
        for b in reversed(self.balls):
            dist = math.hypot(b.x - tx, b.y - ty)
            if dist <= b.radius * 1.5:
                self.active_ball = b
                b.is_dragged = True
                b.vx = 0
                b.vy = 0
                self.touch_prev_pos = (tx, ty)
                if self.host and self.host.hardware:
                    self.host.hardware.vibrate(20)
                return True

        # Otherwise spawn a new ball
        if len(self.balls) < 12:
            colors = [
                (0.02, 0.71, 0.83, 1.0), # Cyan
                (0.54, 0.36, 0.96, 1.0), # Violet
                (0.15, 0.68, 0.38, 1.0), # Green
                (0.95, 0.60, 0.07, 1.0), # Amber
                (0.91, 0.30, 0.24, 1.0)  # Coral
            ]
            col = random.choice(colors)
            rad = dp(random.randint(18, 30))
            new_b = Ball(tx, ty, vx=random.uniform(-100, 100), vy=random.uniform(50, 200), radius=rad, color=col)
            self.balls.append(new_b)
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(30)
            self.redraw()
            return True

        return True

    def on_touch_move(self, touch):
        if self.active_ball and self.collide_point(*touch.pos):
            tx, ty = touch.pos
            if self.touch_prev_pos:
                dt = 0.016
                self.active_ball.vx = (tx - self.touch_prev_pos[0]) / dt
                self.active_ball.vy = (ty - self.touch_prev_pos[1]) / dt
            self.active_ball.x = tx
            self.active_ball.y = ty
            self.touch_prev_pos = (tx, ty)
            self.redraw()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.active_ball:
            self.active_ball.is_dragged = False
            # Clamp throw velocity
            max_v = 2500
            self.active_ball.vx = max(-max_v, min(max_v, self.active_ball.vx))
            self.active_ball.vy = max(-max_v, min(max_v, self.active_ball.vy))
            self.active_ball = None
            self.touch_prev_pos = None
            return True
        return super().on_touch_up(touch)

    def update_physics(self, dt):
        if self.width <= 0 or self.height <= 0:
            return

        import time
        now = time.time()
        had_hard_collision = False

        # Read accelerometer tilt if available
        if self.host and self.host.hardware:
            try:
                pitch, roll, is_sim = self.host.hardware.get_orientation_angles()
                # roll (-90 to +90) -> gravity X, pitch (-90 to +90) -> gravity Y
                self.gravity_x = math.sin(math.radians(roll)) * 1200.0
                self.gravity_y = -math.cos(math.radians(roll)) * math.sin(math.radians(pitch)) * 1200.0 - 400.0
            except Exception:
                pass

        min_x = self.x
        max_x = self.x + self.width
        min_y = self.y
        max_y = self.y + self.height

        for b in self.balls:
            if b.is_dragged:
                continue

            # Apply gravity & drag
            b.vx += self.gravity_x * dt
            b.vy += self.gravity_y * dt
            b.vx *= self.friction
            b.vy *= self.friction

            # Move
            b.x += b.vx * dt
            b.y += b.vy * dt

            # Wall Collisions: Left / Right
            if b.x - b.radius < min_x:
                b.x = min_x + b.radius
                b.vx = -b.vx * self.elasticity
                if abs(b.vx) > 150:
                    had_hard_collision = True
            elif b.x + b.radius > max_x:
                b.x = max_x - b.radius
                b.vx = -b.vx * self.elasticity
                if abs(b.vx) > 150:
                    had_hard_collision = True

            # Floor / Ceiling Collisions
            if b.y - b.radius < min_y:
                b.y = min_y + b.radius
                b.vy = -b.vy * self.elasticity
                # Surface friction
                b.vx *= 0.95
                if abs(b.vy) > 150:
                    had_hard_collision = True
            elif b.y + b.radius > max_y:
                b.y = max_y - b.radius
                b.vy = -b.vy * self.elasticity
                if abs(b.vy) > 150:
                    had_hard_collision = True

        # Ball-to-ball collisions
        num_balls = len(self.balls)
        for i in range(num_balls):
            b1 = self.balls[i]
            for j in range(i + 1, num_balls):
                b2 = self.balls[j]
                dx = b2.x - b1.x
                dy = b2.y - b1.y
                dist = math.hypot(dx, dy)
                min_dist = b1.radius + b2.radius
                if dist < min_dist and dist > 0:
                    # Overlap resolution
                    overlap = 0.5 * (min_dist - dist)
                    nx = dx / dist
                    ny = dy / dist
                    b1.x -= nx * overlap
                    b1.y -= ny * overlap
                    b2.x += nx * overlap
                    b2.y += ny * overlap

                    # Elastic collision impulse
                    kx = b1.vx - b2.vx
                    ky = b1.vy - b2.vy
                    p = 2 * (nx * kx + ny * ky) / 2.0
                    b1.vx -= p * nx * self.elasticity
                    b1.vy -= p * ny * self.elasticity
                    b2.vx += p * nx * self.elasticity
                    b2.vy += p * ny * self.elasticity
                    had_hard_collision = True

        if had_hard_collision and now - self.last_haptic_time > 0.08:
            self.last_haptic_time = now
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(15)

        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Background arena
            Color(0.07, 0.07, 0.11, 1.0)
            Rectangle(pos=self.pos, size=self.size)

            # Arena border
            Color(0.02, 0.71, 0.83, 0.5)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=1.5)

            # Draw Balls
            for b in self.balls:
                # Glow halo
                Color(b.color[0], b.color[1], b.color[2], 0.25)
                halo_rad = b.radius * 1.5
                Ellipse(pos=(b.x - halo_rad, b.y - halo_rad), size=(halo_rad * 2, halo_rad * 2))

                # Core Ball
                Color(*b.color)
                Ellipse(pos=(b.x - b.radius, b.y - b.radius), size=(b.radius * 2, b.radius * 2))

                # Inner light reflection
                Color(1, 1, 1, 0.6)
                spec_rad = b.radius * 0.35
                Ellipse(pos=(b.x - b.radius * 0.45, b.y + b.radius * 0.2), size=(spec_rad, spec_rad))


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(8), **kwargs)
        self.host = None
        self.event_clock = None

        # Title & Info Bar
        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))
        self.lbl_title = Label(
            text="⚡ KINETIC PHYSICS SANDBOX",
            font_size="17sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        head.add_widget(self.lbl_title)

        self.lbl_info = Label(
            text="Tap: Spawn | Fling: Throw",
            font_size="12sp",
            color=(0.7, 0.7, 0.8, 1),
            size_hint_x=None,
            width=dp(150),
            halign='right',
            valign='middle'
        )
        self.lbl_info.bind(size=self.lbl_info.setter('text_size'))
        head.add_widget(self.lbl_info)
        self.add_widget(head)

        # Physics Arena
        self.arena = PhysicsArena(size_hint_y=1.0)
        self.add_widget(self.arena)

        # Control Row 1: [💥 EXPLODE] [🎲 ADD 3] [🧹 CLEAR]
        ctrl_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(6))
        
        btn_blast = Button(
            text="💥 BLAST",
            size_hint_x=0.34,
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 0.95),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="14sp",
            always_release=True
        )
        btn_blast.bind(on_release=self.blast_balls)
        ctrl_row.add_widget(btn_blast)

        btn_add = Button(
            text="➕ ADD 3",
            size_hint_x=0.33,
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="14sp",
            always_release=True
        )
        btn_add.bind(on_release=self.add_multiple_balls)
        ctrl_row.add_widget(btn_add)

        btn_clear = Button(
            text="🧹 CLEAR",
            size_hint_x=0.33,
            background_normal="",
            background_color=(0.3, 0.1, 0.1, 1.0),
            color=(1, 0.4, 0.4, 1.0),
            bold=True,
            font_size="14sp",
            always_release=True
        )
        btn_clear.bind(on_release=self.clear_arena)
        ctrl_row.add_widget(btn_clear)
        self.add_widget(ctrl_row)

        # Control Row 2: Elasticity / Bounciness Slider
        bounce_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(6))
        bounce_row.add_widget(Label(text="Bounciness:", font_size="13sp", size_hint_x=None, width=dp(85), color=(0.8, 0.8, 0.9, 1)))
        
        self.slider_bounce = Slider(min=0.1, max=0.98, value=0.78, size_hint_x=1.0)
        self.slider_bounce.bind(value=self.on_bounce_changed)
        bounce_row.add_widget(self.slider_bounce)
        self.add_widget(bounce_row)

        # Spawn initial 3 balls
        Clock.schedule_once(lambda dt: self.spawn_initial_balls(), 0.1)

    def on_load(self, host_api):
        self.host = host_api
        self.arena.host = host_api

    def on_resume(self):
        if not self.event_clock:
            self.event_clock = Clock.schedule_interval(self.arena.update_physics, 1.0 / 60.0)

    def on_pause(self):
        if self.event_clock:
            self.event_clock.cancel()
            self.event_clock = None

    def spawn_initial_balls(self):
        cx = self.arena.x + self.arena.width * 0.5
        cy = self.arena.y + self.arena.height * 0.6
        if self.arena.width <= 0:
            cx, cy = dp(180), dp(300)
        colors = [(0.02, 0.71, 0.83, 1), (0.54, 0.36, 0.96, 1), (0.15, 0.68, 0.38, 1)]
        for i, col in enumerate(colors):
            b = Ball(cx + (i - 1) * dp(50), cy, vx=random.uniform(-150, 150), vy=random.uniform(50, 200), radius=dp(22), color=col)
            self.arena.balls.append(b)
        self.arena.redraw()
        if not self.event_clock:
            self.event_clock = Clock.schedule_interval(self.arena.update_physics, 1.0 / 60.0)

    def blast_balls(self, *args):
        for b in self.arena.balls:
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(800, 1800)
            b.vx = math.cos(angle) * speed
            b.vy = math.sin(angle) * speed
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(45)

    def add_multiple_balls(self, *args):
        cx = self.arena.x + self.arena.width * 0.5
        cy = self.arena.y + self.arena.height * 0.7
        colors = [(0.95, 0.60, 0.07, 1), (0.91, 0.30, 0.24, 1), (0.02, 0.71, 0.83, 1)]
        for col in colors:
            if len(self.arena.balls) < 14:
                b = Ball(cx + random.uniform(-dp(40), dp(40)), cy, vx=random.uniform(-200, 200), vy=random.uniform(-50, 200), radius=dp(random.randint(18, 26)), color=col)
                self.arena.balls.append(b)
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(30)

    def clear_arena(self, *args):
        self.arena.balls.clear()
        self.arena.redraw()

    def on_bounce_changed(self, inst, val):
        self.arena.elasticity = float(val)
