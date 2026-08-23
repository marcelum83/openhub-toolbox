from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp, sp
from kivy.clock import Clock
import random

class ReactionSpeedTest(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(12), **kwargs)
        self.host = None
        self.game_over = False
        self.response_time = None

        # Title
        self.lbl_title = Label(
            text="Reaction Speed Test",
            font_size="24sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            size_hint_y=None,
            height=dp(50)
        )
        self.add_widget(self.lbl_title)

        # Primary Display
        self.lbl_display = Label(
            text="Press 'GO!' when you're ready",
            font_size="20sp",
            color=(0.95, 0.95, 0.97, 1),
            size_hint_y=0.5
        )
        self.add_widget(self.lbl_display)

        # Interactive Button
        self.btn_action = Button(
            text="GO!",
            size_hint_y=None,
            height=dp(64),
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="20sp",
            always_release=True
        )
        self.btn_action.bind(on_release=self.on_btn_pressed)
        self.add_widget(self.btn_action)

    def on_load(self, host_api):
        self.host = host_api

    def on_resume(self):
        pass

    def on_pause(self):
        pass

    def on_btn_pressed(self, *args):
        if not self.game_over:
            self.start_test()

    def start_test(self):
        delay = random.uniform(1.0, 3.0)
        Clock.schedule_once(self.show_go, delay)

    def show_go(self, dt):
        self.lbl_display.text = "GO!"
        self.btn_action.disabled = True
        Clock.schedule_once(self.record_response, 2.0)  # Time to react

    def record_response(self, dt):
        if not self.game_over:
            self.response_time = dt - 2.0
            self.lbl_display.text = f"Your reaction time: {self.response_time:.2f} seconds"
            self.btn_action.disabled = False
            Clock.schedule_once(self.start_test, 3.0)  # Wait before next test

    def on_pause(self):
        self.game_over = True

    def on_resume(self):
        self.game_over = False

# OpenHub Container Alias
OpenHubModule = ReactionSpeedTest

# OpenHub Container Alias
OpenHubModule = ReactionSpeedTest
