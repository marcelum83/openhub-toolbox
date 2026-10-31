"""
OpenHub Central Sync & Cloud Registry Server
Accepts mobile tool publications, syncs modules to disk, auto-commits to GitHub, and serves the module catalog.
"""
import os
import sys
import json
import subprocess
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
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

        # 4. API: Get SimpleAgent Active Layer
        if parsed.path == "/api/simple_agent/layer":
            simple_agent_dir = "/home/mike/Documents/Nexus_Core/ACE/simple_agent"
            if simple_agent_dir not in sys.path:
                sys.path.insert(0, simple_agent_dir)
            active_layer = "L6_Prosecution"
            try:
                import simple_agent
                mem = simple_agent.load_memory()
                active_layer = mem.get("current_role", "L6_Prosecution")
            except Exception:
                pass
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"active_layer": active_layer}).encode('utf-8'))
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

        # API: Shift SimpleAgent Active Layer
        if parsed.path == "/api/simple_agent/layer":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                requested_layer = data.get("layer", "").strip().upper()
                role_map = {
                    "L1": "L1_Aspirational",
                    "L2": "L2_Strategy",
                    "L6": "L6_Prosecution"
                }
                new_role = role_map.get(requested_layer, requested_layer)
                simple_agent_dir = "/home/mike/Documents/Nexus_Core/ACE/simple_agent"
                if simple_agent_dir not in sys.path:
                    sys.path.insert(0, simple_agent_dir)
                import simple_agent
                mem = simple_agent.load_memory()
                mem["current_role"] = new_role
                simple_agent.save_memory(mem)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "active_layer": new_role}).encode('utf-8'))
                return
            except Exception as e:
                self.send_error(500, f"Failed to shift layer: {e}")
                return

        # API: SimpleAgent (ACE-OS Full Cognitive Engine Bridge)
        if parsed.path == "/api/simple_agent/chat":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                prompt = data.get("prompt", "")
                sensor_ctx = data.get("sensor_context", "")
                conv_id = data.get("conversation_id")
                model = data.get("model") or "qwen2.5-coder:7b"
                if model == "gemma4:e4b":
                    model = "qwen2.5-coder:7b"

                # Check if camera image is attached
                image_base64 = data.get("image_base64")
                if image_base64:
                    try:
                        import base64
                        img_bytes = base64.b64decode(image_base64)
                        with open("/tmp/pixel_snapshot.jpg", "wb") as f_img:
                            f_img.write(img_bytes)
                    except Exception as ie:
                        print(f"[SyncServer] Image write error: {ie}")

                    # Ask local moondream vision model to analyze the camera snapshot
                    vision_desc = ""
                    try:
                        v_payload = json.dumps({
                            "model": "moondream:latest",
                            "prompt": "Describe what you see in this photo taken by the user's Pixel 7a camera in detail, including text, objects, and environment:",
                            "images": [image_base64],
                            "stream": False
                        }).encode('utf-8')
                        v_req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=v_payload, headers={"Content-Type": "application/json"})
                        with urllib.request.urlopen(v_req, timeout=25) as v_resp:
                            v_data = json.loads(v_resp.read().decode('utf-8'))
                            vision_desc = v_data.get("response", "").strip()
                    except Exception as ve:
                        print(f"[SyncServer] Vision model error: {ve}")

                    if vision_desc:
                        prompt = f"[Visual Observation from Pixel 7a Camera]: {vision_desc}\n\nUser Question/Request: {prompt or 'Analyze this scene and suggest any relevant actions or tools.'}"
                    else:
                        prompt = f"[Visual Observation]: Image saved at /tmp/pixel_snapshot.jpg\n\nUser Request: {prompt or 'Analyze this image.'}"

                # If sensor_ctx wasn't explicitly provided, attach LATEST_TELEMETRY if recent
                if not sensor_ctx and LATEST_TELEMETRY.get("timestamp", 0) > 0:
                    sensor_ctx = f"Compass={LATEST_TELEMETRY.get('heading', 0):.1f}°, Pitch={LATEST_TELEMETRY.get('pitch', 0):.1f}°, Roll={LATEST_TELEMETRY.get('roll', 0):.1f}°, Lux={LATEST_TELEMETRY.get('lux', 0):.0f} lx, Mic={LATEST_TELEMETRY.get('db', 0):.0f} dB"

                # Invoke SimpleAgent with full ACE OS cognitive execution
                simple_agent_dir = "/home/mike/Documents/Nexus_Core/ACE/simple_agent"
                if simple_agent_dir not in sys.path:
                    sys.path.insert(0, simple_agent_dir)
                import importlib
                if "simple_agent" in sys.modules:
                    simple_agent = importlib.reload(sys.modules["simple_agent"])
                else:
                    import simple_agent
                turn_result = simple_agent.execute_agent_turn(
                    prompt=prompt,
                    conv_id=conv_id,
                    sensor_context=sensor_ctx,
                    model_name=model
                )

                reply = turn_result.get("content", "")
                tools_run = turn_result.get("tools_executed", [])
                active_role = turn_result.get("role", "L6_Prosecution")
                out_conv_id = turn_result.get("conversation_id", conv_id)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "response": reply,
                    "tools_executed": tools_run,
                    "active_layer": active_role,
                    "provider": "simple_agent_ace",
                    "model": model,
                    "conversation_id": out_conv_id
                }).encode('utf-8'))
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
            try:
                import build_catalog
                build_catalog.generate_catalog()
            except Exception:
                pass
            cmd = f'cd "{REPO_DIR}" && git add "modules/{mod_id}" catalog.json && git commit -m "Publish module: {name} via OpenHub Mobile" && git push origin master'
            subprocess.run(cmd, shell=True, check=False)
            print(f"[SyncServer] Published '{name}' and updated catalog.json on GitHub repository!")
        except Exception as e:
            print(f"[SyncServer] Git commit error: {e}")


def get_lan_ip():
    """Detect current active LAN or Wi-Fi hotspot IP."""
    try:
        ip = os.popen("ip route get 1.1.1.1 2>/dev/null | awk '{print $7}'").read().strip()
        if ip:
            return ip
    except Exception:
        pass
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def run_server(port=8080, bind="0.0.0.0", host_ip=None):
    if not host_ip or host_ip == "0.0.0.0":
        host_ip = get_lan_ip()

    # Start LAN Discovery Beacon for OpenHub Mobile
    try:
        from core.discovery import LANDiscoveryBeacon
        beacon = LANDiscoveryBeacon(host_ip=host_ip, server_port=port)
        beacon.start()
        print(f"📡 LAN Auto-Discovery Beacon: ACTIVE (Broadcasting {host_ip}:{port} on UDP 8089)")
    except Exception as e:
        print(f"⚠️ Could not start discovery beacon: {e}")

    server_address = (bind, port)
    httpd = HTTPServer(server_address, OpenHubSyncHandler)
    print(f"==================================================")
    print(f"🚀 OpenHub Cloud Sync & Download Server Live on port {port}")
    print(f"   LAN IP:  http://{host_ip}:{port}")
    print(f"   Catalog: http://{host_ip}:{port}/api/modules/catalog")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping OpenHub server...")
        httpd.server_close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenHub Sync & Download Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--bind", type=str, default="0.0.0.0", help="Address to bind to")
    parser.add_argument("--host", type=str, default=None, help="Advertised host IP")
    args = parser.parse_args()
    run_server(port=args.port, bind=args.bind, host_ip=args.host)

