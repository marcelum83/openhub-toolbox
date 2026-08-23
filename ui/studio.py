"""
OpenHub Forge Studio Screen
Scaled with dp/sp for high-DPI Android touch editing.
"""
import ast
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from ui.themes import ColorSystem

STARTER_CODE = """# OpenHub Dynamic Module
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.metrics import dp

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(14), **kwargs)
        
        self.add_widget(Label(
            text="✨ My Custom Tool",
            font_size="24sp",
            bold=True,
            size_hint_y=None,
            height=dp(45),
            color=(0.02, 0.71, 0.83, 1)
        ))
        
        self.val_label = Label(text="Input Value: 10.0", font_size="18sp", size_hint_y=None, height=dp(35))
        self.add_widget(self.val_label)
        
        slider = Slider(min=1, max=100, value=10, size_hint_y=None, height=dp(50))
        slider.bind(value=self.on_slider)
        self.add_widget(slider)
        
        btn = Button(
            text="Calculate / Actuate",
            size_hint_y=None,
            height=dp(54),
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1),
            bold=True,
            font_size="16sp"
        )
        btn.bind(on_release=self.on_press_btn)
        self.add_widget(btn)

    def on_load(self, host_api):
        self.host = host_api

    def on_slider(self, inst, val):
        self.val_label.text = f"Input Value: {val:.1f}"

    def on_press_btn(self, inst):
        if hasattr(self, 'host') and self.host and self.host.hardware:
            self.host.hardware.vibrate(40)
        self.val_label.text = "⚡ Executed with Haptic Pulse!"
"""

class ForgeStudioScreen(Screen):
    def __init__(self, app_manager, **kwargs):
        super().__init__(**kwargs)
        self.app_manager = app_manager
        self.active_descriptor = None
        self.forge = app_manager.forge
        self.forge.bind(on_forge_success=self.on_forge_success)
        self.forge.bind(on_forge_error=self.on_forge_error)

        root = BoxLayout(orientation='vertical', spacing=0)
        with root.canvas.before:
            Color(*ColorSystem.BG_DARK)
            self.bg_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # 1. Top Navigation Bar
        nav = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), padding=[dp(12), dp(8), dp(12), dp(8)], spacing=dp(10))
        with nav.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.nav_rect = Rectangle(size=nav.size, pos=nav.pos)
        nav.bind(size=self._update_nav_rect, pos=self._update_nav_rect)

        btn_back = Button(
            text="◀ DECK",
            size_hint_x=None,
            width=dp(95),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.PRIMARY,
            bold=True,
            font_size="15sp"
        )
        btn_back.bind(on_release=self.switch_to_deck)
        nav.add_widget(btn_back)

        self.lbl_editor_title = Label(
            text="⚡ FORGE STUDIO",
            font_size="18sp",
            bold=True,
            color=ColorSystem.SECONDARY,
            halign='left',
            valign='middle'
        )
        self.lbl_editor_title.bind(size=self.lbl_editor_title.setter('text_size'))
        nav.add_widget(self.lbl_editor_title)
        root.add_widget(nav)

        # 2. Action Toolbar: [▶ RUN LIVE] [💾 SAVE] [➕ NEW]
        toolbar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), padding=[dp(12), dp(6), dp(12), dp(6)], spacing=dp(8))
        
        btn_run = Button(
            text="▶ RUN LIVE",
            background_normal="",
            background_color=ColorSystem.SUCCESS,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="14sp"
        )
        btn_run.bind(on_release=self.run_code_live)
        toolbar.add_widget(btn_run)

        btn_save = Button(
            text="💾 SAVE FILE",
            background_normal="",
            background_color=ColorSystem.PRIMARY,
            color=ColorSystem.BG_DARK,
            bold=True,
            font_size="14sp"
        )
        btn_save.bind(on_release=self.save_current_file)
        toolbar.add_widget(btn_save)

        btn_new = Button(
            text="➕ NEW",
            size_hint_x=0.3,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp"
        )
        btn_new.bind(on_release=self.new_scratch_file)
        toolbar.add_widget(btn_new)
        root.add_widget(toolbar)

        # 3. Touch Code Editor
        self.code_editor = TextInput(
            text=STARTER_CODE,
            font_size="14sp",
            background_color=ColorSystem.SURFACE,
            foreground_color=ColorSystem.TEXT_PRIMARY,
            cursor_color=ColorSystem.PRIMARY,
            padding=[dp(12), dp(12), dp(12), dp(12)]
        )
        root.add_widget(self.code_editor)

        # 4. Status / Console Bar
        self.lbl_status = Label(
            text="Ready. Edit code or enter instruction below.",
            font_size="13sp",
            color=ColorSystem.TEXT_MUTED,
            size_hint_y=None,
            height=dp(30),
            halign='left'
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        root.add_widget(self.lbl_status)

        # 5. Agent Prompt Bar
        prompt_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(58), padding=[dp(12), dp(8), dp(12), dp(8)], spacing=dp(8))
        self.prompt_input = TextInput(
            hint_text="🤖 Ask AI to mutate: e.g. 'Add gallons & drawing'...",
            multiline=False,
            font_size="14sp",
            background_color=ColorSystem.SURFACE,
            foreground_color=ColorSystem.TEXT_PRIMARY,
            hint_text_color=ColorSystem.TEXT_HINT,
            cursor_color=ColorSystem.SECONDARY,
            padding=[dp(10), dp(10), dp(10), dp(10)]
        )
        self.prompt_input.bind(on_text_validate=self.ask_forge_to_mutate)
        prompt_box.add_widget(self.prompt_input)

        self.btn_ask = Button(
            text="⚡ MUTATE",
            size_hint_x=None,
            width=dp(110),
            background_normal="",
            background_color=ColorSystem.SECONDARY,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="14sp"
        )
        self.btn_ask.bind(on_release=self.ask_forge_to_mutate)
        prompt_box.add_widget(self.btn_ask)
        root.add_widget(prompt_box)

        self.add_widget(root)

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _update_nav_rect(self, instance, value):
        self.nav_rect.pos = instance.pos
        self.nav_rect.size = instance.size

    def switch_to_deck(self, instance):
        if self.manager:
            self.manager.current = 'launcher'

    def load_descriptor_for_editing(self, descriptor, code):
        self.active_descriptor = descriptor
        self.code_editor.text = code
        self.lbl_editor_title.text = f"✏️ {descriptor.name}"
        self.lbl_status.text = f"Editing: {descriptor.id}"

    def new_scratch_file(self, instance):
        self.active_descriptor = None
        self.code_editor.text = STARTER_CODE
        self.lbl_editor_title.text = "⚡ FORGE STUDIO (NEW)"
        self.lbl_status.text = "New scratch draft initialized."

    def save_current_file(self, instance):
        code = self.code_editor.text
        if self.active_descriptor:
            self.app_manager.module_mgr.save_code(self.active_descriptor, code)
            self.lbl_status.text = f"✅ Saved '{self.active_descriptor.name}'"
        else:
            self.active_descriptor = self.app_manager.module_mgr.create_scratch(code, prompt="custom_tool")
            self.lbl_status.text = f"✅ Created '{self.active_descriptor.name}' in Scratch"
        Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)

    def ask_forge_to_mutate(self, instance):
        instruction = self.prompt_input.text.strip()
        if not instruction:
            self.lbl_status.text = "Please enter an instruction for Forge."
            return
        
        self.lbl_status.text = f"🤖 Mutating: '{instruction}'..."
        self.btn_ask.text = "⏳ ..."
        self.forge.mutate(self.code_editor.text, instruction)

    def on_forge_success(self, instance, action, code, explanation):
        self.btn_ask.text = "⚡ MUTATE"
        self.code_editor.text = code
        self.lbl_status.text = f"✨ {explanation}"
        self.prompt_input.text = ""
        if self.active_descriptor:
            self.app_manager.module_mgr.save_code(self.active_descriptor, code)
            Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)

    def on_forge_error(self, instance, action, error_msg):
        self.btn_ask.text = "⚡ MUTATE"
        self.lbl_status.text = f"❌ Error: {error_msg}"

    def run_code_live(self, instance):
        code = self.code_editor.text
        try:
            ast.parse(code)
        except SyntaxError as e:
            self.lbl_status.text = f"Syntax Error: {e}"
            return

        if not self.active_descriptor:
            self.active_descriptor = self.app_manager.module_mgr.create_scratch(code, prompt="live_preview")
        else:
            self.app_manager.module_mgr.save_code(self.active_descriptor, code)

        Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)
        Clock.schedule_once(lambda dt, d=self.active_descriptor: self.app_manager.launch_module(d), 0.05)
