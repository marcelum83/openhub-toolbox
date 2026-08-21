"""
OpenHub Active Module Runner Screen
Wraps the dynamically loaded module widget inside a clean host screen with a header.
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle
from ui.themes import ColorSystem

class ModuleRunnerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_module_widget = None
        self.active_descriptor = None
        
        self.layout = BoxLayout(orientation='vertical')
        
        # Header Bar
        self.header = BoxLayout(orientation='horizontal', size_hint_y=None, height=56, padding=[10, 6, 10, 6], spacing=10)
        with self.header.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.header_bg = Rectangle(size=self.header.size, pos=self.header.pos)
        self.header.bind(size=self._update_header_rect, pos=self._update_header_rect)
        
        # Back Button
        self.btn_back = Button(
            text="◀ BACK",
            size_hint_x=None,
            width=90,
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
            font_size="18sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            halign='left',
            valign='middle'
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        self.header.add_widget(self.lbl_title)
        
        # Category / Trust Badge
        self.lbl_badge = Label(
            text="TRUSTED",
            font_size="11sp",
            size_hint_x=None,
            width=85,
            color=ColorSystem.SUCCESS,
            bold=True
        )
        self.header.add_widget(self.lbl_badge)
        
        self.layout.add_widget(self.header)
        
        # Viewport Container for the loaded module widget
        self.viewport = BoxLayout(orientation='vertical')
        self.layout.add_widget(self.viewport)
        
        self.add_widget(self.layout)

    def _update_header_rect(self, instance, value):
        self.header_bg.pos = instance.pos
        self.header_bg.size = instance.size

    def set_module(self, descriptor, widget):
        self.active_descriptor = descriptor
        self.active_module_widget = widget
        self.lbl_title.text = f"{descriptor.name}"
        
        # Trust badge coloring
        if descriptor.trust_level == "trusted":
            self.lbl_badge.text = "🟢 TRUSTED"
            self.lbl_badge.color = ColorSystem.SUCCESS
        elif descriptor.trust_level == "community":
            self.lbl_badge.text = "🟡 COMMUNITY"
            self.lbl_badge.color = ColorSystem.WARNING
        else:
            self.lbl_badge.text = "🔴 EXPERIMENTAL"
            self.lbl_badge.color = ColorSystem.DANGER

        # Clear and mount new widget
        self.viewport.clear_widgets()
        self.viewport.add_widget(widget)
        
        # Call on_resume lifecycle hook if present
        if hasattr(widget, 'on_resume'):
            try:
                widget.on_resume()
            except Exception as e:
                print(f"[ModuleRunner] on_resume error: {e}")

    def on_back_clicked(self, instance):
        # Call on_pause on active widget
        if self.active_module_widget and hasattr(self.active_module_widget, 'on_pause'):
            try:
                self.active_module_widget.on_pause()
            except Exception as e:
                print(f"[ModuleRunner] on_pause error: {e}")
                
        # Return to launcher screen
        if self.manager:
            self.manager.current = 'launcher'
