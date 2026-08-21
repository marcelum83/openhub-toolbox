"""
OpenHub Forge & In-App Studio Screen
Pydroid3-style live code editor, AI self-mutator bar, and instant test runner.
"""
import os
import ast
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from ui.themes import ColorSystem
from core.forge_agent import ForgeAgent
from core.scanner import ModuleDescriptor
from core.security import TrustLevel

STARTER_CODE = """# OpenHub Dynamic Module
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider

class OpenHubModule(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=15, **kwargs)
        
        self.add_widget(Label(
            text="✨ My Custom Tool",
            font_size="22sp",
            size_hint_y=None,
            height=45,
            color=(0.02, 0.71, 0.83, 1)
        ))
        
        self.val_label = Label(text="Scale Factor: 1.0", font_size="16sp", size_hint_y=None, height=35)
        self.add_widget(self.val_label)
        
        slider = Slider(min=1, max=10, value=1)
        slider.bind(value=self.on_slider)
        self.add_widget(slider)
        
        btn = Button(
            text="Trigger Action",
            size_hint_y=None,
            height=50,
            background_color=(0.54, 0.36, 0.96, 1)
        )
        btn.bind(on_release=self.on_press_btn)
        self.add_widget(btn)

    def on_load(self, host_api):
        self.host = host_api

    def on_slider(self, inst, val):
        self.val_label.text = f"Scale Factor: {val:.1f}"

    def on_press_btn(self, inst):
        if hasattr(self, 'host') and self.host and self.host.hardware:
            self.host.hardware.vibrate(50)
        self.val_label.text = "⚡ Action Executed with Haptics!"
"""

class ForgeStudioScreen(Screen):
    def __init__(self, app_manager, **kwargs):
        super().__init__(**kwargs)
        self.app_manager = app_manager
        self.active_file_path = None
        self.agent = ForgeAgent()
        self.agent.bind(on_agent_result=self.on_agent_result)
        self.agent.bind(on_agent_error=self.on_agent_error)

        root = BoxLayout(orientation='vertical', spacing=0)
        with root.canvas.before:
            Color(*ColorSystem.BG_DARK)
            self.bg_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # 1. Top Nav Bar
        nav = BoxLayout(orientation='horizontal', size_hint_y=None, height=52, padding=[12, 6, 12, 6], spacing=10)
        with nav.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.nav_rect = Rectangle(size=nav.size, pos=nav.pos)
        nav.bind(size=self._update_nav_rect, pos=self._update_nav_rect)

        # Back to Deck Button
        btn_back = Button(
            text="◀ DECK",
            size_hint_x=None,
            width=80,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.PRIMARY,
            bold=True
        )
        btn_back.bind(on_release=self.switch_to_deck)
        nav.add_widget(btn_back)

        self.lbl_editor_title = Label(
            text="⚡ FORGE STUDIO",
            font_size="16sp",
            bold=True,
            color=ColorSystem.SECONDARY,
            halign='left',
            valign='middle'
        )
        self.lbl_editor_title.bind(size=self.lbl_editor_title.setter('text_size'))
        nav.add_widget(self.lbl_editor_title)

        root.add_widget(nav)

        # 2. Action Toolbar: [▶ RUN LIVE] [💾 SAVE] [➕ NEW]
        toolbar = BoxLayout(orientation='horizontal', size_hint_y=None, height=44, padding=[12, 4, 12, 4], spacing=8)
        
        btn_run = Button(
            text="▶ RUN LIVE",
            background_normal="",
            background_color=ColorSystem.SUCCESS,
            color=(1, 1, 1, 1),
            bold=True
        )
        btn_run.bind(on_release=self.run_code_live)
        toolbar.add_widget(btn_run)

        btn_save = Button(
            text="💾 SAVE FILE",
            background_normal="",
            background_color=ColorSystem.PRIMARY,
            color=ColorSystem.BG_DARK,
            bold=True
        )
        btn_save.bind(on_release=self.save_current_file)
        toolbar.add_widget(btn_save)

        btn_new = Button(
            text="➕ NEW",
            size_hint_x=0.3,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True
        )
        btn_new.bind(on_release=self.new_scratch_file)
        toolbar.add_widget(btn_new)

        root.add_widget(toolbar)

        # 3. Touch Code Editor
        self.code_editor = TextInput(
            text=STARTER_CODE,
            font_name="RobotoMono-Regular" if os.path.exists("RobotoMono-Regular.ttf") else "Roboto",
            font_size="13sp",
            background_color=ColorSystem.SURFACE,
            foreground_color=ColorSystem.TEXT_PRIMARY,
            cursor_color=ColorSystem.PRIMARY,
            padding=[10, 10, 10, 10]
        )
        root.add_widget(self.code_editor)

        # 4. Status / Console Log Bar
        self.lbl_status = Label(
            text="Ready. Edit code or prompt AI below.",
            font_size="12sp",
            color=ColorSystem.TEXT_MUTED,
            size_hint_y=None,
            height=28,
            halign='left'
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        root.add_widget(self.lbl_status)

        # 5. Agent Prompt & Mutation Bar
        prompt_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, padding=[12, 6, 12, 6], spacing=8)
        self.prompt_input = TextInput(
            hint_text="🤖 Ask AI to mutate: e.g. 'Add a drawing showing dimensions'...",
            multiline=False,
            background_color=ColorSystem.SURFACE,
            foreground_color=ColorSystem.TEXT_PRIMARY,
            hint_text_color=ColorSystem.TEXT_HINT,
            cursor_color=ColorSystem.SECONDARY,
            padding=[10, 8, 10, 8]
        )
        self.prompt_input.bind(on_text_validate=self.ask_agent_to_mutate)
        prompt_box.add_widget(self.prompt_input)

        self.btn_ask = Button(
            text="⚡ MUTATE",
            size_hint_x=None,
            width=100,
            background_normal="",
            background_color=ColorSystem.SECONDARY,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True
        )
        self.btn_ask.bind(on_release=self.ask_agent_to_mutate)
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

    def load_code_for_editing(self, title, code, file_path):
        self.active_file_path = file_path
        self.code_editor.text = code
        self.lbl_editor_title.text = f"✏️ {title}"
        self.lbl_status.text = f"Editing: {os.path.basename(file_path)}"

    def new_scratch_file(self, instance):
        self.active_file_path = None
        self.code_editor.text = STARTER_CODE
        self.lbl_editor_title.text = "⚡ FORGE STUDIO (NEW)"
        self.lbl_status.text = "New scratch draft initialized."

    def save_current_file(self, instance):
        code = self.code_editor.text
        if self.active_file_path:
            with open(self.active_file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            self.lbl_status.text = f"✅ Saved to {os.path.basename(self.active_file_path)}"
            self.app_manager.refresh_modules()
        else:
            # Create new scratch file
            scratch_dir = os.path.abspath("./modules/scratch")
            os.makedirs(scratch_dir, exist_ok=True)
            existing = [f for f in os.listdir(scratch_dir) if f.startswith("tmp_") and f.endswith(".py")]
            next_idx = len(existing) + 1
            filename = f"tmp_{next_idx:03d}_custom_tool.py"
            self.active_file_path = os.path.join(scratch_dir, filename)
            with open(self.active_file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            self.lbl_status.text = f"✅ Created {filename}"
            self.app_manager.refresh_modules()

    def ask_agent_to_mutate(self, instance):
        prompt = self.prompt_input.text.strip()
        if not prompt:
            self.lbl_status.text = "Please enter an instruction for the agent."
            return
        
        self.lbl_status.text = f"🤖 Agent mutating code: '{prompt}'..."
        self.btn_ask.text = "⏳ ..."
        self.agent.generate_or_mutate_tool(prompt, self.code_editor.text)

    def on_agent_result(self, instance, code, explanation):
        self.btn_ask.text = "⚡ MUTATE"
        self.code_editor.text = code
        self.lbl_status.text = f"✨ {explanation}"
        self.prompt_input.text = ""
        # Auto-save to active file if present
        if self.active_file_path:
            with open(self.active_file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            self.app_manager.refresh_modules()

    def on_agent_error(self, instance, error_msg):
        self.btn_ask.text = "⚡ MUTATE"
        self.lbl_status.text = f"❌ Error: {error_msg}"

    def run_code_live(self, instance):
        code = self.code_editor.text
        try:
            ast.parse(code)
        except SyntaxError as e:
            self.lbl_status.text = f"Syntax Error: {e}"
            return

        # Ensure file exists
        if not self.active_file_path:
            scratch_dir = os.path.abspath("./modules/scratch")
            os.makedirs(scratch_dir, exist_ok=True)
            self.active_file_path = os.path.join(scratch_dir, "live_preview.py")

        with open(self.active_file_path, 'w', encoding='utf-8') as f:
            f.write(code)

        desc = ModuleDescriptor(
            mod_id="live_preview",
            name=os.path.basename(self.active_file_path),
            category="Scratch",
            description="Active Live Code Session",
            entrypoint=self.active_file_path,
            trust_level=TrustLevel.EXPERIMENTAL,
            is_scratch=True
        )
        self.app_manager.launch_module(desc)
