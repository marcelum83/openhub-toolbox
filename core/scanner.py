"""
OpenHub Module Scanner
Discovers permanent manifest-based tools in `modules/` and disposable scratch experiments in `modules/scratch/`.
"""
import os
import json
import inspect
import importlib.util
from core.security import TrustLevel

class ModuleDescriptor:
    def __init__(self, mod_id, name, category, description, entrypoint, icon=None, 
                 trust_level=TrustLevel.TRUSTED, path=None, version="1.0.0", is_scratch=False):
        self.id = mod_id
        self.name = name
        self.category = category
        self.description = description
        self.entrypoint = entrypoint
        self.icon = icon
        self.trust_level = trust_level
        self.path = path
        self.version = version
        self.is_scratch = is_scratch

class ModuleScanner:
    def __init__(self, modules_root):
        self.modules_root = os.path.abspath(modules_root)
        self.scratch_root = os.path.join(self.modules_root, "scratch")
        os.makedirs(self.modules_root, exist_ok=True)
        os.makedirs(self.scratch_root, exist_ok=True)

    def scan_all(self):
        """Scans and returns (permanent_modules, scratch_modules)."""
        permanent = []
        scratch = []

        if not os.path.exists(self.modules_root):
            return permanent, scratch

        # 1. Scan Permanent Tools in modules/*
        for item in sorted(os.listdir(self.modules_root)):
            if item == "scratch":
                continue
            item_path = os.path.join(self.modules_root, item)
            
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
                            description=data.get("description", "OpenHub tool"),
                            entrypoint=os.path.join(item_path, entrypoint),
                            icon=icon_path,
                            trust_level=data.get("trust_level", TrustLevel.TRUSTED),
                            path=item_path,
                            version=data.get("version", "1.0.0"),
                            is_scratch=False
                        )
                        permanent.append(desc)
                    except Exception as e:
                        print(f"[Scanner] Error parsing manifest in {item}: {e}")

        # 2. Scan Scratch / Temporary Experiments in modules/scratch/*.py
        if os.path.exists(self.scratch_root):
            for file in sorted(os.listdir(self.scratch_root), reverse=True):
                if file.endswith(".py") and not file.startswith("__") and not file.endswith(".tmp.py"):
                    file_path = os.path.join(self.scratch_root, file)
                    clean_name = os.path.splitext(file)[0].replace("_", " ").title()
                    desc = ModuleDescriptor(
                        mod_id=os.path.splitext(file)[0],
                        name=clean_name,
                        category="Scratch",
                        description=f"Experiment ({file})",
                        entrypoint=file_path,
                        icon=None,
                        trust_level=TrustLevel.EXPERIMENTAL,
                        path=file_path,
                        version="0.1.0",
                        is_scratch=True
                    )
                    scratch.append(desc)

        return permanent, scratch
