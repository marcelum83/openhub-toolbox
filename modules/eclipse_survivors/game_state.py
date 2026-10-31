"""
Eclipse Survivors - Core Game State & Action Roguelite Systems
Dungeon-style station floor exploration, persistent room layouts, sliding doors,
room clearance objectives, Keycard gating, Floor Completion, and Deck Transit.
"""
import math
import random
import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable, Set

# --- Sleeve Morph Catalog (Eclipse Phase Bodily Chassis) ---
MORPH_CATALOG = {
    "synth": {
        "name": "Synth Chassis",
        "tagline": "Industrial Zero-G Robotic Frame",
        "icon": "🤖",
        "hp": 140.0,
        "speed": 120.0,
        "armor": 3.5,
        "pickup_radius": 65.0,
        "cooldown_mult": 1.0,
        "starting_weapons": {"emp_shock": 1, "titanium_chassis": 1},
        "color": (0.95, 0.45, 0.15, 1.0)
    },
    "fury": {
        "name": "Fury Biomorph",
        "tagline": "Predatory Transgenic Combat Chassis",
        "icon": "🐆",
        "hp": 110.0,
        "speed": 150.0,
        "armor": 2.0,
        "pickup_radius": 70.0,
        "cooldown_mult": 0.95,
        "starting_weapons": {"nanite_aura": 1, "myomer_overclock": 1},
        "color": (0.75, 0.25, 0.90, 1.0)
    },
    "menton": {
        "name": "Menton Cognitive Morph",
        "tagline": "Neural-Overclocked Cybernetic Brain",
        "icon": "🧠",
        "hp": 90.0,
        "speed": 130.0,
        "armor": 1.5,
        "pickup_radius": 115.0,
        "cooldown_mult": 0.80,
        "starting_weapons": {"seeker_drone": 1, "nanite_harvester": 1},
        "color": (0.02, 0.71, 0.83, 1.0)
    },
    "ghost": {
        "name": "Ghost Infiltrator",
        "tagline": "High-Agility Covert Reconnaissance Chassis",
        "icon": "👤",
        "hp": 95.0,
        "speed": 165.0,
        "armor": 1.0,
        "pickup_radius": 65.0,
        "cooldown_mult": 0.90,
        "starting_weapons": {"shard_pistol": 1, "rapid_synapse": 1},
        "color": (0.2, 0.95, 0.65, 1.0)
    }
}

# --- Upgrades & Implants Catalog ---
UPGRADE_CATALOG = {
    # Base Weapons
    "shard_pistol": {
        "name": "Shard Flechette Pistol",
        "type": "weapon",
        "description": "Auto-targeting flechette gun firing diamond shards at nearest threat.",
        "icon": "⚡",
        "max_level": 5,
        "evolution": "evo_diamond_hailstorm"
    },
    "seeker_drone": {
        "name": "Orbital Seeker Drone",
        "type": "weapon",
        "description": "Companion micro-drone orbiting your sleeve and firing laser pulses.",
        "icon": "🛸",
        "max_level": 5,
        "evolution": "evo_apex_swarm"
    },
    "nanite_aura": {
        "name": "Nanite Defense Cloud",
        "type": "weapon",
        "description": "Swirling nanite aura that corrodes adjacent enemies and slowly heals sleeve.",
        "icon": "🧪",
        "max_level": 5,
        "evolution": "evo_grey_goo"
    },
    "emp_shock": {
        "name": "EMP Pulse Emitter",
        "type": "weapon",
        "description": "Periodic expanding electrical shockwave that stuns and repels hostiles.",
        "icon": "💥",
        "max_level": 5,
        "evolution": "evo_emp_cataclysm"
    },
    "railgun_beam": {
        "name": "Linear Railgun Pylon",
        "type": "weapon",
        "description": "Penetrating high-velocity linear beam cutting through rows of enemies.",
        "icon": "☄️",
        "max_level": 5,
        "evolution": "evo_tachyon_lance"
    },

    # Passives
    "titanium_chassis": {
        "name": "Titanium Composite Plating",
        "type": "passive",
        "description": "+25 Max Durability (HP) and passive damage reduction.",
        "icon": "🛡️",
        "max_level": 5
    },
    "myomer_overclock": {
        "name": "Myomer Muscle Overclock",
        "type": "passive",
        "description": "+15% Movement speed and rapid directional acceleration.",
        "icon": "🏃",
        "max_level": 5
    },
    "nanite_harvester": {
        "name": "Magnetic Nanite Harvester",
        "type": "passive",
        "description": "+40% XP Nanocore pickup suction radius.",
        "icon": "🧲",
        "max_level": 5
    },
    "rapid_synapse": {
        "name": "Rapid Synapse Accelerator",
        "type": "passive",
        "description": "-15% Weapon cooldowns across all equipped cybernetics.",
        "icon": "🧠",
        "max_level": 5
    },

    # --- Cybernetic Evolutions (Legendary Tier) ---
    "evo_diamond_hailstorm": {
        "name": "Diamond Hailstorm",
        "type": "evolution",
        "base_weapon": "shard_pistol",
        "required_passive": "titanium_chassis",
        "description": "Continuous 360° storm of 8 ricocheting hyper-dense diamond flechettes.",
        "icon": "💎",
        "max_level": 1
    },
    "evo_grey_goo": {
        "name": "Grey Goo Singularity",
        "type": "evolution",
        "base_weapon": "nanite_aura",
        "required_passive": "rapid_synapse",
        "description": "Massive sub-molecular nanite vortex consuming organic matter, repairing sleeve HP and triggering XP nanocore bursts.",
        "icon": "🦠",
        "max_level": 1
    },
    "evo_tachyon_lance": {
        "name": "Tachyon Relativistic Lance",
        "type": "evolution",
        "base_weapon": "railgun_beam",
        "required_passive": "myomer_overclock",
        "description": "Infinite-penetration relativistic plasma beam incinerating everything across entire station wings.",
        "icon": "☄️⚡",
        "max_level": 1
    },
    "evo_apex_swarm": {
        "name": "Apex Swarm Matrix",
        "type": "evolution",
        "base_weapon": "seeker_drone",
        "required_passive": "nanite_harvester",
        "description": "Tri-drone constellation firing triangulated laser containment nets and auto-vacuuming all nanocores.",
        "icon": "🛸⚡",
        "max_level": 1
    },
    "evo_emp_cataclysm": {
        "name": "Neuro-Cascade Cataclysm",
        "type": "evolution",
        "base_weapon": "emp_shock",
        "required_passive": "rapid_synapse",
        "description": "Dual-ring catastrophic EMP shockwave with chain lightning arcing between all stunned hostiles.",
        "icon": "💥⚡",
        "max_level": 1
    }
}


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    radius: float = 4.0
    lifetime: float = 1.2
    penetration: int = 1
    color: Tuple[float, float, float, float] = (0.02, 0.9, 1.0, 1.0)
    is_ricochet: bool = False
    trail: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class XPCore:
    x: float
    y: float
    value: int = 10
    radius: float = 5.0
    color: Tuple[float, float, float, float] = (0.2, 0.95, 0.65, 1.0)
    vx: float = 0.0
    vy: float = 0.0


@dataclass
class KeycardPickup:
    x: float
    y: float
    radius: float = 14.0
    collected: bool = False


@dataclass
class SupplyCrate:
    x: float
    y: float
    w: float = 28.0
    h: float = 28.0
    hp: float = 20.0
    is_broken: bool = False


@dataclass
class Wall:
    x: float
    y: float
    w: float
    h: float


@dataclass
class StationDoor:
    id: str
    x: float
    y: float
    w: float
    h: float
    is_vertical: bool = False
    is_open: bool = False
    is_locked: bool = False
    lock_reason: str = ""
    open_progress: float = 0.0  # 0.0 = closed, 1.0 = fully open


@dataclass
class StationRoom:
    id: str
    name: str
    x1: float
    y1: float
    x2: float
    y2: float
    is_discovered: bool = False
    is_cleared: bool = False
    initial_enemy_count: int = 0


@dataclass
class StationTerminal:
    id: str
    name: str
    x: float
    y: float
    terminal_type: str  # "gas_vent", "defense_turret", "emp_beacon", "elevator_console"
    radius: float = 28.0
    cooldown: float = 25.0
    timer: float = 0.0
    is_active: bool = False
    active_timer: float = 0.0
    active_duration: float = 10.0
    hack_progress: float = 0.0
    is_used_once: bool = False


@dataclass
class StationNPC:
    id: str
    name: str
    title: str
    x: float
    y: float
    room_id: str
    icon: str = "👨‍🔬"
    radius: float = 22.0
    color: Tuple[float, float, float, float] = (0.2, 0.95, 0.65, 1.0)
    dialogue_state: str = "initial"



@dataclass
class Enemy:
    id_name: str
    x: float
    y: float
    hp: float
    max_hp: float
    speed: float
    radius: float
    damage: float
    xp_reward: int
    color: Tuple[float, float, float, float]
    is_boss: bool = False
    is_captain: bool = False
    stun_timer: float = 0.0
    home_room_id: str = ""

    # Aggro & AI state machine
    state: str = "idle"         # "idle", "patrol", "alert", "chase", "search"
    facing_angle: float = 0.0   # Degrees (0-360)
    alert_timer: float = 0.0    # Visual '!' alert icon timer
    search_timer: float = 0.0   # Search time at last known position
    patrol_timer: float = 0.0   # Interval before choosing new patrol destination
    patrol_target_x: float = 0.0
    patrol_target_y: float = 0.0
    last_known_x: float = 0.0
    last_known_y: float = 0.0
    aggro_range: float = 400.0  # Visual acquisition range
    hearing_range: float = 340.0# Audio detection range

    def is_alive(self) -> bool:
        return self.hp > 0


class Player:
    def __init__(self, x: float = 0.0, y: float = -820.0, morph_id: str = "synth"):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = 14.0
        self.facing_angle = 90.0  # Degrees (90 = North)
        self.morph_id = morph_id

        # Morph stats
        morph = MORPH_CATALOG.get(morph_id, MORPH_CATALOG["synth"])
        self.morph_name = morph["name"]
        self.max_hp = morph["hp"]
        self.hp = self.max_hp
        self.speed = morph["speed"]
        self.armor = morph["armor"]
        self.pickup_radius = morph["pickup_radius"]
        self.cooldown_mult = morph["cooldown_mult"]

        # Transhuman Ego & Biometrics (Unified MUD / Survivors)
        self.callsign = "Vagabond"
        self.archetype = "sentinel"
        self.muse_name = "Athena"
        self.muse_persona = "athena"
        self.stress = 0.0
        self.max_stress = 34.0
        self.nanocores = 25

        # Progression
        self.level = 1
        self.xp = 0
        self.xp_to_next = 35
        self.kills = 0

        # Floor Objectives
        self.has_keycard = False
        self.has_stack_insurance = False
        self.current_room_id = "airlock"

        # Inventory (id: level)
        self.inventory: Dict[str, int] = dict(morph["starting_weapons"])

        # Weapon Timers
        self.weapon_timers: Dict[str, float] = {
            "shard_pistol": 0.0,
            "seeker_drone": 0.0,
            "nanite_aura": 0.0,
            "emp_shock": 0.0,
            "railgun_beam": 0.0,
            "evo_diamond_hailstorm": 0.0,
            "evo_grey_goo": 0.0,
            "evo_tachyon_lance": 0.0,
            "evo_apex_swarm": 0.0,
            "evo_emp_cataclysm": 0.0
        }

        self.drone_angle = 0.0

    def resleeve_morph(self, new_morph_id: str):
        """Swaps the physical transhuman chassis mid-run while preserving Ego level and progression."""
        morph = MORPH_CATALOG.get(new_morph_id, MORPH_CATALOG["synth"])
        self.morph_id = new_morph_id
        self.morph_name = morph["name"]

        # Preserve HP ratio or restore healthy threshold
        hp_pct = max(0.4, self.hp / self.max_hp) if self.max_hp > 0 else 1.0
        self.max_hp = morph["hp"]
        self.hp = min(self.max_hp, self.max_hp * hp_pct)
        self.speed = morph["speed"]
        self.armor = morph["armor"]
        self.pickup_radius = morph["pickup_radius"]
        self.cooldown_mult = morph["cooldown_mult"]

        # Grant new morph starting weapon if not already possessed
        for w_id, w_lvl in morph["starting_weapons"].items():
            if w_id not in self.inventory:
                self.inventory[w_id] = w_lvl

    def apply_upgrade(self, upgrade_id: str):
        current_lvl = self.inventory.get(upgrade_id, 0)
        self.inventory[upgrade_id] = current_lvl + 1

        if upgrade_id == "titanium_chassis":
            self.max_hp += 25.0
            self.hp = min(self.max_hp, self.hp + 25.0)
            self.armor += 1.5
        elif upgrade_id == "myomer_overclock":
            self.speed *= 1.12
        elif upgrade_id == "nanite_harvester":
            self.pickup_radius += 30.0
        elif upgrade_id == "rapid_synapse":
            self.cooldown_mult *= 0.88


class StationMap:
    """Represents a large station deck floor with distinct rooms, doors, crates, terminals, and NPCs."""
    def __init__(self, deck_level: int = 1):
        self.deck_level = deck_level
        self.width = 2400.0
        self.height = 2000.0
        self.walls: List[Wall] = []
        self.doors: List[StationDoor] = []
        self.rooms: List[StationRoom] = []
        self.crates: List[SupplyCrate] = []
        self.terminals: List[StationTerminal] = []
        self.npcs: List[StationNPC] = []
        self.elevator_terminal: Optional[StationTerminal] = None

        self.waypoint_nodes: Dict[str, Tuple[float, float]] = {}
        self.waypoint_adj: Dict[str, List[Tuple[str, float]]] = {}

        # Distinct Visual Sector Theme per Deck Level
        if self.deck_level == 1:
            self.theme_name = "Cassini Habitation & Research Ring"
            self.wall_color = (0.12, 0.22, 0.35, 1.0)
            self.floor_color = (0.05, 0.07, 0.11, 1.0)
            self.accent_color = (0.02, 0.71, 0.83, 1.0)
        elif self.deck_level == 2:
            self.theme_name = "Sub-Level Fusion Engineering"
            self.wall_color = (0.38, 0.22, 0.08, 1.0)
            self.floor_color = (0.09, 0.07, 0.05, 1.0)
            self.accent_color = (0.95, 0.60, 0.10, 1.0)
        else:
            self.theme_name = "Deep Stasis & TITAN Quarantine Hive"
            self.wall_color = (0.32, 0.08, 0.28, 1.0)
            self.floor_color = (0.08, 0.04, 0.08, 1.0)
            self.accent_color = (0.85, 0.30, 0.95, 1.0)

        self._build_floor_layout()
        self._generate_navigation_graph()

    def _build_floor_layout(self):
        th = 20.0
        w_half = self.width / 2.0
        h_half = self.height / 2.0

        # Outer Station Hull Enclosure (All Decks)
        self.walls.append(Wall(-w_half, -h_half, self.width, th))
        self.walls.append(Wall(-w_half, h_half - th, self.width, th))
        self.walls.append(Wall(-w_half, -h_half, th, self.height))
        self.walls.append(Wall(w_half - th, -h_half, th, self.height))

        if self.deck_level == 1:
            self._build_deck_1_habitation(th)
        elif self.deck_level == 2:
            self._build_deck_2_engineering(th)
        else:
            self._build_deck_3_alien_hive(th)

    def _build_deck_1_habitation(self, th: float):
        # 1. Airlock Alpha (Spawn)
        self.rooms.append(StationRoom("airlock", "Airlock Staging Alpha", -180, -960, 180, -720, is_discovered=True, initial_enemy_count=0))
        self.walls.extend([Wall(-180, -960, 360, th), Wall(-180, -960, th, 240), Wall(160, -960, th, 240), Wall(-180, -720, 130, th), Wall(50, -720, 130, th)])
        self.doors.append(StationDoor("door_airlock", -50, -720, 100, th))
        self.walls.extend([Wall(-50, -720, th, 220), Wall(30, -720, th, 220)])

        # 2. Central Promenade
        self.rooms.append(StationRoom("promenade", "Central Promenade & Junction", -460, -500, 460, -140, initial_enemy_count=6))
        self.walls.extend([Wall(-460, -500, 410, th), Wall(50, -500, 410, th)])
        self.walls.extend([Wall(-460, -500, th, 140), Wall(-460, -260, th, 120)])
        self.doors.append(StationDoor("door_prom_west", -460, -360, th, 100, is_vertical=True))
        self.walls.extend([Wall(440, -500, th, 140), Wall(440, -260, th, 120)])
        self.doors.append(StationDoor("door_prom_east", 440, -360, th, 100, is_vertical=True))
        self.walls.extend([Wall(-460, -140, 400, th), Wall(60, -140, 400, th)])
        self.doors.append(StationDoor("door_prom_north", -60, -140, 120, th))
        self.walls.extend([Wall(-200, -380, 40, 80), Wall(160, -380, 40, 80)])
        self.crates.extend([SupplyCrate(-320, -420), SupplyCrate(320, -420), SupplyCrate(-120, -220), SupplyCrate(120, -220)])
        self.terminals.append(StationTerminal("term_turret", "Station Laser Turret", 0.0, -320.0, terminal_type="defense_turret"))
        self.npcs.append(StationNPC("zephyr", "Zephyr", "Scum Anarchist Hacker", -220.0, -220.0, "promenade", icon="🐙", color=(0.85, 0.35, 0.95, 1.0)))

        # 3. Cryo-Storage (West)
        self.rooms.append(StationRoom("cryo", "Cryo-Storage & Stasis Morgue", -960, -480, -460, -140, initial_enemy_count=6))
        self.walls.extend([Wall(-960, -480, 500, th), Wall(-960, -480, th, 340), Wall(-960, -140, 500, th)])
        self.crates.extend([SupplyCrate(-820, -380), SupplyCrate(-820, -220), SupplyCrate(-640, -400), SupplyCrate(-640, -200)])
        self.npcs.append(StationNPC("clinic_agi", "Clinic Epsilon AI", "Automated Resleeving Vats", -720.0, -200.0, "cryo", icon="🧬", color=(0.2, 0.95, 0.65, 1.0)))

        # 4. Hydroponics (East)
        self.rooms.append(StationRoom("hydroponics", "Hydroponics & Life Support", 460, -480, 960, -140, initial_enemy_count=6))
        self.walls.extend([Wall(460, -480, 500, th), Wall(940, -480, th, 340), Wall(460, -140, 500, th)])
        self.terminals.append(StationTerminal("term_gas", "Neuro-Gas Vents", 720.0, -310.0, terminal_type="gas_vent"))
        self.crates.extend([SupplyCrate(620, -360), SupplyCrate(800, -240)])

        # Armory Corridor
        self.walls.extend([Wall(-60, -140, th, 200), Wall(40, -140, th, 200)])

        # 5. Security Armory
        self.rooms.append(StationRoom("armory", "Security Armory & Officer Garrison", -400, 60, 400, 440, initial_enemy_count=4))
        self.walls.extend([Wall(-400, 60, 340, th), Wall(60, 60, 340, th)])
        self.doors.append(StationDoor("door_armory_south", -60, 60, 120, th))
        self.walls.extend([Wall(-400, 60, th, 140), Wall(-400, 300, th, 140)])
        self.doors.append(StationDoor("door_armory_west", -400, 200, th, 100, is_vertical=True))
        self.walls.append(Wall(380, 60, th, 380))
        self.walls.extend([Wall(-400, 440, 320, th), Wall(80, 440, 320, th)])
        self.doors.append(StationDoor("door_reactor_blast", -80, 440, 160, th, is_locked=True, lock_reason="keycard"))
        self.crates.extend([SupplyCrate(-280, 140), SupplyCrate(280, 140), SupplyCrate(-140, 320), SupplyCrate(140, 320), SupplyCrate(0, 240)])

        # 6. Research Bio-Labs
        self.rooms.append(StationRoom("research", "Research Bio-Labs & Server Core", -960, 100, -400, 500, initial_enemy_count=7))
        self.walls.extend([Wall(-960, 100, 560, th), Wall(-960, 100, th, 400), Wall(-960, 500, 560, th)])
        self.terminals.append(StationTerminal("term_emp", "Overload EMP Sub-Capacitor", -700.0, 300.0, terminal_type="emp_beacon"))
        self.crates.extend([SupplyCrate(-820, 220), SupplyCrate(-580, 380)])
        self.npcs.append(StationNPC("sorenson", "Dr. Sorenson", "Cassini Project Lead", -720.0, 380.0, "research", icon="👨‍🔬", color=(0.02, 0.9, 1.0, 1.0)))

        # 7. Sector Transit Elevator
        self.rooms.append(StationRoom("elevator", "Sector Transit Elevator", -300, 460, 300, 880, initial_enemy_count=1))
        self.walls.extend([Wall(-300, 460, 220, th), Wall(80, 460, 220, th), Wall(-300, 460, th, 420), Wall(280, 460, th, 420), Wall(-300, 880, 600, th)])
        self.elevator_terminal = StationTerminal("term_elevator", "Deck Transit Elevator Console", 0.0, 720.0, terminal_type="elevator_console", radius=34.0)
        self.terminals.append(self.elevator_terminal)

    def _build_deck_2_engineering(self, th: float):
        # 1. Engineering Airlock (Spawn)
        self.rooms.append(StationRoom("airlock", "Engineering Staging Alpha", -180, -960, 180, -720, is_discovered=True, initial_enemy_count=0))
        self.walls.extend([Wall(-180, -960, 360, th), Wall(-180, -960, th, 240), Wall(160, -960, th, 240), Wall(-180, -720, 130, th), Wall(50, -720, 130, th)])
        self.doors.append(StationDoor("door_airlock", -50, -720, 100, th))
        self.walls.extend([Wall(-50, -720, th, 140), Wall(30, -720, th, 140)])

        # 2. Coolant Distribution Concourse
        self.rooms.append(StationRoom("coolant", "Coolant Distribution Concourse", -480, -680, 480, -320, initial_enemy_count=7))
        self.walls.extend([Wall(-480, -680, 430, th), Wall(50, -680, 430, th)])
        self.walls.extend([Wall(-480, -680, th, 140), Wall(-480, -440, th, 120)])
        self.doors.append(StationDoor("door_substation_west", -480, -540, th, 100, is_vertical=True))
        self.walls.extend([Wall(460, -680, th, 140), Wall(460, -440, th, 120)])
        self.doors.append(StationDoor("door_fabrication_east", 460, -540, th, 100, is_vertical=True))
        self.walls.extend([Wall(-480, -320, 420, th), Wall(60, -320, 420, th)])
        self.doors.append(StationDoor("door_coolant_north", -60, -320, 120, th))
        self.crates.extend([SupplyCrate(-280, -480), SupplyCrate(280, -480), SupplyCrate(0, -540)])

        # 3. High-Voltage Substation (West)
        self.rooms.append(StationRoom("substation", "High-Voltage Tesla Substation", -960, -680, -480, -320, initial_enemy_count=6))
        self.walls.extend([Wall(-960, -680, 480, th), Wall(-960, -680, th, 360), Wall(-960, -320, 480, th)])
        self.terminals.append(StationTerminal("term_tesla", "Overload Tesla Grid Node", -720.0, -500.0, terminal_type="emp_beacon"))
        self.crates.extend([SupplyCrate(-820, -580), SupplyCrate(-640, -420)])

        # 4. Automated Heavy Fabrication (East)
        self.rooms.append(StationRoom("fabrication", "Automated Heavy Fabrication", 480, -680, 960, -320, initial_enemy_count=6))
        self.walls.extend([Wall(480, -680, 480, th), Wall(940, -680, th, 360), Wall(480, -320, 480, th)])
        self.crates.extend([SupplyCrate(640, -540), SupplyCrate(820, -420)])
        self.npcs.append(StationNPC("clinic_agi", "Fab Clinic Epsilon", "Industrial Resleeving Vat", 720.0, -480.0, "fabrication", icon="🧬", color=(0.2, 0.95, 0.65, 1.0)))

        # Corridor between Coolant and Fusion Core
        self.walls.extend([Wall(-60, -320, th, 120), Wall(40, -320, th, 120)])

        # 5. Central Fusion Core
        self.rooms.append(StationRoom("fusion_core", "Central Fusion Reactor Core", -450, -200, 450, 240, initial_enemy_count=5))
        self.walls.extend([Wall(-450, -200, 390, th), Wall(60, -200, 390, th)])
        self.doors.append(StationDoor("door_core_south", -60, -200, 120, th))
        self.walls.extend([Wall(-450, -200, th, 180), Wall(-450, 80, th, 160)])
        self.doors.append(StationDoor("door_processing_west", -450, -20, th, 100, is_vertical=True))
        self.walls.append(Wall(430, -200, th, 440))
        self.walls.extend([Wall(-450, 240, 370, th), Wall(80, 240, 370, th)])
        self.doors.append(StationDoor("door_reactor_blast", -80, 240, 160, th, is_locked=True, lock_reason="keycard"))
        self.walls.extend([Wall(-100, -40, 200, th), Wall(-100, 60, 200, th), Wall(-100, -40, th, 100), Wall(80, -40, th, 100)])
        self.crates.extend([SupplyCrate(-280, 100), SupplyCrate(280, 100), SupplyCrate(0, 160)])

        # 6. Maintenance & Fuel Rod Processing (West)
        self.rooms.append(StationRoom("rod_processing", "Fuel Rod Processing & Safety", -960, -200, -450, 240, initial_enemy_count=7))
        self.walls.extend([Wall(-960, -200, 510, th), Wall(-960, -200, th, 440), Wall(-960, 240, 510, th)])
        self.terminals.append(StationTerminal("term_coolant", "Emergency Coolant Flood", -700.0, 40.0, terminal_type="gas_vent"))
        self.crates.extend([SupplyCrate(-820, -100), SupplyCrate(-620, 140)])
        self.npcs.append(StationNPC("sorenson", "Chief Engineer Kovic", "Lead Fusion Engineer", -720.0, 80.0, "rod_processing", icon="👨‍🔧", color=(0.95, 0.60, 0.10, 1.0)))

        # 7. Mag-Lev Transit Elevator (Goal)
        self.rooms.append(StationRoom("elevator", "Mag-Lev Transit Lift Core", -300, 260, 300, 780, initial_enemy_count=1))
        self.walls.extend([Wall(-300, 260, 220, th), Wall(80, 260, 220, th), Wall(-300, 260, th, 520), Wall(280, 260, th, 520), Wall(-300, 780, 600, th)])
        self.elevator_terminal = StationTerminal("term_elevator", "Mag-Lev Elevator Console", 0.0, 640.0, terminal_type="elevator_console", radius=34.0)
        self.terminals.append(self.elevator_terminal)

    def _build_deck_3_alien_hive(self, th: float):
        # 1. Hive Decontamination Airlock
        self.rooms.append(StationRoom("airlock", "Quarantine Decontamination Airlock", -180, -960, 180, -720, is_discovered=True, initial_enemy_count=0))
        self.walls.extend([Wall(-180, -960, 360, th), Wall(-180, -960, th, 240), Wall(160, -960, th, 240), Wall(-180, -720, 130, th), Wall(50, -720, 130, th)])
        self.doors.append(StationDoor("door_airlock", -50, -720, 100, th))
        self.walls.extend([Wall(-50, -720, th, 140), Wall(30, -720, th, 140)])

        # 2. Fractured Neural Concourse
        self.rooms.append(StationRoom("neural_concourse", "Fractured Neural Concourse", -500, -660, 500, -260, initial_enemy_count=8))
        self.walls.extend([Wall(-500, -660, 450, th), Wall(50, -660, 450, th)])
        self.walls.extend([Wall(-500, -660, th, 140), Wall(-500, -420, th, 160)])
        self.doors.append(StationDoor("door_hive_west", -500, -520, th, 100, is_vertical=True))
        self.walls.extend([Wall(480, -660, th, 140), Wall(480, -420, th, 160)])
        self.doors.append(StationDoor("door_spire_east", 480, -520, th, 100, is_vertical=True))
        self.walls.extend([Wall(-500, -260, 440, th), Wall(60, -260, 440, th)])
        self.doors.append(StationDoor("door_vault_north", -60, -260, 120, th))
        self.crates.extend([SupplyCrate(-240, -520), SupplyCrate(240, -520), SupplyCrate(0, -420)])

        # 3. Biomechanical Incubation Chamber (West)
        self.rooms.append(StationRoom("biotech", "Biomechanical Incubation Chamber", -980, -660, -500, -200, initial_enemy_count=8))
        self.walls.extend([Wall(-980, -660, 480, th), Wall(-980, -660, th, 460), Wall(-980, -200, 480, th)])
        self.terminals.append(StationTerminal("term_biocide", "Biocide Purge Emitter", -740.0, -440.0, terminal_type="gas_vent"))
        self.crates.extend([SupplyCrate(-780, -480), SupplyCrate(-620, -320)])

        # 4. Neural Mesh Spire (East)
        self.rooms.append(StationRoom("server_spire", "TITAN Neural Mesh Spire", 500, -660, 980, -200, initial_enemy_count=7))
        self.walls.extend([Wall(500, -660, 480, th), Wall(960, -660, th, 460), Wall(500, -200, 480, th)])
        self.crates.extend([SupplyCrate(640, -520), SupplyCrate(820, -340)])
        self.npcs.append(StationNPC("clinic_agi", "Stasis Unit Omega", "Neural Resleeving Node", 720.0, -440.0, "server_spire", icon="🧬", color=(0.2, 0.95, 0.65, 1.0)))

        # Corridor to Vault
        self.walls.extend([Wall(-60, -260, th, 100), Wall(40, -260, th, 100)])

        # 5. Black-Box Containment Vault
        self.rooms.append(StationRoom("quarantine_vault", "Black-Box Containment Vault", -440, -160, 440, 300, initial_enemy_count=6))
        self.walls.extend([Wall(-440, -160, 380, th), Wall(60, -160, 380, th)])
        self.doors.append(StationDoor("door_vault_south", -60, -160, 120, th))
        self.walls.extend([Wall(-440, -160, th, 180), Wall(-440, 120, th, 180)])
        self.doors.append(StationDoor("door_mutation_west", -440, 20, th, 100, is_vertical=True))
        self.walls.append(Wall(420, -160, th, 460))
        self.walls.extend([Wall(-440, 300, 360, th), Wall(80, 300, 360, th)])
        self.doors.append(StationDoor("door_reactor_blast", -80, 300, 160, th, is_locked=True, lock_reason="keycard"))
        self.crates.extend([SupplyCrate(-200, 60), SupplyCrate(200, 60), SupplyCrate(0, 160)])

        # 6. Alien Mutation Laboratory (West)
        self.rooms.append(StationRoom("mutation_lab", "Alien Mutation Laboratory", -980, -140, -440, 340, initial_enemy_count=8))
        self.walls.extend([Wall(-980, -140, 540, th), Wall(-980, -140, th, 480), Wall(-980, 340, 540, th)])
        self.crates.extend([SupplyCrate(-800, -20), SupplyCrate(-600, 220)])
        self.npcs.append(StationNPC("sorenson", "Agent Vane", "Firewall Infiltrator", -720.0, 120.0, "mutation_lab", icon="🕵️‍♂️", color=(0.85, 0.35, 0.95, 1.0)))

        # 7. Primary Evacuation Core (Goal)
        self.rooms.append(StationRoom("elevator", "Primary Evacuation Launch Core", -320, 320, 320, 880, initial_enemy_count=1))
        self.walls.extend([Wall(-320, 320, 240, th), Wall(80, 320, 240, th), Wall(-320, 320, th, 560), Wall(300, 320, th, 560), Wall(-320, 880, 640, th)])
        self.elevator_terminal = StationTerminal("term_elevator", "Evacuation Shuttle Console", 0.0, 720.0, terminal_type="elevator_console", radius=34.0)
        self.terminals.append(self.elevator_terminal)

    def _generate_navigation_graph(self):
        """Builds a dynamic A* waypoint navigation graph for this specific deck layout."""
        self.waypoint_nodes.clear()
        self.waypoint_adj.clear()

        # 1. Room center waypoints
        for room in self.rooms:
            cx = (room.x1 + room.x2) / 2.0
            cy = (room.y1 + room.y2) / 2.0
            r_id = f"room_{room.id}"
            self.waypoint_nodes[r_id] = (cx, cy)
            self.waypoint_adj[r_id] = []

        # 2. Door waypoints and threshold connectors
        for door in self.doors:
            dcx = door.x + door.w / 2.0
            dcy = door.y + door.h / 2.0
            d_id = f"door_{door.id}"
            self.waypoint_nodes[d_id] = (dcx, dcy)
            self.waypoint_adj[d_id] = []

            if door.is_vertical:
                app1 = (dcx - 45.0, dcy)
                app2 = (dcx + 45.0, dcy)
            else:
                app1 = (dcx, dcy - 45.0)
                app2 = (dcx, dcy + 45.0)

            app1_id = f"app1_{door.id}"
            app2_id = f"app2_{door.id}"
            self.waypoint_nodes[app1_id] = app1
            self.waypoint_nodes[app2_id] = app2
            self.waypoint_adj[app1_id] = []
            self.waypoint_adj[app2_id] = []

            d1 = math.hypot(app1[0] - dcx, app1[1] - dcy)
            d2 = math.hypot(app2[0] - dcx, app2[1] - dcy)
            self.waypoint_adj[d_id].extend([(app1_id, d1), (app2_id, d2)])
            self.waypoint_adj[app1_id].append((d_id, d1))
            self.waypoint_adj[app2_id].append((d_id, d2))

            for a_id, a_pos in [(app1_id, app1), (app2_id, app2)]:
                linked = False
                for room in self.rooms:
                    if room.x1 - 25 <= a_pos[0] <= room.x2 + 25 and room.y1 - 25 <= a_pos[1] <= room.y2 + 25:
                        rn = f"room_{room.id}"
                        dist = math.hypot(a_pos[0] - self.waypoint_nodes[rn][0], a_pos[1] - self.waypoint_nodes[rn][1])
                        self.waypoint_adj[a_id].append((rn, dist))
                        self.waypoint_adj[rn].append((a_id, dist))
                        linked = True
                if not linked:
                    best_r = min(self.rooms, key=lambda r: math.hypot(a_pos[0] - (r.x1+r.x2)/2, a_pos[1] - (r.y1+r.y2)/2))
                    rn = f"room_{best_r.id}"
                    dist = math.hypot(a_pos[0] - self.waypoint_nodes[rn][0], a_pos[1] - self.waypoint_nodes[rn][1])
                    self.waypoint_adj[a_id].append((rn, dist))
                    self.waypoint_adj[rn].append((a_id, dist))

    def get_path(self, start_x: float, start_y: float, goal_x: float, goal_y: float, locked_doors: Optional[Set[str]] = None) -> List[Tuple[float, float]]:
        if locked_doors is None:
            locked_doors = set()
        if not self.waypoint_nodes:
            return [(goal_x, goal_y)]

        s_node = min(self.waypoint_nodes.keys(), key=lambda k: math.hypot(start_x - self.waypoint_nodes[k][0], start_y - self.waypoint_nodes[k][1]))
        g_node = min(self.waypoint_nodes.keys(), key=lambda k: math.hypot(goal_x - self.waypoint_nodes[k][0], goal_y - self.waypoint_nodes[k][1]))

        if s_node == g_node:
            return [self.waypoint_nodes[g_node]]

        q = [(0.0, s_node, [s_node])]
        visited = {}
        while q:
            cost, cur, path = heapq.heappop(q)
            if cur in visited and visited[cur] <= cost:
                continue
            visited[cur] = cost

            if cur == g_node:
                return [self.waypoint_nodes[n] for n in path]

            for nxt, weight in self.waypoint_adj.get(cur, []):
                if nxt.startswith("door_"):
                    d_id = nxt[5:]
                    if d_id in locked_doors:
                        continue
                heapq.heappush(q, (cost + weight, nxt, path + [nxt]))

        return [(goal_x, goal_y)]


class GameWorld:
    def __init__(self, morph_id: str = "synth", deck_level: int = 1,
                 is_breach_mode: bool = False, breach_time_limit: float = 45.0,
                 breach_target_kills: int = 20, on_breach_complete: Optional[Callable] = None):
        self.morph_id = morph_id
        self.deck_level = deck_level
        self.player = Player(0.0, -820.0, morph_id=morph_id)
        self.map = StationMap(deck_level=deck_level)

        self.enemies: List[Enemy] = []
        self.projectiles: List[Projectile] = []
        self.xp_cores: List[XPCore] = []
        self.keycard_pickup: Optional[KeycardPickup] = None

        self.wave_time = 0.0
        self.difficulty_level = 1.0 + (deck_level - 1) * 0.45
        self.is_paused = False
        self.is_game_over = False
        self.floor_completed = False

        # Keycard & Boss State
        self.captain_killed = False
        self.boss_killed = False
        self.active_npc: Optional[StationNPC] = None
        self.cured_sorenson: bool = False
        self.zephyr_turret_hacked: bool = False
        self.nanocores: int = 25

        # Combat Sound Perception
        self.last_combat_sound_time = -10.0
        self.last_combat_sound_pos = (0.0, 0.0)

        # Terminal Active Effect Timers
        self.gas_vent_active = 0.0
        self.turret_active = 0.0
        self.turret_shot_timer = 0.0

        # Tactical Breach Mode
        self.is_breach_mode = is_breach_mode
        self.breach_time_remaining = breach_time_limit
        self.breach_target_kills = breach_target_kills
        self.breach_completed = False
        self.on_breach_complete = on_breach_complete

        # Alerts Queue
        self.alert_notifications: List[dict] = []

        # Populate Station Floor Enemies
        self._populate_station_enemies()

    def trigger_alert(self, text: str, color=(0.02, 0.71, 0.83, 1.0)):
        self.alert_notifications.append({"text": text, "color": color, "timer": 3.5})

    def _populate_station_enemies(self):
        """Populates rooms with hand-placed garrisons according to deck level and sector theme."""
        scale = self.difficulty_level

        if self.deck_level == 1:
            self._populate_deck_1(scale)
        elif self.deck_level == 2:
            self._populate_deck_2(scale)
        else:
            self._populate_deck_3(scale)

    def _populate_deck_1(self, scale: float):
        # 1. Promenade
        for e_id, ex, ey in [("patrol_drone", -220, -250), ("patrol_drone", 220, -250), ("patrol_drone", -120, -420), ("patrol_drone", 120, -420), ("exsurgent_husk", -60, -320), ("exsurgent_husk", 60, -320)]:
            self._spawn_enemy_type(e_id, ex, ey, "promenade", scale)

        # 2. Cryo-Storage
        for e_id, ex, ey in [("exsurgent_husk", -840, -420), ("exsurgent_husk", -840, -240), ("exsurgent_husk", -720, -320), ("exsurgent_husk", -600, -400), ("exsurgent_husk", -600, -220), ("basilisk_spider", -760, -280)]:
            self._spawn_enemy_type(e_id, ex, ey, "cryo", scale)

        # 3. Hydroponics
        for e_id, ex, ey in [("basilisk_spider", 600, -400), ("basilisk_spider", 600, -220), ("basilisk_spider", 820, -400), ("basilisk_spider", 820, -220), ("patrol_drone", 710, -240), ("patrol_drone", 710, -380)]:
            self._spawn_enemy_type(e_id, ex, ey, "hydroponics", scale)

        # 4. Security Armory
        self._spawn_enemy_type("patrol_drone", -180, 200, "armory", scale)
        self._spawn_enemy_type("patrol_drone", 180, 200, "armory", scale)
        self._spawn_enemy_type("patrol_drone", 0, 320, "armory", scale)
        self.enemies.append(Enemy("captain_drone", 0.0, 200.0, 320.0 * scale, 320.0 * scale, 68.0, 22.0, 22.0, 220, (1.0, 0.84, 0.0, 1.0), is_captain=True, home_room_id="armory", aggro_range=520.0))

        # 5. Research Bio-Labs
        for e_id, ex, ey in [("exsurgent_husk", -800, 180), ("exsurgent_husk", -800, 420), ("exsurgent_husk", -600, 200), ("exsurgent_husk", -600, 440), ("basilisk_spider", -720, 320), ("basilisk_spider", -840, 300), ("basilisk_spider", -540, 300)]:
            self._spawn_enemy_type(e_id, ex, ey, "research", scale)

        # 6. Sector Transit Elevator Boss
        self.enemies.append(Enemy("reaper_combat_mech", 0.0, 600.0, 480.0 * scale, 480.0 * scale, 48.0, 28.0, 28.0, 300, (0.91, 0.30, 0.24, 1.0), is_boss=True, home_room_id="elevator", aggro_range=600.0))

    def _populate_deck_2(self, scale: float):
        # 1. Coolant Concourse
        for e_id, ex, ey in [("welding_android", -240, -460), ("welding_android", 240, -460), ("spark_drone", -120, -560), ("spark_drone", 120, -560), ("thermite_husk", 0, -420), ("thermite_husk", -180, -360), ("thermite_husk", 180, -360)]:
            self._spawn_enemy_type(e_id, ex, ey, "coolant", scale)

        # 2. High-Voltage Substation
        for e_id, ex, ey in [("spark_drone", -840, -560), ("spark_drone", -640, -420), ("welding_android", -780, -440), ("welding_android", -620, -540), ("thermite_husk", -720, -360), ("thermite_husk", -860, -380)]:
            self._spawn_enemy_type(e_id, ex, ey, "substation", scale)

        # 3. Automated Heavy Fabrication
        for e_id, ex, ey in [("welding_android", 620, -560), ("welding_android", 820, -440), ("spark_drone", 720, -380), ("thermite_husk", 640, -380), ("thermite_husk", 840, -540), ("spark_drone", 740, -580)]:
            self._spawn_enemy_type(e_id, ex, ey, "fabrication", scale)

        # 4. Maintenance & Fuel Rod Processing (West)
        for e_id, ex, ey in [("thermite_husk", -820, -100), ("thermite_husk", -620, 140), ("welding_android", -780, 0), ("spark_drone", -600, -40), ("spark_drone", -840, 160)]:
            self._spawn_enemy_type(e_id, ex, ey, "rod_processing", scale)
        self.enemies.append(Enemy("engineer_captain", -700.0, -80.0, 420.0 * scale, 420.0 * scale, 72.0, 24.0, 26.0, 260, (1.0, 0.84, 0.0, 1.0), is_captain=True, home_room_id="rod_processing", aggro_range=550.0))

        # 5. Central Fusion Core
        for e_id, ex, ey in [("welding_android", -260, 40), ("welding_android", 260, 40), ("thermite_husk", -180, 160), ("thermite_husk", 180, 160), ("spark_drone", 0, -120)]:
            self._spawn_enemy_type(e_id, ex, ey, "fusion_core", scale)

        # 6. Mag-Lev Transit Elevator (Boss)
        self.enemies.append(Enemy("aegis_colossus", 0.0, 560.0, 680.0 * scale, 680.0 * scale, 42.0, 32.0, 34.0, 400, (0.95, 0.45, 0.15, 1.0), is_boss=True, home_room_id="elevator", aggro_range=650.0))

    def _populate_deck_3(self, scale: float):
        # 1. Neural Concourse
        for e_id, ex, ey in [("titan_swarmer", -200, -500), ("titan_swarmer", 200, -500), ("titan_swarmer", 0, -400), ("apex_shifter", -280, -360), ("apex_shifter", 280, -360), ("basilisk_horror", -140, -580), ("basilisk_horror", 140, -580)]:
            self._spawn_enemy_type(e_id, ex, ey, "neural_concourse", scale)

        # 2. Biotech Incubation
        for e_id, ex, ey in [("titan_swarmer", -840, -520), ("titan_swarmer", -640, -380), ("titan_swarmer", -740, -460), ("apex_shifter", -820, -340), ("apex_shifter", -660, -540), ("basilisk_horror", -720, -280), ("basilisk_horror", -880, -420)]:
            self._spawn_enemy_type(e_id, ex, ey, "biotech", scale)

        # 3. Neural Mesh Spire
        for e_id, ex, ey in [("apex_shifter", 640, -520), ("apex_shifter", 820, -360), ("titan_swarmer", 720, -420), ("titan_swarmer", 840, -520), ("basilisk_horror", 660, -340), ("basilisk_horror", 780, -560)]:
            self._spawn_enemy_type(e_id, ex, ey, "server_spire", scale)

        # 4. Alien Mutation Laboratory (West)
        for e_id, ex, ey in [("apex_shifter", -800, 0), ("apex_shifter", -600, 220), ("titan_swarmer", -740, 40), ("titan_swarmer", -840, 160), ("basilisk_horror", -620, -60), ("basilisk_horror", -700, 260)]:
            self._spawn_enemy_type(e_id, ex, ey, "mutation_lab", scale)
        self.enemies.append(Enemy("vault_guardian", -720.0, -40.0, 520.0 * scale, 520.0 * scale, 75.0, 26.0, 30.0, 320, (1.0, 0.84, 0.0, 1.0), is_captain=True, home_room_id="mutation_lab", aggro_range=580.0))

        # 5. Black-Box Containment Vault
        for e_id, ex, ey in [("apex_shifter", -220, 80), ("apex_shifter", 220, 80), ("titan_swarmer", -140, 200), ("titan_swarmer", 140, 200), ("basilisk_horror", 0, -40)]:
            self._spawn_enemy_type(e_id, ex, ey, "quarantine_vault", scale)

        # 6. Primary Evac Core (Final Boss)
        self.enemies.append(Enemy("titan_abomination", 0.0, 620.0, 950.0 * scale, 950.0 * scale, 45.0, 36.0, 40.0, 600, (0.85, 0.20, 0.90, 1.0), is_boss=True, home_room_id="elevator", aggro_range=700.0))

    def _spawn_enemy_type(self, e_type: str, x: float, y: float, room_id: str, scale: float):
        if e_type == "patrol_drone":
            self.enemies.append(Enemy(e_type, x, y, 18.0 * scale, 18.0 * scale, 75.0, 12.0, 8.0, 12, (0.95, 0.45, 0.15, 1.0), home_room_id=room_id))
        elif e_type == "exsurgent_husk":
            self.enemies.append(Enemy(e_type, x, y, 34.0 * scale, 34.0 * scale, 55.0, 15.0, 14.0, 22, (0.75, 0.25, 0.90, 1.0), home_room_id=room_id))
        elif e_type == "basilisk_spider":
            self.enemies.append(Enemy(e_type, x, y, 24.0 * scale, 24.0 * scale, 98.0, 10.0, 10.0, 18, (0.02, 0.85, 0.65, 1.0), home_room_id=room_id))
        elif e_type == "welding_android":
            self.enemies.append(Enemy(e_type, x, y, 48.0 * scale, 48.0 * scale, 54.0, 16.0, 16.0, 28, (0.85, 0.50, 0.15, 1.0), home_room_id=room_id))
        elif e_type == "spark_drone":
            self.enemies.append(Enemy(e_type, x, y, 22.0 * scale, 22.0 * scale, 108.0, 11.0, 12.0, 20, (0.2, 0.9, 1.0, 1.0), home_room_id=room_id))
        elif e_type == "thermite_husk":
            self.enemies.append(Enemy(e_type, x, y, 38.0 * scale, 38.0 * scale, 76.0, 14.0, 18.0, 30, (0.95, 0.35, 0.10, 1.0), home_room_id=room_id))
        elif e_type == "titan_swarmer":
            self.enemies.append(Enemy(e_type, x, y, 20.0 * scale, 20.0 * scale, 118.0, 9.0, 11.0, 16, (0.6, 0.95, 0.3, 1.0), home_room_id=room_id))
        elif e_type == "apex_shifter":
            self.enemies.append(Enemy(e_type, x, y, 62.0 * scale, 62.0 * scale, 68.0, 17.0, 22.0, 36, (0.80, 0.15, 0.40, 1.0), home_room_id=room_id))
        elif e_type == "basilisk_horror":
            self.enemies.append(Enemy(e_type, x, y, 42.0 * scale, 42.0 * scale, 88.0, 13.0, 16.0, 32, (0.1, 0.85, 0.85, 1.0), home_room_id=room_id))

    def get_current_room(self, px: float, py: float) -> Optional[StationRoom]:
        for r in self.map.rooms:
            if r.x1 <= px <= r.x2 and r.y1 <= py <= r.y2:
                return r
        return None

    def get_secured_rooms_count(self) -> int:
        return len([r for r in self.map.rooms if r.is_cleared])

    def update_room_states(self):
        """Checks if rooms have been cleared of hostiles."""
        cur = self.get_current_room(self.player.x, self.player.y)
        if cur:
            self.player.current_room_id = cur.id
            if not cur.is_discovered:
                cur.is_discovered = True
                self.trigger_alert(f"📍 ENTERING: {cur.name.upper()}", (0.02, 0.71, 0.83, 1.0))

        # Check clearing
        for room in self.map.rooms:
            if not room.is_cleared and room.initial_enemy_count > 0:
                alive_in_room = [e for e in self.enemies if room.x1 <= e.x <= room.x2 and room.y1 <= e.y <= room.y2]
                if len(alive_in_room) == 0:
                    room.is_cleared = True
                    self.player.xp += 40
                    self.trigger_alert(f"✓ {room.name.upper()} SECURED! (+40 XP)", (0.2, 0.95, 0.65, 1.0))

    def update_floor_time(self, dt: float):
        self.wave_time += dt

        # Breach Mode countdown
        if self.is_breach_mode and not self.breach_completed:
            self.breach_time_remaining -= dt
            if self.breach_time_remaining <= 0 or self.player.kills >= self.breach_target_kills:
                self.breach_completed = True
                if self.on_breach_complete:
                    self.on_breach_complete(True, self.player.kills, "Sector Quarantine Successfully Purged")
