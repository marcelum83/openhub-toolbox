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

    def publish_module(self, descriptor, server_host="10.112.214.29:8080", callback=None):
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

    def fetch_github_catalog(self, repo="marcelum83/openhub-toolbox", branch="master", token=None, callback=None):
        """Fetches the module catalog directly from GitHub repository or raw catalog.json."""
        def _worker():
            try:
                import urllib.request
                from kivy.clock import Clock
                headers = {"User-Agent": "OpenHub-Client"}
                if token and token.strip():
                    headers["Authorization"] = f"token {token.strip()}"

                catalog = None
                # Strategy 1: Try reading catalog.json directly
                catalog_url = f"https://raw.githubusercontent.com/{repo}/{branch}/catalog.json"
                try:
                    req = urllib.request.Request(catalog_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=7) as resp:
                        if resp.status == 200:
                            catalog = json.loads(resp.read().decode('utf-8'))
                except Exception as cat_err:
                    # If raw failed with token, try API contents endpoint with raw Accept header
                    if token and token.strip():
                        try:
                            api_url = f"https://api.github.com/repos/{repo}/contents/catalog.json?ref={branch}"
                            api_headers = dict(headers)
                            api_headers["Accept"] = "application/vnd.github.v3.raw"
                            req = urllib.request.Request(api_url, headers=api_headers)
                            with urllib.request.urlopen(req, timeout=7) as resp:
                                if resp.status == 200:
                                    catalog = json.loads(resp.read().decode('utf-8'))
                        except Exception:
                            catalog = None

                # Strategy 2: Fallback to GitHub Contents API for modules/
                if not catalog:
                    from concurrent.futures import ThreadPoolExecutor
                    api_url = f"https://api.github.com/repos/{repo}/contents/modules?ref={branch}"
                    req = urllib.request.Request(api_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=9) as resp:
                        items = json.loads(resp.read().decode('utf-8'))
                    
                    dirs = [it["name"] for it in items if it.get("type") == "dir" and it.get("name") not in ("scratch", "__pycache__")]
                    
                    def _fetch_one_manifest(dir_name):
                        m_url = f"https://raw.githubusercontent.com/{repo}/{branch}/modules/{dir_name}/manifest.json"
                        try:
                            m_req = urllib.request.Request(m_url, headers=headers)
                            with urllib.request.urlopen(m_req, timeout=4) as m_resp:
                                m_data = json.loads(m_resp.read().decode('utf-8'))
                                m_data["dir_name"] = dir_name
                                return m_data
                        except Exception:
                            return {
                                "id": dir_name,
                                "dir_name": dir_name,
                                "name": dir_name.replace("_", " ").title(),
                                "version": "1.0.0",
                                "author": "community",
                                "category": "Tools",
                                "description": f"Sub-app: {dir_name}",
                                "files": ["manifest.json", "main.py"]
                            }

                    with ThreadPoolExecutor(max_workers=8) as executor:
                        catalog = list(executor.map(_fetch_one_manifest, dirs))

                if callback:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt: callback(True, catalog, None), 0)
            except Exception as e:
                if callback:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt, err=e: callback(False, None, str(err)), 0)

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def install_github_module(self, item_or_id, repo="marcelum83/openhub-toolbox", branch="master", token=None, callback=None):
        """Downloads a module directly from GitHub into local modules/ directory."""
        def _worker():
            try:
                import urllib.request
                from kivy.clock import Clock

                if isinstance(item_or_id, dict):
                    dir_name = item_or_id.get("dir_name") or item_or_id.get("id")
                    file_list = item_or_id.get("files") or ["manifest.json", "main.py"]
                else:
                    dir_name = str(item_or_id)
                    file_list = ["manifest.json", "main.py"]

                if "manifest.json" not in file_list:
                    file_list.append("manifest.json")
                if "main.py" not in file_list:
                    file_list.append("main.py")

                headers = {"User-Agent": "OpenHub-Client"}
                if token and token.strip():
                    headers["Authorization"] = f"token {token.strip()}"

                target_dir = os.path.join(self.modules_dir, dir_name)
                os.makedirs(target_dir, exist_ok=True)

                saved_files = []
                for fname in file_list:
                    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/modules/{dir_name}/{fname}"
                    content = None
                    try:
                        req = urllib.request.Request(raw_url, headers=headers)
                        with urllib.request.urlopen(req, timeout=8) as resp:
                            if resp.status == 200:
                                content = resp.read()
                    except Exception:
                        # Fallback to GitHub contents API if raw failed
                        if token and token.strip():
                            api_url = f"https://api.github.com/repos/{repo}/contents/modules/{dir_name}/{fname}?ref={branch}"
                            api_headers = dict(headers)
                            api_headers["Accept"] = "application/vnd.github.v3.raw"
                            try:
                                api_req = urllib.request.Request(api_url, headers=api_headers)
                                with urllib.request.urlopen(api_req, timeout=8) as resp:
                                    if resp.status == 200:
                                        content = resp.read()
                            except Exception:
                                pass

                    if content is not None:
                        dest_path = os.path.join(target_dir, fname)
                        with open(dest_path, "wb") as f:
                            f.write(content)
                        saved_files.append(fname)
                        if fname == "main.py":
                            with open(os.path.join(target_dir, "main.py.txt"), "wb") as f:
                                f.write(content)

                if "main.py" not in saved_files:
                    raise RuntimeError(f"Failed to download main.py for module '{dir_name}' from GitHub.")

                if callback:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt: callback(True, dir_name, None), 0)
            except Exception as e:
                if callback:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt, err=e: callback(False, None, str(err)), 0)

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def uninstall_module(self, mod_id_or_dir):
        """Safely uninstalls and removes a permanent module from local modules/ storage."""
        if not mod_id_or_dir or mod_id_or_dir == "scratch":
            return False
        # Try direct directory match
        target_dir = os.path.join(self.modules_dir, mod_id_or_dir)
        if not os.path.isdir(target_dir):
            # Check by manifest id
            found = False
            for item in os.listdir(self.modules_dir):
                m_path = os.path.join(self.modules_dir, item, "manifest.json")
                if os.path.exists(m_path):
                    try:
                        with open(m_path, "r", encoding="utf-8") as f:
                            d = json.load(f)
                            if d.get("id") == mod_id_or_dir:
                                target_dir = os.path.join(self.modules_dir, item)
                                found = True
                                break
                    except Exception:
                        pass
            if not found:
                return False

        try:
            shutil.rmtree(target_dir)
            return True
        except Exception as e:
            print(f"[ModuleManager] Error uninstalling {mod_id_or_dir}: {e}")
            return False

    def fetch_community_catalog(self, server_host="10.112.214.29:8080", callback=None):
        """Fetches catalog of modules from the central workstation LAN server."""
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

    def install_community_module(self, mod_id, server_host="10.112.214.29:8080", callback=None):
        """Downloads a community tool from the central workstation LAN server into local storage."""
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

    def fetch_catalog(self, updater, callback=None):
        """Unified catalog fetcher based on current settings (GitHub or LAN Server)."""
        src = updater.get_catalog_source()
        if src == "github":
            self.fetch_github_catalog(
                repo=updater.get_github_repo(),
                branch=updater.get_github_branch(),
                token=updater.get_github_token(),
                callback=callback
            )
        else:
            self.fetch_community_catalog(server_host=updater.server_host, callback=callback)

    def install_module(self, item_or_id, updater, callback=None):
        """Unified module installer based on current settings (GitHub or LAN Server)."""
        src = updater.get_catalog_source()
        if src == "github":
            self.install_github_module(
                item_or_id,
                repo=updater.get_github_repo(),
                branch=updater.get_github_branch(),
                token=updater.get_github_token(),
                callback=callback
            )
        else:
            mod_id = item_or_id.get("id") if isinstance(item_or_id, dict) else item_or_id
            self.install_community_module(mod_id, server_host=updater.server_host, callback=callback)
