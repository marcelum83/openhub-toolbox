"""
Eclipse Phase MUD - Core Game Engine
State machine, d100 skill checks, transhuman resleeving mechanics,
command processing, and LLM orchestration.
"""
import random
from typing import Dict, List, Optional, Callable, Tuple, Any
try:
    from models import Ego, Morph, Room, Item, NPC, TerminalNode, MORPH_CATALOG
    from world_gen import create_cassini_station, render_ascii_radar
    from llm_bridge import LLMBridge
except ImportError:
    from .models import Ego, Morph, Room, Item, NPC, TerminalNode, MORPH_CATALOG
    from .world_gen import create_cassini_station, render_ascii_radar
    from .llm_bridge import LLMBridge


class GameEngine:
    def __init__(self, host_api=None):
        self.host = host_api
        self.llm = LLMBridge(host_api=host_api)
        
        # State
        self.ego = Ego()
        self.morph = Morph.create("synthmorph")
        self.rooms: Dict[str, Room] = create_cassini_station()
        self.current_room_id = "airlock_1"
        self.inventory: List[Item] = []
        self.turn_count = 0
        self.is_game_over = False
        self.is_won = False
        
        # Event Callbacks
        self.log_callback: Optional[Callable[[str], None]] = None
        self.state_callback: Optional[Callable[[], None]] = None
        self.haptic_callback: Optional[Callable[[str], None]] = None
        self.ending_callback: Optional[Callable[[str, str], None]] = None
        self.tactical_breach_callback: Optional[Callable[[], None]] = None

        # Mark starting room visited
        self.get_current_room().visited = True

    def init_character(self, callsign: str, archetype_key: str, morph_key: str, muse_key: str):
        from models import ARCHETYPES, MUSE_PERSONAS, MORPH_CATALOG
        arch = ARCHETYPES.get(archetype_key, ARCHETYPES["sentinel"])
        muse_info = MUSE_PERSONAS.get(muse_key, MUSE_PERSONAS["mnemosyne"])
        
        self.ego.callsign = callsign or "Vagabond"
        self.ego.archetype = archetype_key
        self.ego.background = arch["name"]
        self.ego.muse_name = muse_info["name"]
        self.ego.muse_persona = muse_key
        self.ego.is_async = (archetype_key == "async")
        
        # Apply skill bonuses
        for skill, bonus in arch.get("bonuses", {}).items():
            if skill in self.ego.skills:
                self.ego.skills[skill] += bonus
        
        # Starting morph
        self.morph = Morph.create(morph_key)
        
        # Starting gear
        self.inventory = []
        item_id = arch.get("default_item")
        if item_id:
            item_map = {
                "shard_pistol": Item("shard_pistol", "Tactical Shard Pistol", "weapon", "Monomolecular diamond flechette pistol.", damage=16),
                "psi_baffle": Item("psi_baffle", "Faraday Psi-Baffle", "tool", "Mesh insert baffle that dampens alien cognitive frequencies.", heal_stress=5),
                "emp_grenade": Item("emp_grenade", "Micro-EMP Charge", "weapon", "Electromagnetic pulse cylinder devastating to synthetic frames.", damage=30),
                "neuro_stabilizer": Item("neuro_stabilizer", "Neuro-Chemical Stabilizer", "med", "Calms mental trauma and heals 15 Stress.", heal_stress=15)
            }
            if item_id in item_map:
                self.inventory.append(item_map[item_id])
                
        self.current_room_id = "airlock_1"
        self.rooms = create_cassini_station()
        self.get_current_room().visited = True
        self.is_game_over = False
        self.is_won = False
        self.turn_count = 0
        self.notify_state_change()

    def move_to_room_id(self, target_id: str) -> bool:
        cur = self.get_current_room()
        for d, r_id in cur.exits.items():
            if r_id == target_id:
                self._handle_move(d)
                self.notify_state_change()
                return True
        return False

    def get_current_room(self) -> Room:
        return self.rooms[self.current_room_id]

    def log(self, text: str):
        if self.log_callback:
            self.log_callback(text)

    def trigger_haptic(self, style: str = "light"):
        if self.haptic_callback:
            self.haptic_callback(style)
        elif self.host and hasattr(self.host, "hardware") and self.host.hardware:
            try:
                self.host.hardware.vibrate()
            except Exception:
                pass

    def notify_state_change(self):
        if self.state_callback:
            self.state_callback()

    # --- D100 Skill Check Engine (Eclipse Phase Rules) ---

    def roll_d100(self, skill_name: str, modifier: int = 0) -> Tuple[bool, bool, int, int]:
        """
        Rolls 1d100 against skill target number.
        Returns: (success: bool, is_critical: bool, roll: int, target: int)
        """
        target = self.ego.skills.get(skill_name, 50) + modifier
        roll = random.randint(1, 100)
        
        is_double = (roll % 11 == 0) or (roll == 100)
        success = roll <= target
        
        # Eclipse Phase doubles rule:
        # Doubles on roll <= target -> Critical Success
        # Doubles on roll > target -> Critical Failure
        # 99 and 00 (100) are always severe failures
        is_critical = is_double or (roll >= 99)
        
        return success, is_critical, roll, target

    # --- Start Game ---

    def start_game(self):
        self.log("[color=05B4D4][b]═══════════════════════════════════════════════[/b][/color]")
        self.log("[color=8A5CF5][b]🌌 ECLIPSE PHASE: THE CASSINI INCIDENT[/b][/color]")
        self.log("[color=707090]Location: Outpost Epsilon-9 | Saturnian Rings | Firewall Operation[/color]")
        self.log(f"[color=05B4D4]Ego: {self.ego.name} ({self.ego.callsign}) | Sleeve: {self.morph.name}[/color]")
        self.log("[color=05B4D4][b]═══════════════════════════════════════════════[/b][/color]")
        
        cur = self.get_current_room()
        self.log(f"[color=27AE60][b]LOCATION: {cur.title.upper()}[/b][/color]")
        self.log(f"[color=D0D5E5]{cur.description}[/color]")
        
        # Query Muse intro
        self.llm.query_muse_async(
            "Give initial mission briefing on arrival at Cassini Outpost Epsilon-9.",
            cur, self.ego, self.morph,
            lambda txt: self.log(f"[color=8A5CF5]◈ MUSE [{self.ego.muse_name}]: {txt}[/color]")
        )
        self.notify_state_change()

    # --- Command Processor ---

    def process_command(self, user_input: str):
        cmd = user_input.strip()
        if not cmd:
            return

        self.turn_count += 1
        self.log(f"[color=FFFFFF][b]> {cmd}[/b][/color]")
        
        lower = cmd.lower()
        tokens = lower.split()
        verb = tokens[0]
        args = tokens[1:]

        # 1. Navigation
        direction_aliases = {
            "n": "north", "north": "north",
            "s": "south", "south": "south",
            "e": "east", "east": "east",
            "w": "west", "west": "west",
            "u": "up", "up": "up",
            "d": "down", "down": "down"
        }

        if verb in ("go", "move", "walk", "run") and args:
            dir_target = direction_aliases.get(args[0], args[0])
            self._handle_move(dir_target)
        elif verb in direction_aliases:
            self._handle_move(direction_aliases[verb])
        
        # 2. Look / Inspect
        elif verb in ("look", "l"):
            self._handle_look()
        elif verb in ("examine", "x", "inspect") and args:
            self._handle_examine(" ".join(args))
            
        # 3. Inventory / Items
        elif verb in ("inv", "inventory", "i"):
            self._handle_inventory()
        elif verb in ("take", "get", "grab") and args:
            self._handle_take(" ".join(args))
        elif verb in ("drop", "discard") and args:
            self._handle_drop(" ".join(args))
        elif verb in ("use", "inject", "apply") and args:
            self._handle_use(" ".join(args))
            
        # 4. Hacking & Terminals
        elif verb in ("hack", "mesh", "interface") and args:
            self._handle_hack(" ".join(args))
        elif verb in ("scan", "ping", "radar"):
            self._handle_scan()
            
        # 5. Combat
        elif verb in ("attack", "fight", "shoot", "kill") and args:
            self._handle_attack(" ".join(args))
        elif verb in ("breach", "simulation"):
            if self.tactical_breach_callback:
                self.tactical_breach_callback()
            else:
                self.log("[color=E74C3C]Tactical breach interface unavailable in this terminal mode.[/color]")

            
        # 6. Dialogue
        elif verb in ("talk", "speak", "ask", "chat"):
            self._handle_dialogue(args)

        # 7. Item Giving
        elif verb in ("give", "offer", "hand") and args:
            self._handle_give(args)
            
        # 7. Muse
        elif verb in ("muse", "ai") and args:
            query = " ".join(args)
            self._handle_muse(query)
            
        # 8. Resleeving
        elif verb in ("resleeve", "clone", "vat"):
            target_sleeve = args[0] if args else "random"
            self._handle_resleeve(target_sleeve)

        # 9. Map / Radar
        elif verb in ("map",):
            radar = render_ascii_radar(self.rooms, self.current_room_id)
            self.log(f"[color=05B4D4][font=RobotoMono-Regular]{radar}[/font][/color]")

        # 10. Endings & Epilogues
        elif verb in ("ending", "resolve") and args:
            self.trigger_ending(args[0])

        # 11. Help
        elif verb in ("help", "commands", "?"):
            self._handle_help()

        # 12. Free-form Roleplay Action via LLM GM
        else:
            self._handle_freeform_action(cmd)

        self.notify_state_change()

    # --- Handlers ---

    def _handle_move(self, direction: str):
        cur = self.get_current_room()
        if direction not in cur.exits:
            self.log(f"[color=E74C3C]Bulkhead seal locked: No passage to the {direction}.[/color]")
            return

        target_room_id = cur.exits[direction]

        # Check locked exits
        if direction in cur.locked_exits:
            req_key = cur.locked_exits[direction]
            has_key = any(item.id == req_key for item in self.inventory)
            if not has_key:
                self.log(f"[color=E74C3C]Access Denied: The {direction} bulkhead requires '{req_key}' or an Infosec bypass.[/color]")
                self.trigger_haptic("medium")
                return
            else:
                self.log(f"[color=27AE60]Access Granted: Your {req_key} disengages the magnetic seals.[/color]")

        # Perform movement
        self.current_room_id = target_room_id
        new_room = self.get_current_room()
        new_room.visited = True
        self.trigger_haptic("light")

        self.log(f"\n[color=27AE60][b]» {new_room.title.upper()} ({new_room.sector})[/b][/color]")

        # Environmental hazards
        if new_room.hazard:
            self.log(f"[color=F39C12]⚠️ HAZARD DETECTED: {new_room.hazard}[/color]")
            if "Vacuum" in new_room.hazard and self.morph.morph_type != "synth":
                self.take_morph_damage(10, "Rapid decompression & hypoxia")
            if "Resonance" in new_room.hazard or "Exsurgent" in new_room.hazard:
                self.take_stress(8, "Psychic Basilisk frequency")

        # LLM GM Narrative
        self.llm.narrate_room_async(
            new_room, self.ego, self.morph,
            lambda narrative: self.log(f"[color=05B4D4]◈ GM: {narrative}[/color]")
        )

    def _handle_look(self):
        cur = self.get_current_room()
        self.log(f"\n[color=27AE60][b]LOCATION: {cur.title}[/b][/color]")
        self.log(f"[color=D0D5E5]{cur.description}[/color]")
        
        # Exits
        exits_str = ", ".join([f"[b]{k.upper()}[/b]" for k in cur.exits.keys()])
        self.log(f"[color=707090]Exits: {exits_str}[/color]")
        
        # Items
        if cur.items:
            item_names = ", ".join([f"[color=F39C12]{i.name}[/color]" for i in cur.items])
            self.log(f"Visible Gear: {item_names}")
            
        # NPCs
        alive_npcs = [n for n in cur.npcs if n.is_alive()]
        if alive_npcs:
            for n in alive_npcs:
                color = "E74C3C" if n.hostility == "hostile" else "8A5CF5"
                self.log(f"[color={color}]Entity: {n.name} ({n.morph_name}) - [{n.hostility.upper()}][/color]")
                
        # Terminal
        if cur.terminal:
            status = "[SECURED]" if not cur.terminal.is_hacked else "[HACKED / ONLINE]"
            self.log(f"[color=05B4D4]Mesh Terminal: {cur.terminal.name} {status}[/color]")

    def _handle_examine(self, target_name: str):
        cur = self.get_current_room()
        target_lower = target_name.lower()
        
        # Check items in inventory or room
        for item in self.inventory + cur.items:
            if target_lower in item.name.lower() or target_lower == item.id:
                self.log(f"[color=F39C12][b]{item.name}[/b][/color] ({item.item_type}): {item.description}")
                return
                
        # Check NPCs
        for npc in cur.npcs:
            if target_lower in npc.name.lower() or target_lower == npc.id:
                self.log(f"[color=8A5CF5][b]{npc.name}[/b][/color] ({npc.morph_name}): {npc.description}")
                return

        # Check Terminal
        if cur.terminal and target_lower in cur.terminal.name.lower():
            self.log(f"[color=05B4D4][b]{cur.terminal.name}[/b][/color]: Security Level {cur.terminal.security_level}. Requires 'hack' or Infosec credentials.")
            return

        self.log(f"[color=707090]Optical sensors cannot resolve '{target_name}'.[/color]")

    def _handle_take(self, item_name: str):
        cur = self.get_current_room()
        target = item_name.lower()
        for item in list(cur.items):
            if target in item.name.lower() or target == item.id:
                cur.items.remove(item)
                self.inventory.append(item)
                self.log(f"[color=27AE60]Acquired: {item.name}[/color]")
                self.trigger_haptic("light")
                return
        self.log(f"[color=E74C3C]Item '{item_name}' is not present in this chamber.[/color]")

    def _handle_drop(self, item_name: str):
        cur = self.get_current_room()
        target = item_name.lower()
        for item in list(self.inventory):
            if target in item.name.lower() or target == item.id:
                self.inventory.remove(item)
                cur.items.append(item)
                self.log(f"[color=F39C12]Disengaged from magnetic webbing: {item.name}[/color]")
                return
        self.log(f"[color=E74C3C]Item '{item_name}' is not in your sleeve inventory.[/color]")

    def _handle_use(self, item_name: str):
        cur = self.get_current_room()
        target = item_name.lower()

        # If in chamber with injured Dr. Sorenson and using medicine
        if any(n.id == "sorenson" and n.is_alive() for n in cur.npcs):
            if "spray" in target or "med" in target or "nanite" in target:
                self._handle_give(["nanite_spray", "to", "sorenson"])
                return

        for item in list(self.inventory):
            if target in item.name.lower() or target == item.id:
                if item.heal_hp > 0:
                    old_hp = self.morph.durability
                    self.morph.durability = min(self.morph.max_durability, self.morph.durability + item.heal_hp)
                    self.log(f"[color=27AE60]Applied {item.name}: Repaired {self.morph.durability - old_hp} Durability.[/color]")
                    self.inventory.remove(item)
                    self.trigger_haptic("light")
                    return
                elif item.heal_stress > 0:
                    old_stress = self.ego.stress
                    self.ego.stress = max(0, self.ego.stress - item.heal_stress)
                    self.log(f"[color=8A5CF5]Synthesized {item.name}: Neural calm restored. Reduced {old_stress - self.ego.stress} Stress.[/color]")
                    self.inventory.remove(item)
                    return
                else:
                    self.log(f"[color=707090]{item.name} cannot be consumed directly. Use in combat or hacking.[/color]")
                    return
        self.log(f"[color=E74C3C]You do not possess '{item_name}'.[/color]")

    def _handle_inventory(self):
        if not self.inventory:
            self.log("[color=707090]Your sleeve inventory is currently empty.[/color]")
            return
        self.log("[color=F39C12][b]--- SLEEVE INVENTORY ---[/b][/color]")
        for i, item in enumerate(self.inventory, 1):
            stats = f" [DMG: {item.damage}]" if item.damage else ""
            stats += f" [HEAL: {item.heal_hp}]" if item.heal_hp else ""
            self.log(f"{i}. [color=FFFFFF]{item.name}[/color] ({item.item_type}){stats}")

    def _handle_hack(self, target_name: str):
        cur = self.get_current_room()
        terminal = cur.terminal
        if not terminal:
            self.log("[color=E74C3C]No mesh terminal node found in this chamber.[/color]")
            return

        success, is_crit, roll, target = self.roll_d100("Infosec", modifier=-(terminal.security_level * 5))
        roll_desc = f"Rolled {roll} vs TN {target}"
        if is_crit:
            roll_desc += " [b](CRITICAL!)[/b]"

        if success:
            terminal.is_hacked = True
            self.log(f"[color=27AE60]⚡ MESH INTRUSION SUCCESSFUL: {roll_desc}[/color]")
            self.log(f"[color=05B4D4]Decrypted Node [{terminal.name}]:\n'{terminal.log_content}'[/color]")
            self.trigger_haptic("medium")

            # Check special terminal win condition
            if terminal.id == "term_needlecast":
                self.log("\n[color=05B4D4][b]═══════════════════════════════════════════════[/b][/color]")
                self.log("[color=27AE60][b]⚡ NEEDLECAST ARRAY RECEPTIVE: CHOOSE MISSION RESOLUTION[/b][/color]")
                self.log("• [color=E74C3C][b]ending purge[/b][/color]     - Firewall Protocol Omega (Orbital De-orbit into Saturn)")
                self.log("• [color=F39C12][b]ending hypercorp[/b][/color] - Sell TITAN nanites to Hypercorp Syndicate")
                self.log("• [color=8A5CF5][b]ending gatecrash[/b][/color] - Step into the active Pandora Gate to extrasolar world")
                self.log("• [color=05B4D4][b]ending infomorph[/b][/color] - Ascend ego into interplanetary Mesh as digital ghost")
                self.log("[color=05B4D4][b]═══════════════════════════════════════════════[/b][/color]")
        else:
            self.log(f"[color=E74C3C]⚠️ MESH INTRUSION FAILED: {roll_desc}[/color]")
            self.take_stress(5, "Firewall ICE counter-attack")
            self.trigger_haptic("heavy")

    def trigger_ending(self, ending_key: str):
        from models import ENDINGS
        if ending_key not in ENDINGS:
            self.log(f"[color=E74C3C]Unknown resolution protocol '{ending_key}'. Valid choices: purge, hypercorp, gatecrash, infomorph[/color]")
            return

        info = ENDINGS[ending_key]
        self.is_won = True
        self.log(f"\n[color=05B4D4][b]═══════════════════════════════════════════════[/b][/color]")
        self.log(f"[color=27AE60][b]🌟 EPILOGUE RESOLUTION: {info['title']}[/b][/color]")
        self.log(f"[color=D0D5E5]{info['summary']}[/color]")
        self.trigger_haptic("heavy")

        def _on_epilogue(narrative_text: str):
            self.log(f"\n[color=05B4D4]◈ GM EPILOGUE CHRONICLE:\n{narrative_text}[/color]")
            self.log("[color=05B4D4][b]═══════════════════════════════════════════════[/b][/color]")
            if self.ending_callback:
                self.ending_callback(ending_key, narrative_text)
            self.notify_state_change()

        self.llm.narrate_ending_async(ending_key, self.ego, self.morph, _on_epilogue)

    def _handle_scan(self):
        cur = self.get_current_room()
        radar = render_ascii_radar(self.rooms, self.current_room_id)
        self.log("[color=05B4D4][b]--- TACTICAL RADAR SWEEP ---[/b][/color]")
        self.log(f"[color=05B4D4]{radar}[/color]")
        self.llm.query_muse_async(
            "Scan adjacent rooms and highlight lifeforms or anomalous signals.",
            cur, self.ego, self.morph,
            lambda txt: self.log(f"[color=8A5CF5]◈ MUSE RADAR ANALYSIS: {txt}[/color]")
        )

    def _handle_attack(self, target_name: str):
        cur = self.get_current_room()
        target_lower = target_name.lower()
        npc = None
        for n in cur.npcs:
            if n.is_alive() and (target_lower in n.name.lower() or target_lower == n.id):
                npc = n
                break

        if not npc:
            self.log(f"[color=E74C3C]No hostile entity matching '{target_name}' in range.[/color]")
            return

        # Player Attack
        weapon = next((i for i in self.inventory if i.damage > 0), None)
        base_dmg = weapon.damage if weapon else 8
        wpn_name = weapon.name if weapon else "Synthetic Unarmed Blow"

        success, is_crit, roll, target = self.roll_d100("Guns" if weapon else "Athletics")
        roll_desc = f"Rolled {roll} vs TN {target}"

        if success:
            crit_mult = 1.5 if is_crit else 1.0
            raw_dmg = int((base_dmg + random.randint(2, 8)) * crit_mult)
            actual_dmg = max(1, raw_dmg - npc.armor)
            npc.hp = max(0, npc.hp - actual_dmg)
            self.log(f"[color=27AE60]⚔️ HIT on {npc.name}! {wpn_name} deals {actual_dmg} kinetic damage! ({roll_desc})[/color]")
            self.trigger_haptic("medium")

            if not npc.is_alive():
                self.log(f"[color=27AE60]💀 TARGET DESTROYED: {npc.name} collapses in sparks and bio-sludge.[/color]")
                if npc.inventory:
                    cur.items.extend(npc.inventory)
                    self.log(f"[color=F39C12]Dropped gear: {', '.join([i.name for i in npc.inventory])}[/color]")
                return
        else:
            self.log(f"[color=E74C3C]MISS! Your attack on {npc.name} deflected off the bulkheads ({roll_desc}).[/color]")

        # NPC Counter-attack
        if npc.is_alive():
            c_success, _, _, _ = self.roll_d100("Fray")  # Player dodges?
            if not c_success:
                npc_dmg = max(2, random.randint(8, 16) - self.morph.armor_kinetic)
                self.take_morph_damage(npc_dmg, f"Counter-strike from {npc.name}")
            else:
                self.log(f"[color=27AE60]🛡️ Reflexes triggered: You evade {npc.name}'s return strike.[/color]")

    def _handle_dialogue(self, args: List[str]):
        cur = self.get_current_room()
        cleaned_args = list(args)
        if cleaned_args and cleaned_args[0].lower() in ("to", "with", "at"):
            cleaned_args.pop(0)

        alive_npcs = [n for n in cur.npcs if n.is_alive()]
        target_npc = None
        msg_start_idx = 0

        # 1. Try to find target NPC from args
        if cleaned_args:
            # Check 2-word name first (e.g. "dr sorenson", "unit 9")
            if len(cleaned_args) >= 2:
                two_words = f"{cleaned_args[0]} {cleaned_args[1]}".lower().replace(".", "")
                for n in alive_npcs:
                    if two_words in n.name.lower().replace(".", "") or two_words in n.id:
                        target_npc = n
                        msg_start_idx = 2
                        break

            # Check 1-word name (e.g. "sorenson", "dr", "zephyr", "reaper")
            if not target_npc and len(cleaned_args) >= 1:
                first_word = cleaned_args[0].lower().replace(".", "")
                for n in alive_npcs:
                    n_parts = [p.lower().replace(".", "") for p in n.name.split()]
                    if first_word in n_parts or first_word == n.id or first_word in n.name.lower():
                        target_npc = n
                        msg_start_idx = 1
                        break

        # 2. If no target specified, but exactly 1 alive NPC in this chamber
        if not target_npc and len(alive_npcs) == 1:
            target_npc = alive_npcs[0]
            msg_start_idx = 0

        # 3. If still not found, check if player asked for an NPC in another room!
        if not target_npc:
            all_station_npcs = [n for r in self.rooms.values() for n in r.npcs if n.is_alive()]
            query_str = " ".join(args).lower().replace(".", "")
            found_remote = None
            for n in all_station_npcs:
                n_clean = n.name.lower().replace(".", "")
                if any(part in query_str for part in n_clean.split()) or n.id in query_str:
                    found_remote = n
                    break

            if found_remote:
                remote_room = next((r for r in self.rooms.values() if found_remote in r.npcs), None)
                loc_name = remote_room.title if remote_room else "another sector"
                sec_name = remote_room.sector if remote_room else ""
                self.log(f"[color=F39C12]🛰️ Bio-Telemetry: {found_remote.name} is not in this chamber.[/color]")
                self.log(f"[color=D5DDF0]They are located in the [b]{loc_name}[/b] ({sec_name}).[/color]")
                if found_remote.id == "sorenson":
                    self.log("[color=05B4D4]Navigation Route: North (Promenade) -> North (Clinic) -> East (Hydroponics) -> North (Bio-Incubator).[/color]")
                    self.log("[color=05B4D4]Tip: You can also tap the [🗺️ RADAR] button and tap the glowing nodes to move there![/color]")
            else:
                if not alive_npcs:
                    self.log("[color=E74C3C]There is nobody in this chamber to converse with.[/color]")
                else:
                    self.log(f"[color=E74C3C]Could not identify who to talk to. Present entities: {', '.join([n.name for n in alive_npcs])}[/color]")
            return

        # Prepare message
        remaining = cleaned_args[msg_start_idx:]
        if remaining and remaining[0].lower() in ("about", "for"):
            remaining.pop(0)

        player_msg = " ".join(remaining) if remaining else "Status report? What happened here?"
        self._handle_talk_direct(target_npc, player_msg)

    def _handle_talk_direct(self, npc: NPC, player_msg: str):
        cur = self.get_current_room()
        self.log(f"[color=FFFFFF]You to {npc.name}: '{player_msg}'[/color]")

        # Special narrative interactions
        lower = player_msg.lower()
        if npc.id == "sorenson":
            has_med = any(i.id == "nanite_spray" for i in self.inventory)
            has_key = any(i.id == "quarantine_keycard" for i in self.inventory)

            if ("key" in lower or "card" in lower or "door" in lower or "quarantine" in lower or "help" in lower or "heal" in lower or "cure" in lower or "med" in lower or "spray" in lower) and not has_key:
                if has_med:
                    self.log(f"[color=8A5CF5]{npc.name}: 'You have Nanite Med-Spray! Please, inject me with the cellular repair nanites and I will hand over my Class-5 Quarantine Keycard!'[/color]")
                    self.log("[color=27AE60]Tip: Type 'give nanite_spray to sorenson' or 'use nanite_spray' to administer the medical spray.[/color]")
                    return
                else:
                    self.log(f"[color=8A5CF5]{npc.name}: 'The Basilisk hack is burning my neural stack... I can't think clearly! If you bring me Nanite Med-Spray from the clinic or airlock, I will give you my Class-5 Quarantine Keycard to unlock Sector 4.'[/color]")
                    return

        # General LLM dialogue
        self.llm.chat_npc_async(
            npc, player_msg, cur, self.ego, self.morph,
            lambda reply: self.log(f"[color=8A5CF5]{npc.name}: '{reply}'[/color]")
        )

    def _handle_give(self, args: List[str]):
        cur = self.get_current_room()
        alive_npcs = [n for n in cur.npcs if n.is_alive()]
        if not alive_npcs:
            self.log("[color=E74C3C]Nobody here to give items to.[/color]")
            return

        text = " ".join(args).lower()
        target_npc = alive_npcs[0]
        for n in alive_npcs:
            if n.name.lower() in text or n.id in text or "sorenson" in text:
                target_npc = n
                break

        item_to_give = None
        for item in list(self.inventory):
            if item.id in text or item.name.lower() in text:
                item_to_give = item
                break

        if not item_to_give:
            for item in list(self.inventory):
                if "med" in text or "spray" in text or "nanite" in text:
                    if item.id == "nanite_spray":
                        item_to_give = item
                        break

        if not item_to_give:
            self.log("[color=E74C3C]You do not possess that item in your sleeve inventory.[/color]")
            return

        self.inventory.remove(item_to_give)
        self.log(f"[color=27AE60]You hand the {item_to_give.name} to {target_npc.name}.[/color]")

        if target_npc.id == "sorenson" and item_to_give.id == "nanite_spray":
            target_npc.hp = target_npc.max_hp
            self.log("[color=27AE60]💉 Dr. Sorenson presses the nanite spray to his throat. His shivering ceases as cellular stabilizers suppress the Basilisk infection.[/color]")
            keycard = next((i for i in target_npc.inventory if i.id == "quarantine_keycard"), None)
            if keycard:
                target_npc.inventory.remove(keycard)
                self.inventory.append(keycard)
                self.log(f"[color=05B4D4][b]🔑 KEYCARD ACQUIRED: Dr. Sorenson hands you the {keycard.name}![/b][/color]")
                self.log(f"[color=8A5CF5]Dr. Sorenson: 'Thank you, Sentinel. Take my Class-5 pass. The Quarantine blast door to Sector 4 is unlocked.'[/color]")
                self.trigger_haptic("medium")
                self.notify_state_change()
                return

        target_npc.inventory.append(item_to_give)
        self.log(f"[color=8A5CF5]{target_npc.name}: 'Thank you, Sentinel. Every resource counts out here.'[/color]")

    def _handle_muse(self, query: str):
        cur = self.get_current_room()
        self.log(f"[color=8A5CF5]Querying personal Muse: '{query}'...[/color]")
        self.llm.query_muse_async(
            query, cur, self.ego, self.morph,
            lambda reply: self.log(f"[color=8A5CF5]◈ {self.ego.muse_name}: {reply}[/color]")
        )

    def _handle_resleeve(self, target_key: str):
        cur = self.get_current_room()
        if "clinic" not in cur.id:
            self.log("[color=E74C3C]Resleeving can only be initiated at an authorized automated Resleeving Clinic.[/color]")
            return

        if target_key not in MORPH_CATALOG:
            target_key = random.choice(list(MORPH_CATALOG.keys()))

        self.log(f"[color=05B4D4]Initiating Ego-Needlecast into {MORPH_CATALOG[target_key]['name']}...[/color]")
        self.morph = Morph.create(target_key)
        self.ego.resleeve_count += 1
        self.take_stress(6, "Resleeving Alienation & Phantom Limb Distortion")
        self.log(f"[color=27AE60]Transfer Complete! You awaken in your new {self.morph.name}.[/color]")
        self.trigger_haptic("heavy")

    def _handle_freeform_action(self, action_text: str):
        cur = self.get_current_room()
        self.log(f"[color=707090]Adjudicating freeform action with GM...[/color]")
        
        def _apply_adjudication(res: Dict[str, Any]):
            skill = res.get("skill_tested", "Athletics")
            narration = res.get("narration", "You proceed with the action.")
            tn = res.get("target_number", 50)
            
            if skill and skill.lower() != "none":
                success, is_crit, roll, _ = self.roll_d100(skill)
                roll_tag = f"[{skill} Check: Rolled {roll} vs TN {tn} -> {'SUCCESS' if success else 'FAILURE'}]"
                self.log(f"[color=F39C12]{roll_tag}[/color]")
            
            self.log(f"[color=05B4D4]◈ GM: {narration}[/color]")
            
            if res.get("hp_damage", 0) > 0:
                self.take_morph_damage(res["hp_damage"], "Environmental impact")
            if res.get("stress_damage", 0) > 0:
                self.take_stress(res["stress_damage"], "Cognitive trauma")
            self.notify_state_change()

        self.llm.adjudicate_action_async(action_text, cur, self.ego, self.morph, _apply_adjudication)

    # --- Damage & Permadeath / Resleeving ---

    def take_morph_damage(self, amount: int, source: str):
        self.morph.durability = max(0, self.morph.durability - amount)
        self.log(f"[color=E74C3C]⚡ IMPACT: {source} causes {amount} damage! (Morph Durability: {self.morph.durability}/{self.morph.max_durability})[/color]")
        self.trigger_haptic("medium")

        if self.morph.durability <= 0:
            self._handle_morph_death(source)

    def _handle_morph_death(self, source: str):
        self.log(f"\n[color=E74C3C][b]💥 MORPH DESTRUCTION: Your {self.morph.name} has suffered catastrophic structural failure ({source}).[/b][/color]")
        self.trigger_haptic("heavy")
        
        # Cortical Stack Recovery Check
        self.log("[color=8A5CF5]◈ MUSE: Cortical stack backup broadcast initiated... Transmitting ego stream to Clinic Epsilon.[/color]")
        
        # Alienation & Stress
        self.ego.resleeve_count += 1
        self.take_stress(12, "Traumatic Sleeve Demise")
        
        # Wake up at clinic in random available sleeve
        available_morphs = ["synthmorph", "splicer", "olympian", "flat"]
        new_key = random.choice(available_morphs)
        self.morph = Morph.create(new_key)
        self.current_room_id = "clinic"
        self.get_current_room().visited = True
        
        self.log(f"[color=27AE60][b]🔄 RESLEEVING SUCCESS: Your ego has been restored into a {self.morph.name} at Resleeving Clinic Epsilon.[/b][/color]")
        self.notify_state_change()

    def take_stress(self, amount: int, reason: str):
        self.ego.stress += amount
        self.log(f"[color=8A5CF5]🧠 PSYCHOLOGICAL STRESS: +{amount} ({reason}). Total Stress: {self.ego.stress}/{self.ego.lucidity}[/color]")
        
        if self.ego.stress >= self.ego.lucidity:
            self.ego.trauma += 1
            self.ego.stress = max(0, self.ego.stress - self.ego.lucidity)
            self.ego.lucidity = max(10, self.ego.lucidity - 2)
            self.log(f"[color=E74C3C][b]⚡ PSYCHIC TRAUMA TRIGGERED: Trauma Count {self.ego.trauma}! Reality fractures around your sensory buffer.[/b][/color]")
            self.trigger_haptic("heavy")

    def _handle_help(self):
        self.log("[color=05B4D4][b]--- COMMAND DIRECTORY ---[/b][/color]")
        self.log("• [b]Movement[/b]: n, s, e, w, or go <direction>")
        self.log("• [b]Sensors[/b]: look, examine <target>, scan, map")
        self.log("• [b]Inventory[/b]: inv, take <item>, drop <item>, use <item>")
        self.log("• [b]Combat & Mesh[/b]: attack <target>, hack <node>")
        self.log("• [b]Social & AI[/b]: talk <npc> <message>, muse <question>")
        self.log("• [b]Transhuman[/b]: resleeve <sleeve_type> (at clinic)")
        self.log("• [b]Free-form[/b]: Type any action (e.g. 'I bypass the lock with my nanites') to have the GM adjudicate!")
