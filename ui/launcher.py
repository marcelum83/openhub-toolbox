"""
OpenHub Home Launcher (The Deck & Fast Creation Engine)
Flat GridLayout architecture: every card and section is a direct child with guaranteed touch propagation.
"""
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.clock import Clock
from ui.themes import ColorSystem

class ProgressBarWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress = 0.0
        self.bind(size=self.draw, pos=self.draw)

    def set_progress(self, val):
        self.progress = max(0.0, min(1.0, val))
        self.draw()

    def draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.15, 0.15, 0.22, 1.0)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])
            if self.progress > 0:
                Color(0.02, 0.71, 0.83, 1.0)
                RoundedRectangle(pos=self.pos, size=(self.width * self.progress, self.height), radius=[dp(6)])


class UpdateModal(ModalView):
    def __init__(self, update_info, updater, **kwargs):
        super().__init__(size_hint=(0.92, 0.65), auto_dismiss=True, **kwargs)
        self.update_info = update_info
        self.updater = updater

        root = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(12))
        with root.canvas.before:
            Color(0.09, 0.09, 0.13, 0.98)
            self.bg_rect = RoundedRectangle(size=root.size, pos=root.pos, radius=[dp(18)])
            Color(0.02, 0.71, 0.83, 0.8)
            self.border_rect = Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(18)), width=1.5)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # Title
        lbl_title = Label(
            text="🚀 NEW UPDATE AVAILABLE",
            font_size="20sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1.0),
            size_hint_y=None,
            height=dp(36),
            halign='center'
        )
        root.add_widget(lbl_title)

        # Version & Date
        v_str = update_info.get("version", "1.0.0")
        b_date = update_info.get("build_date", "Latest")
        lbl_meta = Label(
            text=f"Version: v{v_str}  •  Built: {b_date}",
            font_size="13sp",
            color=(0.7, 0.7, 0.8, 1.0),
            size_hint_y=None,
            height=dp(24),
            halign='center'
        )
        root.add_widget(lbl_meta)

        # Changelog
        changelog = update_info.get("changelog", "Core updates and sensor improvements.")
        lbl_change = Label(
            text=f"What's New:\n{changelog}",
            font_size="14sp",
            color=(0.9, 0.9, 0.95, 1.0),
            halign='left',
            valign='top'
        )
        lbl_change.bind(size=lbl_change.setter('text_size'))
        root.add_widget(lbl_change)

        # Progress Bar & Status Text
        self.progress_bar = ProgressBarWidget(size_hint_y=None, height=dp(12))
        root.add_widget(self.progress_bar)

        self.lbl_status = Label(
            text="Ready to download and install.",
            font_size="13sp",
            color=(0.6, 0.6, 0.7, 1.0),
            size_hint_y=None,
            height=dp(24),
            halign='center'
        )
        root.add_widget(self.lbl_status)

        # Action Buttons
        btn_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(10))
        
        self.btn_install = Button(
            text="⬇️ INSTALL UPDATE",
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="15sp",
            always_release=True
        )
        self.btn_install.bind(on_release=self.start_update)
        btn_box.add_widget(self.btn_install)

        btn_close = Button(
            text="LATER",
            size_hint_x=0.35,
            background_normal="",
            background_color=(0.18, 0.18, 0.26, 1.0),
            color=(0.8, 0.8, 0.9, 1.0),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_close.bind(on_release=lambda x: self.dismiss())
        btn_box.add_widget(btn_close)
        root.add_widget(btn_box)

        self.add_widget(root)

    def _update_bg(self, inst, val):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size
        self.border_rect.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(18))

    def start_update(self, *args):
        self.btn_install.disabled = True
        self.btn_install.text = "DOWNLOADING..."
        self.lbl_status.text = "Starting download..."
        self.updater.start_download_and_install(
            self.update_info,
            on_progress=self.on_download_progress,
            on_complete=self.on_download_complete
        )

    def on_download_progress(self, percent, downloaded, total):
        self.progress_bar.set_progress(percent / 100.0)
        mb_down = downloaded / (1024.0 * 1024.0)
        mb_tot = total / (1024.0 * 1024.0) if total > 0 else 0
        self.lbl_status.text = f"Downloading: {mb_down:.1f} MB / {mb_tot:.1f} MB ({int(percent)}%)"

    def on_download_complete(self, success, path, error):
        if success:
            self.progress_bar.set_progress(1.0)
            self.lbl_status.text = "✅ Launching Package Installer..."
            self.btn_install.text = "LAUNCHING..."
            Clock.schedule_once(lambda dt: self.dismiss(), 1.5)
        else:
            self.lbl_status.text = f"❌ Error: {error or 'Download failed'}"
            self.btn_install.disabled = False
            self.btn_install.text = "RETRY INSTALL"


class SettingsModal(ModalView):
    def __init__(self, updater, on_check_updates_cb, app_manager=None, **kwargs):
        super().__init__(size_hint=(0.94, 0.75), auto_dismiss=True, **kwargs)
        self.updater = updater
        self.on_check_updates_cb = on_check_updates_cb
        self.app_manager = app_manager

        root = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(10))
        with root.canvas.before:
            Color(0.09, 0.09, 0.13, 0.98)
            self.bg_rect = RoundedRectangle(size=root.size, pos=root.pos, radius=[dp(18)])
            Color(0.54, 0.36, 0.96, 0.8)
            self.border_rect = Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(18)), width=1.5)
        root.bind(size=self._update_bg, pos=self._update_bg)

        lbl_title = Label(text="⚙️ SETTINGS & FORGE AI", font_size="18sp", bold=True, color=(0.54, 0.36, 0.96, 1.0), size_hint_y=None, height=dp(30))
        root.add_widget(lbl_title)

        # Server Host
        lbl_host = Label(text="Local Server Address (IP:PORT):", font_size="13sp", color=(0.7, 0.7, 0.8, 1.0), size_hint_y=None, height=dp(20), halign='left')
        lbl_host.bind(size=lbl_host.setter('text_size'))
        root.add_widget(lbl_host)

        self.txt_host = TextInput(text=self.updater.server_host, multiline=False, font_size="15sp", size_hint_y=None, height=dp(42))
        root.add_widget(self.txt_host)

        # Gemini API Key
        lbl_api = Label(text="Gemini API Key (for Live AI Generation):", font_size="13sp", color=(0.7, 0.7, 0.8, 1.0), size_hint_y=None, height=dp(20), halign='left')
        lbl_api.bind(size=lbl_api.setter('text_size'))
        root.add_widget(lbl_api)

        current_key = self.updater.get_api_key()
        self.txt_api_key = TextInput(
            text=current_key,
            password=True,
            multiline=False,
            font_size="15sp",
            hint_text="Paste AI Studio API Key here...",
            size_hint_y=None,
            height=dp(42)
        )
        root.add_widget(self.txt_api_key)

        self.lbl_feedback = Label(text="Configure your local WiFi server or Gemini AI key.", font_size="12sp", color=(0.6, 0.6, 0.7, 1.0), size_hint_y=None, height=dp(22))
        root.add_widget(self.lbl_feedback)

        btn_check = Button(
            text="🔍 CHECK FOR APK UPDATES",
            background_normal="",
            background_color=(0.02, 0.71, 0.83, 1.0),
            color=(0.05, 0.05, 0.08, 1.0),
            bold=True,
            font_size="14sp",
            size_hint_y=None,
            height=dp(44),
            always_release=True
        )
        btn_check.bind(on_release=self.check_now)
        root.add_widget(btn_check)

        btn_close = Button(
            text="💾 SAVE & CLOSE",
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="14sp",
            size_hint_y=None,
            height=dp(44),
            always_release=True
        )
        btn_close.bind(on_release=self.save_and_close)
        root.add_widget(btn_close)

        self.add_widget(root)

    def _update_bg(self, inst, val):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size
        self.border_rect.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(18))

    def check_now(self, *args):
        new_host = self.txt_host.text.strip()
        new_key = self.txt_api_key.text.strip()
        self.updater.save_settings(server_host=new_host, gemini_api_key=new_key)
        if self.app_manager and hasattr(self.app_manager, 'forge'):
            self.app_manager.forge.gemini_api_key = new_key
        self.lbl_feedback.text = "Checking server..."
        self.updater.check_for_updates(self._on_check_cb)

    def _on_check_cb(self, has_update, data, error):
        if error:
            self.lbl_feedback.text = f"❌ Server unreachable: {error}"
        elif has_update:
            self.lbl_feedback.text = "🚀 New update found!"
            self.dismiss()
            if self.on_check_updates_cb:
                self.on_check_updates_cb(has_update, data, None)
        else:
            self.lbl_feedback.text = "✅ You have the latest version."

    def save_and_close(self, *args):
        new_host = self.txt_host.text.strip()
        new_key = self.txt_api_key.text.strip()
        self.updater.save_settings(server_host=new_host, gemini_api_key=new_key)
        if self.app_manager and hasattr(self.app_manager, 'forge'):
            self.app_manager.forge.gemini_api_key = new_key
        self.dismiss()

class ScratchCard(BoxLayout):
    """
    Card for disposable scratchpad experiments.
    Large touch targets: [▶ RUN] [✏️ EDIT] [📑 FORK] [💾 SAVE] [🗑️ DELETE]
    """
    def __init__(self, descriptor, on_run, on_edit, on_fork, on_save, on_delete, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=dp(140), padding=[dp(12), dp(10), dp(12), dp(10)], spacing=dp(8), **kwargs)
        self.descriptor = descriptor
        self.on_run = on_run
        self.on_edit = on_edit
        self.on_fork = on_fork
        self.on_save = on_save
        self.on_delete = on_delete
        
        with self.canvas.before:
            Color(0.12, 0.10, 0.18, 1.0)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(14)])
            Color(0.54, 0.36, 0.96, 0.6)
            self.border_rect = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(14)), width=1.0)
        self.bind(size=self._update_rects, pos=self._update_rects)

        # Header Row
        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(32), spacing=dp(8))
        lbl_title = Label(
            text=f"🧪 {descriptor.name}",
            font_size="18sp",
            bold=True,
            color=(0.95, 0.95, 0.97, 1),
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        head.add_widget(lbl_title)
        
        lbl_tag = Label(text="DRAFT", font_size="12sp", size_hint_x=None, width=dp(70), color=ColorSystem.SECONDARY, bold=True)
        head.add_widget(lbl_tag)
        self.add_widget(head)

        # Action Buttons Row
        self.actions_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        
        btn_run = Button(
            text="▶ RUN",
            size_hint_x=0.30,
            background_normal="",
            background_color=ColorSystem.SUCCESS,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="15sp",
            always_release=True
        )
        btn_run.bind(on_release=lambda *a, d=descriptor: self.on_run(d))
        self.actions_box.add_widget(btn_run)

        btn_edit = Button(
            text="✏️ EDIT",
            size_hint_x=0.22,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_edit.bind(on_release=lambda *a, d=descriptor: self.on_edit(d))
        self.actions_box.add_widget(btn_edit)

        btn_fork = Button(
            text="📑 FORK",
            size_hint_x=0.22,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_fork.bind(on_release=lambda *a, d=descriptor: self.on_fork(d))
        self.actions_box.add_widget(btn_fork)

        btn_save = Button(
            text="💾 SAVE",
            size_hint_x=0.22,
            background_normal="",
            background_color=ColorSystem.PRIMARY,
            color=ColorSystem.BG_DARK,
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_save.bind(on_release=lambda *a, d=descriptor: self.on_save(d))
        self.actions_box.add_widget(btn_save)

        btn_del = Button(
            text="🗑️",
            size_hint_x=None,
            width=dp(48),
            background_normal="",
            background_color=(0.35, 0.1, 0.1, 1),
            color=ColorSystem.DANGER,
            bold=True,
            font_size="16sp",
            always_release=True
        )
        btn_del.bind(on_release=lambda *a, d=descriptor: self.on_delete(d))
        self.actions_box.add_widget(btn_del)

        self.add_widget(self.actions_box)

    def _update_rects(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        self.border_rect.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, dp(14))


class PermanentToolCard(BoxLayout):
    """
    Card for established permanent tools.
    Mirrors ScratchCard layout for reliable mobile touch propagation.
    """
    def __init__(self, descriptor, on_run, on_edit, on_fork, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=dp(130), padding=[dp(12), dp(10), dp(12), dp(10)], spacing=dp(8), **kwargs)
        self.descriptor = descriptor
        self.on_run = on_run
        self.on_edit = on_edit
        self.on_fork = on_fork
        
        with self.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(14)])
            Color(*ColorSystem.SURFACE_BORDER)
            self.border_rect = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(14)), width=1.0)
        self.bind(size=self._update_rects, pos=self._update_rects)

        cat_emojis = {
            "Tools": "🛠️",
            "Field": "🌱",
            "Agents": "🤖",
            "Creative": "🎨",
            "Experiments": "🔬"
        }
        emoji = cat_emojis.get(descriptor.category, "📦")

        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(32), spacing=dp(8))
        lbl_title = Label(
            text=f"{emoji} {descriptor.name}",
            font_size="18sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        head.add_widget(lbl_title)
        
        lbl_cat = Label(
            text=f"[{descriptor.category.upper()}]",
            font_size="12sp",
            size_hint_x=None,
            width=dp(90),
            color=ColorSystem.PRIMARY,
            halign='right',
            valign='middle',
            bold=True
        )
        lbl_cat.bind(size=lbl_cat.setter('text_size'))
        head.add_widget(lbl_cat)
        self.add_widget(head)

        # Quick Actions Row
        actions = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        
        btn_run = Button(
            text="▶ RUN TOOL",
            size_hint_x=0.52,
            background_normal="",
            background_color=ColorSystem.SUCCESS,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="15sp",
            always_release=True
        )
        btn_run.bind(on_release=lambda *a, d=descriptor: self.on_run(d))
        actions.add_widget(btn_run)

        btn_edit = Button(
            text="✏️ CODE",
            size_hint_x=0.24,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_edit.bind(on_release=lambda *a, d=descriptor: self.on_edit(d))
        actions.add_widget(btn_edit)

        btn_fork = Button(
            text="📑 FORK",
            size_hint_x=0.24,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_fork.bind(on_release=lambda *a, d=descriptor: self.on_fork(d))
        actions.add_widget(btn_fork)

        self.add_widget(actions)

    def _update_rects(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        self.border_rect.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, dp(14))


class LauncherScreen(Screen):
    def __init__(self, app_manager, **kwargs):
        super().__init__(**kwargs)
        self.app_manager = app_manager
        self.forge = app_manager.forge
        self.forge.bind(on_forge_success=self.on_forge_generated_module)
        self.forge.bind(on_forge_error=self.on_forge_error)

        self.permanent_tools = []
        self.scratch_tools = []
        self.active_category = "All"

        root = BoxLayout(orientation='vertical', spacing=0)
        with root.canvas.before:
            Color(*ColorSystem.BG_DARK)
            self.bg_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # 1. Header Bar
        nav_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(64), padding=[dp(14), dp(8), dp(14), dp(8)], spacing=dp(10))
        with nav_bar.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.nav_rect = Rectangle(size=nav_bar.size, pos=nav_bar.pos)
        nav_bar.bind(size=self._update_nav_rect, pos=self._update_nav_rect)

        lbl_logo = Label(
            text="🌌 OPENHUB",
            font_size="18sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            size_hint_x=None,
            width=dp(110),
            halign='left',
            valign='middle'
        )
        lbl_logo.bind(size=lbl_logo.setter('text_size'))
        nav_bar.add_widget(lbl_logo)

        btn_agent = Button(
            text="💬 AGENT",
            size_hint_x=0.35,
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 0.9),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="12sp",
            always_release=True
        )
        btn_agent.bind(on_release=lambda x: setattr(self.manager, 'current', 'agent'))
        nav_bar.add_widget(btn_agent)

        btn_forge = Button(
            text="⚡ FORGE",
            size_hint_x=0.35,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="12sp",
            always_release=True
        )
        btn_forge.bind(on_release=lambda x: setattr(self.manager, 'current', 'forge'))
        nav_bar.add_widget(btn_forge)

        self.btn_update = Button(
            text="⚙️",
            size_hint_x=None,
            width=dp(42),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="15sp",
            always_release=True
        )
        self.btn_update.bind(on_release=self.on_nav_update_pressed)
        nav_bar.add_widget(self.btn_update)

        btn_refresh = Button(
            text="🔄",
            size_hint_x=None,
            width=dp(42),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="15sp",
            always_release=True
        )
        btn_refresh.bind(on_release=lambda x: self.app_manager.refresh_modules())
        nav_bar.add_widget(btn_refresh)
        root.add_widget(nav_bar)

        # 2. Main Scrollable Container with Flat GridLayout
        # Optimized for mobile touchscreen responsiveness
        self.main_scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            scroll_timeout=250,
            scroll_distance=dp(10),
            effect_cls='ScrollEffect'
        )
        self.content_grid = GridLayout(cols=1, spacing=dp(14), padding=dp(12), size_hint_y=None)
        self.content_grid.bind(minimum_height=self.content_grid.setter('height'))

        # SECTION A: "WHAT SHALL WE MAKE?" CREATION BOX
        self.create_panel = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(165), padding=dp(14), spacing=dp(10))
        with self.create_panel.canvas.before:
            Color(0.11, 0.11, 0.17, 1.0)
            self.create_bg = RoundedRectangle(size=self.create_panel.size, pos=self.create_panel.pos, radius=[dp(16)])
            Color(0.02, 0.71, 0.83, 0.5)
            self.create_border = Line(rounded_rectangle=(self.create_panel.x, self.create_panel.y, self.create_panel.width, self.create_panel.height, dp(16)), width=1.0)
        self.create_panel.bind(size=self._update_create_rects, pos=self._update_create_rects)

        lbl_prompt_title = Label(
            text="✨ What shall we make?",
            font_size="18sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            size_hint_y=None,
            height=dp(26),
            halign='left'
        )
        lbl_prompt_title.bind(size=lbl_prompt_title.setter('text_size'))
        self.create_panel.add_widget(lbl_prompt_title)

        prompt_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(56), spacing=dp(10))
        self.txt_prompt = TextInput(
            hint_text='e.g. "Solar collector heat calculator"...',
            multiline=False,
            font_size="15sp",
            background_color=ColorSystem.SURFACE,
            foreground_color=ColorSystem.TEXT_PRIMARY,
            hint_text_color=ColorSystem.TEXT_HINT,
            cursor_color=ColorSystem.PRIMARY,
            padding=[dp(12), dp(14), dp(12), dp(14)]
        )
        self.txt_prompt.bind(on_text_validate=self.on_create_prompt_submit)
        prompt_row.add_widget(self.txt_prompt)

        self.btn_create = Button(
            text="⚡ CREATE",
            size_hint_x=None,
            width=dp(120),
            background_normal="",
            background_color=ColorSystem.SECONDARY,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="14sp",
            always_release=True
        )
        self.btn_create.bind(on_release=self.on_create_prompt_submit)
        prompt_row.add_widget(self.btn_create)
        self.create_panel.add_widget(prompt_row)

        self.lbl_create_status = Label(
            text="Type any tool idea above to generate and test it instantly.",
            font_size="13sp",
            color=ColorSystem.TEXT_MUTED,
            size_hint_y=None,
            height=dp(22),
            halign='left'
        )
        self.lbl_create_status.bind(size=self.lbl_create_status.setter('text_size'))
        self.create_panel.add_widget(self.lbl_create_status)

        # Category Filter Row
        self.cat_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
        self.categories = ["All", "Tools", "Field", "Agents"]
        self.cat_btns = {}
        for cat in self.categories:
            b = Button(
                text=cat,
                background_normal="",
                background_color=ColorSystem.PRIMARY if cat == "All" else ColorSystem.SURFACE,
                color=ColorSystem.BG_DARK if cat == "All" else ColorSystem.TEXT_MUTED,
                bold=True,
                font_size="14sp",
                always_release=True
            )
            b.bind(on_release=lambda inst, c=cat: self.set_category_filter(c))
            self.cat_btns[cat] = b
            self.cat_box.add_widget(b)

        self.main_scroll.add_widget(self.content_grid)
        root.add_widget(self.main_scroll)
        self.add_widget(root)

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _update_nav_rect(self, instance, value):
        self.nav_rect.pos = instance.pos
        self.nav_rect.size = instance.size

    def _update_create_rects(self, instance, value):
        self.create_bg.pos = instance.pos
        self.create_bg.size = instance.size
        self.create_border.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, dp(16))

    def on_create_prompt_submit(self, instance):
        prompt = self.txt_prompt.text.strip()
        if not prompt:
            self.lbl_create_status.text = "Please enter what tool you want to create."
            return
        
        self.lbl_create_status.text = f"🤖 Generating '{prompt}'..."
        self.btn_create.text = "⏳ ..."
        self.current_generating_prompt = prompt
        self.forge.generate(prompt)

    def on_forge_generated_module(self, instance, action, code, explanation):
        if action != "generate":
            return
        self.btn_create.text = "⚡ CREATE"
        prompt_text = getattr(self, 'current_generating_prompt', 'tool')
        self.txt_prompt.text = ""
        self.lbl_create_status.text = f"✨ Created: {explanation}"

        desc = self.app_manager.module_mgr.create_scratch(code, prompt=prompt_text)
        Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)
        Clock.schedule_once(lambda dt, d=desc: self.app_manager.launch_module(d), 0.05)

    def on_forge_error(self, instance, action, error_msg):
        self.btn_create.text = "⚡ CREATE"
        self.lbl_create_status.text = f"❌ Error: {error_msg}"

    def update_all_modules(self, permanent, scratch):
        self.permanent_tools = permanent
        self.scratch_tools = scratch
        self.rebuild_views()

    def set_category_filter(self, category):
        self.active_category = category
        for cat, btn in self.cat_btns.items():
            if cat == category:
                btn.background_color = ColorSystem.PRIMARY
                btn.color = ColorSystem.BG_DARK
            else:
                btn.background_color = ColorSystem.SURFACE
                btn.color = ColorSystem.TEXT_MUTED
        Clock.schedule_once(lambda dt: self.rebuild_views(), 0)

    def rebuild_views(self):
        """Rebuilds the entire flat content grid with exact height calculations."""
        self.content_grid.clear_widgets()

        # 1. Top Creation Panel
        self.content_grid.add_widget(self.create_panel)

        # 2. Scratch / Live Experiments Shelf
        if self.scratch_tools:
            lbl_scratch = Label(
                text=f"🧪 LIVE EXPERIMENTS & SCRATCH ({len(self.scratch_tools)} Active)",
                font_size="15sp",
                bold=True,
                color=ColorSystem.SECONDARY,
                size_hint_y=None,
                height=dp(28),
                halign='left'
            )
            lbl_scratch.bind(size=lbl_scratch.setter('text_size'))
            self.content_grid.add_widget(lbl_scratch)

            for desc in self.scratch_tools:
                card = ScratchCard(
                    desc,
                    on_run=self.app_manager.launch_module,
                    on_edit=self.edit_module,
                    on_fork=self.fork_module,
                    on_save=self.prompt_save_scratch,
                    on_delete=self.delete_module
                )
                self.content_grid.add_widget(card)

        # 3. Category Filter Tabs
        self.content_grid.add_widget(self.cat_box)

        # 4. Permanent Toolbox Shelf
        lbl_tools = Label(
            text="🛠️ MY SAVED TOOLS",
            font_size="15sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            size_hint_y=None,
            height=dp(28),
            halign='left'
        )
        lbl_tools.bind(size=lbl_tools.setter('text_size'))
        self.content_grid.add_widget(lbl_tools)

        for desc in self.permanent_tools:
            if self.active_category != "All" and desc.category != self.active_category:
                continue
            card = PermanentToolCard(
                desc,
                on_run=self.app_manager.launch_module,
                on_edit=self.edit_module,
                on_fork=self.fork_module
            )
            self.content_grid.add_widget(card)

    def edit_module(self, descriptor):
        print(f"[Launcher] edit_module called for: {descriptor.name} ({descriptor.entrypoint})")
        try:
            code = self.app_manager.module_mgr.read_code(descriptor)
            forge_screen = self.manager.get_screen('forge')
            forge_screen.load_descriptor_for_editing(descriptor, code)
            Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'forge'), 0)
        except Exception as e:
            err_msg = f"Error opening code: {e}"
            print(f"[Launcher] {err_msg}")
            import traceback
            traceback.print_exc()
            self.lbl_create_status.text = f"❌ {err_msg}"

    def fork_module(self, descriptor):
        print(f"[Launcher] fork_module called for: {descriptor.name}")
        try:
            new_desc = self.app_manager.module_mgr.fork(descriptor)
            self.lbl_create_status.text = f"📑 Forked '{descriptor.name}' as '{new_desc.name}'"
            Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)
            Clock.schedule_once(lambda dt, d=new_desc: self.app_manager.launch_module(d), 0.05)
        except Exception as e:
            err_msg = f"Fork error: {e}"
            print(f"[Launcher] {err_msg}")
            import traceback
            traceback.print_exc()
            self.lbl_create_status.text = f"❌ {err_msg}"

    def prompt_save_scratch(self, descriptor):
        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(16))
        content.add_widget(Label(text=f"Save '{descriptor.name}' as Permanent Tool:", font_size="16sp"))
        name_in = TextInput(text=descriptor.name, multiline=False, font_size="16sp", size_hint_y=None, height=dp(52))
        content.add_widget(name_in)
        
        btn_row = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(52))
        popup = Popup(title="Promote to Permanent Tool", content=content, size_hint=(0.9, 0.45))
        
        btn_ok = Button(text="Save to Toolbox", background_color=ColorSystem.PRIMARY, bold=True, font_size="15sp", always_release=True)
        def confirm_save(inst):
            final_name = name_in.text.strip() or descriptor.name
            try:
                self.app_manager.module_mgr.promote_to_permanent(descriptor, final_name)
                self.lbl_create_status.text = f"💾 Saved '{final_name}' to Toolbox"
                Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)
            except Exception as e:
                print(f"[Launcher] Error promoting module: {e}")
            popup.dismiss()
            
        btn_ok.bind(on_release=confirm_save)
        btn_row.add_widget(btn_ok)
        content.add_widget(btn_row)
        popup.open()

    def delete_module(self, descriptor):
        try:
            self.app_manager.module_mgr.delete(descriptor)
            self.lbl_create_status.text = f"🗑️ Deleted '{descriptor.name}'"
            Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)
        except Exception as e:
            print(f"[Launcher] Error deleting module: {e}")

    def on_update_check_result(self, has_update, update_info, error):
        """Called asynchronously when server update check finishes."""
        if error:
            print(f"[Launcher] Update check notice: {error}")
            return
        
        if has_update and update_info:
            self.btn_update.text = "🚀 UPDATE"
            self.btn_update.background_color = (0.15, 0.68, 0.38, 1.0)
            self.btn_update.color = (1, 1, 1, 1)
            # Show update modal
            modal = UpdateModal(update_info, self.app_manager.updater)
            modal.open()
        else:
            self.btn_update.text = "⚙️ SYNC"
            self.btn_update.background_color = ColorSystem.SURFACE_HOVER
            self.btn_update.color = ColorSystem.TEXT_PRIMARY

    def on_nav_update_pressed(self, *args):
        updater = self.app_manager.updater
        if updater.latest_update_info and self.btn_update.text == "🚀 UPDATE":
            UpdateModal(updater.latest_update_info, updater).open()
        else:
            SettingsModal(updater, self.on_update_check_result, app_manager=self.app_manager).open()
