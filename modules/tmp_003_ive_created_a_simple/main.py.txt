from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.graphics.rectangle import Rectangle
from kivy.graphics.color import Color
from kivy.clock import Clock
import random

class Player(Scatter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (50, 50)
        with self.canvas:
            Color(1, 0.5, 0.3)
            Rectangle(pos=self.pos, size=self.size)

class Item(Scatter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (20, 20)
        with self.canvas:
            Color(0.1, 0.8, 0.4)
            Rectangle(pos=self.pos, size=self.size)

class GameLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(12), **kwargs)
        self.host = None
        self.player = Player()
        self.add_widget(self.player)
        self.items = []
        for _ in range(5):
            item = Item(pos=(random.randint(0, 800), random.randint(0, 600)))
            self.add_widget(item)
            self.items.append(item)

    def on_load(self, host_api):
        self.host = host_api
        Clock.schedule_interval(self.update, 1.0 / 30.0)

    def update(self, dt):
        for item in self.items:
            if (self.player.center_x - item.center_x) ** 2 + (self.player.center_y - item.center_y) ** 2 < (item.size[0] / 2 + self.player.size[0] / 2) ** 2:
                self.remove_widget(item)
                self.items.remove(item)

class PokemonCloneApp(App):
    def build(self):
        layout = GameLayout()
        return layout

if __name__ == '__main__':
    PokemonCloneApp().run()