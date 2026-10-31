"""
Eclipse Phase MUD - Procedural World Generator
Builds the derelict research station 'Cassini Outpost Epsilon-9'
with interconnected rooms, terminals, items, and NPCs.
"""
from typing import Dict, List, Tuple
from models import Room, Item, NPC, TerminalNode

def create_cassini_station() -> Dict[str, Room]:
    """Generates the room graph for Cassini Outpost Epsilon-9."""
    rooms: Dict[str, Room] = {}

    # --- Items ---
    item_shard_pistol = Item(
        id="shard_pistol",
        name="Tactical Shard Pistol",
        item_type="weapon",
        description="Fires high-velocity monomolecular diamond flechettes. Silent, lethal in pressurized or vacuum environments.",
        damage=16
    )
    item_nanite_med = Item(
        id="nanite_spray",
        name="Nanite Med-Spray",
        item_type="med",
        description="Aerosol cellular repair swarm. Restores 25 Morph Durability or synthetics integrity.",
        heal_hp=25
    )
    item_neuro_stabilizer = Item(
        id="neuro_stabilizer",
        name="Neuro-Chemical Stabilizer",
        item_type="med",
        description="Injectable dopamine-serotonin balancer that soothes mental trauma and clears 15 Stress.",
        heal_stress=15
    )
    item_keycard = Item(
        id="quarantine_keycard",
        name="TITAN Quarantine Keycard",
        item_type="keycard",
        description="Class-5 biometric encryption card belonging to Station Director Vance. Unlocks the Sector 4 blast doors.",
        hack_bonus=15
    )
    item_emp_grenade = Item(
        id="emp_grenade",
        name="Micro-EMP Charge",
        item_type="weapon",
        description="Directional electromagnetic pulse cylinder. Devastating against synthmorphs, drones, and electronic security grids.",
        damage=30
    )
    item_psi_amulet = Item(
        id="psi_baffle",
        name="Faraday Psi-Baffle",
        item_type="tool",
        description="An experimental mesh insert baffle that dampens alien exsurgent cognitive frequencies.",
        heal_stress=5
    )

    # --- NPCs ---
    npc_zephyr = NPC(
        id="zephyr",
        name="Zephyr (Octomorph)",
        morph_name="Uplifted Octomorph",
        faction="Scum Anarchist Collective",
        description="An eight-armed uplifted octopus in a microgravity harness, dexterously manipulating three cyber-decks at once.",
        persona="Cynical, fast-talking, distrustful of hypercorps, passionate about open-source mesh autonomy.",
        hostility="neutral",
        hp=35,
        max_hp=35,
        armor=2,
        inventory=[item_neuro_stabilizer]
    )

    npc_sorenson = NPC(
        id="sorenson",
        name="Dr. Sorenson",
        morph_name="Damaged Menton Biomorph",
        faction="Cassini Project Lead",
        description="A frail scientist whose eyes show the telltale iridescence of early-stage Basilisk-hack infection.",
        persona="Nervous, twitching, clutching an encrypted datapad, pleading for nanite medical help.",
        hostility="cautious",
        hp=28,
        max_hp=28,
        armor=1,
        inventory=[item_keycard]
    )

    npc_reaper = NPC(
        id="unit_reaper",
        name="Unit 9-Omega",
        morph_name="Reaper Combat Frame",
        faction="Rogue Security AI Subroutine",
        description="A hulking combat chassis equipped with quad-tracks and a spinning flechette cannon. Optical sensors glow predatory amber.",
        persona="Staccato synthetic threats, operating on corrupted quarantine protocol logic.",
        hostility="cautious",
        hp=65,
        max_hp=65,
        armor=12,
        inventory=[item_emp_grenade]
    )

    npc_exsurgent = NPC(
        id="exsurgent_horror",
        name="The Blighted Chimera",
        morph_name="Biomorphic Amalgamation",
        faction="Exsurgent Hive Entity",
        description="A horrific fusion of three human biomorphs bonded with alien crystalline black nanite extrusions. It whispers in dead tongues.",
        persona="Cosmic predatory malice, seeking to consume ego cortical stacks.",
        hostility="hostile",
        hp=50,
        max_hp=50,
        armor=6,
        inventory=[]
    )

    # --- Sector 1: Airlock & Habitation ---
    r_airlock = Room(
        id="airlock_1",
        x=0, y=0, z=0,
        sector="Sector 1: Airlock Ring",
        title="Airlock Alpha-1",
        description="A depressurized cylindrical vestibule. Frost clings to the titanium bulkheads, and warning beacons flash silent amber.",
        exits={"north": "promenade", "east": "cargo_bay"},
        items=[item_nanite_med],
        hazard="Microgravity / Decompression"
    )

    r_cargo = Room(
        id="cargo_bay",
        x=1, y=0, z=0,
        sector="Sector 1: Airlock Ring",
        title="Cargo Staging Bay",
        description="Massive zero-g containers secured by magnetic webbing. A hydraulic loading frame floats lifelessly above a ruptured crate.",
        exits={"west": "airlock_1", "north": "conduit"},
        items=[item_shard_pistol],
        hazard=None
    )

    r_conduit = Room(
        id="conduit",
        x=1, y=1, z=0,
        sector="Sector 1: Engineering",
        title="Maintenance Conduit 12",
        description="A claustrophobic corridor packed with bundles of optical fiber and liquid nitrogen coolant pipes that hiss faintly.",
        exits={"south": "cargo_bay", "north": "hydroponics"},
        items=[],
        terminal=TerminalNode(
            id="term_conduit",
            name="Environmental Diagnostic Node",
            security_level=2,
            log_content="LOG 884-B: 'Atmospheric scrubbers offline in Sector 3. Quarantine protocol initiated by Dr. Sorenson.'"
        )
    )

    r_promenade = Room(
        id="promenade",
        x=0, y=1, z=0,
        sector="Sector 1: Habitation",
        title="Habitation Promenade",
        description="Once the station's central social thoroughfare. Glitching augmented-reality advertisements drift through the vacant hall.",
        exits={"south": "airlock_1", "north": "clinic", "west": "lounge"},
        items=[],
        terminal=TerminalNode(
            id="term_prom",
            name="Public Mesh Access Kiosk",
            security_level=1,
            log_content="EVACUATION ALERT: All personnel to emergency egocasting shuttles. Do NOT attempt to contact Server Core."
        )
    )

    r_lounge = Room(
        id="lounge",
        x=-1, y=1, z=0,
        sector="Sector 1: Habitation",
        title="The Drifting Nomad Bar",
        description="A zero-g bar lined with magnetic stools and shattered synthetic glass. Neon holographic signs buzz softly in the corner.",
        exits={"east": "promenade"},
        items=[item_psi_amulet],
        npcs=[npc_zephyr]
    )

    r_clinic = Room(
        id="clinic",
        x=0, y=2, z=0,
        sector="Sector 1: Habitation",
        title="Resleeving Clinic Epsilon",
        description="Rows of vertical nutrient-fluid resleeving vats. Two cloned biomorphs float in stasis, awaiting ego-transfer. Backup beacons pulse slowly.",
        exits={"south": "promenade", "east": "hydroponics"},
        items=[item_nanite_med, item_neuro_stabilizer],
        terminal=TerminalNode(
            id="term_clinic",
            name="Cortical Stack Backup Transceiver",
            security_level=3,
            log_content="CLINIC STATUS: Automated resleeving vats primed. Stack recovery protocols active for Sentinel agents."
        )
    )

    # --- Sector 2: Hydroponics & Life Support ---
    r_hydroponics = Room(
        id="hydroponics",
        x=1, y=2, z=0,
        sector="Sector 2: Life Support",
        title="Hydroponics Biome",
        description="Towering cylindrical aeroponic arrays covered in pulsating luminescent violet fungal growths. The air smells sharply of ozone and decay.",
        exits={"west": "clinic", "south": "conduit", "north": "incubator"},
        items=[],
        hazard="Sporadic Bio-Toxins"
    )

    r_incubator = Room(
        id="incubator",
        x=1, y=3, z=0,
        sector="Sector 2: Life Support",
        title="Bio-Culture Incubator",
        description="Shattered incubation vats spill nutrient sludge across the deck. Emergency bio-hazard lights bathe the lab in blood red.",
        exits={"south": "hydroponics", "east": "server_hall"},
        items=[],
        npcs=[npc_sorenson]
    )

    # --- Sector 3: Server Hub & Nanofabrication ---
    r_server_hall = Room(
        id="server_hall",
        x=2, y=3, z=0,
        sector="Sector 3: Nanofabrication",
        title="Sub-Zero Server Hall",
        description="The temperature drops below freezing. Banks of superconducting quantum server blades glow ice blue behind vacuum-sealed partitions.",
        exits={"west": "incubator", "south": "nanofab", "north": "quantum_core"},
        items=[],
        terminal=TerminalNode(
            id="term_server",
            name="Security Subsystem Router",
            security_level=3,
            log_content="CRITICAL: Mesh contagion detected. Quarantine lockdown engaged on Vault Blast Doors."
        )
    )

    r_nanofab = Room(
        id="nanofab",
        x=2, y=2, z=0,
        sector="Sector 3: Nanofabrication",
        title="Cornucopia Nanofabrication Lab",
        description="A high-end molecular assembler sits in the center of the room, humming on standby. Workbenches are littered with dismantled tech.",
        exits={"north": "server_hall"},
        items=[item_emp_grenade]
    )

    r_quantum_core = Room(
        id="quantum_core",
        x=2, y=4, z=0,
        sector="Sector 3: Core",
        title="Quantum Core & Security Hub",
        description="A cathedral-like chamber dominated by a spherical optical quantum processing sphere suspended in magnetic fields.",
        exits={"south": "server_hall", "east": "quarantine_airlock"},
        locked_exits={"east": "quarantine_keycard"},
        npcs=[npc_reaper]
    )

    # --- Sector 4: TITAN Quarantine Vault ---
    r_vault_airlock = Room(
        id="quarantine_airlock",
        x=3, y=4, z=0,
        sector="Sector 4: Quarantine Vault",
        title="Quarantine Blast Airlock",
        description="Reinforced depleted-uranium blast doors etched with radiation and bio-hazard hazard sigils. An iris scanner monitors access.",
        exits={"west": "quantum_core", "east": "containment_core"},
        items=[]
    )

    r_containment = Room(
        id="containment_core",
        x=4, y=4, z=0,
        sector="Sector 4: Quarantine Vault",
        title="TITAN Containment Chamber",
        description="The station's darkest sanctuary. The walls have melted into non-Euclidean obsidian fractal patterns. A pulsating needlecast antenna rises above an alien obelisk.",
        exits={"west": "quarantine_airlock"},
        items=[],
        npcs=[npc_exsurgent],
        terminal=TerminalNode(
            id="term_needlecast",
            name="Off-Station Needlecast Transmitter",
            security_level=4,
            log_content="TRANSMITTER READY: Broadcast ego backup or station purge command to complete Firewall Mission."
        ),
        hazard="Psychic Resonance / Exsurgent Contagion"
    )

    # Index into dictionary
    for r in [r_airlock, r_cargo, r_conduit, r_promenade, r_lounge, r_clinic,
              r_hydroponics, r_incubator, r_server_hall, r_nanofab, r_quantum_core,
              r_vault_airlock, r_containment]:
        rooms[r.id] = r

    return rooms


def render_ascii_radar(rooms: Dict[str, Room], current_room_id: str) -> str:
    """Renders a 9x9 tactical ASCII radar map showing explored sectors and current position."""
    cur = rooms.get(current_room_id)
    if not cur:
        return "[ RADAR OFFLINE ]"

    cx, cy = cur.x, cur.y
    grid = [["  " for _ in range(7)] for _ in range(7)]

    for r_id, r in rooms.items():
        gx = r.x - cx + 3
        gy = -(r.y - cy) + 3  # Invert Y so North is Up

        if 0 <= gx < 7 and 0 <= gy < 7:
            if r_id == current_room_id:
                grid[gy][gx] = "[@]"
            elif r.visited:
                if r.npcs and any(n.is_alive() for n in r.npcs):
                    grid[gy][gx] = "[!]"  # Entity
                elif r.items:
                    grid[gy][gx] = "[*]"  # Item
                elif r.terminal:
                    grid[gy][gx] = "[#]"  # Terminal
                else:
                    grid[gy][gx] = "[.]"  # Explored room
            else:
                # Adjacent unvisited rooms visible on radar
                is_adj = any(target == r_id for target in cur.exits.values())
                if is_adj:
                    grid[gy][gx] = "(?)"

    lines = ["┌─────────────────────────┐"]
    for row in grid:
        lines.append("│ " + " ".join(row) + " │")
    lines.append("└─────────────────────────┘")
    lines.append(f"[@]=YOU [!]=ENTITY [*]=ITEM [#]=NODE")
    return "\n".join(lines)
