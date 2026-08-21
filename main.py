"""
OpenHub: Programmable Physical Toolbox & Dynamic Module Host
Entry point for Linux desktop testing and Android (Pixel 7a) APK runtime.
"""
import os
import sys
from dotenv import load_dotenv

# Load local environment if present (e.g. for GEMINI_API_KEY)
load_dotenv()

# Configure Kivy Window for mobile portrait aspect ratio on desktop
from kivy.config import Config
Config.set('graphics', 'width', '440')
Config.set('graphics', 'height', '860')
Config.set('graphics', 'resizable', '1')

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.clock import Clock

from core.hardware import HardwareBridge
from core.scanner import ModuleScanner
from core.security import HostAPI
from core.runner import ModuleLoader
from ui.launcher import LauncherScreen
from ui.studio import ForgeStudioScreen
from ui.module_runner import ModuleRunnerScreen
from ui.themes import ColorSystem

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
        self.modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules")
        self.scanner = ModuleScanner(self.modules_dir)

        # Build Screen Manager
        self.sm = OpenHubScreenManager()
        
        # 1. Launcher Screen (The Deck & Fast Creation Engine)
        self.launcher_screen = LauncherScreen(self, name='launcher')
        self.sm.add_widget(self.launcher_screen)

        # 2. Forge Screen (The Pydroid3 Studio & Agentic Self-Mutator)
        self.forge_screen = ForgeStudioScreen(self, name='forge')
        self.sm.add_widget(self.forge_screen)

        # 3. Active Module Runner Screen
        self.runner_screen = ModuleRunnerScreen(self, name='runner')
        self.sm.add_widget(self.runner_screen)

        # Initial module scan
        Clock.schedule_once(lambda dt: self.refresh_modules(), 0.1)

        return self.sm

    def refresh_modules(self):
        """Scans the modules directory and refreshes both scratch and permanent shelves."""
        permanent, scratch = self.scanner.scan_all()
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
            print(f"[OpenHubApp] Failed to launch module '{descriptor.name}': {e}")
            import traceback
            traceback.print_exc()

    def on_pause(self):
        """Handle Android home button / app switch to background."""
        if hasattr(self, 'hardware') and self.hardware:
            self.hardware.stop_sensors()
        return True

    def on_resume(self):
        """Handle Android app coming back to foreground."""
        pass


if __name__ == '__main__':
    OpenHubApp().run()
