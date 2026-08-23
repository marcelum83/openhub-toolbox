"""
Precision Reflex & Reaction Speed Test (Professional State Machine)
Sub-millisecond high-precision timer with false-start detection, haptic triggers, and high-score tracking.
"""
import time
import random
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp, sp
from kivy.clock import Clock

class State:
    IDLE = 0
    ARMED = 1
    TRIGGERED = 2
    RESULT = 3

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(12), **kwargs)
        self.host = None
        self.state = State.IDLE
        self.armed_time = 0
        self.trigger_time = 0
        self.scheduled_trigger = None
        self.best_score_ms = None
        self.history = []

        # 1. Header Bar
        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))
        self.lbl_title = Label(
            text="⚡ REACTION SPEED BENCHMARK",
            font_size="17sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        head.add_widget(self.lbl_title)

        self.lbl_best = Label(
            text="Best: -- ms",
            font_size="14sp",
            bold=True,
            color=(0.95, 0.75, 0.1, 1),
            size_hint_x=None,
            width=dp(110),
            halign='right',
            valign='middle'
        )
        self.lbl_best.bind(size=self.lbl_best.setter('text_size'))
        head.add_widget(self.lbl_best)
        self.add_widget(head)

        # 2. Main Large Reaction Touch Pad Button
        self.pad_box = BoxLayout(orientation='vertical', size_hint_y=1.0, padding=dp(16))
        with self.pad_box.canvas.before:
            self.bg_color = Color(0.12, 0.13, 0.20, 1.0)
            self.bg_rect = RoundedRectangle(size=self.pad_box.size, pos=self.pad_box.pos, radius=[dp(18)])
            self.bdr_color = Color(0.02, 0.71, 0.83, 0.5)
            self.bdr_rect = Line(rounded_rectangle=(self.pad_box.x, self.pad_box.y, self.pad_box.width, self.pad_box.height, dp(18)), width=1.5)
        self.pad_box.bind(size=self._update_pad_rects, pos=self._update_pad_rects)

        self.lbl_main = Label(
            text="TAP TO START",
            font_size="28sp",
            bold=True,
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            size_hint_y=0.6
        )
        self.lbl_main.bind(size=self.lbl_main.setter('text_size'))
        self.pad_box.add_widget(self.lbl_main)

        self.lbl_sub = Label(
            text="Wait for the pad to turn GREEN, then tap as fast as you can.",
            font_size="14sp",
            color=(0.7, 0.7, 0.8, 1),
            halign='center',
            valign='middle',
            size_hint_y=0.4
        )
        self.lbl_sub.bind(size=self.lbl_sub.setter('text_size'))
        self.pad_box.add_widget(self.lbl_sub)

        # Invisible large button overlay over entire pad for responsive touch
        self.btn_pad = Button(
            text="",
            background_normal="",
            background_color=(0, 0, 0, 0),
            size_hint=(1.0, 1.0),
            always_release=True
        )
        self.btn_pad.bind(on_release=self.on_pad_tapped)
        
        # Overlay container
        container = BoxLayout(size_hint_y=1.0)
        container.add_widget(self.pad_box)
        self.add_widget(container)

        # 3. Bottom Reset / Stats Row
        self.lbl_stats = Label(
            text="Attempts: 0 | Avg: -- ms",
            font_size="13sp",
            color=(0.6, 0.6, 0.7, 1),
            size_hint_y=None,
            height=dp(30),
            halign='center'
        )
        self.lbl_stats.bind(size=self.lbl_stats.setter('text_size'))
        self.add_widget(self.lbl_stats)

    def _update_pad_rects(self, inst, val):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size
        self.bdr_rect.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(18))

    def on_load(self, host_api):
        self.host = host_api

    def on_resume(self):
        pass

    def on_pause(self):
        self._cancel_timer()
        self.state = State.IDLE
        self._set_ui_idle()

    def _cancel_timer(self):
        if self.scheduled_trigger:
            self.scheduled_trigger.cancel()
            self.scheduled_trigger = None

    def on_pad_tapped(self, *args):
        now = time.perf_counter()

        if self.state == State.IDLE or self.state == State.RESULT:
            # Transition to ARMED
            self.state = State.ARMED
            self._set_ui_armed()
            delay = random.uniform(1.8, 4.2)
            self._cancel_timer()
            self.scheduled_trigger = Clock.schedule_once(self._trigger_green, delay)

        elif self.state == State.ARMED:
            # FALSE START! User tapped too early
            self._cancel_timer()
            self.state = State.RESULT
            self._set_ui_false_start()
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(50)

        elif self.state == State.TRIGGERED:
            # VALID HIT! Calculate exact milliseconds
            reaction_ms = int((now - self.trigger_time) * 1000)
            self.state = State.RESULT
            self.history.append(reaction_ms)
            
            if self.best_score_ms is None or reaction_ms < self.best_score_ms:
                self.best_score_ms = reaction_ms
                self.lbl_best.text = f"Best: {reaction_ms} ms"

            avg_ms = int(sum(self.history) / len(self.history))
            self.lbl_stats.text = f"Attempts: {len(self.history)} | Avg: {avg_ms} ms | Last: {reaction_ms} ms"

            self._set_ui_result(reaction_ms)
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(30)

    def _trigger_green(self, dt):
        if self.state != State.ARMED:
            return
        self.state = State.TRIGGERED
        self.trigger_time = time.perf_counter()
        self._set_ui_triggered()
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(40)

    def _set_ui_idle(self):
        self.bg_color.rgba = (0.12, 0.13, 0.20, 1.0)
        self.bdr_color.rgba = (0.02, 0.71, 0.83, 0.5)
        self.lbl_main.text = "TAP TO START"
        self.lbl_main.color = (1, 1, 1, 1)
        self.lbl_sub.text = "Wait for GREEN, then tap as fast as possible."

    def _set_ui_armed(self):
        # Amber / Red: WAITING
        self.bg_color.rgba = (0.75, 0.18, 0.15, 1.0)
        self.bdr_color.rgba = (1.0, 0.4, 0.3, 0.8)
        self.lbl_main.text = "WAIT FOR GREEN..."
        self.lbl_main.color = (1, 1, 1, 1)
        self.lbl_sub.text = "Don't tap yet! Watch the screen..."

    def _set_ui_triggered(self):
        # Emerald Green: TAP NOW!
        self.bg_color.rgba = (0.15, 0.75, 0.35, 1.0)
        self.bdr_color.rgba = (0.4, 1.0, 0.6, 1.0)
        self.lbl_main.text = "⚡ TAP NOW! ⚡"
        self.lbl_main.color = (1, 1, 1, 1)
        self.lbl_sub.text = "TAP THE SCREEN NOW!"

    def _set_ui_false_start(self):
        self.bg_color.rgba = (0.35, 0.10, 0.10, 1.0)
        self.bdr_color.rgba = (0.9, 0.2, 0.2, 1.0)
        self.lbl_main.text = "❌ TOO EARLY!"
        self.lbl_main.color = (1.0, 0.4, 0.4, 1)
        self.lbl_sub.text = "You tapped before it turned green. Tap to try again."

    def _set_ui_result(self, ms):
        # Blue / Violet Result
        self.bg_color.rgba = (0.15, 0.18, 0.30, 1.0)
        self.bdr_color.rgba = (0.02, 0.71, 0.83, 0.9)
        self.lbl_main.text = f"{ms} ms"
        
        rating = "⚡ Lightning Fast!"
        if ms < 200:
            rating = "🏆 Godlike Reflexes (<200ms)!"
        elif ms < 260:
            rating = "⚡ Pro Gamer Speed (<260ms)!"
        elif ms < 350:
            rating = "👍 Good Human Reflexes!"
        else:
            rating = "🐢 A bit slow! Try again!"

        self.lbl_main.color = (0.02, 0.85, 0.95, 1)
        self.lbl_sub.text = f"{rating}\nTap anywhere to test again."

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.on_pad_tapped()
            return True
        return super().on_touch_down(touch)
