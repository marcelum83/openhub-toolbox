"""
Monster Battle RPG (Pokémon Clone for OpenHub)
Turn-based combat with animated health bars, battle arena, special moves, catching, and haptics.
"""
import random
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.metrics import dp, sp
from kivy.clock import Clock

class BattleArena(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player_hp = 100
        self.player_max_hp = 100
        self.enemy_hp = 100
        self.enemy_max_hp = 100
        self.enemy_name = "Shadowfang"
        self.player_name = "Voltachu"
        self.anim_offset = 0.0
        self.is_flashing = False
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return

        with self.canvas:
            # Arena Background
            Color(0.08, 0.09, 0.14, 1.0)
            Rectangle(pos=self.pos, size=self.size)

            # Arena Border
            Color(0.02, 0.71, 0.83, 0.4)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=1.2)

            # Enemy Podium (Top Right)
            e_pod_x = self.x + self.width * 0.7
            e_pod_y = self.y + self.height * 0.65
            Color(0.15, 0.16, 0.24, 0.8)
            Ellipse(pos=(e_pod_x - dp(60), e_pod_y - dp(18)), size=(dp(120), dp(36)))

            # Enemy Creature (Shadowfang)
            Color(0.75, 0.25, 0.90, 1.0) # Violet
            Ellipse(pos=(e_pod_x - dp(32), e_pod_y + dp(6)), size=(dp(64), dp(64)))
            # Eyes
            Color(1.0, 0.2, 0.2, 1.0)
            Ellipse(pos=(e_pod_x - dp(18), e_pod_y + dp(38)), size=(dp(10), dp(10)))
            Ellipse(pos=(e_pod_x + dp(8), e_pod_y + dp(38)), size=(dp(10), dp(10)))

            # Player Podium (Bottom Left)
            p_pod_x = self.x + self.width * 0.3
            p_pod_y = self.y + self.height * 0.25
            Color(0.15, 0.16, 0.24, 0.8)
            Ellipse(pos=(p_pod_x - dp(70), p_pod_y - dp(22)), size=(dp(140), dp(44)))

            # Player Creature (Voltachu)
            Color(0.95, 0.75, 0.10, 1.0) # Electric Yellow
            Ellipse(pos=(p_pod_x - dp(36), p_pod_y + dp(8)), size=(dp(72), dp(72)))
            # Cheeks & Eyes
            Color(0.9, 0.2, 0.2, 1.0)
            Ellipse(pos=(p_pod_x - dp(28), p_pod_y + dp(22)), size=(dp(14), dp(14)))
            Ellipse(pos=(p_pod_x + dp(14), p_pod_y + dp(22)), size=(dp(14), dp(14)))
            Color(0.1, 0.1, 0.1, 1.0)
            Ellipse(pos=(p_pod_x - dp(18), p_pod_y + dp(46)), size=(dp(10), dp(10)))
            Ellipse(pos=(p_pod_x + dp(8), p_pod_y + dp(46)), size=(dp(10), dp(10)))


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(8), **kwargs)
        self.host = None
        self.player_hp = 100
        self.player_max_hp = 100
        self.enemy_hp = 100
        self.enemy_max_hp = 100
        self.is_defending = False
        self.is_busy = False

        # 1. Header & Monster Status Row
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))
        self.lbl_title = Label(
            text="⚡ MONSTER BATTLE RPG",
            font_size="17sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        header.add_widget(self.lbl_title)
        self.add_widget(header)

        # Health Bars Box
        hp_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        # Player HP
        p_box = BoxLayout(orientation='vertical', spacing=dp(2))
        self.lbl_p_hp = Label(text="Voltachu: 100/100 HP", font_size="12sp", bold=True, color=(0.95, 0.75, 0.1, 1), halign='left')
        self.lbl_p_hp.bind(size=self.lbl_p_hp.setter('text_size'))
        self.bar_p_hp = ProgressBar(max=100, value=100, size_hint_y=None, height=dp(12))
        p_box.add_widget(self.lbl_p_hp)
        p_box.add_widget(self.bar_p_hp)
        hp_box.add_widget(p_box)

        # Enemy HP
        e_box = BoxLayout(orientation='vertical', spacing=dp(2))
        self.lbl_e_hp = Label(text="Shadowfang: 100/100 HP", font_size="12sp", bold=True, color=(0.75, 0.25, 0.9, 1), halign='right')
        self.lbl_e_hp.bind(size=self.lbl_e_hp.setter('text_size'))
        self.bar_e_hp = ProgressBar(max=100, value=100, size_hint_y=None, height=dp(12))
        e_box.add_widget(self.lbl_e_hp)
        e_box.add_widget(self.bar_e_hp)
        hp_box.add_widget(e_box)
        self.add_widget(hp_box)

        # 2. Central Visual Battle Arena
        self.arena = BattleArena(size_hint_y=1.0)
        self.add_widget(self.arena)

        # 3. Battle Narrative Log
        self.lbl_log = Label(
            text="A wild Shadowfang appeared! What will Voltachu do?",
            font_size="13sp",
            bold=True,
            color=(0.9, 0.9, 0.95, 1),
            size_hint_y=None,
            height=dp(38),
            halign='center',
            valign='middle'
        )
        self.lbl_log.bind(size=self.lbl_log.setter('text_size'))
        self.add_widget(self.lbl_log)

        # 4. Combat Move Command Grid (4 Buttons)
        cmd_grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(100))
        
        self.btn_atk1 = Button(
            text="⚡ THUNDER BOLT",
            background_normal="",
            background_color=(0.95, 0.65, 0.05, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        self.btn_atk1.bind(on_release=lambda x: self.on_player_move("thunder"))
        cmd_grid.add_widget(self.btn_atk1)

        self.btn_spec = Button(
            text="💥 NOVA BLAST",
            background_normal="",
            background_color=(0.85, 0.20, 0.20, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        self.btn_spec.bind(on_release=lambda x: self.on_player_move("nova"))
        cmd_grid.add_widget(self.btn_spec)

        self.btn_heal = Button(
            text="🧪 POTION (+35 HP)",
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        self.btn_heal.bind(on_release=lambda x: self.on_player_move("heal"))
        cmd_grid.add_widget(self.btn_heal)

        self.btn_catch = Button(
            text="🔴 CATCH MONSTER",
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        self.btn_catch.bind(on_release=lambda x: self.on_player_move("catch"))
        cmd_grid.add_widget(self.btn_catch)
        self.add_widget(cmd_grid)

        # 5. Bottom Reset / New Encounter Button
        self.btn_reset = Button(
            text="🔄 NEW ENCOUNTER",
            background_normal="",
            background_color=(0.18, 0.18, 0.26, 1.0),
            color=(0.8, 0.8, 0.9, 1.0),
            bold=True,
            font_size="13sp",
            size_hint_y=None,
            height=dp(38),
            always_release=True
        )
        self.btn_reset.bind(on_release=self.reset_battle)
        self.add_widget(self.btn_reset)

    def on_load(self, host_api):
        self.host = host_api

    def on_player_move(self, move_type):
        if self.is_busy or self.player_hp <= 0 or self.enemy_hp <= 0:
            return

        self.is_busy = True

        if move_type == "thunder":
            dmg = random.randint(18, 28)
            self.enemy_hp = max(0, self.enemy_hp - dmg)
            self.lbl_log.text = f"Voltachu used Thunderbolt! Dealt {dmg} damage!"
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(35)
        elif move_type == "nova":
            dmg = random.randint(30, 48)
            self.enemy_hp = max(0, self.enemy_hp - dmg)
            self.lbl_log.text = f"CRITICAL! Voltachu used Nova Blast! Dealt {dmg} damage!"
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(60)
        elif move_type == "heal":
            heal = 35
            self.player_hp = min(self.player_max_hp, self.player_hp + heal)
            self.lbl_log.text = f"Voltachu drank a Potion and restored {heal} HP!"
            if self.host and self.host.hardware:
                self.host.hardware.vibrate(25)
        elif move_type == "catch":
            catch_chance = (1.0 - (self.enemy_hp / self.enemy_max_hp)) * 0.85 + 0.15
            if random.random() < catch_chance:
                self.enemy_hp = 0
                self.lbl_log.text = "🎉 All right! Shadowfang was caught!"
                if self.host and self.host.hardware:
                    self.host.hardware.vibrate(80)
                self.update_bars()
                self.is_busy = False
                return
            else:
                self.lbl_log.text = "Oh no! The monster broke free!"
                if self.host and self.host.hardware:
                    self.host.hardware.vibrate(20)

        self.update_bars()

        if self.enemy_hp <= 0:
            self.lbl_log.text = "🏆 Wild Shadowfang fainted! You won!"
            self.is_busy = False
            return

        # Enemy Turn after 1 second
        Clock.schedule_once(self.enemy_turn, 1.1)

    def enemy_turn(self, dt):
        if self.enemy_hp <= 0 or self.player_hp <= 0:
            self.is_busy = False
            return

        moves = [
            ("Shadow Claw", random.randint(14, 24)),
            ("Dark Pulse", random.randint(18, 30)),
            ("Night Slash", random.randint(12, 20))
        ]
        m_name, dmg = random.choice(moves)
        self.player_hp = max(0, self.player_hp - dmg)
        self.lbl_log.text = f"Wild Shadowfang used {m_name}! Dealt {dmg} damage!"
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(40)

        self.update_bars()

        if self.player_hp <= 0:
            self.lbl_log.text = "💀 Voltachu fainted! Tap 'NEW ENCOUNTER' to retry."

        self.is_busy = False

    def update_bars(self):
        self.bar_p_hp.value = self.player_hp
        self.bar_e_hp.value = self.enemy_hp
        self.lbl_p_hp.text = f"Voltachu: {self.player_hp}/{self.player_max_hp} HP"
        self.lbl_e_hp.text = f"Shadowfang: {self.enemy_hp}/{self.enemy_max_hp} HP"

    def reset_battle(self, *args):
        self.player_hp = 100
        self.enemy_hp = 100
        self.is_busy = False
        self.lbl_log.text = "A wild Shadowfang appeared! What will Voltachu do?"
        self.update_bars()
        if self.host and self.host.hardware:
            self.host.hardware.vibrate(30)