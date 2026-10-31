# OpenHub Dynamic Module
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.metrics import dp

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(14), **kwargs)
        
        self.add_widget(Label(
            text="✨ My Custom Tool",
            font_size="24sp",
            bold=True,
            size_hint_y=None,
            height=dp(45),
            color=(0.02, 0.71, 0.83, 1)
        ))
        
        self.val_label = Label(text="Input Value: 10.0", font_size="18sp", size_hint_y=None, height=dp(35))
        self.add_widget(self.val_label)
        
        slider = Slider(min=1, max=100, value=10, size_hint_y=None, height=dp(50))
        slider.bind(value=self.on_slider)
        self.add_widget(slider)
        
        btn = Button(
            text="Calculate / Actuate",
            size_hint_y=None,
            height=dp(54),
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1),
            bold=True,
            font_size="16sp"
        )
        btn.bind(on_release=self.on_press_btn)
        self.add_widget(btn)

    def on_load(self, host_api):
        self.host = host_api

    def on_slider(self, inst, val):
        self.val_label.text = f"Input Value: {val:.1f}"

    def on_press_btn(self, inst):
        if hasattr(self, 'host') and self.host and self.host.hardware:
            self.host.hardware.vibrate(40)
        self.val_label.text = "⚡ Executed with Haptic Pulse!"