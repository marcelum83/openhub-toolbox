# 🌌 Eclipse Phase: The Cassini Incident (Roguelike MUD)

An ARL-compliant transhuman sci-fi horror Roguelike MUD built as a native OpenHub module for Linux and Google Pixel 7a. Features an LLM-driven Game Master, deterministic d100 skill check engine, Ego/Morph resleeving loop, interactive visual radar canvas, operative character creation, typewriter streaming, and branching multiple endings.

---

## 🧬 Transhuman Mechanics & New Features

### 1. 📇 Operative Character Creation Dossier
At the start of every run (or by tapping `[DOS]`), configure your transhuman operative:
- **Operative Callsign**: Choose your agent handle (e.g. *Vagabond*, *Acheron*, *Kestrel*).
- **Ego Background & Archetype**:
  - **Firewall Sentinel**: +15 Infosec, +10 Guns, +5 Fray; starts with *Tactical Shard Pistol*.
  - **Hypercorp Infiltrator**: +15 Interface, +15 Kinesics, +10 Perception; starts with *Faraday Psi-Baffle*.
  - **Extrasolar Gatecrasher**: +15 Athletics, +15 Perception, +10 Fray; starts with *Micro-EMP Charge*.
  - **Async Psychic Sleeper**: +10 Willpower, +10 Intuition, +10 Infosec; attuned to Watts-MacLeod psi sleights; starts with *Neuro-Chemical Stabilizer*.
- **Starting Sleeve / Morph**:
  - *Steel Synthmorph Mk-IV* (Vacuum proof, high kinetic armor)
  - *Olympian Bio-Athlete* (Enhanced stamina and somatic prowess)
  - *Ghost Infiltration Spec* (Chameleon skin and thermal dampers)
  - *Splicer Biomorph* (Classic balanced transhuman body)
- **Personal Muse AI Persona**:
  - *Mnemosyne*: Analytical, tactical calculation.
  - *Loki*: Sardonic, witty anarchist hacker.
  - *Aegis*: Stoic, formal military defense AI.

---

### 2. 🗺️ Holographic Visual Radar Canvas & Tap-to-Move
Tap the **`[🗺️ RADAR]`** button in the top header to toggle the live visual radar view:
- **Holographic HUD**: Circular distance rings, crosshairs, and a sweeping radar beam rotating in real-time.
- **Sector Nodes**: Color-coded chambers (Sector 1 Cyan, Sector 2 Emerald, Sector 3 Amber, Sector 4 Violet).
- **Blips**:
  - `[@]` (Pulsing Cyan): Current player location.
  - `[!]` (Red Blip): Active entity/enemy.
  - `[*]` (Gold Blip): Uncollected item/weapon.
  - `[#]` (Cyan Blip): Hackable mesh terminal node.
- **Interactive Tap-to-Move**: Tap any adjacent room on the radar canvas to navigate there immediately without typing!

---

### 3. ⚡ Typewriter Streaming Terminal Log
- Narrative text from the Game Master, Muse, and NPCs now streams token-by-token with a snappy phosphor CRT cadence.
- **Tap to Flush**: Tap anywhere on the terminal to instantly skip the typing animation and display the full text immediately.
- Preserves all Kivy BBCode tags without visual distortion.

---

### 4. 🔀 Branching Multiple Endings & Epilogue Chronicles
When reaching the *Needlecast Array* in Sector 4 (`term_needlecast`), choose how to conclude your mission:
1. **Firewall Protocol Omega (`ending purge`)**:
   - Lock the station's orbital thrusters into a descent burn. Cassini Outpost Epsilon-9 falls into the crushing hydrogen depths of Saturn, incinerating the TITAN outbreak.
2. **The Golden Stack (`ending hypercorp`)**:
   - Extract the pristine TITAN nanite code and needlecast it to a private hypercorp bidding syndicate in exchange for an immortal luxury lifestyle.
3. **The Pandora Incursion (`ending gatecrash`)**:
   - Overload the containment core to stabilize the alien singularity. Step through the Pandora Gate threshold onto an uncharted extrasolar world.
4. **Ghost in the Mesh (`ending infomorph`)**:
   - Strip away physical flesh and metal, uploading your consciousness into the interplanetary Mesh as an untraceable digital ghost.

Each ending generates an LLM-narrated chronicle and an Operative Record tracking your final sleeve, total resleeves, cognitive traumas, and survived turns.

---

## 🎮 Controls & Interface

### Tactical Touch Deck
- **D-Pad**: `[▲ N]`, `[◀ W]`, `[▼ S]`, `[▶ E]`
- **Quick Action Chips**:
  - `[👁 LOOK]`: Re-scans current chamber.
  - `[🎒 INV]`: Displays sleeve inventory and equipped weapons.
  - `[📡 ASCII]`: Displays the legacy ASCII radar map.
  - `[🗺️ RADAR]`: Toggles the visual radar canvas split-screen.
  - `[🤖 MUSE]`: Queries your embedded AI assistant.
  - `[⚡ HACK]`: Infiltrates local mesh terminal nodes.
  - `[🔄 RESLEEVE]`: Transfers your ego into a new body at Clinic Epsilon.
  - `[DOS]`: Opens the Operative Character Creation Dossier.

### Command Prompt Examples
- `go <north|south|east|west>`
- `take <item>` / `drop <item>` / `use <item>`
- `hack <terminal>`
- `attack <enemy>`
- `talk <npc> <message>`
- `muse <query>`
- `ending <purge|hypercorp|gatecrash|infomorph>`
- Freeform Roleplay: *"I overload the coolant line with my shard pistol to freeze the doorway"*

---

## 🚀 Running the Game

### Within OpenHub:
```bash
cd /home/mike/Documents/pixel
bash run.sh
```
Tap **Eclipse Phase MUD** (`[EP]` badge) in the app drawer.

### Standalone Direct Launch:
```bash
cd /home/mike/Documents/pixel
python3 modules/eclipse_mud/main.py
```
