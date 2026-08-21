"""
OpenHub Module Scanner
Discovers manifest-based tools in `modules/` and standalone `.py` apps.
"""
import os
import json
import inspect
import importlib.util
from core.security import TrustLevel

class ModuleDescriptor:
    def __init__(self, mod_id, name, category, description, entrypoint, icon=None, 
                 trust_level=TrustLevel.TRUSTED, path=None, version="1.0.0", is_loose_script=False):
        self.id = mod_id
        self.name = name
        self.category = category
        self.description = description
        self.entrypoint = entrypoint
        self.icon = icon
        self.trust_level = trust_level
        self.path = path # Directory path or file path
        self.version = version
        self.is_loose_script = is_loose_script

class ModuleScanner:
    def __init__(self, modules_root):
        self.modules_root = os.path.abspath(modules_root)
        os.makedirs(self.modules_root, exist_ok=True)

    def scan(self):
        """Scans the modules directory and returns a list of ModuleDescriptors."""
        discovered = []
        if not os.path.exists(self.modules_root):
            return discovered

        for item in sorted(os.listdir(self.modules_root)):
            item_path = os.path.join(self.modules_root, item)
            
            # 1. Directory-based module with manifest.json
            if os.path.isdir(item_path):
                manifest_path = os.path.join(item_path, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        entrypoint = data.get("entrypoint", "main.py")
                        icon_file = data.get("icon", "icon.png")
                        icon_path = os.path.join(item_path, icon_file)
                        if not os.path.exists(icon_path):
                            icon_path = None
                            
                        desc = ModuleDescriptor(
                            mod_id=data.get("id", item),
                            name=data.get("name", item.replace("_", " ").title()),
                            category=data.get("category", "Tools"),
                            description=data.get("description", "OpenHub dynamic module"),
                            entrypoint=os.path.join(item_path, entrypoint),
                            icon=icon_path,
                            trust_level=data.get("trust_level", TrustLevel.TRUSTED),
                            path=item_path,
                            version=data.get("version", "1.0.0"),
                            is_loose_script=False
                        )
                        discovered.append(desc)
                    except Exception as e:
                        print(f"[Scanner] Error parsing manifest in {item}: {e}")

            # 2. Loose .py files (standalone Kivy scripts)
            elif item.endswith(".py") and not item.startswith("__") and not item.endswith(".tmp.py"):
                name = os.path.splitext(item)[0].replace("_", " ").title()
                desc = ModuleDescriptor(
                    mod_id=os.path.splitext(item)[0],
                    name=name,
                    category="Scratch",
                    description="Standalone Python / Kivy script",
                    entrypoint=item_path,
                    icon=None,
                    trust_level=TrustLevel.EXPERIMENTAL,
                    path=item_path,
                    version="0.1.0",
                    is_loose_script=True
                )
                discovered.append(desc)

        return discovered
