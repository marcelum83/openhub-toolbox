"""
OpenHub Home Screen Layout Manager
Handles persistence and slot management for the Android-style Home Screen grid and bottom dock.
"""
import os
import json

class HomeLayoutManager:
    def __init__(self, root_dir=None):
        if root_dir is None:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.root_dir = os.path.abspath(root_dir)
        self.data_dir = os.path.join(self.root_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.layout_file = os.path.join(self.data_dir, "home_layout.json")
        self.layout_data = self.load()

    def get_default_layout(self):
        """Returns the default curated home screen grid and dock icons."""
        return {
            "version": 1,
            # Home Screen pinned app IDs in order of grid position
            "pinned_apps": [
                "spirit_level",
                "metronome",
                "unit_converter",
                "compass",
                "reaction",
                "stopwatch",
                "decibel_meter",
                "monster_battle",
                "nexus_remote",
                "flashlight",
                "lux_meter",
                "pitch_tuner",
                "cellular_automata",
                "dice_roller",
                "bouncing_ball"
            ],
            # Bottom dock shortcuts (max 4-5)
            "dock_apps": [
                {"id": "agent", "type": "system", "name": "Agent", "icon": "🧠"},
                {"id": "forge", "type": "system", "name": "Forge", "icon": "⚡"},
                {"id": "nexus_remote", "type": "module", "name": "Remote", "icon": "🖥️"},
                {"id": "settings", "type": "system", "name": "Sync", "icon": "⚙️"}
            ]
        }

    def load(self):
        """Loads the layout from JSON file or creates defaults if missing."""
        if os.path.exists(self.layout_file):
            try:
                with open(self.layout_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "pinned_apps" in data and isinstance(data["pinned_apps"], list):
                        return data
            except Exception as e:
                print(f"[HomeLayoutManager] Error reading layout file: {e}")
        
        defaults = self.get_default_layout()
        self.save(defaults)
        return defaults

    def save(self, data=None):
        """Persists the layout data to disk."""
        if data is not None:
            self.layout_data = data
        try:
            with open(self.layout_file, "w", encoding="utf-8") as f:
                json.dump(self.layout_data, f, indent=2)
        except Exception as e:
            print(f"[HomeLayoutManager] Error saving layout file: {e}")

    def get_pinned_apps(self):
        return self.layout_data.get("pinned_apps", [])

    def is_pinned(self, mod_id):
        return mod_id in self.get_pinned_apps()

    def pin_app(self, mod_id, index=None):
        """Pins an app to the home screen grid."""
        pinned = self.get_pinned_apps()
        if mod_id in pinned:
            pinned.remove(mod_id)
        
        if index is not None and 0 <= index <= len(pinned):
            pinned.insert(index, mod_id)
        else:
            pinned.append(mod_id)
            
        self.layout_data["pinned_apps"] = pinned
        self.save()

    def unpin_app(self, mod_id):
        """Removes an app from the home screen grid."""
        pinned = self.get_pinned_apps()
        if mod_id in pinned:
            pinned.remove(mod_id)
            self.layout_data["pinned_apps"] = pinned
            self.save()
            return True
        return False

    def reorder_pinned_apps(self, new_order):
        """Updates the list of pinned apps in specific order."""
        self.layout_data["pinned_apps"] = new_order
        self.save()
