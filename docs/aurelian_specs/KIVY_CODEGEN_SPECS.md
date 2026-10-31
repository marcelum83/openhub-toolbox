# Kivy Code Generation Framework (Antigravity Specs)

To ensure that AI-generated modules can be seamlessly deployed and hot-reloaded within the Aurelian Kivy Plane, all generated code MUST adhere to the following structure.

## 1. Module Naming
- **Module Name**: PascalCase (e.g., `BatteryMonitor`, `SystemDashboard`).
- **Filename**: snake_case (e.g., `battery_monitor.py`).

## 2. Component Structure
Each module must define a primary class that inherits from a Kivy Layout (usually `BoxLayout` or `RelativeLayout`) and includes standard lifecycle methods.

```python
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty

class Component(BoxLayout):
    """
    Standard Antigravity Component.
    The class name MUST be 'Component' for the loader to find it.
    """
    status_text = StringProperty("Initialized")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self._build_ui()

    def _build_ui(self):
        # UI Implementation here
        pass

    def on_deploy(self):
        """Called immediately after the module is loaded/reloaded."""
        print(f"[{self.__class__.__name__}] Deployed successfully.")

    def on_shutdown(self):
        """Called before the module is destroyed or reloaded."""
        print(f"[{self.__class__.__name__}] Shutting down...")
```

## 3. Communication Pattern
- **Hub Interaction**: Components should use the existing WebSocket connection (accessible via `App.get_running_app().root`) to send updates back to the Hub.
- **Signals**: Use Kivy Properties for reactive UI updates.

## 4. Resource Management
- **Imports**: Only use standard libraries or pre-installed packages (kivy, websockets, requests).
- **Cleanup**: Always implement `on_shutdown` to stop any `Clock` schedules or background threads.

## 5. Deployment Metadata
When sending a `HUB_DEPLOY` tag, the AI must provide:
- `module`: The logical name.
- `filename`: The target path.
- `action`: `install` or `hot_reload`.
- `code`: The complete source.
