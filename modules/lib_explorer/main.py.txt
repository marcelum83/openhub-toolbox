"""
Python Library & Runtime Explorer
Interactive introspection tool for Python modules, classes, functions, and docstrings.
"""
import inspect
import importlib
import pkgutil
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp, sp

CATEGORIES = {
    "Core & Stdlib": ["os", "sys", "json", "math", "datetime", "random", "re", "time", "threading", "urllib.request"],
    "Kivy UI": ["kivy.app", "kivy.uix.boxlayout", "kivy.uix.button", "kivy.uix.label", "kivy.uix.scrollview", "kivy.clock", "kivy.graphics"],
    "Hardware / Mobile": ["jnius", "plyer", "android"],
    "Network & AI": ["requests", "urllib", "http.client", "socket", "websockets"]
}

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(8), **kwargs)
        self.host = None
        self.active_category = "Core & Stdlib"
        self.cat_buttons = {}

        # 1. Header
        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))
        lbl_title = Label(
            text="🔬 PYTHON RUNTIME EXPLORER",
            font_size="16sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        head.add_widget(lbl_title)
        self.add_widget(head)

        # 2. Category Selector
        cat_scroll = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint_y=None, height=dp(32))
        cat_box = BoxLayout(orientation='horizontal', spacing=dp(6), size_hint_x=None)
        cat_box.bind(minimum_width=cat_box.setter('width'))
        for cat_name in CATEGORIES.keys():
            btn = Button(
                text=cat_name,
                size_hint_x=None,
                width=dp(120),
                background_normal="",
                background_color=(0.02, 0.71, 0.83, 1.0) if cat_name == self.active_category else (0.15, 0.15, 0.22, 1.0),
                color=(0.05, 0.05, 0.08, 1.0) if cat_name == self.active_category else (0.8, 0.8, 0.9, 1.0),
                bold=True,
                font_size="11sp",
                always_release=True
            )
            btn.bind(on_release=lambda inst, c=cat_name: self.set_category(c))
            self.cat_buttons[cat_name] = btn
            cat_box.add_widget(btn)
        cat_scroll.add_widget(cat_box)
        self.add_widget(cat_scroll)

        # 3. Search & Module Buttons Row
        self.mod_scroll = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint_y=None, height=dp(34))
        self.mod_box = BoxLayout(orientation='horizontal', spacing=dp(6), size_hint_x=None)
        self.mod_box.bind(minimum_width=self.mod_box.setter('width'))
        self.mod_scroll.add_widget(self.mod_box)
        self.add_widget(self.mod_scroll)

        # 4. Search input for custom import
        search_box = BoxLayout(orientation='horizontal', spacing=dp(6), size_hint_y=None, height=dp(36))
        self.txt_custom = TextInput(
            hint_text="Type custom module name (e.g. hashlib, sqlite3)...",
            multiline=False,
            font_size="13sp",
            background_color=(0.13, 0.13, 0.19, 1.0),
            foreground_color=(0.95, 0.95, 0.98, 1.0)
        )
        search_box.add_widget(self.txt_custom)

        btn_inspect = Button(
            text="INSPECT",
            size_hint_x=None,
            width=dp(80),
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="12sp",
            always_release=True
        )
        btn_inspect.bind(on_release=lambda x: self.inspect_module(self.txt_custom.text.strip()))
        search_box.add_widget(btn_inspect)
        self.add_widget(search_box)

        # 5. Content Viewport
        self.doc_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.lbl_details = Label(
            text="Select a module above or type a package name to inspect.",
            font_size="12sp",
            color=(0.85, 0.85, 0.92, 1.0),
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        self.lbl_details.bind(
            width=lambda *x: self.lbl_details.setter('text_size')(self.lbl_details, (self.lbl_details.width, None)),
            texture_size=lambda *x: setattr(self.lbl_details, 'height', self.lbl_details.texture_size[1])
        )
        self.doc_scroll.add_widget(self.lbl_details)
        self.add_widget(self.doc_scroll)

        self.set_category(self.active_category)

    def on_load(self, host_api):
        self.host = host_api
        if self.host:
            self.host.log("Python Library Explorer loaded.")

    def set_category(self, cat_name):
        self.active_category = cat_name
        for name, btn in self.cat_buttons.items():
            if name == cat_name:
                btn.background_color = (0.02, 0.71, 0.83, 1.0)
                btn.color = (0.05, 0.05, 0.08, 1.0)
            else:
                btn.background_color = (0.15, 0.15, 0.22, 1.0)
                btn.color = (0.8, 0.8, 0.9, 1.0)

        self.mod_box.clear_widgets()
        modules = CATEGORIES.get(cat_name, [])
        for mod in modules:
            btn_mod = Button(
                text=mod,
                size_hint_x=None,
                width=dp(len(mod) * 9 + 20),
                background_normal="",
                background_color=(0.18, 0.22, 0.32, 1.0),
                color=(0.9, 0.95, 1.0, 1.0),
                font_size="11sp",
                always_release=True
            )
            btn_mod.bind(on_release=lambda inst, m=mod: self.inspect_module(m))
            self.mod_box.add_widget(btn_mod)

        if modules:
            self.inspect_module(modules[0])

    def inspect_module(self, mod_name):
        if not mod_name:
            return
        try:
            mod = importlib.import_module(mod_name)
            doc = inspect.getdoc(mod) or "No docstring available."
            classes = [name for name, cls in inspect.getmembers(mod, inspect.isclass) if cls.__module__ == mod.__name__]
            functions = [name for name, fn in inspect.getmembers(mod, inspect.isfunction) if fn.__module__ == mod.__name__]
            file_path = getattr(mod, '__file__', 'built-in / frozen')

            report = [
                f"📦 MODULE: {mod_name}",
                f"📁 Location: {file_path}",
                "-" * 50,
                f"📖 DOCSTRING:\n{doc}\n",
                "-" * 50,
                f"🏛️ CLASSES ({len(classes)}):\n" + (", ".join(classes[:30]) if classes else "None declared directly."),
                "\n" + "-" * 50,
                f"⚡ FUNCTIONS ({len(functions)}):\n" + (", ".join(functions[:40]) if functions else "None declared directly.")
            ]
            self.lbl_details.text = "\n".join(report)
        except Exception as e:
            self.lbl_details.text = f"❌ Failed to inspect '{mod_name}':\n\n{str(e)}"
