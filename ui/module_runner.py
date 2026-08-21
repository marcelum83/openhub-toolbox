"""
OpenHub Active Module Runner Screen
Wraps the dynamically loaded module widget inside a clean host screen with a header
and an inline live AI mutation bar.
"""
import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, RoundedRectangle
from ui.themes import ColorSystem
from core.forge_agent import ForgeAgent

class ModuleRunnerScreen(Screen):
    def __init__(self, app_manager, **kwargs):
        super().__init__(**kwargs)
        self.app_manager = app_manager
        self.active_module_widget = None
        self.active_descriptor = None
        
        self.agent = ForgeAgent()
        self.agent.bind(on_agent_result=self.on_live_mutate_result)
        self.agent.bind(on_agent_error=self.on_live_mutate_error)
        
        self.layout = BoxLayout(orientation='vertical')
        
        # 1. Header Bar
        self.header = BoxLayout(orientation='horizontal', size_hint_y=None, height=52, padding=[10, 6, 10, 6], spacing=10)
        with self.header.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.header_bg = Rectangle(size=self.header.size, pos=self.header.pos)
        self.header.bind(size=self._update_header_rect, pos=self._update_header_rect)
        
        # Back Button
        self.btn_back = Button(
            text="◀ DECK",
            size_hint_x=None,
            width=80,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.PRIMARY,
            bold=True
        )
        self.btn_back.bind(on_release=self.on_back_clicked)
        self.header.add_widget(self.btn_back)
        
        # Module Title
        self.lbl_title = Label(
            text="Module",
            font_size="16sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        self.header.add_widget(self.lbl_title)
        
        # Edit in Forge Button
        self.btn_edit_code = Button(
            text="✏️ CODE",
            size_hint_x=None,
            width=75,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="11sp"
        )
        self.btn_edit_code.bind(on_release=self.open_in_forge)
        self.header.add_widget(self.btn_edit_code)
        
        self.layout.add_widget(self.header)
        
        # 2. Viewport Container for the loaded module widget
        self.viewport = BoxLayout(orientation='vertical')
        self.layout.add_widget(self.viewport)
        
        # 3. Bottom Inline Live AI Mutator Bar
        self.mutate_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=48, padding=[8, 4, 8, 4], spacing=6)
        with self.mutate_bar.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.mutate_bg = Rectangle(size=self.mutate_bar.size, pos=self.mutate_bar.pos)
        self.mutate_bar.bind(size=self._update_mutate_rect, pos=self._update_mutate_rect)

        self.txt_mutate = TextInput(
            hint_text="⚡ Tweak tool: e.g. 'Add gallons & drawing'...",
            multiline=False,
            background_color=ColorSystem.BG_DARK,
            foreground_color=ColorSystem.TEXT_PRIMARY,
            hint_text_color=ColorSystem.TEXT_HINT,
            cursor_color=ColorSystem.SECONDARY,
            padding=[8, 6, 8, 6]
        )
        self.txt_mutate.bind(on_text_validate=self.trigger_inline_mutation)
        self.mutate_bar.add_widget(self.txt_mutate)

        self.btn_mutate = Button(
            text="⚡ TWEAK",
            size_hint_x=None,
            width=85,
            background_normal="",
            background_color=ColorSystem.SECONDARY,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="11sp"
        )
        self.btn_mutate.bind(on_release=self.trigger_inline_mutation)
        self.mutate_bar.add_widget(self.btn_mutate)

        self.layout.add_widget(self.mutate_bar)
        self.add_widget(self.layout)

    def _update_header_rect(self, instance, value):
        self.header_bg.pos = instance.pos
        self.header_bg.size = instance.size

    def _update_mutate_rect(self, instance, value):
        self.mutate_bg.pos = instance.pos
        self.mutate_bg.size = instance.size

    def set_module(self, descriptor, widget):
        self.active_descriptor = descriptor
        self.active_module_widget = widget
        self.lbl_title.text = f"{descriptor.name}"
        
        self.viewport.clear_widgets()
        self.viewport.add_widget(widget)
        
        if hasattr(widget, 'on_resume'):
            try:
                widget.on_resume()
            except Exception as e:
                print(f"[ModuleRunner] on_resume error: {e}")

    def on_back_clicked(self, instance):
        if self.active_module_widget and hasattr(self.active_module_widget, 'on_pause'):
            try:
                self.active_module_widget.on_pause()
            except Exception as e:
                print(f"[ModuleRunner] on_pause error: {e}")
                
        if self.manager:
            self.manager.current = 'launcher'

    def open_in_forge(self, instance):
        if not self.active_descriptor or not os.path.exists(self.active_descriptor.entrypoint):
            return
        try:
            with open(self.active_descriptor.entrypoint, 'r', encoding='utf-8') as f:
                code = f.read()
            forge = self.manager.get_screen('forge')
            forge.load_code_for_editing(self.active_descriptor.name, code, self.active_descriptor.entrypoint)
            self.manager.current = 'forge'
        except Exception as e:
            print(f"Error opening code in forge: {e}")

    def trigger_inline_mutation(self, instance):
        instruction = self.txt_mutate.text.strip()
        if not instruction or not self.active_descriptor:
            return
        
        try:
            with open(self.active_descriptor.entrypoint, 'r', encoding='utf-8') as f:
                current_code = f.read()
        except Exception as e:
            print(f"Failed to read current module code: {e}")
            return

        self.btn_mutate.text = "⏳ ..."
        self.agent.generate_or_mutate_tool(instruction, current_code)

    def on_live_mutate_result(self, instance, new_code, explanation):
        self.btn_mutate.text = "⚡ TWEAK"
        self.txt_mutate.text = ""
        if not self.active_descriptor:
            return

        # Write mutated code directly to entrypoint file
        with open(self.active_descriptor.entrypoint, 'w', encoding='utf-8') as f:
            f.write(new_code)

        # Hot-reload the module immediately in place!
        self.app_manager.launch_module(self.active_descriptor)

    def on_live_mutate_error(self, instance, error_msg):
        self.btn_mutate.text = "⚡ TWEAK"
        print(f"[LiveMutate Error] {error_msg}")
