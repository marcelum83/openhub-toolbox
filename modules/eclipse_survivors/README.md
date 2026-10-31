# ⚔️ Eclipse Survivors: Outpost Infiltration

A 2D top-down transhuman action-roguelite dungeon exploration game built natively for **OpenHub** on Linux and Google Pixel 7a, set in the **Eclipse Phase** universe.

Inspired by *Teleglitch* and *Vampire Survivors*: navigate an expansive 2400x2000 multi-room derelict station deck, explore closed and locked chambers, auto-slide pneumatic doors, clear enemy garrisons room-by-room, hack security terminals, retrieve encryption keycards from mini-bosses, and activate the **Sector Transit Elevator** to complete the floor and descend deeper into Cassini Outpost!

---

## 🗺️ 1. Station Floor Dungeon & Exploration

Instead of continuous random circle spawns, each deck is a **persistent multi-room layout** populated with room-specific enemy garrisons:

| Sector Room | Dimensions | Threat Encounter & Objectives |
| :--- | :---: | :--- |
| **Airlock Staging Alpha** | South Hub | **Safe Starting Zone**. Sleeve diagnostic, briefing, and opening pneumatic door. |
| **Central Promenade & Hub** | `920 x 360 px` | **Hub Junction**. 4 Patrol Drones + 2 Husks. Features **Station Defense Turret Terminal**. Exits West, East, and North. |
| **Cryo-Storage & Morgue** | West Wing | **Biohazard Zone**. 5 Exsurgent Mutated Husks crawling out of pods + 1 Basilisk Spider. 4 Supply Crates. |
| **Hydroponics & Life Support** | East Wing | **Environmental Control**. 4 Basilisk Spiders + 2 Patrol Drones. Features **Neuro-Gas Vent Terminal**. |
| **Security Armory & Garrison** | Central North | **High-Security Sector**. Guarded by the **Elite Security Captain (Mini-Boss)** + 3 Patrol Drones. Purging the Captain drops the **Class-5 Encryption Keycard**! |
| **Research Bio-Labs & Server Core** | North-West | **TITAN Contagion Wing**. 4 Husks + 3 Spiders. Features **EMP Sub-Capacitor Terminal**. |
| **Sector Transit Elevator (Goal!)** | Far North | **Sealed Containment Vault**. Requires Class-5 Keycard to open blast doors. Guarded by the **Reaper Combat Mech (Floor Boss)**. Houses the **Deck Transit Elevator Console**! |

---

## 🚪 2. Pneumatic Sliding Doors & Security Locks

- **Auto-Sliding Proximity**: Walk within 85px of any unlocked doorway to smoothly slide the pneumatic bulkhead open. Doors automatically slide shut when moving away.
- **Doorway Combat & Line of Sight**: Open doorways allow flechettes, rail beams, and drones to shoot through. Closed doors block both movement and projectiles.
- **Keycard Gated Blast Doors**: The far-north transit elevator is sealed behind heavy blast doors requiring the **Class-5 Encryption Keycard** dropped by the Security Captain in the Armory.

---

## 🏆 3. Room Clearance & Floor Completion

- **Room Clearance Detection**: Entering a room triggers a location alert (`📍 ENTERING: CRYO-STORAGE`). Eliminating all hostiles in that room secures the chamber (`✓ CRYO-STORAGE SECURED! (+40 XP)`).
- **Floor Progress Tracking**: Real-time HUD tracks:
  - `DECK 1` (or `DECK 2`)
  - Current location: `📍 Central Promenade`
  - Hostiles remaining on deck: `💀 14/30 REMAINING`
  - Rooms secured: `✓ 3/7 ROOMS`
- **Floor Completion Modal**: Hacking the **Transit Elevator Console** with the floor boss eliminated triggers **`🎉 DECK SECURED // FLOOR COMPLETE!`**, awarding bonus Cortical Stack nanocores and enabling **Transit to Deck 2 (Deep Containment)** with scaled difficulty, tougher enemy variants, and preserved character build!

---

## 🧬 4. Sleeve Morph Selection on Deployment

| Morph Chassis | Icon | Specialization & Baseline Stats | Innate Starting Loadout |
| :--- | :---: | :--- | :--- |
| **Synth Chassis** | 🤖 | Heavy armored zero-g android. `140 HP`, `3.5 Armor`, `120 Spd`. | **EMP Pulse Emitter** + **Titanium Composite Plating** |
| **Fury Biomorph** | 🐆 | Predatory transgenic combat chassis. `110 HP`, `2.0 Armor`, `150 Spd`. | **Nanite Defense Cloud** + **Myomer Muscle Overclock** |
| **Menton Morph** | 🧠 | Overclocked cognitive specialist. `90 HP`, `1.5 Armor`, `+60% Pickup Suction`. | **Orbital Seeker Drone** + **Magnetic Nanite Harvester** |
| **Ghost Infiltrator** | 👤 | Agile stealth chassis. `95 HP`, `1.0 Armor`, `165 Spd`. | **Shard Flechette Pistol** + **Rapid Synapse Accelerator** |

---

## 🌟 5. Legendary Cybernetic Evolutions

| Legendary Evolution | Icon | Recipe | Combat Mechanics |
| :--- | :---: | :--- | :--- |
| **Diamond Hailstorm** | 💎 | *Shard Pistol (Lvl 5)* + *Titanium Plating* | 360-degree storm of 8 hyper-dense diamond flechettes with 3x penetration that **ricochets off station walls**. |
| **Grey Goo Singularity** | 🦠 | *Nanite Cloud (Lvl 5)* + *Rapid Synapse* | Expanding sub-molecular vortex dealing massive continuous corrosion DPS, rapid sleeve HP repair, and triggering nanocore bursts from slain hostiles. |
| **Tachyon Relativistic Lance** | ☄️⚡ | *Railgun Beam (Lvl 5)* + *Muscle Overclock* | Massive infinite-penetration relativistic plasma beam incinerating everything across entire station wings. |
| **Apex Swarm Matrix** | 🛸⚡ | *Seeker Drone (Lvl 5)* + *Nanite Harvester* | Constellation of 3 synchronized hunter-killer micro-drones emitting triangulated laser nets while auto-vacuuming nanocores within 180px. |
| **Neuro-Cascade Cataclysm** | 💥⚡ | *EMP Shock (Lvl 5)* + *Rapid Synapse* | Dual-ring catastrophic EMP shockwave stunning swarms, inflicting heavy knockback, and arcing chain-lightning between hostiles. |

---

## 🕹️ Controls

- **Desktop (Linux Keyboard)**: `WASD` or Arrow keys for 8-directional smooth movement.
- **Mobile Touch (Google Pixel 7a)**:
  - Left half of screen: Floating analog joystick.
  - Right half of screen: Tap to aim flashlight & visor.

---

## 🚀 Running the Game

```bash
cd /home/mike/Documents/pixel
python3 modules/eclipse_survivors/main.py
```
*(Or inside OpenHub's launcher via the **`[SURV]`** badge).*
