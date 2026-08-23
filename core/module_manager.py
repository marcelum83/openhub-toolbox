"""
OpenHub Module Manager
The single source of truth for creating, forking, mutating, promoting, and deleting modules.
Usable by both the UI layer and autonomous AI agents.
"""
import os
import re
import json
import shutil
from core.scanner import ModuleDescriptor, ModuleScanner
from core.security import TrustLevel

class ModuleManager:
    def __init__(self, root_dir=None):
        if root_dir is None:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.root_dir = os.path.abspath(root_dir)
        self.modules_dir = os.path.join(self.root_dir, "modules")
        self.scratch_dir = os.path.join(self.modules_dir, "scratch")
        
        os.makedirs(self.modules_dir, exist_ok=True)
        os.makedirs(self.scratch_dir, exist_ok=True)
        self.ensure_source_files()
        self.scanner = ModuleScanner(self.modules_dir)

    def ensure_source_files(self):
        """Ensures that all permanent modules have their .py source files restored from .txt if stripped by Android packager."""
        if not os.path.exists(self.modules_dir):
            return
        for item in os.listdir(self.modules_dir):
            item_path = os.path.join(self.modules_dir, item)
            if os.path.isdir(item_path):
                main_py = os.path.join(item_path, "main.py")
                main_txt = os.path.join(item_path, "main.py.txt")
                if not os.path.exists(main_py) and os.path.exists(main_txt):
                    try:
                        shutil.copyfile(main_txt, main_py)
                    except Exception as e:
                        print(f"[ModuleManager] Failed to restore {main_py}: {e}")

    def scan(self):
        """Returns (permanent_modules, scratch_modules)."""
        self.ensure_source_files()
        return self.scanner.scan_all()

    def create_scratch(self, code, prompt="custom_tool"):
        """
        Creates a new disposable scratch script in modules/scratch/.
        Filename format: tmp_NNN_<slug>.py
        """
        existing = [f for f in os.listdir(self.scratch_dir) if f.startswith("tmp_") and f.endswith(".py")]
        max_idx = 0
        for f in existing:
            m = re.match(r'^tmp_(\d+)_', f)
            if m:
                try:
                    max_idx = max(max_idx, int(m.group(1)))
                except ValueError:
                    pass
        next_idx = max_idx + 1
        
        slug = "_".join(prompt.lower().split()[:4])
        slug = re.sub(r'[^a-z0-9_]', '', slug).strip('_') or "tool"
        filename = f"tmp_{next_idx:03d}_{slug}.py"
        file_path = os.path.join(self.scratch_dir, filename)

        try:
            from core.sanitizer import CodeSanitizer
            code = CodeSanitizer.sanitize(code)
        except Exception:
            pass

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)

        return ModuleDescriptor(
            mod_id=os.path.splitext(filename)[0],
            name=slug.replace("_", " ").title(),
            category="Scratch",
            description=f"Draft: {prompt}",
            entrypoint=file_path,
            trust_level=TrustLevel.EXPERIMENTAL,
            is_scratch=True
        )

    def fork(self, descriptor, new_title=None):
        """
        Forks any module (permanent or scratch) into a new disposable scratchpad for safe experimentation.
        """
        code = self.read_code(descriptor)
        base_name = descriptor.name.lower().replace(" ", "_")
        fork_label = f"fork_{base_name}" if not new_title else new_title.lower().replace(" ", "_")
        return self.create_scratch(code, prompt=fork_label)

    def promote_to_permanent(self, descriptor, name, category="Tools", description=None):
        """
        Graduates a scratch script into a permanent module directory with a manifest.json.
        """
        mod_id = re.sub(r'[^a-z0-9_]', '', name.lower().replace(" ", "_").replace("-", "_"))
        target_dir = os.path.join(self.modules_dir, mod_id)
        os.makedirs(target_dir, exist_ok=True)

        code = self.read_code(descriptor)
        target_main = os.path.join(target_dir, "main.py")
        with open(target_main, 'w', encoding='utf-8') as f:
            f.write(code)

        desc_text = description or f"Saved tool: {name}"
        manifest = {
            "id": mod_id,
            "name": name,
            "version": "1.0.0",
            "author": "mike",
            "category": category,
            "description": desc_text,
            "entrypoint": "main.py",
            "trust_level": TrustLevel.TRUSTED
        }
        with open(os.path.join(target_dir, "manifest.json"), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)

        return ModuleDescriptor(
            mod_id=mod_id,
            name=name,
            category=category,
            description=desc_text,
            entrypoint=target_main,
            trust_level=TrustLevel.TRUSTED,
            path=target_dir,
            is_scratch=False
        )

    def delete(self, descriptor):
        """Deletes a scratch script or permanent module directory."""
        if descriptor.is_scratch:
            if os.path.exists(descriptor.entrypoint):
                os.remove(descriptor.entrypoint)
        else:
            if descriptor.path and os.path.isdir(descriptor.path):
                shutil.rmtree(descriptor.path)

    def read_code(self, descriptor):
        """Reads source code from descriptor's entrypoint."""
        entrypoint = descriptor.entrypoint
        if not os.path.exists(entrypoint):
            txt_path = entrypoint + ".txt"
            if os.path.exists(txt_path):
                try:
                    shutil.copyfile(txt_path, entrypoint)
                except Exception:
                    pass
                with open(txt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            raise FileNotFoundError(f"Source file not found: {entrypoint}")
        with open(entrypoint, 'r', encoding='utf-8') as f:
            return f.read()

    def save_code(self, descriptor, new_code):
        """Overwrites the entrypoint file with updated code."""
        with open(descriptor.entrypoint, 'w', encoding='utf-8') as f:
            f.write(new_code)
        txt_path = descriptor.entrypoint + ".txt"
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
        except Exception:
            pass

    def publish_module(self, descriptor, server_host="10.62.206.29:8080", callback=None):
        """Asynchronously publishes a tool to the Central OpenHub & GitHub Repository."""
        def _worker():
            try:
                import urllib.request
                from kivy.clock import Clock
                code = self.read_code(descriptor)
                url = f"http://{server_host}/api/modules/publish"
                payload = json.dumps({
                    "id": descriptor.id,
                    "name": descriptor.name,
                    "category": descriptor.category,
                    "description": descriptor.description,
                    "code": code
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if callback:
                        Clock.schedule_once(lambda dt: callback(True, data.get("repo_url", ""), None), 0)
            except Exception as e:
                if callback:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt, err=e: callback(False, None, str(err)), 0)

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def fetch_community_catalog(self, server_host="10.62.206.29:8080", callback=None):
        """Fetches catalog of modules from the central repository."""
        def _worker():
            try:
                import urllib.request
                from kivy.clock import Clock
                url = f"http://{server_host}/api/modules/catalog"
                req = urllib.request.Request(url, headers={"User-Agent": "OpenHub-Client"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if callback:
                        Clock.schedule_once(lambda dt: callback(True, data, None), 0)
            except Exception as e:
                if callback:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt, err=e: callback(False, None, str(err)), 0)

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def install_community_module(self, mod_id, server_host="10.62.206.29:8080", callback=None):
        """Downloads a community tool from the central repository into local storage."""
        def _worker():
            try:
                import urllib.request
                from kivy.clock import Clock
                url = f"http://{server_host}/api/modules/download/{mod_id}"
                req = urllib.request.Request(url, headers={"User-Agent": "OpenHub-Client"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    manifest = data.get("manifest", {})
                    code = data.get("code", "")
                    
                    target_dir = os.path.join(self.modules_dir, mod_id)
                    os.makedirs(target_dir, exist_ok=True)
                    with open(os.path.join(target_dir, "main.py"), "w", encoding="utf-8") as f:
                        f.write(code)
                    with open(os.path.join(target_dir, "main.py.txt"), "w", encoding="utf-8") as f:
                        f.write(code)
                    with open(os.path.join(target_dir, "manifest.json"), "w", encoding="utf-8") as f:
                        json.dump(manifest, f, indent=2)

                    if callback:
                        Clock.schedule_once(lambda dt: callback(True, mod_id, None), 0)
            except Exception as e:
                if callback:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt, err=e: callback(False, None, str(err)), 0)

        import threading
        threading.Thread(target=_worker, daemon=True).start()
