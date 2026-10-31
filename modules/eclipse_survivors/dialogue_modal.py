"""
Eclipse Survivors - In-World NPC Dialogue & Interaction Modal
Provides interactive branching conversations, transhuman lore decryption,
Basilisk virus cures (dispensing the Class-5 Keycard), black-market augment barter,
and mid-run chassis resleeving at Clinic Epsilon.
"""
from typing import Dict, Any, List, Optional, Callable
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
from kivy.metrics import dp, sp
from kivy.clock import Clock


class NPCDialogueModal(ModalView):
    """
    Holographic Comms & Proximity Interaction Modal.
    Pauses the real-time simulation while the operative converses with in-world NPCs.
    """
    def __init__(
        self,
        npc,
        world,
        on_close_callback: Optional[Callable] = None,
        on_trigger_resleeve: Optional[Callable] = None,
        on_trigger_upgrade_draft: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(size_hint=(0.94, 0.82), auto_dismiss=False, **kwargs)
        self.npc = npc
        self.world = world
        self.player = world.player
        self.on_close_callback = on_close_callback
        self.on_trigger_resleeve = on_trigger_resleeve
        self.on_trigger_upgrade_draft = on_trigger_upgrade_draft

        self.current_node_id = "root"

        # Theme styling based on NPC
        npc_id = npc.id
        if npc_id == "sorenson":
            self.accent_color = (0.02, 0.71, 0.83, 1.0)
            self.status_tag = "[color=E74C3C][b]VIRAL CONTAMINATION: CRITICAL[/b][/color]" if npc.dialogue_state != "cured" else "[color=27AE60][b]NEURAL STATUS: STABILIZED[/b][/color]"
        elif npc_id == "zephyr":
            self.accent_color = (0.85, 0.35, 0.95, 1.0)
            self.status_tag = "[color=05B4D4][b]MESH LINK: UNRESTRICTED[/b][/color]"
        elif npc_id == "clinic_agi":
            self.accent_color = (0.20, 0.95, 0.65, 1.0)
            self.status_tag = "[color=27AE60][b]VAT REPLICATION: ONLINE[/b][/color]"
        else:
            self.accent_color = (0.9, 0.9, 0.9, 1.0)
            self.status_tag = "[color=F39C12][b]IFF: UNIDENTIFIED[/b][/color]"

        self._build_ui()
        self._load_node("root")

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        with root.canvas.before:
            Color(0.06, 0.08, 0.12, 0.98)
            RoundedRectangle(pos=root.pos, size=root.size, radius=[dp(8)])
            Color(*self.accent_color)
            Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(8)), width=1.8)

        # 1. Header Bar
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
        
        # NPC Icon Portrait
        lbl_icon = Label(
            text=self.npc.icon,
            font_size="26sp",
            size_hint_x=None,
            width=dp(44)
        )
        header.add_widget(lbl_icon)

        # Name and Title Box
        title_box = BoxLayout(orientation='vertical', spacing=dp(2))
        lbl_name = Label(
            text=f"{self.npc.name.upper()} // {self.npc.title.upper()}",
            font_size="13sp",
            bold=True,
            color=self.accent_color,
            halign='left',
            size_hint_y=None,
            height=dp(20)
        )
        lbl_name.bind(size=lbl_name.setter('text_size'))
        title_box.add_widget(lbl_name)

        self.lbl_status = Label(
            text=self.status_tag,
            markup=True,
            font_size="10sp",
            halign='left',
            size_hint_y=None,
            height=dp(16)
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        title_box.add_widget(self.lbl_status)
        header.add_widget(title_box)

        # Close / Dismiss Button
        btn_close = Button(
            text="✕ DISMISS",
            size_hint_x=None,
            width=dp(80),
            size_hint_y=None,
            height=dp(34),
            background_normal="",
            background_color=(0.18, 0.22, 0.30, 0.95),
            color=(0.85, 0.90, 0.98, 1.0),
            font_size="11sp",
            bold=True,
            always_release=True
        )
        btn_close.bind(on_release=lambda x: self._on_close())
        header.add_widget(btn_close)
        root.add_widget(header)

        # 2. Main Dialogue Text Transcript (Scrollable)
        scroll = ScrollView(size_hint_y=0.55, bar_width=dp(4), bar_color=(*self.accent_color[:3], 0.6))
        self.lbl_dialogue = Label(
            text="",
            markup=True,
            font_size="12sp",
            size_hint_y=None,
            halign='left',
            valign='top',
            color=(0.92, 0.94, 0.98, 1.0)
        )
        self.lbl_dialogue.bind(texture_size=self._update_text_height)
        self.lbl_dialogue.bind(width=self._update_text_width)
        scroll.add_widget(self.lbl_dialogue)
        root.add_widget(scroll)

        # 3. Interactive Choice Options Container
        self.options_box = BoxLayout(orientation='vertical', size_hint_y=0.45, spacing=dp(5))
        root.add_widget(self.options_box)

        self.add_widget(root)

    def _update_text_height(self, instance, value):
        self.lbl_dialogue.height = max(dp(80), value[1] + dp(10))

    def _update_text_width(self, instance, value):
        self.lbl_dialogue.text_size = (value - dp(10), None)

    def _load_node(self, node_id: str):
        self.current_node_id = node_id
        dialogue_tree = self._get_dialogue_tree()
        node = dialogue_tree.get(node_id) or dialogue_tree.get("root", {})

        text = node.get("text", "")
        self.lbl_dialogue.text = text

        # Rebuild options buttons
        self.options_box.clear_widgets()
        for opt in node.get("options", []):
            label_txt = opt.get("label", "...")
            target_node = opt.get("target_node")
            action_code = opt.get("action")
            bg_col = opt.get("bg_color", (0.14, 0.18, 0.26, 0.95))
            txt_col = opt.get("txt_color", (0.9, 0.95, 1.0, 1.0))
            is_enabled = opt.get("enabled", True)

            btn = Button(
                text=label_txt,
                markup=True,
                size_hint_y=None,
                height=dp(34),
                background_normal="",
                background_color=bg_col if is_enabled else (0.10, 0.12, 0.16, 0.7),
                color=txt_col if is_enabled else (0.45, 0.50, 0.60, 1.0),
                font_size="11sp",
                bold=True,
                disabled=not is_enabled,
                always_release=True
            )
            btn.bind(on_release=lambda x, tn=target_node, act=action_code: self._handle_choice(tn, act))
            self.options_box.add_widget(btn)

    def _handle_choice(self, target_node: Optional[str], action: Optional[str]):
        if action:
            self._execute_action(action)

        if target_node == "CLOSE":
            self._on_close()
            return

        if target_node:
            self._load_node(target_node)

    def _execute_action(self, action: str):
        player = self.player
        world = self.world
        npc = self.npc

        if action == "cure_sorenson":
            npc.dialogue_state = "cured"
            player.has_keycard = True
            player.hp = min(player.max_hp, player.hp + 40.0)
            player.stress = max(0.0, player.stress - 15.0)
            self.lbl_status.text = "[color=27AE60][b]NEURAL STATUS: STABILIZED[/b][/color]"
            world.trigger_alert("🔑 CLASS-5 KEYCARD RECEIVED FROM DR. SORENSON!", (1.0, 0.84, 0.0, 1.0))

        elif action == "heal_sorenson_supplies":
            player.hp = min(player.max_hp, player.hp + 35.0)
            world.trigger_alert("💉 BIO-GEL APPLIED: +35 HP REPAIRED", (0.2, 0.95, 0.65, 1.0))

        elif action == "zephyr_hack_turrets":
            world.turret_active = 90.0  # 90 seconds of automated turret fire
            npc.dialogue_state = "turret_hacked"
            world.trigger_alert("⚡ ZEPHYR REPROGRAMMED STATION TURRETS TO COVER YOU!", (0.02, 0.9, 1.0, 1.0))

        elif action == "zephyr_barter_augment":
            # Costs 25 XP or nanocores to draft an immediate upgrade
            if player.xp >= 25:
                player.xp -= 25
            else:
                player.nanocores = max(0, player.nanocores - 25)
            self._on_close()
            if self.on_trigger_upgrade_draft:
                Clock.schedule_once(lambda dt: self.on_trigger_upgrade_draft(player), 0.1)

        elif action == "zephyr_emp_burst":
            # Overloads EMP in promenade
            world.trigger_alert("💥 PROMENADE SUB-GRID EMP DISCHARGED!", (0.85, 0.35, 0.95, 1.0))
            for enemy in world.enemies:
                if enemy.home_room_id == "promenade" or enemy.home_room_id == "":
                    enemy.hp -= 80.0
                    enemy.stun_timer = 4.0

        elif action == "clinic_resleeve":
            self._on_close()
            if self.on_trigger_resleeve:
                Clock.schedule_once(lambda dt: self.on_trigger_resleeve(), 0.1)

        elif action == "clinic_full_repair":
            player.hp = player.max_hp
            player.stress = 0.0
            world.trigger_alert("🧬 CHASSIS RESTORED TO 100% DURABILITY // STRESS PURGED", (0.2, 0.95, 0.65, 1.0))

        elif action == "clinic_insurance":
            player.has_stack_insurance = True
            world.trigger_alert("🧬 CORTICAL STACK CLOUD INSURANCE SYNCHED", (0.2, 0.95, 0.65, 1.0))

    def _on_close(self):
        self.dismiss()
        if self.on_close_callback:
            self.on_close_callback()

    # --- Dialogue Content Trees ---

    def _get_dialogue_tree(self) -> Dict[str, Any]:
        npc_id = self.npc.id

        if npc_id == "sorenson":
            return self._build_sorenson_tree()
        elif npc_id == "zephyr":
            return self._build_zephyr_tree()
        elif npc_id == "clinic_agi":
            return self._build_clinic_tree()

        return {
            "root": {
                "text": "Transhuman entity responds with encrypted carrier signals.",
                "options": [{"label": "🚪 [Step back]", "target_node": "CLOSE"}]
            }
        }

    def _build_sorenson_tree(self) -> Dict[str, Any]:
        is_cured = (self.npc.dialogue_state == "cured")
        has_keycard = self.player.has_keycard

        if not is_cured:
            return {
                "root": {
                    "text": (
                        "[color=05B4D4]Dr. Sorenson clutches his neck where dark bio-mechanical veins pulse against synthetic skin.[/color]\n\n"
                        "[color=E74C3C]'Hold your fire, Sentinel! I'm Dr. Sorenson, lead researcher for Project Cassini.'[/color]\n\n"
                        "'The containment seals in Sector 3 collapsed cycles ago. An Exsurgent Basilisk nanovirus is burning "
                        "through my Cortical Stack right now! My thoughts are fragmenting... if you have medical nanite stabilizers, "
                        "administer them before the infection overtakes my ego!'"
                    ),
                    "options": [
                        {
                            "label": "💉 [ADMINISTER NANITE MED-SPRAY] Suppress the Basilisk infection",
                            "target_node": "cured_reward",
                            "action": "cure_sorenson",
                            "bg_color": (0.15, 0.68, 0.38, 0.95),
                            "txt_color": (1.0, 1.0, 1.0, 1.0)
                        },
                        {
                            "label": "💬 'Doctor, what happened to this station deck?'",
                            "target_node": "lore_outbreak",
                            "bg_color": (0.14, 0.18, 0.26, 0.95)
                        },
                        {
                            "label": "❓ 'How do I access the Sector Transit Elevator?'",
                            "target_node": "elevator_info",
                            "bg_color": (0.14, 0.18, 0.26, 0.95)
                        },
                        {
                            "label": "🚪 [Step back] 'Hold steady, Doctor. I'm securing the perimeter.'",
                            "target_node": "CLOSE",
                            "bg_color": (0.18, 0.20, 0.28, 0.9)
                        }
                    ]
                },
                "cured_reward": {
                    "text": (
                        "[color=27AE60]The pressurized nanite spray hisses into Dr. Sorenson's carotid mesh port. "
                        "The black capillary veins receding from his neck visibly dissolve as cellular stabilizers neutralize the pathogen.[/color]\n\n"
                        "[color=05B4D4]'By the mesh... the viral replication has ceased! My stack telemetry is clearing.'[/color]\n\n"
                        "[color=FFD700][b]🔑 'Take this: my Class-5 TITAN Quarantine Keycard.[/b][/color] "
                        "The heavy blast doors between the Security Armory and the Sector Transit Elevator are electronically locked. "
                        "This card will override the magnetic bulkheads. But be warned: a rogue [b]Reaper Combat Mech[/b] has entrenched itself "
                        "inside the elevator chamber. Destroy it to activate the transit lift!'"
                    ),
                    "options": [
                        {
                            "label": "🛡️ 'Understood. What weapons do you recommend against the Reaper Mech?'",
                            "target_node": "reaper_intel",
                            "bg_color": (0.14, 0.18, 0.26, 0.95)
                        },
                        {
                            "label": "💊 'Do you have any spare medical biogel for my chassis?'",
                            "target_node": "sorenson_meds",
                            "action": "heal_sorenson_supplies",
                            "bg_color": (0.18, 0.40, 0.30, 0.95)
                        },
                        {
                            "label": "🚀 'Thank you, Doctor. Heading north to unlock the Elevator.'",
                            "target_node": "CLOSE",
                            "bg_color": (0.15, 0.68, 0.38, 0.95)
                        }
                    ]
                },
                "lore_outbreak": {
                    "text": (
                        "'We recovered a fractured alien memory core from the Saturnian rings. We thought it was inert. "
                        "The moment the decoding array initialized, an Exsurgent quantum hack propagated across the local mesh. "
                        "Security androids tore through the staff, and biological morphs began twisting into flesh-metal abominations. "
                        "The station quarantine protocol triggered, sealing all decks. Only the transit elevator remains.'"
                    ),
                    "options": [
                        {
                            "label": "💉 'Here, take this Nanite Med-Spray. Let me stabilize you.'",
                            "target_node": "cured_reward",
                            "action": "cure_sorenson",
                            "bg_color": (0.15, 0.68, 0.38, 0.95)
                        },
                        {
                            "label": "🔙 [Back to main inquiry]",
                            "target_node": "root",
                            "bg_color": (0.14, 0.18, 0.26, 0.95)
                        }
                    ]
                },
                "elevator_info": {
                    "text": (
                        "'The Sector Transit Elevator is north beyond the Security Armory. "
                        "The blast door is sealed under heavy quarantine locks. You will need my [color=FFD700]Class-5 Keycard[/color] to open it. "
                        "Cure my Basilisk contamination, Sentinel, and the keycard is yours!'"
                    ),
                    "options": [
                        {
                            "label": "💉 [ADMINISTER NANITE MED-SPRAY]",
                            "target_node": "cured_reward",
                            "action": "cure_sorenson",
                            "bg_color": (0.15, 0.68, 0.38, 0.95)
                        },
                        {
                            "label": "🔙 [Back]",
                            "target_node": "root"
                        }
                    ]
                }
            }
        else:
            return {
                "root": {
                    "text": (
                        "[color=27AE60]Dr. Sorenson stands upright, his biometric HUD glowing calm azure.[/color]\n\n"
                        "[color=05B4D4]'Sentinel! My neural vitals are fully stabilized thanks to you. "
                        f"{'You possess my Class-5 Keycard.' if has_keycard else 'Here is my Class-5 Keycard.'} "
                        "Proceed north through the Armory and unlock the elevator blast door. The future of this station rests in your hands.'[/color]"
                    ),
                    "options": [
                        {
                            "label": "🛡️ 'Review tactical intel on the Reaper Combat Mech'",
                            "target_node": "reaper_intel",
                            "bg_color": (0.14, 0.18, 0.26, 0.95)
                        },
                        {
                            "label": "💊 'Request emergency chassis biogel repair'",
                            "target_node": "sorenson_meds",
                            "action": "heal_sorenson_supplies",
                            "bg_color": (0.18, 0.40, 0.30, 0.95)
                        },
                        {
                            "label": "🚀 'Understood, Doctor. Moving out.'",
                            "target_node": "CLOSE",
                            "bg_color": (0.15, 0.68, 0.38, 0.95)
                        }
                    ]
                },
                "reaper_intel": {
                    "text": (
                        "'The Reaper Combat Mech is a 4-legged military assault platform. "
                        "Its mass prevents normal knockback, and its plasma pulse cannons will vaporize light chassis in seconds. "
                        "Keep moving in circular vectors, use the elevator structural pillars for cover, and don't stay in its rail line!'"
                    ),
                    "options": [
                        {
                            "label": "🔙 [Understood]",
                            "target_node": "root"
                        }
                    ]
                },
                "sorenson_meds": {
                    "text": (
                        "[color=27AE60]Dr. Sorenson synthesizes a batch of high-potency dermal spray.\n\n"
                        "+35 Durability restored to your chassis! Neural stress reduced.[/color]"
                    ),
                    "options": [
                        {
                            "label": "🔙 [Back]",
                            "target_node": "root"
                        }
                    ]
                }
            }

    def _build_zephyr_tree(self) -> Dict[str, Any]:
        can_afford_augment = (self.player.xp >= 25 or self.player.nanocores >= 25)
        turret_hacked = (self.npc.dialogue_state == "turret_hacked")

        return {
            "root": {
                "text": (
                    "[color=05B4D4]A sleek Octomorph floats gracefully inside a zero-g harness, "
                    "eight cybernetic tentacles dancing across three translucent holo-windows.[/color]\n\n"
                    "[color=D980FA]'Yo, Firewall Sentinel! Nice moves evading those glitching husks. "
                    "I'm Zephyr—Rim-Scum autonomist and freelance mesh infiltrator. "
                    "I've tapped directly into this deck's sub-grid. You looking for an edge in this combat zone?'[/color]"
                ),
                "options": [
                    {
                        "label": "⚡ [GRID OVERRIDE] Slice the Station Defense Turrets to assist you" if not turret_hacked else "⚡ [GRID OVERRIDE] Turrets are currently slaved to your IFF! (Active)",
                        "target_node": "turrets_online" if not turret_hacked else "turrets_already",
                        "action": "zephyr_hack_turrets" if not turret_hacked else None,
                        "bg_color": (0.54, 0.36, 0.96, 0.95),
                        "txt_color": (1.0, 1.0, 1.0, 1.0)
                    },
                    {
                        "label": f"💎 [BLACK MARKET] Barter 25 Nanocores for an Immediate Augment Upgrade {'(AVAILABLE)' if can_afford_augment else '(INSUFFICIENT NANOCORES)'}",
                        "target_node": "augment_bartered" if can_afford_augment else "need_nanocores",
                        "action": "zephyr_barter_augment" if can_afford_augment else None,
                        "enabled": can_afford_augment,
                        "bg_color": (0.15, 0.68, 0.38, 0.95) if can_afford_augment else (0.2, 0.2, 0.2, 0.5)
                    },
                    {
                        "label": "💥 [EMP OVERLOAD] Discharge an EMP Shockwave across Central Promenade",
                        "target_node": "emp_discharged",
                        "action": "zephyr_emp_burst",
                        "bg_color": (0.85, 0.35, 0.95, 0.95)
                    },
                    {
                        "label": "💬 'Zephyr, what are the Scum doing on this hypercorp station?'",
                        "target_node": "zephyr_lore",
                        "bg_color": (0.14, 0.18, 0.26, 0.95)
                    },
                    {
                        "label": "🚪 [Step back] 'Keep your sensors sharp, Zephyr.'",
                        "target_node": "CLOSE",
                        "bg_color": (0.18, 0.20, 0.28, 0.9)
                    }
                ]
            },
            "turrets_online": {
                "text": (
                    "[color=27AE60]Zephyr's suction cups hammer into the sub-bus interface. "
                    "A cascade of glowing green cipher code floods the Promenade displays.[/color]\n\n"
                    "[color=D980FA]'Root access granted! I patched the automated defense turret into your tactical IFF. "
                    "For the next 90 seconds, that turret will incinerate any hostile that enters the Promenade. Enjoy the fireworks!'[/color]"
                ),
                "options": [
                    {
                        "label": "🔙 [Awesome, back to Zephyr]",
                        "target_node": "root"
                    }
                ]
            },
            "turrets_already": {
                "text": (
                    "[color=D980FA]'The turret is already slaved to your beacon, Sentinel! "
                    "Lure the infected into the center of Promenade and watch them get turned into slag.'[/color]"
                ),
                "options": [{"label": "🔙 [Back]", "target_node": "root"}]
            },
            "emp_discharged": {
                "text": (
                    "[color=05B4D4]A brilliant electric blue shockwave pulses through the floor grates! "
                    "Hostile electronics squeal and shudder under sudden EMP surge.[/color]\n\n"
                    "[color=D980FA]'Sub-capacitors dumped! All threats in the Promenade are stunned and heavily damaged. Finish them off!'[/color]"
                ),
                "options": [{"label": "🔙 [Back]", "target_node": "root"}]
            },
            "need_nanocores": {
                "text": (
                    "[color=D980FA]'Hey, transhuman capitalism might be dead in the Scum barges, "
                    "but raw nanocores don't grow on space trees. Slay some more Exsurgents and come back with 25 Nanocores!'[/color]"
                ),
                "options": [{"label": "🔙 [Back]", "target_node": "root"}]
            },
            "zephyr_lore": {
                "text": (
                    "'Hypercorps like Direct Action and Experia think they can cage TITAN tech and sell it as intellectual property. "
                    "Idiots. Our autonomous swarm was tracking suspicious telemetry transmissions. "
                    "When the station went dark, I slipped in through the outer radiator vents to see what went wrong. "
                    "Turns out: EVERYTHING went wrong. Let's make sure neither the TITANs nor the hypercorps bury the truth.'"
                ),
                "options": [{"label": "🔙 [Back to options]", "target_node": "root"}]
            }
        }

    def _build_clinic_tree(self) -> Dict[str, Any]:
        has_insurance = getattr(self.player, "has_stack_insurance", False)

        return {
            "root": {
                "text": (
                    "[color=05B4D4]A soothing biometric synth-voice resonates from the cryo-stasis speakers. "
                    "A soft emerald holographic caduceus pulses gently above the incubation vats.[/color]\n\n"
                    "[color=27AE60]'Welcome to Clinic Epsilon Automated Resleeving Facility.\n"
                    f"Transhuman Ego Verified: [[ {self.player.callsign} ]] | Morph: {self.player.morph_name.upper()}\n"
                    f"Chassis Durability: {int(self.player.hp)}/{int(self.player.max_hp)} HP | Stress: {int(self.player.stress)}/{int(self.player.max_stress)}[/color]\n\n"
                    "'All biological and synthetic growth chambers are operational. "
                    "How may Clinic Epsilon optimize your operational readiness?'"
                ),
                "options": [
                    {
                        "label": "🔄 [EMERGENCY RESLEEVE] Download Ego into a New Morph Chassis",
                        "target_node": "CLOSE",
                        "action": "clinic_resleeve",
                        "bg_color": (0.02, 0.71, 0.83, 0.95),
                        "txt_color": (0.05, 0.05, 0.08, 1.0)
                    },
                    {
                        "label": "🧪 [CELLULAR REPAIR] Full Chassis Nanite Repair & Psychosurgery (Restore 100% HP)",
                        "target_node": "repaired",
                        "action": "clinic_full_repair",
                        "bg_color": (0.15, 0.68, 0.38, 0.95),
                        "txt_color": (1.0, 1.0, 1.0, 1.0)
                    },
                    {
                        "label": "🧬 [STACK INSURANCE] Synchronize Cortical Stack Emergency Backup" if not has_insurance else "🧬 [STACK INSURANCE] Emergency Cloud Restore Active (Revive 1x on Fatal Damage)",
                        "target_node": "insurance_granted" if not has_insurance else "insurance_already",
                        "action": "clinic_insurance" if not has_insurance else None,
                        "bg_color": (0.85, 0.35, 0.95, 0.95) if not has_insurance else (0.2, 0.25, 0.32, 0.7)
                    },
                    {
                        "label": "🚪 [Step back] Disengage medical terminal",
                        "target_node": "CLOSE",
                        "bg_color": (0.18, 0.20, 0.28, 0.9)
                    }
                ]
            },
            "repaired": {
                "text": (
                    "[color=27AE60]'Administering pressurized biogel suspension and psychosurgical neural calming.\n\n"
                    "✓ Chassis structural integrity restored to 100% (HP Maxed).\n"
                    "✓ Cortical stack trauma purged. Lucidity restored.'[/color]"
                ),
                "options": [{"label": "🔙 [Return to Clinic Menu]", "target_node": "root"}]
            },
            "insurance_granted": {
                "text": (
                    "[color=27AE60]'Cortical stack quantum entanglement established with Clinic Epsilon server node.\n\n"
                    "Should your physical chassis suffer catastrophic destruction, an automated defibrillator burst "
                    "will immediately revive your core systems with 50% durability once per deck.'[/color]"
                ),
                "options": [{"label": "🔙 [Return to Clinic Menu]", "target_node": "root"}]
            },
            "insurance_already": {
                "text": (
                    "[color=05B4D4]'Your Cortical Stack backup beacon is already synchronized with Clinic Epsilon. "
                    "You are fully covered against sudden chassis destruction.'[/color]"
                ),
                "options": [{"label": "🔙 [Return to Clinic Menu]", "target_node": "root"}]
            }
        }
