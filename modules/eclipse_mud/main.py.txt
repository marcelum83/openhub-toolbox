"""
Eclipse Phase MUD - OpenHub Module Entrypoint
Cyber-terminal HUD, typewriter streaming, interactive visual radar canvas,
operative character creation dossier, and branching multiple endings.
"""
import os
import sys
_mod_dir = os.path.dirname(os.path.abspath(__file__))
if _mod_dir not in sys.path:
    sys.path.insert(0, _mod_dir)

import math
import re

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle, Ellipse
from kivy.metrics import dp, sp
from kivy.clock import Clock

try:
    from engine import GameEngine
    from llm_bridge import LLMProvider
    from models import ARCHETYPES, MORPH_CATALOG, MUSE_PERSONAS, ENDINGS
    from world_gen import render_ascii_radar
except ImportError:
    from .engine import GameEngine
    from .llm_bridge import LLMProvider
    from .models import ARCHETYPES, MORPH_CATALOG, MUSE_PERSONAS, ENDINGS
    from .world_gen import render_ascii_radar


# --- 1. Typewriter Streaming Terminal Log ---

class TerminalLog(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bar_width = dp(4)
        self.bar_color = (0.02, 0.71, 0.83, 0.6)
        self.scroll_type = ['bars', 'content']
        
        self.lbl = Label(
            text="",
            markup=True,
            font_size="13sp",
            size_hint_y=None,
            halign='left',
            valign='top',
            color=(0.9, 0.92, 0.96, 1.0)
        )
        self.lbl.bind(texture_size=self._update_height)
        self.lbl.bind(width=self._update_text_width)
        self.add_widget(self.lbl)
        
        self.messages = []
        self._stream_queue = []
        self._current_chunks = []
        self._chunk_idx = 0
        self._stream_event = None

    def _update_height(self, instance, value):
        self.lbl.height = max(self.height, value[1] + dp(20))
        self.scroll_y = 0

    def _update_text_width(self, instance, value):
        self.lbl.text_size = (value - dp(16), None)

    def append_message(self, text: str, stream: bool = True):
        """Appends a message. If stream is True, queues it for typewriter effect."""
        if not stream:
            self.messages.append(text)
            self._prune_and_render()
            return

        self._stream_queue.append(text)
        if not self._stream_event:
            self._start_next_stream()

    def _start_next_stream(self):
        if not self._stream_queue:
            self._stream_event = None
            return

        full_text = self._stream_queue.pop(0)
        # Tokenize by complete BBCode tags or word boundaries
        tokens = re.split(r'(\[/?(?:color|b|i|font)[^\]]*\]|\s+)', full_text)
        self._current_chunks = [t for t in tokens if t]
        self._chunk_idx = 0
        self.messages.append("")
        self._stream_event = Clock.schedule_interval(self._tick_stream, 0.02)

    def _tick_stream(self, dt):
        if not self._current_chunks or self._chunk_idx >= len(self._current_chunks):
            if self._stream_event:
                self._stream_event.cancel()
                self._stream_event = None
            self._start_next_stream()
            return

        # Advance 2 chunks per tick for snappy retro cyber feel
        for _ in range(2):
            if self._chunk_idx < len(self._current_chunks):
                self.messages[-1] += self._current_chunks[self._chunk_idx]
                self._chunk_idx += 1

        self._prune_and_render()

    def flush_stream(self):
        """Instantly flushes all queued and current streams on user tap."""
        if self._stream_event:
            self._stream_event.cancel()
            self._stream_event = None

        if self._current_chunks and self._chunk_idx < len(self._current_chunks):
            self.messages[-1] += "".join(self._current_chunks[self._chunk_idx:])
            self._chunk_idx = len(self._current_chunks)

        while self._stream_queue:
            self.messages.append(self._stream_queue.pop(0))

        self._prune_and_render()

    def _prune_and_render(self):
        if len(self.messages) > 160:
            self.messages = self.messages[-160:]
        self.lbl.text = "\n".join(self.messages)
        self.scroll_y = 0

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.flush_stream()
        return super().on_touch_down(touch)

    def clear(self):
        self.flush_stream()
        self.messages = []
        self.lbl.text = ""


# --- 2. Interactive Visual Radar Canvas Widget ---

class VisualRadarWidget(Widget):
    """
    Holographic tactical radar canvas showing room nodes, corridors,
    pulsing player blip, entity indicators, and interactive tap-to-move navigation.
    """
    def __init__(self, engine: GameEngine, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.sweep_angle = 0.0
        self.room_rects = {}  # room_id: (x, y, w, h)
        self.bind(pos=self.redraw, size=self.redraw)
        self.sweep_event = Clock.schedule_interval(self._tick_sweep, 0.05)

    def _tick_sweep(self, dt):
        self.sweep_angle = (self.sweep_angle + 4.0) % 360.0
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        if self.width <= dp(40) or self.height <= dp(40):
            return

        cur_room = self.engine.get_current_room()
        rooms = self.engine.rooms
        cx, cy = self.center_x, self.center_y
        radius = min(self.width, self.height) * 0.46
        scale = min(self.width, self.height) * 0.17

        self.room_rects = {}

        with self.canvas:
            # 1. Radar Circular HUD Background
            Color(0.05, 0.07, 0.11, 0.95)
            Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))

            # Concentric Distance Rings
            Color(0.02, 0.71, 0.83, 0.2)
            Line(circle=(cx, cy, radius * 0.4), width=1.0)
            Line(circle=(cx, cy, radius * 0.7), width=1.0)
            Line(circle=(cx, cy, radius), width=1.5)

            # Crosshairs
            Line(points=[cx - radius, cy, cx + radius, cy], width=1.0)
            Line(points=[cx, cy - radius, cx, cy + radius], width=1.0)

            # Rotating Radar Sweeping Beam
            rad = math.radians(self.sweep_angle)
            sx = cx + radius * math.cos(rad)
            sy = cy + radius * math.sin(rad)
            Color(0.02, 0.85, 0.95, 0.35)
            Line(points=[cx, cy, sx, sy], width=1.8)

            # 2. Corridors (Connections between rooms)
            Color(0.18, 0.25, 0.38, 0.6)
            for r_id, room in rooms.items():
                if not room.visited:
                    continue
                rx1 = cx + (room.x - cur_room.x) * scale
                ry1 = cy + (room.y - cur_room.y) * scale
                for exit_dir, target_id in room.exits.items():
                    target = rooms.get(target_id)
                    if target and (target.visited or target_id in cur_room.exits.values()):
                        rx2 = cx + (target.x - cur_room.x) * scale
                        ry2 = cy + (target.y - cur_room.y) * scale
                        Line(points=[rx1, ry1, rx2, ry2], width=1.5)

            # 3. Room Nodes
            node_size = dp(24)
            for r_id, room in rooms.items():
                gx = cx + (room.x - cur_room.x) * scale
                gy = cy + (room.y - cur_room.y) * scale
                
                # Check within circular radar bounds
                dist = math.hypot(gx - cx, gy - cy)
                if dist > radius - dp(10):
                    continue

                rect = (gx - node_size / 2, gy - node_size / 2, node_size, node_size)
                self.room_rects[r_id] = rect

                if r_id == cur_room.id:
                    # Current Player Room (Bright Cyber Cyan Pulse)
                    Color(0.02, 0.71, 0.83, 0.9)
                    RoundedRectangle(pos=rect[:2], size=rect[2:], radius=[dp(4)])
                    Color(1.0, 1.0, 1.0, 1.0)
                    Line(rounded_rectangle=rect + (dp(4),), width=1.8)
                elif room.visited:
                    # Sector-based Color Coding
                    if "Sector 1" in room.sector:
                        Color(0.05, 0.55, 0.75, 0.7)  # Cyan
                    elif "Sector 2" in room.sector:
                        Color(0.15, 0.68, 0.38, 0.7)  # Emerald
                    elif "Sector 3" in room.sector:
                        Color(0.95, 0.61, 0.07, 0.7)  # Amber
                    else:
                        Color(0.65, 0.35, 0.95, 0.7)  # Violet
                    RoundedRectangle(pos=rect[:2], size=rect[2:], radius=[dp(4)])

                    # Entity / Item Blip inside room
                    alive_npcs = [n for n in room.npcs if n.is_alive()]
                    if alive_npcs:
                        Color(0.91, 0.30, 0.24, 1.0)  # Red Blip
                        Ellipse(pos=(gx - dp(4), gy - dp(4)), size=(dp(8), dp(8)))
                    elif room.items:
                        Color(0.95, 0.75, 0.10, 1.0)  # Gold Blip
                        Ellipse(pos=(gx - dp(3), gy - dp(3)), size=(dp(6), dp(6)))
                    elif room.terminal:
                        Color(0.2, 0.9, 1.0, 1.0)  # Cyan Blip
                        Ellipse(pos=(gx - dp(3), gy - dp(3)), size=(dp(6), dp(6)))
                else:
                    # Adjacent Unexplored Room (Dashed / Dim Target)
                    if r_id in cur_room.exits.values():
                        Color(0.4, 0.45, 0.55, 0.4)
                        RoundedRectangle(pos=rect[:2], size=rect[2:], radius=[dp(4)])
                        Color(0.02, 0.71, 0.83, 0.5)
                        Line(rounded_rectangle=rect + (dp(4),), width=1.0)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # Check if user touched an adjacent room node (Tap-to-Move!)
            for r_id, rect in self.room_rects.items():
                rx, ry, rw, rh = rect
                if rx <= touch.x <= rx + rw and ry <= touch.y <= ry + rh:
                    if r_id != self.engine.current_room_id:
                        if self.engine.move_to_room_id(r_id):
                            self.redraw()
                            return True
            return True
        return super().on_touch_down(touch)


# --- 3. Transhuman Character Creation Dossier Modal ---

class CharacterCreationModal(ModalView):
    def __init__(self, on_start_callback, **kwargs):
        super().__init__(size_hint=(0.95, 0.90), auto_dismiss=False, **kwargs)
        self.on_start_callback = on_start_callback
        
        self.selected_arch = "sentinel"
        self.selected_morph = "synthmorph"
        self.selected_muse = "mnemosyne"

        root = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        with root.canvas.before:
            Color(0.08, 0.09, 0.13, 0.98)
            RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(8)])
            Color(0.02, 0.71, 0.83, 0.5)
            Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(8)), width=1.2)
        root.bind(pos=lambda *a: self._update_rect(root), size=lambda *a: self._update_rect(root))

        # Title Banner
        title_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(44))
        title_box.add_widget(Label(
            text="🧬 TRANSHUMAN OPERATIVE DOSSIER",
            font_size="16sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0)
        ))
        title_box.add_widget(Label(
            text="Mission: Cassini Outpost Epsilon-9 | Select Identity & Sleeve",
            font_size="11sp",
            color=(0.65, 0.70, 0.85, 1.0)
        ))
        root.add_widget(title_box)

        scroll = ScrollView(size_hint_y=1.0)
        form = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        # Callsign Input
        form.add_widget(Label(text="OPERATIVE CALLSIGN", font_size="12sp", bold=True, color=(0.85, 0.70, 1.0, 1.0), size_hint_y=None, height=dp(20), halign='left'))
        self.txt_callsign = TextInput(
            text="Vagabond",
            multiline=False,
            font_size="13sp",
            size_hint_y=None,
            height=dp(38),
            background_color=(0.12, 0.14, 0.20, 1.0),
            foreground_color=(0.95, 0.95, 0.98, 1.0)
        )
        form.add_widget(self.txt_callsign)

        # Archetype / Background Selection
        form.add_widget(Label(text="EGO ARCHETYPE & TRAINING", font_size="12sp", bold=True, color=(0.85, 0.70, 1.0, 1.0), size_hint_y=None, height=dp(20)))
        arch_grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(76))
        self.arch_btns = {}
        for key, info in ARCHETYPES.items():
            btn = Button(
                text=info["name"],
                font_size="11sp",
                bold=True,
                background_normal="",
                background_color=(0.18, 0.22, 0.32, 1.0) if key == self.selected_arch else (0.12, 0.13, 0.18, 1.0),
                color=(0.2, 0.9, 1.0, 1.0) if key == self.selected_arch else (0.7, 0.75, 0.85, 1.0),
                always_release=True
            )
            btn.bind(on_release=lambda x, k=key: self._select_arch(k))
            self.arch_btns[key] = btn
            arch_grid.add_widget(btn)
        form.add_widget(arch_grid)

        # Starting Morph Selection
        form.add_widget(Label(text="STARTING SLEEVE / CHASSIS", font_size="12sp", bold=True, color=(0.02, 0.85, 0.65, 1.0), size_hint_y=None, height=dp(20)))
        morph_grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(76))
        self.morph_btns = {}
        starting_morphs = ["synthmorph", "olympian", "ghost", "splicer"]
        for key in starting_morphs:
            info = MORPH_CATALOG[key]
            btn = Button(
                text=info["name"].split()[0] + f" ({info['type'][:5].upper()})",
                font_size="11sp",
                bold=True,
                background_normal="",
                background_color=(0.18, 0.22, 0.32, 1.0) if key == self.selected_morph else (0.12, 0.13, 0.18, 1.0),
                color=(0.2, 0.9, 0.65, 1.0) if key == self.selected_morph else (0.7, 0.75, 0.85, 1.0),
                always_release=True
            )
            btn.bind(on_release=lambda x, k=key: self._select_morph(k))
            self.morph_btns[key] = btn
            morph_grid.add_widget(btn)
        form.add_widget(morph_grid)

        # Muse AI Companion Selection
        form.add_widget(Label(text="PERSONAL MUSE PROTOCOL", font_size="12sp", bold=True, color=(0.95, 0.61, 0.07, 1.0), size_hint_y=None, height=dp(20)))
        muse_grid = GridLayout(cols=3, spacing=dp(6), size_hint_y=None, height=dp(38))
        self.muse_btns = {}
        for key, info in MUSE_PERSONAS.items():
            btn = Button(
                text=info["name"],
                font_size="11sp",
                bold=True,
                background_normal="",
                background_color=(0.18, 0.22, 0.32, 1.0) if key == self.selected_muse else (0.12, 0.13, 0.18, 1.0),
                color=(1.0, 0.75, 0.2, 1.0) if key == self.selected_muse else (0.7, 0.75, 0.85, 1.0),
                always_release=True
            )
            btn.bind(on_release=lambda x, k=key: self._select_muse(k))
            self.muse_btns[key] = btn
            muse_grid.add_widget(btn)
        form.add_widget(muse_grid)

        # Dynamic Preview Card
        self.lbl_preview = Label(
            text="",
            font_size="11sp",
            markup=True,
            size_hint_y=None,
            height=dp(64),
            color=(0.9, 0.92, 0.96, 1.0)
        )
        form.add_widget(self.lbl_preview)
        self._update_preview()

        scroll.add_widget(form)
        root.add_widget(scroll)

        # Launch Button
        btn_start = Button(
            text="▶ INITIALIZE OPERATIVE & EGOCAST",
            size_hint_y=None,
            height=dp(44),
            background_normal="",
            background_color=(0.02, 0.71, 0.83, 1.0),
            color=(0.05, 0.05, 0.08, 1.0),
            font_size="13sp",
            bold=True,
            always_release=True
        )
        btn_start.bind(on_release=self._on_confirm)
        root.add_widget(btn_start)

        self.add_widget(root)

    def _update_rect(self, widget):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(0.08, 0.09, 0.13, 0.98)
            RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(8)])
            Color(0.02, 0.71, 0.83, 0.5)
            Line(rounded_rectangle=(widget.x, widget.y, widget.width, widget.height, dp(8)), width=1.2)

    def _select_arch(self, key):
        self.selected_arch = key
        for k, b in self.arch_btns.items():
            b.background_color = (0.18, 0.22, 0.32, 1.0) if k == key else (0.12, 0.13, 0.18, 1.0)
            b.color = (0.2, 0.9, 1.0, 1.0) if k == key else (0.7, 0.75, 0.85, 1.0)
        self._update_preview()

    def _select_morph(self, key):
        self.selected_morph = key
        for k, b in self.morph_btns.items():
            b.background_color = (0.18, 0.22, 0.32, 1.0) if k == key else (0.12, 0.13, 0.18, 1.0)
            b.color = (0.2, 0.9, 0.65, 1.0) if k == key else (0.7, 0.75, 0.85, 1.0)
        self._update_preview()

    def _select_muse(self, key):
        self.selected_muse = key
        for k, b in self.muse_btns.items():
            b.background_color = (0.18, 0.22, 0.32, 1.0) if k == key else (0.12, 0.13, 0.18, 1.0)
            b.color = (1.0, 0.75, 0.2, 1.0) if k == key else (0.7, 0.75, 0.85, 1.0)
        self._update_preview()

    def _update_preview(self):
        arch = ARCHETYPES[self.selected_arch]
        morph = MORPH_CATALOG[self.selected_morph]
        muse = MUSE_PERSONAS[self.selected_muse]
        bonuses_str = ", ".join([f"+{v} {k}" for k, v in arch.get("bonuses", {}).items()])
        self.lbl_preview.text = (
            f"[color=05B4D4][b]Archetype Perk:[/b] {bonuses_str} | {arch.get('trait', '')}[/color]\n"
            f"[color=27AE60][b]Sleeve:[/b] {morph['name']} | HP: {morph['durability']} | Arm: {morph['armor_kinetic']}K/{morph['armor_energy']}E[/color]\n"
            f"[color=F39C12][b]Muse [{muse['name']}]:[/b] {muse['style']}[/color]"
        )

    def _on_confirm(self, *args):
        callsign = self.txt_callsign.text.strip() or "Vagabond"
        self.dismiss()
        self.on_start_callback(callsign, self.selected_arch, self.selected_morph, self.selected_muse)


# --- 4. Climax Resolution & Epilogue Modal ---

class EndingEpilogueModal(ModalView):
    def __init__(self, ending_key: str, epilogue_text: str, engine: GameEngine, on_restart_callback, **kwargs):
        super().__init__(size_hint=(0.94, 0.85), auto_dismiss=False, **kwargs)
        self.on_restart_callback = on_restart_callback
        info = ENDINGS.get(ending_key, ENDINGS["purge"])

        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        with root.canvas.before:
            Color(0.07, 0.08, 0.12, 0.98)
            RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(8)])
            Color(0.85, 0.35, 0.95, 0.6)
            Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(8)), width=1.4)

        # Header
        root.add_widget(Label(
            text="🌟 MISSION RESOLUTION & EPILOGUE",
            font_size="16sp",
            bold=True,
            color=(0.85, 0.35, 0.95, 1.0),
            size_hint_y=None,
            height=dp(28)
        ))
        root.add_widget(Label(
            text=info["title"],
            font_size="12sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0),
            size_hint_y=None,
            height=dp(22)
        ))

        # Chronicle Narrative
        scroll = ScrollView(size_hint_y=1.0)
        lbl_narrative = Label(
            text=f"[color=D5DDF0]{epilogue_text}[/color]\n\n"
                 f"[color=F39C12][b]Operative Chronicle:[/b][/color]\n"
                 f"• Callsign: {engine.ego.callsign} ({engine.ego.background})\n"
                 f"• Final Sleeve: {engine.morph.name}\n"
                 f"• Resleeves Count: {engine.ego.resleeve_count}\n"
                 f"• Cognitive Traumas: {engine.ego.trauma}\n"
                 f"• Survived Turns: {engine.turn_count}",
            markup=True,
            font_size="12sp",
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        lbl_narrative.bind(texture_size=lambda inst, val: setattr(lbl_narrative, 'height', max(dp(200), val[1] + dp(10))))
        lbl_narrative.bind(width=lambda inst, val: setattr(lbl_narrative, 'text_size', (val - dp(12), None)))
        scroll.add_widget(lbl_narrative)
        root.add_widget(scroll)

        # Restart Button
        btn_restart = Button(
            text="🔄 NEW EXPEDITION / RE-EGOCAST",
            size_hint_y=None,
            height=dp(44),
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1.0),
            color=(0.95, 0.95, 1.0, 1.0),
            font_size="13sp",
            bold=True,
            always_release=True
        )
        btn_restart.bind(on_release=lambda x: self._on_restart())
        root.add_widget(btn_restart)

        self.add_widget(root)

    def _on_restart(self):
        self.dismiss()
        self.on_restart_callback()


# --- 4b. Tactical Breach Simulation Modal (Survivors Cross-Mode Bridge) ---

class TacticalBreachModal(ModalView):
    """Integrates real-time top-down combat simulation from Eclipse Survivors into the MUD."""
    def __init__(self, room_name: str, morph_key: str, on_complete_callback, **kwargs):
        super().__init__(size_hint=(0.98, 0.94), auto_dismiss=False, **kwargs)
        self.on_complete_callback = on_complete_callback

        morph_map = {
            "synthmorph": "synth",
            "fury": "fury",
            "menton": "menton",
            "ghost": "ghost",
            "bouncer": "synth",
            "octomorph": "menton"
        }
        surv_morph = morph_map.get(morph_key, "synth")

        root = BoxLayout(orientation='vertical', padding=dp(4), spacing=dp(4))
        with root.canvas.before:
            Color(0.05, 0.06, 0.09, 0.98)
            RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(6)])
            Color(0.91, 0.30, 0.24, 0.8)
            Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(6)), width=1.5)

        # Header Bar
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30), spacing=dp(6))
        header.add_widget(Label(
            text=f"⚡ TACTICAL BREACH SIMULATION // {room_name.upper()}",
            font_size="11sp",
            bold=True,
            color=(0.91, 0.30, 0.24, 1.0)
        ))
        btn_abort = Button(
            text="✕ RETREAT",
            size_hint_x=None,
            width=dp(74),
            background_normal="",
            background_color=(0.2, 0.24, 0.32, 0.9),
            color=(0.9, 0.9, 0.9, 1.0),
            font_size="10sp",
            bold=True,
            always_release=True
        )
        btn_abort.bind(on_release=lambda x: self._finish(False, 0, "Emergency Retreat Initiated"))
        header.add_widget(btn_abort)
        root.add_widget(header)

        # Dynamic import of Survivors Action Arena
        SurvivorsModule = None
        try:
            from modules.eclipse_survivors.main import OpenHubModule as SurvivorsModule
        except ImportError:
            try:
                import sys
                pixel_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                surv_path = os.path.join(pixel_root, "modules", "eclipse_survivors")
                if surv_path not in sys.path:
                    sys.path.insert(0, surv_path)
                from main import OpenHubModule as SurvivorsModule
            except Exception:
                SurvivorsModule = None

        if SurvivorsModule:
            self.surv = SurvivorsModule(
                morph_id=surv_morph,
                is_breach_mode=True,
                breach_time_limit=40.0,
                breach_target_kills=15,
                on_breach_complete_callback=self._finish
            )
            root.add_widget(self.surv)
        else:
            root.add_widget(Label(
                text="⚠️ Eclipse Survivors module unavailable for breach simulation.",
                color=(0.91, 0.30, 0.24, 1.0)
            ))

        self.add_widget(root)

    def _finish(self, success: bool, kills: int, reason: str):
        self.dismiss()
        self.on_complete_callback(success, kills, reason)


# --- 5. Main OpenHub Module UI ---


class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(8), spacing=dp(6), **kwargs)
        self.host = None
        self.engine = None
        self.provider_modes = [LLMProvider.AUTO, LLMProvider.OLLAMA, LLMProvider.GEMINI]
        self.current_provider_idx = 0
        self.show_visual_radar = False

        # Background Canvas
        with self.canvas.before:
            Color(0.06, 0.06, 0.09, 1.0)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # 1. Header Bar
        self._build_header()

        # 2. Transhuman Biometrics HUD Ribbon
        self._build_biometrics_hud()

        # 3. Middle Area: Terminal Log + Visual Radar
        self._build_main_viewport()

        # 4. Action Deck & Directional Controls
        self._build_action_deck()

        # 5. Input Command Bar
        self._build_input_bar()

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_load(self, host_api):
        self.host = host_api
        self.engine = GameEngine(host_api=host_api)
        self.engine.log_callback = self.terminal.append_message
        self.engine.state_callback = self.refresh_hud
        self.engine.haptic_callback = self._handle_haptic
        self.engine.ending_callback = self._show_ending_modal
        self.engine.tactical_breach_callback = self._launch_tactical_breach


        # Launch Character Creation Dossier Modal
        Clock.schedule_once(lambda dt: self._open_character_creation(), 0.1)

    def _open_character_creation(self):
        modal = CharacterCreationModal(on_start_callback=self._start_game_with_character)
        modal.open()

    def _start_game_with_character(self, callsign, arch, morph, muse):
        self.engine.init_character(callsign, arch, morph, muse)
        self.terminal.clear()
        self.engine.start_game()
        self.refresh_hud()

    def _show_ending_modal(self, ending_key: str, epilogue_text: str):
        modal = EndingEpilogueModal(
            ending_key=ending_key,
            epilogue_text=epilogue_text,
            engine=self.engine,
            on_restart_callback=self._open_character_creation
        )
        modal.open()

    def _handle_haptic(self, style: str):
        if self.host and hasattr(self.host, "hardware") and self.host.hardware:
            try:
                self.host.hardware.vibrate()
            except Exception:
                pass

    # --- UI Layout Builders ---

    def _build_header(self):
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(6))
        
        # Title
        self.lbl_title = Label(
            text="🌌 ECLIPSE PHASE",
            font_size="15sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0),
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        header.add_widget(self.lbl_title)

        # Radar Toggle Button
        self.btn_radar_toggle = Button(
            text="🗺️ RADAR",
            size_hint_x=None,
            width=dp(80),
            background_normal="",
            background_color=(0.14, 0.18, 0.26, 1.0),
            color=(0.02, 0.71, 0.83, 1.0),
            font_size="11sp",
            bold=True,
            always_release=True
        )
        self.btn_radar_toggle.bind(on_release=lambda x: self._toggle_radar_view())
        header.add_widget(self.btn_radar_toggle)

        # Provider Toggle Chip
        self.btn_provider = Button(
            text="⚡ LLM: AUTO",
            size_hint_x=None,
            width=dp(115),
            background_normal="",
            background_color=(0.12, 0.14, 0.22, 1.0),
            color=(0.85, 0.70, 1.0, 1.0),
            font_size="11sp",
            bold=True,
            always_release=True
        )
        self.btn_provider.bind(on_release=lambda x: self._toggle_llm_provider())
        header.add_widget(self.btn_provider)

        # Dossier Reset Button
        btn_dossier = Button(
            text="DOS",
            size_hint_x=None,
            width=dp(42),
            background_normal="",
            background_color=(0.20, 0.14, 0.25, 1.0),
            color=(0.9, 0.7, 1.0, 1.0),
            font_size="10sp",
            always_release=True
        )
        btn_dossier.bind(on_release=lambda x: self._open_character_creation())
        header.add_widget(btn_dossier)

        self.add_widget(header)

    def _build_biometrics_hud(self):
        hud = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(52), spacing=dp(3))
        
        row1 = BoxLayout(orientation='horizontal', spacing=dp(8))
        self.lbl_ego = Label(
            text="EGO: Vagabond | STRESS: 0/34 [TR: 0]",
            font_size="11sp",
            bold=True,
            color=(0.75, 0.55, 1.0, 1.0),
            halign='left'
        )
        self.lbl_ego.bind(size=self.lbl_ego.setter('text_size'))
        
        self.lbl_morph = Label(
            text="SLEEVE: Steel Synthmorph | HP: 55/55",
            font_size="11sp",
            bold=True,
            color=(0.02, 0.85, 0.65, 1.0),
            halign='right'
        )
        self.lbl_morph.bind(size=self.lbl_morph.setter('text_size'))
        row1.add_widget(self.lbl_ego)
        row1.add_widget(self.lbl_morph)
        hud.add_widget(row1)

        row2 = BoxLayout(orientation='horizontal', spacing=dp(8))
        self.pb_morph = ProgressBar(max=55, value=55, size_hint_y=None, height=dp(8))
        row2.add_widget(self.pb_morph)
        self.pb_stress = ProgressBar(max=34, value=0, size_hint_y=None, height=dp(8))
        row2.add_widget(self.pb_stress)
        hud.add_widget(row2)

        self.lbl_location = Label(
            text="LOCATION: Airlock Alpha-1 (Sector 1: Airlock Ring)",
            font_size="10sp",
            color=(0.65, 0.70, 0.85, 1.0),
            size_hint_y=None,
            height=dp(16),
            halign='left'
        )
        self.lbl_location.bind(size=self.lbl_location.setter('text_size'))
        hud.add_widget(self.lbl_location)

        self.add_widget(hud)

    def _build_main_viewport(self):
        self.main_split = BoxLayout(orientation='horizontal', spacing=dp(6))

        # Terminal Log View
        self.term_container = BoxLayout(orientation='vertical')
        with self.term_container.canvas.before:
            Color(0.09, 0.10, 0.15, 1.0)
            self.term_bg = RoundedRectangle(pos=self.term_container.pos, size=self.term_container.size, radius=[dp(6)])
            Color(0.20, 0.22, 0.32, 0.7)
            self.term_border = Line(rounded_rectangle=(self.term_container.x, self.term_container.y, self.term_container.width, self.term_container.height, dp(6)), width=1.0)
        
        def _update_term_rect(*args):
            self.term_bg.pos = self.term_container.pos
            self.term_bg.size = self.term_container.size
            self.term_border.rounded_rectangle = (self.term_container.x, self.term_container.y, self.term_container.width, self.term_container.height, dp(6))
        self.term_container.bind(pos=_update_term_rect, size=_update_term_rect)

        self.terminal = TerminalLog()
        self.term_container.add_widget(self.terminal)
        self.main_split.add_widget(self.term_container)

        self.add_widget(self.main_split)

    def _toggle_radar_view(self):
        self.show_visual_radar = not self.show_visual_radar
        if self.show_visual_radar:
            self.btn_radar_toggle.background_color = (0.02, 0.71, 0.83, 1.0)
            self.btn_radar_toggle.color = (0.05, 0.05, 0.08, 1.0)
            if not hasattr(self, 'radar_widget'):
                self.radar_widget = VisualRadarWidget(engine=self.engine, size_hint_x=0.45)
            self.main_split.add_widget(self.radar_widget)
        else:
            self.btn_radar_toggle.background_color = (0.14, 0.18, 0.26, 1.0)
            self.btn_radar_toggle.color = (0.02, 0.71, 0.83, 1.0)
            if hasattr(self, 'radar_widget') and self.radar_widget in self.main_split.children:
                self.main_split.remove_widget(self.radar_widget)

    def _build_action_deck(self):
        deck = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(68), spacing=dp(6))
        
        chips = GridLayout(cols=3, spacing=dp(4), size_hint_x=0.6)
        btn_look = self._create_deck_btn("👁 LOOK", (0.15, 0.20, 0.30, 1.0), (0.2, 0.8, 1.0, 1.0), lambda: self._send_cmd("look"))
        btn_inv = self._create_deck_btn("🎒 INV", (0.18, 0.16, 0.24, 1.0), (0.9, 0.7, 0.2, 1.0), lambda: self._send_cmd("inv"))
        self.btn_talk = self._create_deck_btn("💬 TALK", (0.18, 0.14, 0.26, 1.0), (0.7, 0.5, 1.0, 1.0), self._on_talk_pressed)
        btn_muse = self._create_deck_btn("🤖 MUSE", (0.22, 0.14, 0.28, 1.0), (0.7, 0.5, 1.0, 1.0), lambda: self._send_cmd("muse analyze environment"))
        btn_hack = self._create_deck_btn("⚡ HACK", (0.24, 0.18, 0.10, 1.0), (1.0, 0.7, 0.1, 1.0), lambda: self._send_cmd("hack node"))
        btn_resleeve = self._create_deck_btn("🔄 RESLEEVE", (0.20, 0.12, 0.24, 1.0), (0.9, 0.4, 0.8, 1.0), lambda: self._send_cmd("resleeve random"))

        chips.add_widget(btn_look)
        chips.add_widget(btn_inv)
        chips.add_widget(self.btn_talk)
        chips.add_widget(btn_muse)
        chips.add_widget(btn_hack)
        chips.add_widget(btn_resleeve)
        deck.add_widget(chips)

        dpad = GridLayout(cols=3, spacing=dp(4), size_hint_x=0.4)
        dpad.add_widget(Label())
        dpad.add_widget(self._create_dpad_btn("▲ N", lambda: self._send_cmd("n")))
        dpad.add_widget(Label())
        dpad.add_widget(self._create_dpad_btn("◀ W", lambda: self._send_cmd("w")))
        dpad.add_widget(self._create_dpad_btn("▼ S", lambda: self._send_cmd("s")))
        dpad.add_widget(self._create_dpad_btn("▶ E", lambda: self._send_cmd("e")))
        deck.add_widget(dpad)

        self.add_widget(deck)

        # Contextual Interaction Banner (Lights up when NPCs or interaction targets are present)
        self.context_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=0, opacity=0, spacing=dp(6))
        self.add_widget(self.context_bar)

    def _build_input_bar(self):
        input_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(42), spacing=dp(6))
        
        self.txt_input = TextInput(
            hint_text="Enter MUD command or roleplay action (e.g. 'hack terminal', 'examine airlock')...",
            multiline=False,
            font_size="13sp",
            background_color=(0.11, 0.12, 0.18, 1.0),
            foreground_color=(0.95, 0.95, 0.98, 1.0),
            cursor_color=(0.02, 0.71, 0.83, 1.0),
            padding=[dp(10), dp(10), dp(10), dp(10)]
        )
        self.txt_input.bind(on_text_validate=lambda x: self._on_submit())
        input_bar.add_widget(self.txt_input)

        btn_send = Button(
            text="TRANSMIT",
            size_hint_x=None,
            width=dp(85),
            background_normal="",
            background_color=(0.02, 0.71, 0.83, 1.0),
            color=(0.05, 0.05, 0.08, 1.0),
            font_size="12sp",
            bold=True,
            always_release=True
        )
        btn_send.bind(on_release=lambda x: self._on_submit())
        input_bar.add_widget(btn_send)

        self.add_widget(input_bar)

    def _create_deck_btn(self, text, bg_color, text_color, callback):
        btn = Button(
            text=text,
            background_normal="",
            background_color=bg_color,
            color=text_color,
            font_size="11sp",
            bold=True,
            always_release=True
        )
        btn.bind(on_release=lambda x: callback())
        return btn

    def _create_dpad_btn(self, text, callback):
        btn = Button(
            text=text,
            background_normal="",
            background_color=(0.14, 0.16, 0.24, 1.0),
            color=(0.02, 0.71, 0.83, 1.0),
            font_size="12sp",
            bold=True,
            always_release=True
        )
        btn.bind(on_release=lambda x: callback())
        return btn

    # --- Interaction Logic ---

    def _on_submit(self):
        text = self.txt_input.text.strip()
        if not text:
            return
        self.txt_input.text = ""
        if self.engine:
            self.engine.process_command(text)

    def _send_cmd(self, cmd_str: str):
        if self.engine:
            self.engine.process_command(cmd_str)

    def _toggle_llm_provider(self):
        self.current_provider_idx = (self.current_provider_idx + 1) % len(self.provider_modes)
        mode = self.provider_modes[self.current_provider_idx]
        if self.engine:
            self.engine.llm.set_mode(mode)
        
        mode_names = {
            LLMProvider.AUTO: "⚡ LLM: AUTO",
            LLMProvider.OLLAMA: "⚡ LLM: OLLAMA",
            LLMProvider.GEMINI: "✦ LLM: GEMINI"
        }
        self.btn_provider.text = mode_names.get(mode, "LLM: AUTO")

    def refresh_hud(self):
        if not self.engine:
            return
        ego = self.engine.ego
        morph = self.engine.morph
        cur = self.engine.get_current_room()

        self.lbl_ego.text = f"EGO: {ego.callsign} | STRESS: {ego.stress}/{ego.lucidity} [TR: {ego.trauma}]"
        self.lbl_morph.text = f"SLEEVE: {morph.name} | HP: {morph.durability}/{morph.max_durability}"
        self.lbl_location.text = f"LOCATION: {cur.title} ({cur.sector})"

        self.pb_morph.max = morph.max_durability
        self.pb_morph.value = morph.durability

        self.pb_stress.max = ego.lucidity
        self.pb_stress.value = ego.stress

        if hasattr(self, 'radar_widget'):
            self.radar_widget.redraw()

        # Dynamic Contextual Interaction Banner (Talk & Tactical Breach)
        if hasattr(self, 'context_bar') and hasattr(self, 'btn_talk'):
            self.context_bar.clear_widgets()
            alive_npcs = [n for n in cur.npcs if n.is_alive()]
            
            if alive_npcs:
                target = alive_npcs[0]
                short_name = target.name.split()[0].replace(".", "")
                self.btn_talk.text = f"💬 {short_name.upper()}"
                self.btn_talk.background_color = (0.54, 0.36, 0.96, 1.0)
                self.btn_talk.color = (1.0, 1.0, 1.0, 1.0)

                btn_talk_ctx = Button(
                    text=f"💬 TALK TO {target.name.upper()}",
                    size_hint_x=0.55 if any(n.hostility == 'hostile' for n in cur.npcs) or cur.hazard else 0.65,
                    background_normal="",
                    background_color=(0.54, 0.36, 0.96, 0.95),
                    color=(1.0, 1.0, 1.0, 1.0),
                    font_size="11sp",
                    bold=True,
                    always_release=True
                )
                btn_talk_ctx.bind(on_release=lambda x, t=target: self._trigger_context_talk(t))
                self.context_bar.add_widget(btn_talk_ctx)

                if target.id == "sorenson" and any(i.id == "nanite_spray" for i in self.engine.inventory):
                    btn_give_med = Button(
                        text="💉 GIVE MED-SPRAY",
                        size_hint_x=0.35,
                        background_normal="",
                        background_color=(0.15, 0.68, 0.38, 0.95),
                        color=(1.0, 1.0, 1.0, 1.0),
                        font_size="11sp",
                        bold=True,
                        always_release=True
                    )
                    btn_give_med.bind(on_release=lambda x: self._send_cmd("give nanite_spray to sorenson"))
                    self.context_bar.add_widget(btn_give_med)
            else:
                self.btn_talk.text = "💬 TALK"
                self.btn_talk.background_color = (0.14, 0.15, 0.20, 0.6)
                self.btn_talk.color = (0.5, 0.55, 0.65, 1.0)

            # Prominent Tactical Breach Action Button
            is_combat_sector = (cur.hazard is not None or 
                                any(n.hostility == 'hostile' for n in cur.npcs) or
                                cur.id in ("conduit_alpha", "incubator_bay", "server_hall", "quantum_core", "containment_vault"))

            btn_breach = Button(
                text="⚡ TACTICAL BREACH",
                size_hint_x=0.45 if alive_npcs else 1.0,
                background_normal="",
                background_color=(0.91, 0.30, 0.24, 0.95) if is_combat_sector else (0.75, 0.25, 0.20, 0.75),
                color=(1.0, 1.0, 1.0, 1.0),
                font_size="11sp",
                bold=True,
                always_release=True
            )
            btn_breach.bind(on_release=lambda x: self._launch_tactical_breach())
            self.context_bar.add_widget(btn_breach)
            self.context_bar.height = dp(34)
            self.context_bar.opacity = 1.0

    def _on_talk_pressed(self):
        if not self.engine:
            return
        cur = self.engine.get_current_room()
        alive_npcs = [n for n in cur.npcs if n.is_alive()]
        if alive_npcs:
            target = alive_npcs[0]
            self._send_cmd(f"talk to {target.name}")
            self.txt_input.text = f"talk to {target.name} "
        else:
            self._send_cmd("talk")

    def _trigger_context_talk(self, npc):
        self._send_cmd(f"talk to {npc.name}")
        self.txt_input.text = f"talk to {npc.name} "

    def _launch_tactical_breach(self):
        if not self.engine:
            return
        cur = self.engine.get_current_room()
        morph_k = self.engine.morph.morph_type if self.engine.morph else "synth"
        modal = TacticalBreachModal(
            room_name=cur.name,
            morph_key=morph_k,
            on_complete_callback=self._on_tactical_breach_finished
        )
        modal.open()

    def _on_tactical_breach_finished(self, success: bool, kills: int, reason: str):
        if not self.engine:
            return
        from models import Item
        cur = self.engine.get_current_room()

        if success:
            for npc in cur.npcs:
                if npc.hostility == "hostile":
                    npc.hp = 0

            self.engine.morph.hp = min(self.engine.morph.durability, self.engine.morph.hp + 30)
            self.engine.ego.stress = max(0, self.engine.ego.stress - 15)

            loot_msg = "Chassis repairs and combat stims synthesized."
            if not any(i.id == "nanite_core" for i in self.engine.inventory):
                core_item = Item(
                    id="nanite_core",
                    name="Tactical Nanite Overclock Core",
                    item_type="tool",
                    description="High-density transhuman nanocore salvaged from purged security incursions.",
                    heal_hp=30
                )
                self.engine.inventory.append(core_item)
                loot_msg = "Retrieved [b]Tactical Nanite Overclock Core[/b] into sleeve cargo."

            if cur.id in ("server_hall", "quantum_core", "containment_vault") and not any(i.id == "quarantine_keycard" for i in self.engine.inventory):
                kc_item = Item(
                    id="quarantine_keycard",
                    name="TITAN Quarantine Keycard",
                    item_type="keycard",
                    description="Class-5 biometric encryption card unlocking high-security blast doors."
                )
                self.engine.inventory.append(kc_item)
                loot_msg += " Retrieved [color=FFD700][b]TITAN Quarantine Keycard[/b][/color]!"

            report = (
                f"\n[color=05B4D4]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/color]\n"
                f"[color=27AE60][b]⚡ TACTICAL BREACH PROTOCOL // SECTOR SECURED[/b][/color]\n"
                f"[color=F39C12]Hostiles Purged:[/color] {kills} kills ({reason})\n"
                f"[color=05B4D4]Tactical Salvage:[/color] {loot_msg}\n"
                f"[color=8A5CF5]Operative Status:[/color] +30 Morph Durability repaired, -15 Stress stabilized.\n"
                f"[color=05B4D4]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/color]\n"
            )
            self.terminal.append_message(report, stream=True)
            self.engine.log(f"Muse broadcasts: 'Sensory telemetry confirms sector perimeter secured, operative. Outstanding tactical execution.'")
        else:
            self.engine.morph.hp = max(1, self.engine.morph.hp - 15)
            self.engine.ego.stress = min(self.engine.ego.lucidity, self.engine.ego.stress + 10)
            retreat_report = (
                f"\n[color=05B4D4]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/color]\n"
                f"[color=E74C3C][b]⚠️ TACTICAL BREACH ABORTED // EMERGENCY RETREAT[/b][/color]\n"
                f"[color=F39C12]Status:[/color] {reason}. Evasive thrusters engaged back to staging bulkhead.\n"
                f"[color=E74C3C]Chassis Strain:[/color] -15 Morph Durability, +10 Stress accrued during extraction.\n"
                f"[color=05B4D4]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/color]\n"
            )
            self.terminal.append_message(retreat_report, stream=True)

        self.refresh_hud()



if __name__ == '__main__':
    from kivy.app import App
    import sys
    pixel_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if pixel_root not in sys.path:
        sys.path.insert(0, pixel_root)
    from core.security import HostAPI

    class EclipsePhaseApp(App):
        def build(self):
            mod = OpenHubModule()
            mod.on_load(HostAPI(module_id="eclipse_mud"))
            return mod

    EclipsePhaseApp().run()
