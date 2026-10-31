"""
Eclipse Survivors - Main Module Entrypoint
HUD overlay, Floor dungeon exploration tracking, Room Clearance,
Elevator Transit, Floor Complete Victory Modal, and Cortical Stack Resleeving.
"""
import os
import sys
_mod_dir = os.path.dirname(os.path.abspath(__file__))
if _mod_dir not in sys.path:
    sys.path.insert(0, _mod_dir)

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
from kivy.metrics import dp, sp
from kivy.clock import Clock

try:
    from game_state import GameWorld, UPGRADE_CATALOG, MORPH_CATALOG
    from arena import ActionArena
    from upgrade_modal import UpgradeDraftModal
    from dialogue_modal import NPCDialogueModal
except ImportError:
    from .game_state import GameWorld, UPGRADE_CATALOG, MORPH_CATALOG
    from .arena import ActionArena
    from .upgrade_modal import UpgradeDraftModal
    from .dialogue_modal import NPCDialogueModal


class MorphSelectionModal(ModalView):
    """Presents Transhuman Sleeve Dossiers before deployment or upon resleeving."""
    def __init__(self, on_select_morph, current_morph="synth", **kwargs):
        super().__init__(size_hint=(0.96, 0.76), auto_dismiss=False, **kwargs)
        self.on_select_morph = on_select_morph

        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        with root.canvas.before:
            Color(0.08, 0.09, 0.14, 0.98)
            RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(8)])
            Color(0.02, 0.71, 0.83, 0.8)
            Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(8)), width=1.5)

        # Header
        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(44), spacing=dp(2))
        header.add_widget(Label(
            text="🧬 RESLEEVING FACILITY: SELECT CHASSIS",
            font_size="15sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0)
        ))
        header.add_widget(Label(
            text="Download your Cortical Stack ego into a tactical transhuman chassis:",
            font_size="11sp",
            color=(0.7, 0.75, 0.85, 1.0)
        ))
        root.add_widget(header)

        # 4 Morph Cards in a 2x2 Grid
        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=1.0)

        for m_id, m_info in MORPH_CATALOG.items():
            card = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(4))
            is_active = (m_id == current_morph)

            with card.canvas.before:
                Color(0.12, 0.14, 0.20, 0.95)
                RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(6)])
                if is_active:
                    Color(0.02, 0.71, 0.83, 1.0)
                    line_w = 2.0
                else:
                    Color(0.3, 0.35, 0.45, 0.7)
                    line_w = 1.0
                Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(6)), width=line_w)

            # Icon & Name
            top = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(26), spacing=dp(4))
            top.add_widget(Label(text=m_info["icon"], font_size="16sp", size_hint_x=None, width=dp(24)))
            top.add_widget(Label(
                text=m_info["name"].upper(),
                font_size="11sp",
                bold=True,
                color=(0.95, 0.95, 0.98, 1.0),
                halign='left'
            ))
            card.add_widget(top)

            # Tagline
            lbl_tag = Label(
                text=m_info["tagline"],
                font_size="9sp",
                color=(0.02, 0.71, 0.83, 1.0),
                size_hint_y=None,
                height=dp(16)
            )
            card.add_widget(lbl_tag)

            # Stats summary
            stats_txt = (
                f"[color=F39C12]HP:[/color] {int(m_info['hp'])}  "
                f"[color=27AE60]SPD:[/color] {int(m_info['speed'])}  "
                f"[color=8A5CF5]ARM:[/color] {m_info['armor']}"
            )
            card.add_widget(Label(
                text=stats_txt,
                markup=True,
                font_size="10sp",
                size_hint_y=None,
                height=dp(18)
            ))

            # Select Button
            btn = Button(
                text="SELECT & DEPLOY",
                size_hint_y=None,
                height=dp(32),
                background_normal="",
                background_color=(0.02, 0.71, 0.83, 1.0) if is_active else (0.2, 0.24, 0.32, 1.0),
                color=(0.05, 0.05, 0.08, 1.0) if is_active else (0.9, 0.9, 0.9, 1.0),
                font_size="10sp",
                bold=True,
                always_release=True
            )
            btn.bind(on_release=lambda x, mid=m_id: self._select(mid))
            card.add_widget(btn)

            grid.add_widget(card)

        root.add_widget(grid)
        self.add_widget(root)

    def _select(self, morph_id: str):
        self.dismiss()
        self.on_select_morph(morph_id)


class FloorCompleteModal(ModalView):
    """Celebrates completing a station deck floor and offers transit to next deck."""
    def __init__(self, world: GameWorld, on_next_floor_callback, on_restart_callback, **kwargs):
        super().__init__(size_hint=(0.92, 0.72), auto_dismiss=False, **kwargs)
        self.on_next_floor_callback = on_next_floor_callback
        self.on_restart_callback = on_restart_callback

        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        with root.canvas.before:
            Color(0.06, 0.10, 0.08, 0.98)
            RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(8)])
            Color(0.2, 0.95, 0.65, 0.9)
            Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(8)), width=2.0)

        # Header
        root.add_widget(Label(
            text=f"🎉 DECK {world.deck_level} SECURED // FLOOR COMPLETE!",
            font_size="16sp",
            bold=True,
            color=(0.2, 0.95, 0.65, 1.0),
            size_hint_y=None,
            height=dp(30)
        ))
        root.add_widget(Label(
            text="Station floor cleared and quarantined. Sector transit elevator ready.",
            font_size="11sp",
            color=(0.7, 0.85, 0.80, 1.0),
            size_hint_y=None,
            height=dp(20)
        ))

        mins = int(world.wave_time) // 60
        secs = int(world.wave_time) % 60
        secured_rooms = world.get_secured_rooms_count()
        total_rooms = len(world.map.rooms)

        lbl_stats = Label(
            text=f"[color=05B4D4]Clear Duration:[/color] [b]{mins:02d}:{secs:02d}[/b]\n"
                 f"[color=27AE60]Rooms Secured:[/color] [b]{secured_rooms}/{total_rooms} Rooms[/b]\n"
                 f"[color=F39C12]Threats Neutralized:[/color] [b]{world.player.kills} Hostiles Purged[/b]\n"
                 f"[color=8A5CF5]Operative Level:[/color] [b]Synapse Level {world.player.level}[/b]\n"
                 f"[color=FFD700]Cortical Stack Reward:[/color] [b]+150 Nanocores Deposited[/b]",
            markup=True,
            font_size="12sp",
            halign='center',
            valign='middle'
        )
        root.add_widget(lbl_stats)

        # Buttons Row
        btn_box = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(44))

        btn_next = Button(
            text=f"🚀 TRANSIT TO DECK {world.deck_level + 1}",
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(0.05, 0.05, 0.08, 1.0),
            font_size="12sp",
            bold=True,
            always_release=True
        )
        btn_next.bind(on_release=lambda x: self._on_next())
        btn_box.add_widget(btn_next)

        btn_restart = Button(
            text="🔄 RESLEEVE & EVAC",
            size_hint_x=0.45,
            background_normal="",
            background_color=(0.2, 0.24, 0.32, 1.0),
            color=(0.9, 0.9, 0.9, 1.0),
            font_size="11sp",
            bold=True,
            always_release=True
        )
        btn_restart.bind(on_release=lambda x: self._on_restart_click())
        btn_box.add_widget(btn_restart)

        root.add_widget(btn_box)
        self.add_widget(root)

    def _on_next(self):
        self.dismiss()
        self.on_next_floor_callback()

    def _on_restart_click(self):
        self.dismiss()
        self.on_restart_callback()


class GameOverModal(ModalView):
    def __init__(self, world: GameWorld, on_resleeve_callback, **kwargs):
        super().__init__(size_hint=(0.88, 0.65), auto_dismiss=False, **kwargs)
        self.on_resleeve_callback = on_resleeve_callback

        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        with root.canvas.before:
            Color(0.08, 0.09, 0.14, 0.98)
            RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(8)])
            Color(0.91, 0.30, 0.24, 0.8)
            Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(8)), width=1.5)

        root.add_widget(Label(
            text="💥 SLEEVE DESTRUCTION",
            font_size="17sp",
            bold=True,
            color=(0.91, 0.30, 0.24, 1.0),
            size_hint_y=None,
            height=dp(30)
        ))
        root.add_widget(Label(
            text="Your physical chassis has failed under hostile incursions.",
            font_size="11sp",
            color=(0.7, 0.75, 0.85, 1.0),
            size_hint_y=None,
            height=dp(20)
        ))

        # Stats Card
        mins = int(world.wave_time) // 60
        secs = int(world.wave_time) % 60
        lbl_stats = Label(
            text=f"[color=05B4D4]Exploration Time:[/color] [b]{mins:02d}:{secs:02d}[/b]\n"
                 f"[color=27AE60]Hostiles Purged:[/color] [b]{world.player.kills} kills[/b]\n"
                 f"[color=F39C12]Final Synapse Level:[/color] [b]Level {world.player.level}[/b]\n"
                 f"[color=8A5CF5]Cortical Stack Status:[/color] [b]INTACT - Ready for Resleeve[/b]",
            markup=True,
            font_size="12sp",
            halign='center',
            valign='middle'
        )
        root.add_widget(lbl_stats)

        btn_resleeve = Button(
            text="🔄 RESLEEVE & RE-DEPLOY",
            size_hint_y=None,
            height=dp(44),
            background_normal="",
            background_color=(0.02, 0.71, 0.83, 1.0),
            color=(0.05, 0.05, 0.08, 1.0),
            font_size="13sp",
            bold=True,
            always_release=True
        )
        btn_resleeve.bind(on_release=lambda x: self._on_restart())
        root.add_widget(btn_resleeve)

        self.add_widget(root)

    def _on_restart(self):
        self.dismiss()
        self.on_resleeve_callback()


class OpenHubModule(BoxLayout):
    def __init__(self, morph_id: str = "synth", deck_level: int = 1,
                 is_breach_mode: bool = False, breach_time_limit: float = 45.0,
                 breach_target_kills: int = 20, on_breach_complete_callback=None, **kwargs):
        super().__init__(orientation='vertical', padding=dp(6), spacing=dp(4), **kwargs)
        self.host = None
        self.selected_morph = morph_id
        self.deck_level = deck_level
        self.is_breach_mode = is_breach_mode
        self.breach_time_limit = breach_time_limit
        self.breach_target_kills = breach_target_kills
        self.on_breach_complete_callback = on_breach_complete_callback

        self.world = GameWorld(
            morph_id=self.selected_morph,
            deck_level=self.deck_level,
            is_breach_mode=self.is_breach_mode,
            breach_time_limit=self.breach_time_limit,
            breach_target_kills=self.breach_target_kills,
            on_breach_complete=self._on_breach_finish
        )

        # Background Canvas
        with self.canvas.before:
            Color(0.05, 0.06, 0.09, 1.0)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # 1. Top HUD Ribbon
        self._build_hud()

        # 2. Floor Status & Alert Ribbon
        self._build_alert_ribbon()

        # 3. Active Implants / Cybernetics Ribbon
        self._build_implants_ribbon()

        # 3b. Context Interaction Action Bar (NPC Conversations & Terminal Hacking)
        self._build_context_action_bar()

        # 4. Main 2D Action Arena Viewport
        self.arena = ActionArena(
            world=self.world,
            on_level_up=self._on_level_up_triggered,
            on_game_over=self._on_game_over_triggered,
            on_floor_complete=self._on_floor_completed,
            on_npc_interact=self._open_npc_dialogue
        )
        self.add_widget(self.arena)

        # HUD Refresh Loop
        self.hud_timer = Clock.schedule_interval(self._update_hud, 0.1)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_load(self, host_api):
        self.host = host_api
        self.arena.host = host_api

    def _build_hud(self):
        hud = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(6))

        # Deck Level Badge
        self.lbl_deck = Label(
            text=f"DECK {self.deck_level}",
            font_size="11sp",
            bold=True,
            size_hint_x=None,
            width=dp(56),
            color=(0.2, 0.95, 0.65, 1.0)
        )
        hud.add_widget(self.lbl_deck)

        # Morph Selector Button
        self.btn_morph = Button(
            text="🤖 SYNTH",
            font_size="10sp",
            bold=True,
            size_hint_x=None,
            width=dp(70),
            background_normal="",
            background_color=(0.14, 0.16, 0.24, 0.95),
            color=(0.02, 0.71, 0.83, 1.0),
            always_release=True
        )
        self.btn_morph.bind(on_release=lambda x: self._open_morph_modal())
        hud.add_widget(self.btn_morph)

        # Level Badge
        self.lbl_level = Label(
            text="LVL 1",
            font_size="12sp",
            bold=True,
            size_hint_x=None,
            width=dp(46),
            color=(0.02, 0.71, 0.83, 1.0)
        )
        hud.add_widget(self.lbl_level)

        # XP Progress Bar with label
        xp_box = BoxLayout(orientation='vertical', spacing=dp(2))
        self.lbl_xp = Label(
            text="XP: 0/35",
            font_size="10sp",
            color=(0.2, 0.95, 0.65, 1.0),
            size_hint_y=None,
            height=dp(14),
            halign='left'
        )
        self.lbl_xp.bind(size=self.lbl_xp.setter('text_size'))
        self.pb_xp = ProgressBar(max=35, value=0, size_hint_y=None, height=dp(6))
        xp_box.add_widget(self.lbl_xp)
        xp_box.add_widget(self.pb_xp)
        hud.add_widget(xp_box)

        # HP Health Bar
        hp_box = BoxLayout(orientation='vertical', spacing=dp(2), size_hint_x=0.36)
        self.lbl_hp = Label(
            text="HP: 140/140",
            font_size="10sp",
            color=(0.95, 0.45, 0.15, 1.0),
            size_hint_y=None,
            height=dp(14),
            halign='right'
        )
        self.lbl_hp.bind(size=self.lbl_hp.setter('text_size'))
        self.pb_hp = ProgressBar(max=140, value=140, size_hint_y=None, height=dp(6))
        hp_box.add_widget(self.lbl_hp)
        hp_box.add_widget(self.pb_hp)
        hud.add_widget(hp_box)

        self.add_widget(hud)

    def _build_alert_ribbon(self):
        self.alert_ribbon = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(22), spacing=dp(6))

        # Current Room & Clearance Badge
        self.lbl_room = Label(
            text="📍 AIRLOCK STAGING",
            font_size="10sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0),
            size_hint_x=None,
            width=dp(140),
            halign='left'
        )
        self.lbl_room.bind(size=self.lbl_room.setter('text_size'))
        self.alert_ribbon.add_widget(self.lbl_room)

        # Floor Progress (Hostiles remaining & rooms)
        self.lbl_floor_progress = Label(
            text="💀 30 REMAINING | ✓ 0/7",
            font_size="10sp",
            bold=True,
            color=(0.95, 0.75, 0.1, 1.0),
            halign='left'
        )
        self.lbl_floor_progress.bind(size=self.lbl_floor_progress.setter('text_size'))
        self.alert_ribbon.add_widget(self.lbl_floor_progress)

        # Keycard indicator
        self.lbl_keycard = Label(
            text="[🔒 KEYCARD]",
            font_size="10sp",
            bold=True,
            color=(0.6, 0.65, 0.75, 1.0),
            size_hint_x=None,
            width=dp(80)
        )
        self.alert_ribbon.add_widget(self.lbl_keycard)

        # Evac Button in Breach Mode
        if self.is_breach_mode:
            btn_evac = Button(
                text="🚨 EVAC",
                size_hint_x=None,
                width=dp(56),
                background_normal="",
                background_color=(0.91, 0.30, 0.24, 0.9),
                color=(1.0, 1.0, 1.0, 1.0),
                font_size="10sp",
                bold=True,
                always_release=True
            )
            btn_evac.bind(on_release=lambda x: self._on_breach_finish(False, self.world.player.kills, "Emergency Evacuation Initiated"))
            self.alert_ribbon.add_widget(btn_evac)

        self.add_widget(self.alert_ribbon)

    def _build_implants_ribbon(self):
        self.ribbon = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(24), spacing=dp(4))
        self.lbl_implants = Label(
            text="CYBERNETICS: [Loading...]",
            markup=True,
            font_size="10sp",
            color=(0.7, 0.75, 0.85, 1.0),
            halign='left'
        )
        self.lbl_implants.bind(size=self.lbl_implants.setter('text_size'))
        self.ribbon.add_widget(self.lbl_implants)
        self.add_widget(self.ribbon)

    def _build_context_action_bar(self):
        self.context_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28), spacing=dp(6))
        self.btn_talk = Button(
            text="💬 TALK TO NPC [E]",
            font_size="11sp",
            bold=True,
            background_normal="",
            background_color=(0.02, 0.71, 0.83, 0.95),
            color=(0.05, 0.05, 0.08, 1.0),
            size_hint_x=1.0,
            opacity=0.0,
            disabled=True,
            always_release=True
        )
        self.btn_talk.bind(on_release=lambda x: self._open_npc_dialogue())
        self.context_bar.add_widget(self.btn_talk)
        self.add_widget(self.context_bar)

    def _update_hud(self, dt):
        player = self.world.player

        # Morph Button Text & Deck
        morph_info = MORPH_CATALOG.get(player.morph_id, {})
        self.btn_morph.text = f"{morph_info.get('icon', '🤖')} {player.morph_id.upper()}"
        self.lbl_deck.text = f"DECK {self.world.deck_level}"

        # Level & XP
        self.lbl_level.text = f"LVL {player.level}"
        self.lbl_xp.text = f"XP: {player.xp}/{player.xp_to_next}"
        self.pb_xp.max = player.xp_to_next
        self.pb_xp.value = player.xp

        # Durability (HP)
        self.lbl_hp.text = f"HP: {int(player.hp)}/{int(player.max_hp)}"
        self.pb_hp.max = player.max_hp
        self.pb_hp.value = player.hp

        # Current Room Name
        cur_room = self.world.get_current_room(player.x, player.y)
        if cur_room:
            self.lbl_room.text = f"📍 {cur_room.name.upper()}"
            self.lbl_room.color = (0.2, 0.95, 0.65, 1.0) if cur_room.is_cleared else (0.02, 0.71, 0.83, 1.0)

        # Floor Progress (Hostiles & Rooms)
        alive_threats = len([e for e in self.world.enemies if e.is_alive()])
        secured_rooms = self.world.get_secured_rooms_count()
        total_rooms = len(self.world.map.rooms)
        self.lbl_floor_progress.text = f"💀 {alive_threats} REMAINING | ✓ {secured_rooms}/{total_rooms} ROOMS"

        # Keycard Status
        if player.has_keycard:
            self.lbl_keycard.text = "[🔑 KEYCARD]"
            self.lbl_keycard.color = (1.0, 0.84, 0.0, 1.0)
        else:
            self.lbl_keycard.text = "[🔒 KEYCARD]"
            self.lbl_keycard.color = (0.6, 0.65, 0.75, 1.0)

        # Active Implants Ribbon
        items = []
        for k, lvl in player.inventory.items():
            info = UPGRADE_CATALOG.get(k, {})
            icon = info.get("icon", "•")
            name = info.get("name", k).split()[0]
            if info.get("type") == "evolution":
                items.append(f"[color=FFD700][b]{icon} {name} (EVO)[/b][/color]")
            else:
                items.append(f"[{icon} {name} v{lvl}]")
        self.lbl_implants.text = "AUGMENTS: " + " ".join(items)

        # Context Action (Talk to Proximity NPC)
        active_npc = self.world.active_npc
        if active_npc:
            self.btn_talk.opacity = 1.0
            self.btn_talk.disabled = False
            self.btn_talk.text = f"💬 TALK TO {active_npc.name.upper()} [E]"
            if active_npc.id == "sorenson" and active_npc.dialogue_state != "cured":
                self.btn_talk.background_color = (1.0, 0.84, 0.0, 0.95)
            elif active_npc.id == "clinic_agi":
                self.btn_talk.background_color = (0.2, 0.95, 0.65, 0.95)
            else:
                self.btn_talk.background_color = (0.02, 0.71, 0.83, 0.95)
        else:
            self.btn_talk.opacity = 0.0
            self.btn_talk.disabled = True

    def _open_morph_modal(self):
        self.world.is_paused = True
        modal = MorphSelectionModal(on_select_morph=self._on_morph_selected, current_morph=self.selected_morph)
        modal.open()

    def _on_morph_selected(self, morph_id: str):
        self.selected_morph = morph_id
        self._restart_game()

    def _on_level_up_triggered(self, player):
        modal = UpgradeDraftModal(player=player, on_select_callback=self._on_upgrade_selected)
        modal.open()

    def _on_upgrade_selected(self, upgrade_id: str):
        self.world.player.apply_upgrade(upgrade_id)
        self.world.is_paused = False

    def _on_game_over_triggered(self):
        modal = GameOverModal(world=self.world, on_resleeve_callback=self._open_morph_modal)
        modal.open()

    def _on_floor_completed(self):
        modal = FloorCompleteModal(
            world=self.world,
            on_next_floor_callback=self._advance_to_next_deck,
            on_restart_callback=self._open_morph_modal
        )
        modal.open()

    def _advance_to_next_deck(self):
        # Keep operative character progression across floors!
        old_player = self.world.player
        self.deck_level += 1

        self.world = GameWorld(
            morph_id=self.selected_morph,
            deck_level=self.deck_level,
            is_breach_mode=self.is_breach_mode,
            breach_time_limit=self.breach_time_limit,
            breach_target_kills=self.breach_target_kills,
            on_breach_complete=self._on_breach_finish
        )
        # Restore progression to new floor player
        self.world.player.level = old_player.level
        self.world.player.xp = old_player.xp
        self.world.player.xp_to_next = old_player.xp_to_next
        self.world.player.kills = old_player.kills
        self.world.player.inventory = dict(old_player.inventory)
        self.world.player.max_hp = old_player.max_hp
        self.world.player.hp = old_player.max_hp  # full repair between decks
        self.world.player.armor = old_player.armor
        self.world.player.speed = old_player.speed
        self.world.player.pickup_radius = old_player.pickup_radius
        self.world.player.cooldown_mult = old_player.cooldown_mult

        self.arena.world = self.world
        self.arena.on_npc_interact = self._open_npc_dialogue
        self.arena.keys_pressed.clear()
        self.arena.touch_stick_origin = None
        self.world.trigger_alert(f"🚀 ARRIVED AT {self.world.map.theme_name.upper()}!", getattr(self.world.map, "accent_color", (0.02, 0.71, 0.83, 1.0)))
        self.world.trigger_alert(f"🚀 TRANSITED TO DECK {self.deck_level} // THREAT SCALED", (0.2, 0.95, 0.65, 1.0))

    def _open_npc_dialogue(self, npc=None):
        if npc is None:
            npc = self.world.active_npc
        if not npc:
            return

        self.world.is_paused = True
        modal = NPCDialogueModal(
            npc=npc,
            world=self.world,
            on_close_callback=self._on_dialogue_closed,
            on_trigger_resleeve=self._open_midrun_resleeve,
            on_trigger_upgrade_draft=self._open_barter_upgrade
        )
        modal.open()

    def _on_dialogue_closed(self):
        self.world.is_paused = False

    def _open_midrun_resleeve(self, new_morph_id: str):
        self.world.player.resleeve_morph(new_morph_id)
        self.selected_morph = new_morph_id
        self.world.is_paused = False
        self.world.trigger_alert(f"🧬 RESLEEVED INTO {new_morph_id.upper()} CHASSIS!", (0.2, 0.95, 0.65, 1.0))

    def _open_barter_upgrade(self):
        self.world.is_paused = True
        modal = UpgradeDraftModal(player=self.world.player, on_select_callback=self._on_upgrade_selected)
        modal.open()

    def _on_breach_finish(self, success: bool, kills: int, reason: str):
        self.world.is_paused = True
        if self.on_breach_complete_callback:
            self.on_breach_complete_callback(success, kills, reason)

    def _restart_game(self):
        self.deck_level = 1
        self.world = GameWorld(
            morph_id=self.selected_morph,
            deck_level=1,
            is_breach_mode=self.is_breach_mode,
            breach_time_limit=self.breach_time_limit,
            breach_target_kills=self.breach_target_kills,
            on_breach_complete=self._on_breach_finish
        )
        self.arena.world = self.world
        self.arena.on_npc_interact = self._open_npc_dialogue
        self.arena.keys_pressed.clear()
        self.arena.touch_stick_origin = None
        self.world.trigger_alert(f"🚀 ARRIVED AT {self.world.map.theme_name.upper()}!", getattr(self.world.map, "accent_color", (0.02, 0.71, 0.83, 1.0)))


if __name__ == '__main__':
    from kivy.app import App
    pixel_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if pixel_root not in sys.path:
        sys.path.insert(0, pixel_root)
    from core.security import HostAPI

    class EclipseSurvivorsApp(App):
        def build(self):
            mod = OpenHubModule()
            mod.on_load(HostAPI(module_id="eclipse_survivors"))
            return mod

    EclipseSurvivorsApp().run()
