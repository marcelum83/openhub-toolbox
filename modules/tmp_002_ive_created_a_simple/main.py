from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse
from kivy.clock import Clock
from random import randint

class Ball(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(1, 0.5, 0.2)
            self.ball = Ellipse(pos=(self.center_x - 30, self.center_y - 30), size=(60, 60))

    def update(self, dt):
        dx, dy = 5, 5
        if self.right > self.parent.width or self.left < 0:
            dx *= -1
        if self.top > self.parent.height or self.bottom < 0:
            dy *= -1
        self.center_x += dx
        self.center_y += dy

class BouncingBallApp(App):
    def build(self):
        game_widget = Widget()
        ball = Ball(pos=(self.root.width // 2, self.root.height // 2))
        game_widget.add_widget(ball)
        Clock.schedule_interval(ball.update, 1.0/60.0)
        return game_widget

if __name__ == '__main__':
    BouncingBallApp().run()