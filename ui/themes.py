"""
OpenHub Design System & Color Tokens
Obsidian dark background with glowing neon cyberpunk accents.
"""
class ColorSystem:
    # Backgrounds
    BG_DARK = (0.05, 0.05, 0.08, 1.0)       # #0D0D14
    SURFACE = (0.09, 0.09, 0.13, 1.0)       # #171721
    SURFACE_HOVER = (0.13, 0.13, 0.19, 1.0) # #212130
    SURFACE_BORDER = (0.2, 0.2, 0.28, 0.6)
    DRAWER_BG = (0.07, 0.07, 0.11, 0.98)     # Deep dark overlay
    DOCK_BG = (0.10, 0.10, 0.15, 0.85)       # Translucent dock
    
    # Accent Colors
    PRIMARY = (0.02, 0.71, 0.83, 1.0)       # Cyber Cyan #05B4D4
    SECONDARY = (0.54, 0.36, 0.96, 1.0)     # Neon Violet #8A5CF5
    SUCCESS = (0.15, 0.68, 0.38, 1.0)       # Emerald Green #27AE60
    WARNING = (0.95, 0.61, 0.07, 1.0)       # Amber Gold #F39C12
    DANGER = (0.91, 0.30, 0.24, 1.0)        # Crimson Red #E74C3C
    ORANGE = (0.95, 0.45, 0.15, 1.0)        # Flame Orange
    TEAL = (0.05, 0.80, 0.75, 1.0)          # Electric Teal
    MAGENTA = (0.85, 0.20, 0.65, 1.0)       # Cyber Magenta
    
    # Text
    TEXT_PRIMARY = (0.95, 0.95, 0.97, 1.0)
    TEXT_MUTED = (0.65, 0.65, 0.75, 1.0)
    TEXT_HINT = (0.45, 0.45, 0.55, 1.0)

    # Icon Palettes Mapping
    MODULE_ICONS = {
        "level": {"icon": "🟢", "bg": (0.08, 0.22, 0.15, 1.0), "border": (0.15, 0.68, 0.38, 0.9)},
        "metronome": {"icon": "⏱️", "bg": (0.22, 0.12, 0.05, 1.0), "border": (0.95, 0.61, 0.07, 0.9)},
        "converter": {"icon": "📐", "bg": (0.05, 0.18, 0.24, 1.0), "border": (0.02, 0.71, 0.83, 0.9)},
        "compass": {"icon": "🧭", "bg": (0.18, 0.08, 0.22, 1.0), "border": (0.54, 0.36, 0.96, 0.9)},
        "stopwatch": {"icon": "⏳", "bg": (0.08, 0.18, 0.25, 1.0), "border": (0.15, 0.55, 0.95, 0.9)},
        "decibel": {"icon": "🔊", "bg": (0.24, 0.08, 0.12, 1.0), "border": (0.91, 0.30, 0.24, 0.9)},
        "reaction": {"icon": "⚡", "bg": (0.24, 0.18, 0.05, 1.0), "border": (0.98, 0.75, 0.10, 0.9)},
        "monster_battle": {"icon": "👾", "bg": (0.16, 0.06, 0.26, 1.0), "border": (0.85, 0.20, 0.65, 0.9)},
        "nexus_remote": {"icon": "🖥️", "bg": (0.06, 0.16, 0.24, 1.0), "border": (0.02, 0.71, 0.83, 0.9)},
        "flashlight": {"icon": "🔦", "bg": (0.22, 0.20, 0.06, 1.0), "border": (0.95, 0.85, 0.15, 0.9)},
        "lux_meter": {"icon": "☀️", "bg": (0.24, 0.14, 0.05, 1.0), "border": (0.95, 0.55, 0.10, 0.9)},
        "pitch_tuner": {"icon": "🎵", "bg": (0.10, 0.10, 0.25, 1.0), "border": (0.40, 0.45, 0.95, 0.9)},
        "cellular_automata": {"icon": "🧬", "bg": (0.08, 0.22, 0.18, 1.0), "border": (0.10, 0.80, 0.60, 0.9)},
        "dice_roller": {"icon": "🎲", "bg": (0.20, 0.08, 0.22, 1.0), "border": (0.75, 0.30, 0.90, 0.9)},
        "bouncing_ball": {"icon": "🏀", "bg": (0.24, 0.12, 0.06, 1.0), "border": (0.95, 0.45, 0.15, 0.9)},
        "agent": {"icon": "🧠", "bg": (0.18, 0.08, 0.26, 1.0), "border": (0.65, 0.35, 0.95, 0.9)},
        "forge": {"icon": "⚡", "bg": (0.06, 0.20, 0.22, 1.0), "border": (0.05, 0.80, 0.75, 0.9)},
        "settings": {"icon": "⚙️", "bg": (0.14, 0.14, 0.18, 1.0), "border": (0.60, 0.60, 0.70, 0.9)},
    }

    @classmethod
    def get_icon_meta(cls, mod_id, category="Tools", is_scratch=False):
        """Returns {icon, bg, border} for a module id."""
        key = mod_id.lower().replace("-", "_")
        if key in cls.MODULE_ICONS:
            return cls.MODULE_ICONS[key]
        
        if is_scratch or "tmp_" in key or "scratch" in key:
            return {
                "icon": "🧪",
                "bg": (0.18, 0.08, 0.26, 1.0),
                "border": (0.65, 0.35, 0.95, 0.9)
            }
        
        cat_lower = (category or "").lower()
        if "field" in cat_lower or "sensor" in cat_lower:
            return {"icon": "🧭", "bg": (0.06, 0.18, 0.18, 1.0), "border": (0.10, 0.80, 0.60, 0.9)}
        elif "agent" in cat_lower or "ai" in cat_lower:
            return {"icon": "🧠", "bg": (0.18, 0.08, 0.26, 1.0), "border": (0.65, 0.35, 0.95, 0.9)}
        elif "experiment" in cat_lower or "game" in cat_lower:
            return {"icon": "👾", "bg": (0.22, 0.08, 0.18, 1.0), "border": (0.85, 0.20, 0.65, 0.9)}
        else:
            return {"icon": "📦", "bg": (0.08, 0.15, 0.24, 1.0), "border": (0.02, 0.71, 0.83, 0.9)}

