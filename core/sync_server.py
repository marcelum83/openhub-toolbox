"""
OpenHub Central Sync & Cloud Registry Server
Accepts mobile tool publications, syncs modules to disk, auto-commits to GitHub, and serves the module catalog.
"""
import os
import json
import subprocess
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(REPO_DIR, "modules")
BIN_DIR = os.path.join(REPO_DIR, "bin")

class OpenHubSyncHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BIN_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # 1. API: Module Catalog
        if parsed.path == "/api/modules/catalog":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            catalog = []
            if os.path.exists(MODULES_DIR):
                for item in sorted(os.listdir(MODULES_DIR)):
                    if item == "scratch" or not os.path.isdir(os.path.join(MODULES_DIR, item)):
                        continue
                    m_path = os.path.join(MODULES_DIR, item, "manifest.json")
                    if os.path.exists(m_path):
                        try:
                            with open(m_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                catalog.append(data)
                        except Exception:
                            pass
            self.wfile.write(json.dumps(catalog, indent=2).encode('utf-8'))
            return

        # 2. API: Download single module
        if parsed.path.startswith("/api/modules/download/"):
            mod_id = parsed.path.split("/")[-1]
            mod_dir = os.path.join(MODULES_DIR, mod_id)
            main_py = os.path.join(mod_dir, "main.py")
            m_path = os.path.join(mod_dir, "manifest.json")
            
            if os.path.exists(main_py) and os.path.exists(m_path):
                with open(main_py, 'r', encoding='utf-8') as f:
                    code = f.read()
                with open(m_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"manifest": manifest, "code": code}).encode('utf-8'))
                return
            else:
                self.send_error(404, "Module not found")
                return

        # Fallback to standard bin/ static files (APK, version.json, index.html)
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # API: Publish Module from mobile to Central Repository & GitHub
        if parsed.path == "/api/modules/publish":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                mod_id = data.get("id", "").strip() or "custom_tool"
                name = data.get("name", mod_id.replace("_", " ").title())
                code = data.get("code", "")
                category = data.get("category", "Community")
                description = data.get("description", f"Created via OpenHub: {name}")

                if not code:
                    self.send_error(400, "Missing Python code")
                    return

                # Write to modules/<id>/
                target_dir = os.path.join(MODULES_DIR, mod_id)
                os.makedirs(target_dir, exist_ok=True)

                with open(os.path.join(target_dir, "main.py"), "w", encoding="utf-8") as f:
                    f.write(code)
                with open(os.path.join(target_dir, "main.py.txt"), "w", encoding="utf-8") as f:
                    f.write(code)

                manifest = {
                    "id": mod_id,
                    "name": name,
                    "version": "1.0.0",
                    "author": data.get("author", "mobile_agent"),
                    "category": category,
                    "description": description,
                    "entrypoint": "main.py",
                    "trust_level": "trusted"
                }
                with open(os.path.join(target_dir, "manifest.json"), "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)

                # Background Git commit & push to GitHub
                threading.Thread(target=self._git_commit_and_push, args=(name, mod_id), daemon=True).start()

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                res = {
                    "status": "published",
                    "id": mod_id,
                    "name": name,
                    "repo_url": f"https://github.com/marcelum83/openhub-toolbox/tree/master/modules/{mod_id}"
                }
                self.wfile.write(json.dumps(res).encode('utf-8'))
                return

            except Exception as e:
                self.send_error(500, f"Error publishing module: {e}")
                return

        self.send_error(404, "Endpoint not found")

    def _git_commit_and_push(self, name, mod_id):
        try:
            cmd = f'cd "{REPO_DIR}" && git add "modules/{mod_id}" && git commit -m "Publish module: {name} via OpenHub Mobile" && git push origin master'
            subprocess.run(cmd, shell=True, check=False)
            print(f"[SyncServer] Published '{name}' and pushed to GitHub repository!")
        except Exception as e:
            print(f"[SyncServer] Git commit error: {e}")


def run_server(port=8080, bind="0.0.0.0"):
    server_address = (bind, port)
    httpd = HTTPServer(server_address, OpenHubSyncHandler)
    print(f"==========================================")
    print(f"🚀 OpenHub Cloud Sync & Download Server Live on port {port}")
    print(f"   Catalog: http://{bind}:{port}/api/modules/catalog")
    print(f"==========================================")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
