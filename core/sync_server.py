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

LATEST_TELEMETRY = {
    "pitch": 0.0,
    "roll": 0.0,
    "heading": 0.0,
    "lux": 0.0,
    "db": 0.0,
    "timestamp": 0
}

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

        # 3. API: Get Latest Phone Telemetry
        if parsed.path == "/api/remote/telemetry":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(LATEST_TELEMETRY).encode('utf-8'))
            return

        # Fallback to standard bin/ static files (APK, version.json, index.html)
        return super().do_GET()

    def do_POST(self):
        global LATEST_TELEMETRY
        parsed = urllib.parse.urlparse(self.path)
        
        # API: Remote Action (PC Mouse / Trackpad / Media control)
        if parsed.path == "/api/remote/action":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                act_type = data.get("type", "")
                
                if act_type == "mouse_move":
                    dx = int(data.get("dx", 0))
                    dy = int(data.get("dy", 0))
                    if dx != 0 or dy != 0:
                        subprocess.run(["xdotool", "mousemove_relative", "--", str(dx), str(dy)], capture_output=True)
                elif act_type == "click":
                    btn = int(data.get("button", 1))
                    subprocess.run(["xdotool", "click", str(btn)], capture_output=True)
                elif act_type == "key":
                    key = data.get("key", "")
                    if key:
                        subprocess.run(["xdotool", "key", key], capture_output=True)
                elif act_type == "type":
                    text = data.get("text", "")
                    if text:
                        subprocess.run(["xdotool", "type", "--", text], capture_output=True)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
                return
            except Exception as e:
                self.send_error(500, f"Remote execution error: {e}")
                return

        # API: Telemetry Stream from Mobile
        if parsed.path == "/api/remote/telemetry":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                LATEST_TELEMETRY.update(data)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
                return
            except Exception as e:
                self.send_error(500, f"Telemetry error: {e}")
                return

        # API: SimpleAgent (ACE-OS Cognitive Engine Bridge)
        if parsed.path == "/api/simple_agent/chat":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                prompt = data.get("prompt", "")
                sensor_ctx = data.get("sensor_context", "")
                model = data.get("model", "qwen2.5-coder:7b")

                # Invoke SimpleAgent
                import sys
                simple_agent_dir = "/home/mike/Documents/Nexus_Core/ACE/simple_agent"
                if simple_agent_dir not in sys.path:
                    sys.path.insert(0, simple_agent_dir)

                try:
                    import simple_agent
                    simple_agent.init_db()
                    simple_agent.load_plugins()
                    sys_prompt = simple_agent.generate_system_prompt()
                    if sensor_ctx:
                        sys_prompt += f"\n\n### LIVE MOBILE SENSOR TELEMETRY ###\n{sensor_ctx}\n"

                    # Ensure OpenHub tool building rules are present
                    sys_prompt += "\n\nWhen asked to build or write an OpenHub tool or application, output complete runnable Kivy Python code in ```python ... ``` with class OpenHubModule(BoxLayout)."

                    from openai import OpenAI
                    history = data.get("history", [])
                    conv_id = data.get("conversation_id")
                    if not conv_id:
                        conv_id = simple_agent.create_conversation()

                    messages = [{"role": "system", "content": sys_prompt}]
                    
                    if history:
                        for h in history:
                            r = h.get("role")
                            c = h.get("content")
                            if r in ["user", "assistant"] and c:
                                messages.append({"role": r, "content": c})
                        # If the current prompt is not already the last item in history, append it
                        if not (history and history[-1].get("role") == "user" and history[-1].get("content") == prompt):
                            messages.append({"role": "user", "content": prompt})
                    else:
                        messages.append({"role": "user", "content": prompt})

                    # Auto Web Search Hook for live queries (e.g. "search the web for raspberry pi in hereford")
                    if any(k in prompt.lower() for k in ["search", "web", "google", "find", "buy", "near", "hereford", "price", "weather", "latest", "gigs", "events", "music"]):
                        try:
                            from tools import web_search
                            s_res = web_search.execute(query=prompt)
                            messages.append({"role": "system", "content": f"### REAL-TIME WEB SEARCH RESULTS ###\n{s_res}"})
                        except Exception as ws_e:
                            print(f"[SimpleAgent] Web search hook notice: {ws_e}")

                    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

                    # Persist user prompt in SimpleAgent database
                    try:
                        simple_agent.save_message(conv_id, "user", prompt)
                    except Exception as sm_e:
                        print(f"[SimpleAgent] Notice saving user msg: {sm_e}")

                    resp = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.4
                    )
                    reply = resp.choices[0].message.content

                    # Persist assistant reply in SimpleAgent database
                    try:
                        simple_agent.save_message(conv_id, "assistant", reply)
                    except Exception as sm_e:
                        print(f"[SimpleAgent] Notice saving assistant reply: {sm_e}")
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"response": reply, "provider": "simple_agent_ace", "model": model, "conversation_id": conv_id}).encode('utf-8'))
                    return
                except Exception as sa_err:
                    self.send_error(500, f"SimpleAgent execution error: {sa_err}")
                    return
            except Exception as e:
                self.send_error(400, f"Invalid request: {e}")
                return

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

                try:
                    from core.sanitizer import CodeSanitizer
                    code = CodeSanitizer.sanitize(code)
                except Exception:
                    pass

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
