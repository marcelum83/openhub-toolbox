"""
OpenHub Module Runner
Dynamically imports and mounts Kivy Widgets/Apps into the Host ScreenManager.
"""
import os
import sys
import inspect
import importlib.util
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.app import App

class ModuleLoader:
    @staticmethod
    def load_module_widget(module_descriptor, host_api):
        """
        Dynamically loads the entrypoint file and instantiates the main widget.
        Supports:
        1. OpenHubModule class with on_load(host_api)
        2. Kivy App subclasses (calls app.build())
        3. Standalone Widget subclasses
        """
        entrypoint = module_descriptor.entrypoint
        if not os.path.exists(entrypoint):
            raise FileNotFoundError(f"Entrypoint file not found: {entrypoint}")

        # Add module directory to sys.path so it can import local helpers
        mod_dir = os.path.dirname(entrypoint)
        if mod_dir not in sys.path:
            sys.path.insert(0, mod_dir)

        spec = importlib.util.spec_from_file_location(f"openhub_mod_{module_descriptor.id}", entrypoint)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {entrypoint}")

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise RuntimeError(f"Error executing module code: {e}")

        # Search for OpenHubModule first
        if hasattr(module, "OpenHubModule"):
            cls = getattr(module, "OpenHubModule")
            instance = cls()
            if hasattr(instance, "on_load"):
                try:
                    instance.on_load(host_api)
                except Exception as e:
                    print(f"[ModuleLoader] Warning during on_load: {e}")
            return instance

        # Search for any Widget subclass
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, Widget) and obj != Widget and obj != BoxLayout:
                instance = obj()
                if hasattr(instance, "on_load"):
                    try:
                        instance.on_load(host_api)
                    except Exception:
                        pass
                return instance

        # Search for Kivy App subclass (like in wrapper_old.py)
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, App) and obj != App:
                app_instance = obj()
                if hasattr(app_instance, "build"):
                    root_widget = app_instance.build()
                    return root_widget

        # Fallback if no widget found
        box = BoxLayout(orientation='vertical', padding=20)
        box.add_widget(Label(text=f"Loaded `{os.path.basename(entrypoint)}` successfully,\nbut no Kivy Widget or App class was detected."))
        return box
