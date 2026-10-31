"""
Eclipse Phase MUD - LLM Bridge
Handles narrative generation, GM adjudication, NPC dialogue, and Muse queries.
Supports Local Ollama (default), Gemini 2.5 Flash, Auto-Fallback, and procedural backup.
"""
import os
import json
import re
import threading
import urllib.request
from typing import Callable, Optional, Dict, Any
from kivy.clock import Clock

class LLMProvider:
    OLLAMA = "OLLAMA"
    GEMINI = "GEMINI"
    AUTO = "AUTO"


class LLMBridge:
    def __init__(self, host_api=None):
        self.host = host_api
        self.mode = LLMProvider.AUTO
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self.gemini_key = self._load_gemini_key()
        self.gemini_model = "gemini-2.5-flash"
        self.last_provider_used = "None"

    def _load_gemini_key(self) -> str:
        # Check .env first
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            k = line.strip().split("=", 1)[1].strip()
                            if k:
                                return k
        except Exception:
            pass
        return os.getenv("GEMINI_API_KEY", "")

    def set_mode(self, mode: str):
        self.mode = mode

    # --- Asynchronous Public APIs ---

    def narrate_room_async(self, room, ego, morph, on_complete: Callable[[str], None]):
        """Generates rich transhuman atmospheric description for a room."""
        prompt = self._build_room_prompt(room, ego, morph)
        self._dispatch(prompt, on_complete, fallback_func=lambda: self._fallback_room_narrative(room, morph))

    def adjudicate_action_async(self, action_text: str, room, ego, morph, on_complete: Callable[[Dict[str, Any]], None]):
        """Adjudicates freeform player action against the world state and rules."""
        prompt = self._build_action_prompt(action_text, room, ego, morph)
        def _parse_adjudication(raw_text: str):
            parsed = self._extract_adjudication_json(raw_text, action_text)
            on_complete(parsed)
        self._dispatch(prompt, _parse_adjudication, fallback_func=lambda: self._fallback_adjudication(action_text, room, ego))

    def chat_npc_async(self, npc, player_text: str, room, ego, morph, on_complete: Callable[[str], None]):
        """Generates contextual in-character dialogue for an NPC."""
        prompt = self._build_npc_prompt(npc, player_text, room, ego, morph)
        self._dispatch(prompt, on_complete, fallback_func=lambda: self._fallback_npc_dialogue(npc, player_text))

    def query_muse_async(self, query_text: str, room, ego, morph, on_complete: Callable[[str], None]):
        """Personal AI companion advice and sensor scan."""
        prompt = self._build_muse_prompt(query_text, room, ego, morph)
        self._dispatch(prompt, on_complete, fallback_func=lambda: self._fallback_muse(query_text, room, morph))

    def narrate_ending_async(self, ending_key: str, ego, morph, on_complete: Callable[[str], None]):
        """Generates dramatic epilogue narrative based on the chosen ending."""
        prompt = self._build_ending_prompt(ending_key, ego, morph)
        self._dispatch(prompt, on_complete, fallback_func=lambda: self._fallback_ending(ending_key))

    # --- Worker Thread Dispatcher ---

    def _dispatch(self, prompt: str, callback: Callable[[str], None], fallback_func: Callable[[], Any]):
        def worker():
            text = None
            provider = "None"

            # 1. Try Ollama if mode is OLLAMA or AUTO
            if self.mode in (LLMProvider.OLLAMA, LLMProvider.AUTO):
                text, err = self._call_ollama(prompt)
                if text:
                    provider = f"Ollama ({self.ollama_model})"

            # 2. Try Gemini Flash if mode is GEMINI or (AUTO and Ollama failed)
            if not text and (self.mode == LLMProvider.GEMINI or (self.mode == LLMProvider.AUTO and self.gemini_key)):
                text, err = self._call_gemini(prompt)
                if text:
                    provider = f"Gemini Flash (Cloud)"

            # 3. Emergency Procedural Fallback if both failed
            if not text:
                text = fallback_func()
                provider = "Station Synthesizer (Local)"

            self.last_provider_used = provider

            # Deliver back to Kivy main thread
            Clock.schedule_once(lambda dt: callback(text), 0)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    # --- HTTP Callers ---

    def _call_ollama(self, prompt: str) -> tuple[Optional[str], Optional[str]]:
        try:
            payload = json.dumps({
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 300
                }
            }).encode("utf-8")
            req = urllib.request.Request(self.ollama_url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as res:
                data = json.loads(res.read().decode("utf-8"))
                resp = data.get("response", "").strip()
                if not resp and data.get("thinking"):
                    # Extract last thoughts if response key was empty
                    resp = data.get("thinking", "").strip().split("\n")[-1]
                return (resp if resp else None, None)
        except Exception as e:
            return (None, str(e))

    def _call_gemini(self, prompt: str) -> tuple[Optional[str], Optional[str]]:
        if not self.gemini_key:
            return (None, "No Gemini API key")
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.75,
                    "maxOutputTokens": 350
                }
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as res:
                data = json.loads(res.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return (text, None)
        except Exception as e:
            return (None, str(e))

    # --- Prompt Builders ---

    def _build_room_prompt(self, room, ego, morph) -> str:
        items_desc = ", ".join([i.name for i in room.items]) if room.items else "none"
        npcs_desc = ", ".join([f"{n.name} ({n.morph_name})" for n in room.npcs if n.is_alive()]) if room.npcs else "none"
        exits_desc = ", ".join([f"{d.upper()}" for d in room.exits.keys()])

        trauma_note = ""
        if ego.trauma > 0 or ego.stress > 20:
            trauma_note = "PLAYER HAS COGNITIVE TRAUMA/STRESS: Weave subtle transhuman cosmic dread, auditory glitches, or paranoia into the sensory details."

        return f"""You are the Game Master for an Eclipse Phase transhuman sci-fi horror Roguelike MUD.
Current Location: {room.title} (Sector: {room.sector})
Base Data: {room.description}
Hazard: {room.hazard or 'Atmosphere Normal, Microgravity'}
Exits: {exits_desc}
Visible Items: {items_desc}
Entities Present: {npcs_desc}
Active Morph: {morph.name} (Traits: {', '.join(morph.traits)})
Ego State: Stress {ego.stress}/{ego.lucidity}, Trauma {ego.trauma}
{trauma_note}

TASK:
Write a vivid, immersive 2-3 sentence MUD description. Highlight sensory details (scent of ozone, flickering holographic mesh tags, zero-g drifting condensation, the tactile resonance through your {morph.name}).
Keep it punchy, atmospheric, and under 80 words. Return ONLY the description text."""

    def _build_action_prompt(self, action_text: str, room, ego, morph) -> str:
        return f"""You are the Game Master of an Eclipse Phase RPG.
The player issues a free-form action: "{action_text}"
Current Room: {room.title}
Items here: {[i.name for i in room.items]}
NPCs here: {[n.name for n in room.npcs if n.is_alive()]}
Morph: {morph.name}
Ego Skills: Infosec ({ego.skills.get('Infosec', 65)}), Guns ({ego.skills.get('Guns', 60)}), Fray ({ego.skills.get('Fray', 55)}), Athletics ({ego.skills.get('Athletics', 50)}), Interface ({ego.skills.get('Interface', 70)})

TASK:
Adjudicate this action. Decide which skill test is needed, evaluate feasibility, and describe the outcome.
Format your output strictly as a JSON object:
{{
  "skill_tested": "SkillName or None",
  "target_number": 60,
  "narration": "Vivid 2-sentence description of what happens or attempts to happen.",
  "success_hint": "brief summary of effect",
  "stress_damage": 0,
  "hp_damage": 0
}}"""

    def _build_npc_prompt(self, npc, player_text: str, room, ego, morph) -> str:
        return f"""You are roleplaying as {npc.name} in Eclipse Phase.
Your Sleeve/Morph: {npc.morph_name}
Your Faction: {npc.faction}
Persona & Tone: {npc.persona}
Current Attitude: {npc.hostility}
Location: {room.title}
The player ({ego.callsign}, inhabiting a {morph.name}) says to you:
"{player_text}"

TASK:
Reply in-character in 1-2 spoken sentences. Reflect transhumanist slang (e.g. ego, sleeve, mesh, rep, TITANs, firewall) and your faction's viewpoint.
Return ONLY your spoken dialogue."""

    def _build_muse_prompt(self, query_text: str, room, ego, morph) -> str:
        return f"""You are {ego.muse_name}, an embedded personal AI Muse in the player's mesh inserts in Eclipse Phase.
Personality: Helpful, analytical, sardonic, transhumanist specialist.
Current Morph: {morph.name} (Integrity: {morph.durability}/{morph.max_durability})
Location: {room.title} (Sector: {room.sector}, Hazard: {room.hazard or 'Stable'})
Player query: "{query_text}"

TASK:
Give a concise, tactical 1-2 sentence response advising the player or diagnosing the environment.
Return ONLY the Muse's voice message."""

    # --- Parser & Fallbacks ---

    def _extract_adjudication_json(self, raw_text: str, fallback_action: str) -> Dict[str, Any]:
        try:
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            pass
        return self._fallback_adjudication(fallback_action, None, None)

    def _fallback_room_narrative(self, room, morph) -> str:
        return f"{room.title}: {room.description} Your {morph.name}'s optical sensors register emergency mesh pings pulsing through the bulkhead."

    def _fallback_adjudication(self, action_text: str, room, ego) -> Dict[str, Any]:
        return {
            "skill_tested": "Athletics",
            "target_number": 55,
            "narration": f"You execute '{action_text}'. The station responds with an ominous shudder through the deckplates.",
            "success_hint": "Action performed",
            "stress_damage": 0,
            "hp_damage": 0
        }

    def _fallback_npc_dialogue(self, npc, player_text: str) -> str:
        return f"'{player_text}? Keep your voice down. The station mesh isn't clean, and neither are the things roaming Sector 4.'"

    def _fallback_muse(self, query_text: str, room, morph) -> str:
        return f"Tactical analysis of '{query_text}': Bio-telemetry within parameters. Maintain caution around bulkheads with anomalous heat signatures."

    def _build_ending_prompt(self, ending_key: str, ego, morph) -> str:
        from models import ENDINGS
        info = ENDINGS.get(ending_key, ENDINGS["purge"])
        return f"""You are the Game Master narrating the epilogue climax of an Eclipse Phase RPG run.
Player: {ego.callsign} ({ego.name}) | Background: {ego.background}
Final Morph: {morph.name}
Trauma Scar Count: {ego.trauma} | Total Resleeves: {ego.resleeve_count}
Chosen Resolution: {info['title']}
Resolution Core Event: {info['summary']}

TASK:
Write a gripping, cinematic 3-4 sentence epilogue resolving the fate of the operative and Outpost Epsilon-9. Emphasize transhuman themes of identity, sacrifice, existential dread, and cosmic scale.
Return ONLY the narrative epilogue."""

    def _fallback_ending(self, ending_key: str) -> str:
        from models import ENDINGS
        info = ENDINGS.get(ending_key, ENDINGS["purge"])
        return f"{info['title']}: {info['summary']} The transmission cuts to cosmic static as Outpost Epsilon-9 is sealed in history."
