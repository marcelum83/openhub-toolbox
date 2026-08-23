"""
Cellular Automata Engine (Conway's Game of Life & Viscera CA)
High-performance Canvas-based matrix rendering with touch drawing and presets.
"""
import random
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line
from kivy.metrics import dp, sp
from kivy.clock import Clock

GRID_COLS = 32
GRID_ROWS = 40

class CAGridCanvas(Widget):
    def __init__(self, cols=GRID_COLS, rows=GRID_ROWS, **kwargs):
        super().__init__(**kwargs)
        self.cols = cols
        self.rows = rows
        self.grid = [[0 for _ in range(cols)] for _ in range(rows)]
        self.cell_draw_val = 1
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *args):
        self.canvas.clear()
        cell_w = self.width / self.cols
        cell_h = self.height / self.rows

        with self.canvas:
            # Background
            Color(0.06, 0.06, 0.09, 1.0)
            Rectangle(pos=self.pos, size=self.size)

            # Border
            Color(0.02, 0.71, 0.83, 0.4)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=1.0)

            # Live Cells
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.grid[r][c] == 1:
                        # Cyan to Neon green gradient based on row
                        ratio = r / max(1, self.rows)
                        Color(0.02 + 0.15 * ratio, 0.85 - 0.2 * ratio, 0.83, 0.95)
                        x = self.x + c * cell_w + 1
                        y = self.y + r * cell_h + 1
                        Rectangle(pos=(x, y), size=(max(1, cell_w - 2), max(1, cell_h - 2)))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            c, r = self._pos_to_cell(touch.pos)
            if 0 <= r < self.rows and 0 <= c < self.cols:
                self.cell_draw_val = 0 if self.grid[r][c] == 1 else 1
                self.grid[r][c] = self.cell_draw_val
                self.redraw()
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            c, r = self._pos_to_cell(touch.pos)
            if 0 <= r < self.rows and 0 <= c < self.cols:
                if self.grid[r][c] != self.cell_draw_val:
                    self.grid[r][c] = self.cell_draw_val
                    self.redraw()
            return True
        return super().on_touch_move(touch)

    def _pos_to_cell(self, pos):
        x, y = pos
        cell_w = self.width / self.cols
        cell_h = self.height / self.rows
        c = int((x - self.x) / cell_w)
        r = int((y - self.y) / cell_h)
        return c, r

    def count_neighbors(self, r, c):
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr = (r + dr) % self.rows
                nc = (c + dc) % self.cols
                count += self.grid[nr][nc]
        return count

    def step(self):
        new_grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        population = 0
        for r in range(self.rows):
            for c in range(self.cols):
                neighbors = self.count_neighbors(r, c)
                state = self.grid[r][c]
                if state == 1:
                    if neighbors in (2, 3):
                        new_grid[r][c] = 1
                        population += 1
                else:
                    if neighbors == 3:
                        new_grid[r][c] = 1
                        population += 1
        self.grid = new_grid
        self.redraw()
        return population

    def clear(self):
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.redraw()

    def randomize(self, density=0.25):
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c] = 1 if random.random() < density else 0
        self.redraw()

    def spawn_glider(self):
        self.clear()
        cr, cc = self.rows // 2, self.cols // 2
        pattern = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
        for dr, dc in pattern:
            r, c = (cr + dr) % self.rows, (cc + dc) % self.cols
            self.grid[r][c] = 1
        self.redraw()

    def spawn_pulsar(self):
        self.clear()
        cr, cc = self.rows // 2, self.cols // 2
        offsets = [-6, -1, 1, 6]
        for r_off in offsets:
            for c_off in [-4, -3, -2, 2, 3, 4]:
                self.grid[(cr + r_off) % self.rows][(cc + c_off) % self.cols] = 1
        for c_off in offsets:
            for r_off in [-4, -3, -2, 2, 3, 4]:
                self.grid[(cr + r_off) % self.rows][(cc + c_off) % self.cols] = 1
        self.redraw()


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(8), **kwargs)
        self.host = None
        self.is_running = False
        self.generation = 0
        self.speed_hz = 8.0
        self.event_clock = None

        # Title & Stats Row
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))
        self.lbl_title = Label(
            text="🧬 CELLULAR AUTOMATA",
            font_size="17sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        header.add_widget(self.lbl_title)

        self.lbl_stats = Label(
            text="Gen: 0 | Pop: 0",
            font_size="13sp",
            color=(0.7, 0.7, 0.8, 1),
            size_hint_x=None,
            width=dp(140),
            halign='right',
            valign='middle'
        )
        self.lbl_stats.bind(size=self.lbl_stats.setter('text_size'))
        header.add_widget(self.lbl_stats)
        self.add_widget(header)

        # Main Interactive Grid Canvas
        self.ca_canvas = CAGridCanvas(size_hint_y=1.0)
        self.add_widget(self.ca_canvas)

        # Primary Controls Row: [▶ RUN/PAUSE] [⏭️ STEP] [🎲 RANDOM] [🧹 CLEAR]
        ctrl_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(6))
        
        self.btn_run = Button(
            text="▶ START",
            size_hint_x=0.35,
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="15sp",
            always_release=True
        )
        self.btn_run.bind(on_release=self.toggle_simulation)
        ctrl_row.add_widget(self.btn_run)

        btn_step = Button(
            text="⏭️ STEP",
            size_hint_x=0.22,
            background_normal="",
            background_color=(0.18, 0.18, 0.26, 1.0),
            color=(0.9, 0.9, 0.95, 1.0),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_step.bind(on_release=self.step_forward)
        ctrl_row.add_widget(btn_step)

        btn_rand = Button(
            text="🎲 NOISE",
            size_hint_x=0.22,
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 0.9),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_rand.bind(on_release=self.randomize_grid)
        ctrl_row.add_widget(btn_rand)

        btn_clear = Button(
            text="🧹",
            size_hint_x=None,
            width=dp(46),
            background_normal="",
            background_color=(0.3, 0.1, 0.1, 1.0),
            color=(1, 0.4, 0.4, 1.0),
            bold=True,
            font_size="15sp",
            always_release=True
        )
        btn_clear.bind(on_release=self.clear_grid)
        ctrl_row.add_widget(btn_clear)
        self.add_widget(ctrl_row)

        # Secondary Row: Presets & Speed Slider
        preset_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(42), spacing=dp(6))
        
        btn_glider = Button(
            text="🛸 Glider",
            size_hint_x=0.25,
            background_normal="",
            background_color=(0.14, 0.14, 0.20, 1.0),
            color=(0.7, 0.85, 1.0, 1.0),
            bold=True,
            font_size="12sp",
            always_release=True
        )
        btn_glider.bind(on_release=lambda x: self.load_preset('glider'))
        preset_row.add_widget(btn_glider)

        btn_pulsar = Button(
            text="💫 Pulsar",
            size_hint_x=0.25,
            background_normal="",
            background_color=(0.14, 0.14, 0.20, 1.0),
            color=(0.7, 0.85, 1.0, 1.0),
            bold=True,
            font_size="12sp",
            always_release=True
        )
        btn_pulsar.bind(on_release=lambda x: self.load_preset('pulsar'))
        preset_row.add_widget(btn_pulsar)

        # Speed Slider
        self.speed_slider = Slider(min=1, max=25, value=8, size_hint_x=0.5)
        self.speed_slider.bind(value=self.on_speed_changed)
        preset_row.add_widget(self.speed_slider)
        self.add_widget(preset_row)

        # Initialize with a random colony
        self.ca_canvas.randomize(0.22)
        pop = sum(sum(row) for row in self.ca_canvas.grid)
        self.lbl_stats.text = f"Gen: 0 | Pop: {pop}"

    def on_load(self, host_api):
        self.host = host_api

    def on_resume(self):
        if self.is_running and not self.event_clock:
            self.event_clock = Clock.schedule_interval(self._tick, 1.0 / self.speed_hz)

    def on_pause(self):
        if self.event_clock:
            self.event_clock.cancel()
            self.event_clock = None

    def toggle_simulation(self, *args):
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_run.text = "⏸️ PAUSE"
            self.btn_run.background_color = (0.85, 0.45, 0.05, 1.0)
            self.event_clock = Clock.schedule_interval(self._tick, 1.0 / self.speed_hz)
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(30)
        else:
            self.btn_run.text = "▶ START"
            self.btn_run.background_color = (0.15, 0.68, 0.38, 1.0)
            if self.event_clock:
                self.event_clock.cancel()
                self.event_clock = None

    def _tick(self, dt):
        pop = self.ca_canvas.step()
        self.generation += 1
        self.lbl_stats.text = f"Gen: {self.generation} | Pop: {pop}"
        if pop == 0 and self.is_running:
            self.toggle_simulation()

    def step_forward(self, *args):
        if self.is_running:
            self.toggle_simulation()
        pop = self.ca_canvas.step()
        self.generation += 1
        self.lbl_stats.text = f"Gen: {self.generation} | Pop: {pop}"
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(20)

    def randomize_grid(self, *args):
        self.ca_canvas.randomize(0.24)
        self.generation = 0
        pop = sum(sum(row) for row in self.ca_canvas.grid)
        self.lbl_stats.text = f"Gen: 0 | Pop: {pop}"
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(30)

    def clear_grid(self, *args):
        if self.is_running:
            self.toggle_simulation()
        self.ca_canvas.clear()
        self.generation = 0
        self.lbl_stats.text = "Gen: 0 | Pop: 0"

    def load_preset(self, preset_name):
        if self.is_running:
            self.toggle_simulation()
        self.generation = 0
        if preset_name == 'glider':
            self.ca_canvas.spawn_glider()
        elif preset_name == 'pulsar':
            self.ca_canvas.spawn_pulsar()
        pop = sum(sum(row) for row in self.ca_canvas.grid)
        self.lbl_stats.text = f"Gen: 0 | Pop: {pop}"
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(40)

    def on_speed_changed(self, inst, val):
        self.speed_hz = max(1.0, float(val))
        if self.is_running and self.event_clock:
            self.event_clock.cancel()
            self.event_clock = Clock.schedule_interval(self._tick, 1.0 / self.speed_hz)
