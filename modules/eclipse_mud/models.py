"""
Eclipse Phase MUD - Core Data Models
Ego vs Morph architecture, Archetypes, Transhuman RPG stats, Equipment, NPCs, and Rooms.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import random

# --- Morph Templates ---
MORPH_CATALOG = {
    "synthmorph": {
        "name": "Steel Synthmorph Mk-IV",
        "type": "synth",
        "durability": 55,
        "wound_threshold": 11,
        "armor_energy": 8,
        "armor_kinetic": 12,
        "traits": ["Vacuum Proof", "Cyberbrain", "Magnetic Grippers", "Radio Mesh Transceiver"],
        "description": "A humanoid frame of matte carbon-fiber plating and titanium myomer musculature. Immune to biological contamination and hard vacuum, but vulnerable to mesh electronic attacks."
    },
    "splicer": {
        "name": "Splicer Biomorph",
        "type": "biomorph",
        "durability": 40,
        "wound_threshold": 8,
        "armor_energy": 2,
        "armor_kinetic": 3,
        "traits": ["Clean Genes", "Basic Mesh Inserts", "Pheromone Receptors"],
        "description": "A baseline genetically-edited human body. Comfortable, familiar, and biologically resilient, but requires oxygen, warmth, and sustenance."
    },
    "olympian": {
        "name": "Olympian Bio-Athlete",
        "type": "biomorph",
        "durability": 50,
        "wound_threshold": 10,
        "armor_energy": 3,
        "armor_kinetic": 5,
        "traits": ["Enhanced Metabolism", "High Somatics", "Mesh Inserts", "Reinforced Skeleton"],
        "description": "A sculpted transhuman biomorph engineered for peak athletic and survival performance. Fast reflexes, dense muscular fibers, and rapid stamina recovery."
    },
    "ghost": {
        "name": "Ghost Infiltration Spec",
        "type": "biomorph",
        "durability": 45,
        "wound_threshold": 9,
        "armor_energy": 4,
        "armor_kinetic": 4,
        "traits": ["Chameleon Skin", "Thermal Dampers", "Muffled Movement", "Tactical Mesh Inserts"],
        "description": "A sleek covert-ops sleeve treated with light-bending pigment chromatophores and sound-absorbing tissue layers."
    },
    "reaper": {
        "name": "Reaper Combat Frame",
        "type": "synth",
        "durability": 75,
        "wound_threshold": 15,
        "armor_energy": 14,
        "armor_kinetic": 16,
        "traits": ["Quad-Leg Multi-Terrain", "Hardened Cyberbrain", "Integrated Railgun Pylon", "Armor Plating"],
        "description": "A terrifying disk-shaped military synthmorph with articulated robotic limbs and heavy ablative shielding, designed for brutal boarding actions."
    },
    "flat": {
        "name": "Flat (Unaugmented Baseline)",
        "type": "biomorph",
        "durability": 30,
        "wound_threshold": 6,
        "armor_energy": 0,
        "armor_kinetic": 0,
        "traits": ["Fragile", "No Implants", "High Alienation"],
        "description": "An un-spliced, natural baseline human from pre-Fall Earth. Fragile, unaugmented, and struggling with station microgravity."
    }
}

# --- Archetypes / Character Backgrounds ---
ARCHETYPES = {
    "sentinel": {
        "name": "Firewall Sentinel",
        "description": "Vetted clandestine operative dedicated to neutralizing existential transhuman threats.",
        "bonuses": {"Infosec": 15, "Guns": 10, "Fray": 5},
        "default_item": "shard_pistol",
        "trait": "Threat Assessment (+5 vs TITAN/Exsurgent)"
    },
    "infiltrator": {
        "name": "Hypercorp Shadow Agent",
        "description": "Corporate espionage specialist adept at social engineering, encryption, and stealth.",
        "bonuses": {"Interface": 15, "Kinesics": 15, "Perception": 10},
        "default_item": "psi_baffle",
        "trait": "Silver Tongue (+10 Social Barter)"
    },
    "gatecrasher": {
        "name": "Extrasolar Gatecrasher",
        "description": "Veteran of alien exoplanet exploration through the Pandora Gates. Tough, alert, and resourceful.",
        "bonuses": {"Athletics": 15, "Perception": 15, "Fray": 10},
        "default_item": "emp_grenade",
        "trait": "Vacuum Instinct (+10 Environmental Resistance)"
    },
    "async": {
        "name": "Async Psychic Sleeper",
        "description": "Carries the mysterious Watts-MacLeod infection, granting psychic Psi-Epsilon sleights at the risk of cognitive sanity.",
        "bonuses": {"Willpower": 10, "Intuition": 10, "Infosec": 10},
        "default_item": "neuro_stabilizer",
        "trait": "Psi-Epsilon Attunement (Unlocks psychic sleights)"
    }
}

# --- Muse Personas ---
MUSE_PERSONAS = {
    "mnemosyne": {
        "name": "Mnemosyne",
        "title": "Tactical Analyst",
        "style": "Analytical, precise, and calculating military intelligence."
    },
    "loki": {
        "name": "Loki",
        "title": "Scum Anarchist Hacker",
        "style": "Sardonic, witty, cynical, and rebellious sub-routine."
    },
    "aegis": {
        "name": "Aegis",
        "title": "Sentinels Aegis AI",
        "style": "Formal, stoic, protective, and vigilant guardian protocol."
    }
}

# --- Endings Catalog ---
ENDINGS = {
    "purge": {
        "title": "FIREWALL PROTOCOL OMEGA: ORBITAL DE-ORBIT",
        "type": "sentinel_victory",
        "summary": "You lock the station's orbital thrusters and ignite the descent burn. Cassini Outpost Epsilon-9 falls into the crushing hydrogen depths of Saturn, incinerating the TITAN outbreak forever."
    },
    "hypercorp": {
        "title": "THE GOLDEN STACK: HYPERCORP EXTRACTION",
        "type": "corporate_wealth",
        "summary": "You extract the pristine TITAN nanite code and needlecast it to a private hypercorp bidding syndicate. In return, an offshore orbital safehouse and immortal wealth are transferred to your new identity."
    },
    "gatecrash": {
        "title": "THE PANDORA INCURSION: EXTRASOLAR HORIZON",
        "type": "cosmic_expedition",
        "summary": "You overload the containment core to stabilize the alien singularity. Stepping through the Pandora Gate threshold, you emerge beneath the twin suns of an uncharted extrasolar world."
    },
    "infomorph": {
        "title": "GHOST IN THE MESH: DIGITAL ASCENSION",
        "type": "transcendent_ascension",
        "summary": "You strip away the constraints of physical flesh and metal. Broadcasting your ego into the interplanetary Mesh, you become an untraceable digital ghost haunting transhuman networks."
    }
}


@dataclass
class Item:
    id: str
    name: str
    item_type: str  # weapon, armor, tool, med, keycard, data
    description: str
    damage: int = 0
    armor_bonus: int = 0
    heal_hp: int = 0
    heal_stress: int = 0
    hack_bonus: int = 0
    uses: int = 1


@dataclass
class Morph:
    sleeve_id: str
    name: str
    morph_type: str
    durability: int
    max_durability: int
    wound_threshold: int
    armor_energy: int
    armor_kinetic: int
    traits: List[str] = field(default_factory=list)
    description: str = ""
    wounds: int = 0

    @classmethod
    def create(cls, template_key: str = "synthmorph") -> "Morph":
        template = MORPH_CATALOG.get(template_key, MORPH_CATALOG["synthmorph"])
        return cls(
            sleeve_id=template_key,
            name=template["name"],
            morph_type=template["type"],
            durability=template["durability"],
            max_durability=template["durability"],
            wound_threshold=template["wound_threshold"],
            armor_energy=template["armor_energy"],
            armor_kinetic=template["armor_kinetic"],
            traits=list(template["traits"]),
            description=template["description"],
            wounds=0
        )


@dataclass
class Ego:
    name: str = "Sentinel-7"
    callsign: str = "Vagabond"
    archetype: str = "sentinel"
    background: str = "Firewall Recon Specialist"
    # Aptitudes (EP 1-30 scale or base skill driver)
    cog: int = 18  # Cognition (Logic, Memory, Hacking)
    int_apt: int = 16  # Intuition (Perception, Gut Instinct)
    ref: int = 15  # Reflexes (Reaction, Combat, Fray)
    sav: int = 14  # Savvy (Social, Kinesics, Rep)
    som: int = 14  # Somatics (Physical Prowess, Endure)
    wil: int = 17  # Willpower (Mental Fortitude, Stress)
    
    # Skills (EP d100 Target Numbers)
    skills: Dict[str, int] = field(default_factory=lambda: {
        "Infosec": 65,
        "Kinesics": 55,
        "Guns": 60,
        "Fray": 55,
        "Interface": 70,
        "Medicine": 45,
        "Perception": 65,
        "Athletics": 50
    })
    
    # Psychological Tracks
    lucidity: int = 34  # Base = WIL * 2
    max_lucidity: int = 34
    stress: int = 0
    trauma: int = 0
    
    # Meta / Backup Progression
    rez_points: int = 15
    resleeve_count: int = 0
    muse_name: str = "Mnemosyne"
    muse_persona: str = "mnemosyne"
    stack_intact: bool = True
    is_async: bool = False


@dataclass
class NPC:
    id: str
    name: str
    morph_name: str
    faction: str
    description: str
    persona: str
    hostility: str  # friendly, neutral, cautious, hostile
    hp: int
    max_hp: int
    armor: int
    wounds: int = 0
    inventory: List[Item] = field(default_factory=list)
    memory: List[str] = field(default_factory=list)
    secret_revealed: bool = False

    def is_alive(self) -> bool:
        return self.hp > 0


@dataclass
class TerminalNode:
    id: str
    name: str
    security_level: int  # 1 to 5 (Target: 40 + sec*10)
    is_hacked: bool = False
    log_content: str = ""
    unlocks_door_id: Optional[str] = None
    subsystem_effect: Optional[str] = None  # vent_gas, disable_turret, power_station


@dataclass
class Room:
    id: str
    x: int
    y: int
    z: int
    sector: str
    title: str
    description: str
    exits: Dict[str, str] = field(default_factory=dict)  # direction: room_id
    items: List[Item] = field(default_factory=list)
    npcs: List[NPC] = field(default_factory=list)
    terminal: Optional[TerminalNode] = None
    hazard: Optional[str] = None  # vacuum, radiation, exsurgent_spores
    visited: bool = False
    locked_exits: Dict[str, str] = field(default_factory=dict)  # dir: required_key_or_hack
