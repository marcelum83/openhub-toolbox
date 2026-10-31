"""
Eclipse Survivors - Level Up Augment Draft Modal
Presents 3 holographic cybernetic upgrade cards on level up,
prioritizing legendary Cybernetic Evolutions when unlocked.
"""
import random
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp, sp

try:
    from game_state import UPGRADE_CATALOG, Player
except ImportError:
    from .game_state import UPGRADE_CATALOG, Player


class UpgradeDraftModal(ModalView):
    def __init__(self, player: Player, on_select_callback, **kwargs):
        super().__init__(size_hint=(0.95, 0.74), auto_dismiss=False, **kwargs)
        self.player = player
        self.on_select_callback = on_select_callback

        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        with root.canvas.before:
            Color(0.08, 0.09, 0.14, 0.98)
            RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(8)])
            Color(0.02, 0.71, 0.83, 0.7)
            Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(8)), width=1.5)

        # Header Banner
        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(46), spacing=dp(2))
        header.add_widget(Label(
            text=f"⚡ SYNAPSE OVERCLOCK: LEVEL {player.level}",
            font_size="16sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0)
        ))
        header.add_widget(Label(
            text="Install cybernetics or initiate transhuman evolution:",
            font_size="11sp",
            color=(0.7, 0.75, 0.85, 1.0)
        ))
        root.add_widget(header)

        # Determine eligible upgrades & evolutions
        available_keys = []
        evolution_keys = []

        for k, v in UPGRADE_CATALOG.items():
            if v["type"] == "evolution":
                base_w = v["base_weapon"]
                req_p = v["required_passive"]
                if (player.inventory.get(base_w, 0) >= 5 and 
                    player.inventory.get(req_p, 0) >= 1 and 
                    player.inventory.get(k, 0) == 0):
                    evolution_keys.append(k)
            else:
                if player.inventory.get(k, 0) < v["max_level"]:
                    available_keys.append(k)

        chosen_keys = []
        if evolution_keys:
            chosen_keys.append(evolution_keys[0])

        needed = 3 - len(chosen_keys)
        if len(available_keys) > needed:
            chosen_keys.extend(random.sample(available_keys, needed))
        else:
            chosen_keys.extend(available_keys)

        # Cards Container (Horizontal Row of 3 Cards)
        cards_box = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=1.0)

        for key in chosen_keys:
            info = UPGRADE_CATALOG[key]
            current_lvl = player.inventory.get(key, 0)
            next_lvl = current_lvl + 1
            is_new = current_lvl == 0
            is_evo = info["type"] == "evolution"

            card = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))
            with card.canvas.before:
                if is_evo:
                    Color(0.18, 0.14, 0.05, 0.98)
                else:
                    Color(0.12, 0.14, 0.20, 0.95)
                RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(6)])
                
                # Border color
                if is_evo:
                    Color(1.0, 0.84, 0.0, 1.0)
                    line_w = 2.0
                elif info["type"] == "weapon":
                    Color(0.02, 0.71, 0.83, 0.8)
                    line_w = 1.2
                else:
                    Color(0.85, 0.35, 0.95, 0.8)
                    line_w = 1.2
                Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(6)), width=line_w)

            # Top Tag Row
            top_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28))
            top_row.add_widget(Label(text=info["icon"], font_size="18sp", size_hint_x=None, width=dp(28)))

            if is_evo:
                type_tag = "🌟 EVOLUTION"
                tag_color = (1.0, 0.84, 0.0, 1.0)
            elif is_new and info["type"] == "weapon":
                type_tag = "NEW WEAPON"
                tag_color = (0.02, 0.71, 0.83, 1.0)
            elif is_new:
                type_tag = "NEW PASSIVE"
                tag_color = (0.2, 0.9, 0.65, 1.0)
            else:
                type_tag = f"LVL {current_lvl} ➜ {next_lvl}"
                tag_color = (0.95, 0.75, 0.1, 1.0)

            top_row.add_widget(Label(
                text=type_tag,
                font_size="10sp",
                bold=True,
                color=tag_color,
                halign='right'
            ))
            card.add_widget(top_row)

            # Name
            lbl_name = Label(
                text=info["name"],
                font_size="12sp",
                bold=True,
                color=(1.0, 0.88, 0.2, 1.0) if is_evo else (0.95, 0.95, 0.98, 1.0),
                size_hint_y=None,
                height=dp(28),
                halign='center'
            )
            lbl_name.bind(size=lbl_name.setter('text_size'))
            card.add_widget(lbl_name)

            # Description
            lbl_desc = Label(
                text=info["description"],
                font_size="10sp",
                color=(0.9, 0.85, 0.7, 1.0) if is_evo else (0.75, 0.80, 0.90, 1.0),
                halign='center',
                valign='middle'
            )
            lbl_desc.bind(size=lbl_desc.setter('text_size'))
            card.add_widget(lbl_desc)

            # Action Button
            btn_color = (1.0, 0.84, 0.0, 1.0) if is_evo else (
                (0.02, 0.71, 0.83, 1.0) if info["type"] == "weapon" else (0.54, 0.36, 0.96, 1.0)
            )
            btn_txt = "🧬 EVOLVE" if is_evo else "INSTALL"

            btn_select = Button(
                text=btn_txt,
                size_hint_y=None,
                height=dp(36),
                background_normal="",
                background_color=btn_color,
                color=(0.05, 0.05, 0.08, 1.0),
                font_size="11sp",
                bold=True,
                always_release=True
            )
            btn_select.bind(on_release=lambda x, k=key: self._on_select(k))
            card.add_widget(btn_select)

            cards_box.add_widget(card)

        root.add_widget(cards_box)
        self.add_widget(root)

    def _on_select(self, upgrade_id: str):
        self.dismiss()
        self.on_select_callback(upgrade_id)
