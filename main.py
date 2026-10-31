"""
OpenHub: Programmable Physical Toolbox & Dynamic Module Host
Entry point for Linux desktop testing and Android (Pixel 7a) APK runtime.
"""
import os
import sys

# Load local environment if present (e.g. for GEMINI_API_KEY)
if os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass

# Configure Kivy Window for mobile portrait aspect ratio on desktop
from kivy.utils import platform
if platform != 'android':
    from kivy.config import Config
    Config.set('graphics', 'width', '440')
    Config.set('graphics', 'height', '860')
    Config.set('graphics', 'resizable', '1')

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.clock import Clock

from core.hardware import HardwareBridge
from core.module_manager import ModuleManager
from core.forge_agent import ForgeEngine
from core.agent_chat import AgentChatEngine
from core.security import HostAPI
from core.runner import ModuleLoader
from core.updater import UpdateManager
from ui.launcher import LauncherScreen
from ui.studio import ForgeStudioScreen
from ui.agent_chat import AgentChatScreen
from ui.module_runner import ModuleRunnerScreen

class OpenHubScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(transition=FadeTransition(duration=0.15), **kwargs)


class OpenHubApp(MDApp):
    def build(self):
        self.title = "OpenHub"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"

        # Initialize Core Systems
        self.hardware = HardwareBridge()
        self.module_mgr = ModuleManager(os.path.dirname(os.path.abspath(__file__)))
        self.forge = ForgeEngine()
        self.updater = UpdateManager(os.path.dirname(os.path.abspath(__file__)))
        self.agent_engine = AgentChatEngine(host_bridge=self.hardware)

        # Build Screen Manager
        self.sm = OpenHubScreenManager()
        
        # 1. Launcher Screen (The Deck & Fast Creation Engine)
        self.launcher_screen = LauncherScreen(self, name='launcher')
        self.sm.add_widget(self.launcher_screen)

        # 2. Conversational Agent Screen (Local Ollama & Gemini)
        self.agent_screen = AgentChatScreen(self, name='agent')
        self.sm.add_widget(self.agent_screen)

        # 3. Forge Screen (The Pydroid3 Studio & Agentic Self-Mutator)
        self.forge_screen = ForgeStudioScreen(self, name='forge')
        self.sm.add_widget(self.forge_screen)

        # 4. Active Module Runner Screen
        self.runner_screen = ModuleRunnerScreen(self, name='runner')
        self.sm.add_widget(self.runner_screen)

        # Initial module scan
        Clock.schedule_once(lambda dt: self.refresh_modules(), 0.1)

        return self.sm

    def on_start(self):
        """Called when the application starts and the window is ready."""
        self.refresh_modules()

        # Automatically discover and bind to Desktop Server on Wi-Fi / Hotspot
        try:
            from core.discovery import discover_server
            def _on_discovered(host_str):
                if host_str and host_str != self.updater.server_host:
                    print(f"[OpenHubApp] 🚀 Auto-discovered Desktop Server at {host_str}!")
                    self.updater.save_settings(server_host=host_str)
                    if hasattr(self, 'agent_engine') and self.agent_engine:
                        self.agent_engine.server_host = host_str.split(":")[0]
                    if hasattr(self, 'launcher_screen') and self.launcher_screen:
                        self.launcher_screen.show_toast(f"⚡ Connected to PC: {host_str}")
            discover_server(timeout=1.5, callback=_on_discovered)
        except Exception as e:
            print(f"[OpenHubApp] Discovery notice: {e}")

        Clock.schedule_once(lambda dt: self.updater.check_for_updates(self.launcher_screen.on_update_check_result), 1.2)
        # Periodic background sensor telemetry streaming to PC Server
        self._telemetry_enabled = True
        Clock.schedule_interval(self._stream_telemetry, 3.0)

    def _stream_telemetry(self, dt):
        if not getattr(self, '_telemetry_enabled', True):
            return
        if not hasattr(self, 'hardware') or not self.hardware:
            return
        host = getattr(self.updater, 'server_host', '10.145.112.29:8080').split(':')[0]
        if not host:
            return

        import json
        import time
        import urllib.request
        import threading

        try:
            h, _ = self.hardware.get_compass_heading()
            p, r, _ = self.hardware.get_orientation_angles()
            lux, _ = self.hardware.get_lux()
            db = self.hardware.get_audio_level_db()
            torch = self.hardware.is_torch_active()

            payload = json.dumps({
                "device": "Pixel 7a",
                "heading": round(h, 1),
                "pitch": round(p, 1),
                "roll": round(r, 1),
                "lux": round(lux, 1),
                "db": round(db, 1),
                "torch": torch,
                "timestamp": time.time()
            }).encode('utf-8')

            def _send():
                try:
                    url = f"http://{host}:8080/api/remote/telemetry"
                    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        pass
                except Exception:
                    pass

            threading.Thread(target=_send, daemon=True).start()
        except Exception:
            pass

    def refresh_modules(self):
        """Scans the modules directory and refreshes both scratch and permanent shelves."""
        permanent, scratch = self.module_mgr.scan()
        self.launcher_screen.update_all_modules(permanent, scratch)

    def launch_module(self, descriptor):
        """Loads and executes a dynamic module inside the host runner screen."""
        try:
            host_api = HostAPI(
                module_id=descriptor.id,
                trust_level=descriptor.trust_level,
                hardware_bridge=self.hardware,
                storage_root=os.path.dirname(os.path.abspath(__file__))
            )
            widget = ModuleLoader.load_module_widget(descriptor, host_api)
            self.runner_screen.set_module(descriptor, widget)
            self.sm.current = 'runner'
        except Exception as e:
            err_msg = f"Failed to launch '{descriptor.name}': {e}"
            print(f"[OpenHubApp] {err_msg}")
            import traceback
            traceback.print_exc()
            if hasattr(self, 'launcher_screen') and self.launcher_screen:
                if hasattr(self.launcher_screen, 'show_toast'):
                    self.launcher_screen.show_toast(f"❌ {err_msg}")
                elif hasattr(self.launcher_screen, 'lbl_create_status'):
                    self.launcher_screen.lbl_create_status.text = f"❌ {err_msg}"

    def on_pause(self):
        """Handle Android home button / app switch to background."""
        self._telemetry_enabled = False
        if hasattr(self, 'hardware') and self.hardware:
            self.hardware.stop_sensors()
        return True

    def on_resume(self):
        """Handle Android app coming back to foreground."""
        self._telemetry_enabled = True
        if hasattr(self, 'hardware') and self.hardware:
            self.hardware.start_sensors()


if __name__ == '__main__':
    OpenHubApp().run()
