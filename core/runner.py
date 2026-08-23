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
            # Check for .txt companion or .pyc compiled fallback
            txt_path = entrypoint + ".txt"
            pyc_path = entrypoint + "c" if entrypoint.endswith(".py") else entrypoint.replace(".py", ".pyc")
            if os.path.exists(txt_path):
                try:
                    import shutil
                    shutil.copyfile(txt_path, entrypoint)
                except Exception:
                    pass
            elif os.path.exists(pyc_path):
                entrypoint = pyc_path
            else:
                raise FileNotFoundError(f"Entrypoint file not found: {entrypoint}")

        # Add module directory to sys.path so it can import local helpers
        mod_dir = os.path.dirname(entrypoint)
        if mod_dir not in sys.path:
            sys.path.insert(0, mod_dir)

        spec = importlib.util.spec_from_file_location(f"openhub_mod_{module_descriptor.id}", entrypoint)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {entrypoint}")

        module = importlib.util.module_from_spec(spec)
        if spec.name in sys.modules:
            del sys.modules[spec.name]
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise RuntimeError(f"Error executing module code '{entrypoint}': {e}")

        # 1. Search for OpenHubModule first (Standard Architecture)
        if hasattr(module, "OpenHubModule"):
            cls = getattr(module, "OpenHubModule")
            instance = cls()
            if hasattr(instance, "on_load"):
                try:
                    instance.on_load(host_api)
                except Exception as e:
                    print(f"[ModuleLoader] Warning during on_load: {e}")
            return instance

        # 2. Search for Kivy App subclass (like standalone scripts)
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, App) and obj != App:
                try:
                    app_instance = obj()
                    # Provide dummy root if script references self.root during build
                    class DummyRoot:
                        width = 800
                        height = 1200
                    app_instance.root = DummyRoot()
                    if hasattr(app_instance, "build"):
                        root_widget = app_instance.build()
                        if root_widget is not None:
                            if hasattr(root_widget, "on_load"):
                                try:
                                    root_widget.on_load(host_api)
                                except Exception:
                                    pass
                            return root_widget
                except Exception as e:
                    print(f"[ModuleLoader] App.build() error: {e}")

        # 3. Search for any Widget subclass
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, Widget) and obj != Widget and obj != BoxLayout:
                try:
                    instance = obj()
                    if hasattr(instance, "on_load"):
                        try:
                            instance.on_load(host_api)
                        except Exception:
                            pass
                    # Wrap inside a full-screen BoxLayout container
                    container = BoxLayout(orientation='vertical')
                    container.add_widget(instance)
                    return container
                except Exception as e:
                    print(f"[ModuleLoader] Widget instantiation error: {e}")

        # Fallback if no widget found
        box = BoxLayout(orientation='vertical', padding=20)
        box.add_widget(Label(text=f"Loaded `{os.path.basename(entrypoint)}` successfully,\nbut no Kivy Widget or App class was detected."))
        return box
