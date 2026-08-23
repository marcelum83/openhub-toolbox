# Polyhedral Dice Module
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp, sp
import random

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(16), spacing=dp(12), **kwargs)
        self.host = None
        self.lbl = Label(text="Roll: -")
        self.add_widget(self.lbl)
        btn = Button(text="Roll D20", always_release=True)
        btn.bind(on_release=self.roll)
        self.add_widget(btn)
    def on_load(self, host_api):
        self.host = host_api
    def roll(self, *a):
        val = random.randint(1, 20)
        self.lbl.text = f"Roll: {val}"
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(30)
