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

    # Icon Palettes Mapping (Universal Monograms + High-Contrast Accents)
    MODULE_ICONS = {
        "level": {"badge": "LVL", "symbol": "◎", "bg": (0.06, 0.20, 0.14, 1.0), "border": (0.15, 0.75, 0.40, 1.0), "accent": (0.20, 0.90, 0.50, 1.0)},
        "spirit_level": {"badge": "LVL", "symbol": "◎", "bg": (0.06, 0.20, 0.14, 1.0), "border": (0.15, 0.75, 0.40, 1.0), "accent": (0.20, 0.90, 0.50, 1.0)},
        "metronome": {"badge": "MET", "symbol": "♫", "bg": (0.22, 0.12, 0.04, 1.0), "border": (0.95, 0.60, 0.05, 1.0), "accent": (1.0, 0.70, 0.15, 1.0)},
        "converter": {"badge": "CVT", "symbol": "⇄", "bg": (0.04, 0.18, 0.24, 1.0), "border": (0.02, 0.71, 0.83, 1.0), "accent": (0.10, 0.85, 1.0, 1.0)},
        "unit_converter": {"badge": "CVT", "symbol": "⇄", "bg": (0.04, 0.18, 0.24, 1.0), "border": (0.02, 0.71, 0.83, 1.0), "accent": (0.10, 0.85, 1.0, 1.0)},
        "compass": {"badge": "CMP", "symbol": "✦", "bg": (0.16, 0.06, 0.22, 1.0), "border": (0.54, 0.36, 0.96, 1.0), "accent": (0.70, 0.50, 1.0, 1.0)},
        "stopwatch": {"badge": "TIM", "symbol": "⏱", "bg": (0.06, 0.16, 0.25, 1.0), "border": (0.15, 0.55, 0.95, 1.0), "accent": (0.30, 0.70, 1.0, 1.0)},
        "decibel": {"badge": "dB", "symbol": "∿", "bg": (0.24, 0.06, 0.10, 1.0), "border": (0.91, 0.30, 0.24, 1.0), "accent": (1.0, 0.40, 0.35, 1.0)},
        "decibel_meter": {"badge": "dB", "symbol": "∿", "bg": (0.24, 0.06, 0.10, 1.0), "border": (0.91, 0.30, 0.24, 1.0), "accent": (1.0, 0.40, 0.35, 1.0)},
        "reaction": {"badge": "RXT", "symbol": "⚡", "bg": (0.24, 0.16, 0.04, 1.0), "border": (0.98, 0.75, 0.10, 1.0), "accent": (1.0, 0.85, 0.20, 1.0)},
        "monster_battle": {"badge": "RPG", "symbol": "⚔", "bg": (0.16, 0.05, 0.26, 1.0), "border": (0.85, 0.20, 0.65, 1.0), "accent": (1.0, 0.35, 0.80, 1.0)},
        "nexus_remote": {"badge": "PC", "symbol": "⌨", "bg": (0.05, 0.16, 0.24, 1.0), "border": (0.02, 0.71, 0.83, 1.0), "accent": (0.10, 0.85, 1.0, 1.0)},
        "flashlight": {"badge": "LGT", "symbol": "☀", "bg": (0.22, 0.20, 0.05, 1.0), "border": (0.95, 0.85, 0.15, 1.0), "accent": (1.0, 0.95, 0.30, 1.0)},
        "lux_meter": {"badge": "LUX", "symbol": "☼", "bg": (0.24, 0.14, 0.04, 1.0), "border": (0.95, 0.55, 0.10, 1.0), "accent": (1.0, 0.65, 0.20, 1.0)},
        "pitch_tuner": {"badge": "TUN", "symbol": "♯", "bg": (0.08, 0.08, 0.25, 1.0), "border": (0.40, 0.45, 0.95, 1.0), "accent": (0.55, 0.60, 1.0, 1.0)},
        "cellular_automata": {"badge": "BIO", "symbol": "☷", "bg": (0.06, 0.22, 0.18, 1.0), "border": (0.10, 0.80, 0.60, 1.0), "accent": (0.20, 0.95, 0.75, 1.0)},
        "dice_roller": {"badge": "DCE", "symbol": "⚄", "bg": (0.20, 0.06, 0.22, 1.0), "border": (0.75, 0.30, 0.90, 1.0), "accent": (0.90, 0.45, 1.0, 1.0)},
        "bouncing_ball": {"badge": "BAL", "symbol": "●", "bg": (0.24, 0.10, 0.05, 1.0), "border": (0.95, 0.45, 0.15, 1.0), "accent": (1.0, 0.55, 0.25, 1.0)},
        "agent": {"badge": "ACE", "symbol": "◈", "bg": (0.18, 0.06, 0.26, 1.0), "border": (0.65, 0.35, 0.95, 1.0), "accent": (0.80, 0.50, 1.0, 1.0)},
        "forge": {"badge": "DEV", "symbol": "⚡", "bg": (0.05, 0.20, 0.22, 1.0), "border": (0.05, 0.80, 0.75, 1.0), "accent": (0.15, 0.95, 0.90, 1.0)},
        "settings": {"badge": "CFG", "symbol": "⚙", "bg": (0.12, 0.12, 0.16, 1.0), "border": (0.60, 0.60, 0.70, 1.0), "accent": (0.80, 0.80, 0.90, 1.0)},
    }

    @classmethod
    def get_icon_meta(cls, mod_id, category="Tools", is_scratch=False):
        """Returns {badge, symbol, bg, border, accent} for a module id."""
        key = mod_id.lower().replace("-", "_")
        if key in cls.MODULE_ICONS:
            return cls.MODULE_ICONS[key]
        
        if is_scratch or "tmp_" in key or "scratch" in key:
            # Generate short 3-letter badge from name or slug
            clean = "".join(c for c in key if c.isalpha())
            b_txt = clean[:3].upper() if len(clean) >= 3 else "LAB"
            return {
                "badge": b_txt,
                "symbol": "🧪",
                "bg": (0.18, 0.06, 0.26, 1.0),
                "border": (0.65, 0.35, 0.95, 0.9),
                "accent": (0.80, 0.50, 1.0, 1.0)
            }
        
        cat_lower = (category or "").lower()
        clean = "".join(c for c in key if c.isalpha())
        b_txt = clean[:3].upper() if len(clean) >= 3 else "MOD"

        if "field" in cat_lower or "sensor" in cat_lower:
            return {"badge": b_txt, "symbol": "✦", "bg": (0.06, 0.18, 0.18, 1.0), "border": (0.10, 0.80, 0.60, 0.9), "accent": (0.20, 0.95, 0.75, 1.0)}
        elif "agent" in cat_lower or "ai" in cat_lower:
            return {"badge": b_txt, "symbol": "◈", "bg": (0.18, 0.06, 0.26, 1.0), "border": (0.65, 0.35, 0.95, 0.9), "accent": (0.80, 0.50, 1.0, 1.0)}
        elif "experiment" in cat_lower or "game" in cat_lower:
            return {"badge": b_txt, "symbol": "⚔", "bg": (0.22, 0.06, 0.18, 1.0), "border": (0.85, 0.20, 0.65, 0.9), "accent": (1.0, 0.35, 0.80, 1.0)}
        else:
            return {"badge": b_txt, "symbol": "●", "bg": (0.06, 0.16, 0.24, 1.0), "border": (0.02, 0.71, 0.83, 0.9), "accent": (0.10, 0.85, 1.0, 1.0)}

