"""
OpenHub Android-Style Home Screen & Swipe-Up App Drawer
Features:
- Android / Pixel-style customizable 4-column Home Screen grid with persistent storage
- 'At a Glance' live clock, date, and hardware sensor telemetry widget
- Fixed bottom dock with primary quick-launch shortcuts
- Swipe-up / tap gesture animated App Drawer with real-time search and category filtering
- Full Drag & Drop: long-press any app in the drawer or home screen to drag, pin, reorder, or remove
- Long-press context actions: Launch, Pin/Unpin, Edit Code, Fork, Promote, Publish, Delete
"""
import time
import datetime
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window

from ui.themes import ColorSystem
from core.home_layout import HomeLayoutManager


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

        lbl_host = Label(text="Local Server Address (IP:PORT):", font_size="13sp", color=(0.7, 0.7, 0.8, 1.0), size_hint_y=None, height=dp(20), halign='left')
        lbl_host.bind(size=lbl_host.setter('text_size'))
        root.add_widget(lbl_host)

        self.txt_host = TextInput(text=self.updater.server_host, multiline=False, font_size="15sp", size_hint_y=None, height=dp(42))
        root.add_widget(self.txt_host)

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


class CommunityHubModal(ModalView):
    def __init__(self, app_manager, **kwargs):
        super().__init__(size_hint=(0.94, 0.82), auto_dismiss=True, **kwargs)
        self.app_manager = app_manager
        
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        with root.canvas.before:
            Color(0.09, 0.09, 0.13, 0.98)
            self.bg_rect = RoundedRectangle(size=root.size, pos=root.pos, radius=[dp(18)])
            Color(0.02, 0.71, 0.83, 0.8)
            self.border_rect = Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(18)), width=1.5)
        root.bind(size=self._update_bg, pos=self._update_bg)

        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))
        lbl_title = Label(text="🌐 COMMUNITY TOOL REGISTRY", font_size="17sp", bold=True, color=(0.02, 0.71, 0.83, 1.0), halign='left')
        lbl_title.bind(size=lbl_title.setter('text_size'))
        head.add_widget(lbl_title)
        
        btn_refresh = Button(text="🔄", size_hint_x=None, width=dp(42), background_normal="", background_color=(0.18, 0.18, 0.26, 1.0), always_release=True)
        btn_refresh.bind(on_release=lambda x: self.load_catalog())
        head.add_widget(btn_refresh)
        root.add_widget(head)

        lbl_desc = Label(
            text="Browse & download modules from the central GitHub repository.",
            font_size="12sp",
            color=(0.6, 0.6, 0.7, 1.0),
            size_hint_y=None,
            height=dp(20),
            halign='left'
        )
        lbl_desc.bind(size=lbl_desc.setter('text_size'))
        root.add_widget(lbl_desc)

        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.cat_grid = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.cat_grid.bind(minimum_height=self.cat_grid.setter('height'))
        self.scroll.add_widget(self.cat_grid)
        root.add_widget(self.scroll)

        self.lbl_status = Label(text="Loading catalog...", font_size="13sp", color=(0.7, 0.7, 0.8, 1.0), size_hint_y=None, height=dp(24))
        root.add_widget(self.lbl_status)

        btn_close = Button(
            text="CLOSE",
            background_normal="",
            background_color=(0.18, 0.18, 0.26, 1.0),
            color=(0.8, 0.8, 0.9, 1.0),
            bold=True,
            font_size="14sp",
            size_hint_y=None,
            height=dp(44),
            always_release=True
        )
        btn_close.bind(on_release=lambda x: self.dismiss())
        root.add_widget(btn_close)

        self.add_widget(root)
        Clock.schedule_once(lambda dt: self.load_catalog(), 0.1)

    def _update_bg(self, inst, val):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size
        self.border_rect.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(18))

    def load_catalog(self):
        self.lbl_status.text = "Fetching catalog from central repo..."
        self.cat_grid.clear_widgets()
        host = self.app_manager.updater.server_host
        self.app_manager.module_mgr.fetch_community_catalog(host, self.on_catalog_loaded)

    def on_catalog_loaded(self, success, catalog, error):
        if not success:
            self.lbl_status.text = f"❌ Error: {error or 'Could not connect to repo'}"
            return
        
        self.cat_grid.clear_widgets()
        self.lbl_status.text = f"Found {len(catalog)} tools in central repository"
        
        for item in catalog:
            mod_id = item.get("id", "")
            name = item.get("name", mod_id)
            desc = item.get("description", "OpenHub tool")
            author = item.get("author", "community")
            
            card = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(105), padding=dp(10), spacing=dp(6))
            with card.canvas.before:
                Color(0.12, 0.12, 0.18, 1.0)
                bg = RoundedRectangle(size=card.size, pos=card.pos, radius=[dp(10)])
                Color(0.2, 0.2, 0.28, 0.6)
                bdr = Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(10)), width=1.0)
            card.bind(size=lambda inst, val, b=bg, d=bdr: setattr(b, 'pos', inst.pos) or setattr(b, 'size', inst.size) or setattr(d, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(10))))
            
            h_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(24))
            h_row.add_widget(Label(text=f"📦 {name}", font_size="15sp", bold=True, color=(0.95, 0.95, 0.97, 1.0), halign='left'))
            h_row.add_widget(Label(text=f"by {author}", font_size="11sp", color=(0.6, 0.6, 0.7, 1.0), halign='right'))
            card.add_widget(h_row)
            
            card.add_widget(Label(text=desc, font_size="12sp", color=(0.7, 0.7, 0.8, 1.0), halign='left', size_hint_y=None, height=dp(20)))
            
            btn_inst = Button(
                text="⬇️ INSTALL / SYNC TO PHONE",
                background_normal="",
                background_color=(0.15, 0.68, 0.38, 1.0),
                color=(1, 1, 1, 1),
                bold=True,
                font_size="13sp",
                size_hint_y=None,
                height=dp(36),
                always_release=True
            )
            btn_inst.bind(on_release=lambda inst, m_id=mod_id, m_name=name: self.install_tool(m_id, m_name))
            card.add_widget(btn_inst)
            
            self.cat_grid.add_widget(card)

    def install_tool(self, mod_id, name):
        self.lbl_status.text = f"Installing '{name}'..."
        host = self.app_manager.updater.server_host
        self.app_manager.module_mgr.install_community_module(mod_id, host, lambda s, mid, err: self.on_installed(s, name, err))

    def on_installed(self, success, name, error):
        if success:
            self.lbl_status.text = f"✅ Installed '{name}'! Added to Toolbox."
            self.app_manager.refresh_modules()
            if self.app_manager.hardware:
                self.app_manager.hardware.vibrate(40)
        else:
            self.lbl_status.text = f"❌ Install error: {error}"


class AppContextModal(ModalView):
    """
    Android-style long-press context options for an app icon.
    """
    def __init__(self, descriptor, is_pinned, launcher_screen, **kwargs):
        super().__init__(size_hint=(0.88, None), auto_dismiss=True, **kwargs)
        self.descriptor = descriptor
        self.is_pinned = is_pinned
        self.launcher_screen = launcher_screen

        meta = ColorSystem.get_icon_meta(descriptor.id, descriptor.category, descriptor.is_scratch)
        
        # Calculate dynamic height
        num_buttons = 4 + (1 if descriptor.is_scratch else 0)
        self.height = dp(80 + num_buttons * 48)

        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(8))
        with root.canvas.before:
            Color(0.10, 0.10, 0.15, 0.98)
            self.bg_rect = RoundedRectangle(size=root.size, pos=root.pos, radius=[dp(18)])
            Color(*meta["border"])
            self.border_rect = Line(rounded_rectangle=(root.x, root.y, root.width, root.height, dp(18)), width=1.5)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # Header with App Icon & Name
        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(46), spacing=dp(10))
        lbl_icon = Label(text=meta["icon"], font_size="24sp", size_hint_x=None, width=dp(40))
        head.add_widget(lbl_icon)

        v_head = BoxLayout(orientation='vertical')
        lbl_name = Label(text=descriptor.name, font_size="16sp", bold=True, color=ColorSystem.TEXT_PRIMARY, halign='left')
        lbl_name.bind(size=lbl_name.setter('text_size'))
        v_head.add_widget(lbl_name)

        lbl_cat = Label(text=f"{descriptor.category.upper()} • {'Draft' if descriptor.is_scratch else 'Permanent'}", font_size="11sp", color=ColorSystem.TEXT_MUTED, halign='left')
        lbl_cat.bind(size=lbl_cat.setter('text_size'))
        v_head.add_widget(lbl_cat)
        head.add_widget(v_head)
        root.add_widget(head)

        # Action: Launch
        btn_run = Button(
            text="▶ Launch Tool",
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=ColorSystem.SUCCESS,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="14sp"
        )
        btn_run.bind(on_release=self._action_run)
        root.add_widget(btn_run)

        # Action: Pin / Unpin from Home
        pin_text = "🗑️ Remove from Home Screen" if is_pinned else "📌 Pin to Home Screen"
        pin_color = (0.35, 0.15, 0.15, 1.0) if is_pinned else ColorSystem.PRIMARY
        btn_pin = Button(
            text=pin_text,
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=pin_color,
            color=(1, 1, 1, 1) if is_pinned else ColorSystem.BG_DARK,
            bold=True,
            font_size="13sp"
        )
        btn_pin.bind(on_release=self._action_toggle_pin)
        root.add_widget(btn_pin)

        # Action: Edit Code in Forge
        btn_edit = Button(
            text="✏️ Edit Code in Forge",
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp"
        )
        btn_edit.bind(on_release=self._action_edit)
        root.add_widget(btn_edit)

        # Action: Fork
        btn_fork = Button(
            text="📑 Fork to Scratchpad",
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp"
        )
        btn_fork.bind(on_release=self._action_fork)
        root.add_widget(btn_fork)

        # Action: Promote (if scratch)
        if descriptor.is_scratch:
            btn_promote = Button(
                text="💾 Save to Toolbox",
                size_hint_y=None,
                height=dp(40),
                background_normal="",
                background_color=ColorSystem.SECONDARY,
                color=(1, 1, 1, 1),
                bold=True,
                font_size="13sp"
            )
            btn_promote.bind(on_release=self._action_promote)
            root.add_widget(btn_promote)

        self.add_widget(root)

    def _update_bg(self, inst, val):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size
        self.border_rect.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(18))

    def _action_run(self, *a):
        self.dismiss()
        self.launcher_screen.app_manager.launch_module(self.descriptor)

    def _action_toggle_pin(self, *a):
        self.dismiss()
        if self.is_pinned:
            self.launcher_screen.layout_mgr.unpin_app(self.descriptor.id)
            self.launcher_screen.show_toast(f"Removed '{self.descriptor.name}' from Home")
        else:
            self.launcher_screen.layout_mgr.pin_app(self.descriptor.id)
            self.launcher_screen.show_toast(f"Pinned '{self.descriptor.name}' to Home")
        self.launcher_screen.rebuild_home_grid()

    def _action_edit(self, *a):
        self.dismiss()
        self.launcher_screen.edit_module(self.descriptor)

    def _action_fork(self, *a):
        self.dismiss()
        self.launcher_screen.fork_module(self.descriptor)

    def _action_promote(self, *a):
        self.dismiss()
        self.launcher_screen.prompt_save_scratch(self.descriptor)


class AppIconWidget(BoxLayout):
    """
    Native Android-style squircle App Icon with label, tap detection,
    long-press gesture detection, and drag initiating.
    """
    def __init__(self, descriptor=None, system_shortcut=None, launcher_screen=None, is_home=False, **kwargs):
        super().__init__(orientation='vertical', size_hint=(None, None), size=(dp(82), dp(96)), padding=[dp(4), dp(2), dp(4), dp(2)], spacing=dp(4), **kwargs)
        self.descriptor = descriptor
        self.system_shortcut = system_shortcut
        self.launcher_screen = launcher_screen
        self.is_home = is_home
        
        self.touch_start_time = 0
        self.touch_start_pos = (0, 0)
        self.long_press_event = None
        self.is_dragging = False

        if descriptor:
            mod_id = descriptor.id
            name = descriptor.name
            cat = descriptor.category
            is_scratch = descriptor.is_scratch
        else:
            mod_id = system_shortcut.get("id", "app")
            name = system_shortcut.get("name", "App")
            cat = "System"
            is_scratch = False

        self.mod_id = mod_id
        self.app_name = name
        self.meta = ColorSystem.get_icon_meta(mod_id, cat, is_scratch)

        # Icon Squircle Badge Canvas
        self.icon_badge = Widget(size_hint=(None, None), size=(dp(58), dp(58)), pos_hint={'center_x': 0.5})
        with self.icon_badge.canvas.before:
            self.bg_color = Color(*self.meta["bg"])
            self.bg_rect = RoundedRectangle(size=self.icon_badge.size, pos=self.icon_badge.pos, radius=[dp(18)])
            self.border_color = Color(*self.meta["border"])
            self.border_line = Line(rounded_rectangle=(self.icon_badge.x, self.icon_badge.y, self.icon_badge.width, self.icon_badge.height, dp(18)), width=1.2)
        self.icon_badge.bind(size=self._update_badge, pos=self._update_badge)

        # Emoji / Icon Label inside Badge
        lbl_char = self.meta["icon"]
        self.lbl_emoji = Label(
            text=lbl_char,
            font_size="28sp",
            center_x=self.icon_badge.center_x,
            center_y=self.icon_badge.center_y,
            size=(dp(58), dp(58)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.icon_badge.add_widget(self.lbl_emoji)
        self.add_widget(self.icon_badge)

        # Title Label below Icon
        self.lbl_title = Label(
            text=self.app_name,
            font_size="11sp",
            color=ColorSystem.TEXT_PRIMARY,
            size_hint_y=None,
            height=dp(28),
            halign='center',
            valign='top',
            shorten=True,
            shorten_from='right',
            max_lines=2
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        self.add_widget(self.lbl_title)

    def _update_badge(self, inst, val):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size
        self.border_line.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(18))
        if hasattr(self, 'lbl_emoji'):
            self.lbl_emoji.pos = inst.pos
            self.lbl_emoji.size = inst.size

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        
        touch.grab(self)
        self.touch_start_time = time.time()
        self.touch_start_pos = touch.pos
        self.is_dragging = False

        # Visual press feedback
        self.border_color.a = 1.0
        self.border_line.width = 2.0

        # Schedule Long Press detection (0.38s)
        self.long_press_event = Clock.schedule_once(lambda dt, t=touch: self._on_long_press(t), 0.38)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = abs(touch.pos[0] - self.touch_start_pos[0])
            dy = abs(touch.pos[1] - self.touch_start_pos[1])
            
            # If moved beyond threshold before long-press fires, cancel long-press (user is scrolling)
            if (dx > dp(12) or dy > dp(12)) and not self.is_dragging:
                if self.long_press_event:
                    self.long_press_event.cancel()
                    self.long_press_event = None

            if self.is_dragging and self.launcher_screen:
                self.launcher_screen.update_drag_ghost(touch.pos)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.border_line.width = 1.2
            if self.long_press_event:
                self.long_press_event.cancel()
                self.long_press_event = None

            if self.is_dragging:
                self.is_dragging = False
                if self.launcher_screen:
                    self.launcher_screen.finish_drag(self, touch.pos)
                return True

            # If not dragged and released within collision bounds -> Regular Tap Launch!
            if self.collide_point(*touch.pos):
                self._on_tap()
            return True
        return super().on_touch_up(touch)

    def _on_long_press(self, touch):
        self.long_press_event = None
        self.is_dragging = True
        
        # Trigger Haptic pulse
        if self.launcher_screen and self.launcher_screen.app_manager.hardware:
            self.launcher_screen.app_manager.hardware.vibrate(35)

        if self.launcher_screen:
            self.launcher_screen.start_drag(self, touch.pos)

    def _on_tap(self):
        if not self.launcher_screen:
            return
        
        # System shortcut action
        if self.system_shortcut:
            s_id = self.system_shortcut.get("id")
            if s_id == "agent":
                setattr(self.launcher_screen.manager, 'current', 'agent')
            elif s_id == "forge":
                setattr(self.launcher_screen.manager, 'current', 'forge')
            elif s_id == "settings":
                self.launcher_screen.on_nav_update_pressed()
            elif s_id == "hub":
                CommunityHubModal(self.launcher_screen.app_manager).open()
            return

        # Dynamic module launch
        if self.descriptor:
            self.launcher_screen.app_manager.launch_module(self.descriptor)


class FloatingGhostIcon(Widget):
    """
    Floating icon visualizer that follows the touch/cursor during drag & drop.
    """
    def __init__(self, meta, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(68), dp(68)), **kwargs)
        self.meta = meta
        with self.canvas:
            Color(*meta["bg"])
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(20)])
            Color(*meta["border"])
            self.border_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(20)), width=2.0)
        
        self.lbl_emoji = Label(
            text=meta["icon"],
            font_size="32sp",
            size=(dp(68), dp(68)),
            pos=self.pos
        )
        self.add_widget(self.lbl_emoji)
        self.bind(pos=self._update_pos)

    def _update_pos(self, *a):
        self.bg_rect.pos = self.pos
        self.border_line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(20))
        self.lbl_emoji.pos = self.pos


class LauncherScreen(Screen):
    def __init__(self, app_manager, **kwargs):
        super().__init__(**kwargs)
        self.app_manager = app_manager
        self.forge = app_manager.forge
        self.layout_mgr = HomeLayoutManager(app_manager.module_mgr.root_dir)
        
        self.forge.bind(on_forge_success=self.on_forge_generated_module)
        self.forge.bind(on_forge_error=self.on_forge_error)

        self.permanent_tools = []
        self.scratch_tools = []
        self.all_descriptors = {}
        self.active_category = "ALL"
        self.drawer_open = False
        self.active_drag_source = None
        self.ghost_widget = None

        # Root Layout: FloatLayout enables layered Home Screen + Slide-Up Drawer + Drag Overlay
        self.root_float = FloatLayout()
        with self.root_float.canvas.before:
            Color(*ColorSystem.BG_DARK)
            self.bg_rect = Rectangle(size=self.root_float.size, pos=self.root_float.pos)
        self.root_float.bind(size=self._update_bg, pos=self._update_bg)

        # ----------------------------------------------------
        # LAYER 1: HOME SCREEN (At A Glance + Pinned Grid + Dock)
        # ----------------------------------------------------
        self.home_container = BoxLayout(orientation='vertical', size_hint=(1, 1), spacing=0)
        
        # 1A. Top Status Bar / Toast
        self.top_toast_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(34), padding=[dp(16), dp(4), dp(16), dp(4)])
        self.lbl_toast = Label(
            text="⚡ NEXUS KERNEL ACTIVE",
            font_size="11sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            halign='center'
        )
        self.top_toast_bar.add_widget(self.lbl_toast)
        self.home_container.add_widget(self.top_toast_bar)

        # 1B. At A Glance Widget (Clock, Date, Live Telemetry)
        self.glance_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100), padding=[dp(20), dp(4), dp(20), dp(4)], spacing=dp(2))
        
        self.lbl_time = Label(
            text="12:00",
            font_size="38sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            size_hint_y=None,
            height=dp(46),
            halign='left'
        )
        self.lbl_time.bind(size=self.lbl_time.setter('text_size'))
        self.glance_box.add_widget(self.lbl_time)

        self.lbl_date = Label(
            text="Sunday, August 23  •  OpenHub Ready",
            font_size="13sp",
            color=ColorSystem.TEXT_MUTED,
            size_hint_y=None,
            height=dp(20),
            halign='left'
        )
        self.lbl_date.bind(size=self.lbl_date.setter('text_size'))
        self.glance_box.add_widget(self.lbl_date)

        # Quick AI search pill on Home Screen
        self.ai_pill = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(32), padding=[dp(10), dp(2), dp(10), dp(2)], spacing=dp(6))
        with self.ai_pill.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.pill_bg = RoundedRectangle(size=self.ai_pill.size, pos=self.ai_pill.pos, radius=[dp(16)])
            Color(*ColorSystem.SURFACE_BORDER)
            self.pill_border = Line(rounded_rectangle=(self.ai_pill.x, self.ai_pill.y, self.ai_pill.width, self.ai_pill.height, dp(16)), width=1.0)
        self.ai_pill.bind(size=lambda inst, v: setattr(self.pill_bg, 'size', inst.size) or setattr(self.pill_bg, 'pos', inst.pos) or setattr(self.pill_border, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(16))))
        
        lbl_spark = Label(text="✨", font_size="13sp", size_hint_x=None, width=dp(20))
        self.ai_pill.add_widget(lbl_spark)
        
        lbl_ai_hint = Label(text="Tap to chat with ACE Agent or forge tools...", font_size="12sp", color=ColorSystem.TEXT_HINT, halign='left')
        lbl_ai_hint.bind(size=lbl_ai_hint.setter('text_size'))
        self.ai_pill.add_widget(lbl_ai_hint)
        
        btn_ai_tap = Button(background_normal="", background_color=(0, 0, 0, 0), size_hint=(1, 1))
        btn_ai_tap.bind(on_release=lambda x: setattr(self.manager, 'current', 'agent'))
        self.ai_pill.add_widget(btn_ai_tap)
        self.glance_box.add_widget(self.ai_pill)
        
        self.home_container.add_widget(self.glance_box)

        # 1C. Scrollable Pinned Apps Grid (4 columns)
        self.home_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, effect_cls='ScrollEffect')
        self.home_grid = GridLayout(cols=4, spacing=dp(10), padding=[dp(14), dp(10), dp(14), dp(10)], size_hint_y=None)
        self.home_grid.bind(minimum_height=self.home_grid.setter('height'))
        self.home_scroll.add_widget(self.home_grid)
        self.home_container.add_widget(self.home_scroll)

        # 1D. Fixed Bottom Dock & Swipe Up Handle
        self.dock_container = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(125), padding=[dp(14), dp(4), dp(14), dp(10)], spacing=dp(6))
        
        # Swipe Up Indicator Pill
        self.swipe_handle = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(26), size_hint_x=None, width=dp(180), pos_hint={'center_x': 0.5})
        with self.swipe_handle.canvas.before:
            Color(0.18, 0.18, 0.26, 0.9)
            self.handle_bg = RoundedRectangle(size=self.swipe_handle.size, pos=self.swipe_handle.pos, radius=[dp(13)])
        self.swipe_handle.bind(size=lambda inst, v: setattr(self.handle_bg, 'size', inst.size) or setattr(self.handle_bg, 'pos', inst.pos))
        
        lbl_handle = Label(text="▲  ALL APPS & TOOLS", font_size="11sp", bold=True, color=ColorSystem.PRIMARY, halign='center')
        self.swipe_handle.add_widget(lbl_handle)
        
        btn_open_drawer = Button(background_normal="", background_color=(0, 0, 0, 0), size_hint=(1, 1))
        btn_open_drawer.bind(on_release=lambda x: self.toggle_app_drawer(True))
        self.swipe_handle.add_widget(btn_open_drawer)
        self.dock_container.add_widget(self.swipe_handle)

        # Dock Icons Capsule
        self.dock_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(80), padding=[dp(10), dp(6), dp(10), dp(6)], spacing=dp(8))
        with self.dock_bar.canvas.before:
            Color(*ColorSystem.DOCK_BG)
            self.dock_bg = RoundedRectangle(size=self.dock_bar.size, pos=self.dock_bar.pos, radius=[dp(24)])
            Color(*ColorSystem.SURFACE_BORDER)
            self.dock_border = Line(rounded_rectangle=(self.dock_bar.x, self.dock_bar.y, self.dock_bar.width, self.dock_bar.height, dp(24)), width=1.2)
        self.dock_bar.bind(size=lambda inst, v: setattr(self.dock_bg, 'size', inst.size) or setattr(self.dock_bg, 'pos', inst.pos) or setattr(self.dock_border, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(24))))
        
        self.dock_container.add_widget(self.dock_bar)
        self.home_container.add_widget(self.dock_container)
        
        self.root_float.add_widget(self.home_container)

        # ----------------------------------------------------
        # LAYER 2: TOP REMOVE / DROP ZONE (Visible during Drag)
        # ----------------------------------------------------
        self.remove_drop_zone = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(64), pos_hint={'top': 1}, padding=dp(10), opacity=0)
        with self.remove_drop_zone.canvas.before:
            Color(0.85, 0.20, 0.20, 0.95)
            self.remove_bg = RoundedRectangle(size=self.remove_drop_zone.size, pos=self.remove_drop_zone.pos, radius=[dp(0), dp(0), dp(18), dp(18)])
        self.remove_drop_zone.bind(size=lambda inst, v: setattr(self.remove_bg, 'size', inst.size) or setattr(self.remove_bg, 'pos', inst.pos))
        
        self.lbl_remove_text = Label(text="🗑️ DROP HERE TO REMOVE FROM HOME", font_size="14sp", bold=True, color=(1, 1, 1, 1), halign='center')
        self.remove_drop_zone.add_widget(self.lbl_remove_text)
        self.root_float.add_widget(self.remove_drop_zone)

        # ----------------------------------------------------
        # LAYER 3: APP DRAWER OVERLAY (Slide-up Bottom Sheet)
        # ----------------------------------------------------
        self.drawer_overlay = BoxLayout(orientation='vertical', size_hint=(1, 0.94), pos_hint={'x': 0, 'y': -1}, padding=[dp(12), dp(8), dp(12), dp(12)], spacing=dp(8))
        with self.drawer_overlay.canvas.before:
            Color(*ColorSystem.DRAWER_BG)
            self.drawer_bg = RoundedRectangle(size=self.drawer_overlay.size, pos=self.drawer_overlay.pos, radius=[dp(24), dp(24), 0, 0])
            Color(*ColorSystem.PRIMARY)
            self.drawer_border = Line(rounded_rectangle=(self.drawer_overlay.x, self.drawer_overlay.y, self.drawer_overlay.width, self.drawer_overlay.height, dp(24), dp(24), 0, 0), width=1.5)
        self.drawer_overlay.bind(size=lambda inst, v: setattr(self.drawer_bg, 'size', inst.size) or setattr(self.drawer_bg, 'pos', inst.pos) or setattr(self.drawer_border, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(24), dp(24), 0, 0)))

        # Drawer Grab Bar / Close
        grab_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(24))
        btn_close_drawer = Button(
            text="▼ CLOSE ALL APPS",
            font_size="12sp",
            bold=True,
            color=ColorSystem.TEXT_MUTED,
            background_normal="",
            background_color=(0, 0, 0, 0),
            size_hint=(1, 1)
        )
        btn_close_drawer.bind(on_release=lambda x: self.toggle_app_drawer(False))
        grab_box.add_widget(btn_close_drawer)
        self.drawer_overlay.add_widget(grab_box)

        # Search Bar
        search_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(46), spacing=dp(8))
        self.txt_search = TextInput(
            hint_text='🔍 Search all apps and tools...',
            multiline=False,
            font_size="15sp",
            background_color=ColorSystem.SURFACE,
            foreground_color=ColorSystem.TEXT_PRIMARY,
            hint_text_color=ColorSystem.TEXT_HINT,
            cursor_color=ColorSystem.PRIMARY,
            padding=[dp(12), dp(12), dp(12), dp(12)]
        )
        self.txt_search.bind(text=self.on_search_query_change)
        search_box.add_widget(self.txt_search)

        btn_clear_search = Button(
            text="✕",
            size_hint_x=None,
            width=dp(42),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_MUTED,
            font_size="14sp"
        )
        btn_clear_search.bind(on_release=lambda x: setattr(self.txt_search, 'text', ''))
        search_box.add_widget(btn_clear_search)
        self.drawer_overlay.add_widget(search_box)

        # Category Chips
        self.cat_chips_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(38), spacing=dp(6))
        self.categories = ["ALL", "TOOLS", "FIELD", "AGENTS", "SCRATCH", "HUB"]
        self.cat_chip_btns = {}
        for cat in self.categories:
            b = Button(
                text=cat,
                background_normal="",
                background_color=ColorSystem.PRIMARY if cat == "ALL" else ColorSystem.SURFACE,
                color=ColorSystem.BG_DARK if cat == "ALL" else ColorSystem.TEXT_MUTED,
                bold=True,
                font_size="11sp",
                size_hint_y=None,
                height=dp(34)
            )
            b.bind(on_release=lambda inst, c=cat: self.set_drawer_category(c))
            self.cat_chip_btns[cat] = b
            self.cat_chips_box.add_widget(b)
        self.drawer_overlay.add_widget(self.cat_chips_box)

        # Fast AI Creator Box inside Drawer
        self.forge_pill = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(44), padding=[dp(8), dp(4), dp(8), dp(4)], spacing=dp(6))
        with self.forge_pill.canvas.before:
            Color(0.12, 0.10, 0.18, 1.0)
            self.fp_bg = RoundedRectangle(size=self.forge_pill.size, pos=self.forge_pill.pos, radius=[dp(12)])
            Color(0.54, 0.36, 0.96, 0.7)
            self.fp_bdr = Line(rounded_rectangle=(self.forge_pill.x, self.forge_pill.y, self.forge_pill.width, self.forge_pill.height, dp(12)), width=1.0)
        self.forge_pill.bind(size=lambda inst, v: setattr(self.fp_bg, 'size', inst.size) or setattr(self.fp_bg, 'pos', inst.pos) or setattr(self.fp_bdr, 'rounded_rectangle', (inst.x, inst.y, inst.width, inst.height, dp(12))))
        
        self.txt_create_quick = TextInput(
            hint_text='✨ Quick Create: "e.g. sound pitch graph"...',
            multiline=False,
            font_size="13sp",
            background_color=(0, 0, 0, 0),
            foreground_color=ColorSystem.TEXT_PRIMARY,
            hint_text_color=ColorSystem.TEXT_HINT,
            cursor_color=ColorSystem.SECONDARY,
            padding=[dp(6), dp(8), dp(6), dp(8)]
        )
        self.txt_create_quick.bind(on_text_validate=self.on_quick_create_submit)
        self.forge_pill.add_widget(self.txt_create_quick)

        self.btn_quick_create = Button(
            text="⚡ FORGE",
            size_hint_x=None,
            width=dp(80),
            background_normal="",
            background_color=ColorSystem.SECONDARY,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="11sp"
        )
        self.btn_quick_create.bind(on_release=self.on_quick_create_submit)
        self.forge_pill.add_widget(self.btn_quick_create)
        self.drawer_overlay.add_widget(self.forge_pill)

        # Drawer 4-Column Grid of All Modules
        self.drawer_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, effect_cls='ScrollEffect')
        self.drawer_grid = GridLayout(cols=4, spacing=dp(10), padding=[dp(6), dp(8), dp(6), dp(8)], size_hint_y=None)
        self.drawer_grid.bind(minimum_height=self.drawer_grid.setter('height'))
        self.drawer_scroll.add_widget(self.drawer_grid)
        self.drawer_overlay.add_widget(self.drawer_scroll)

        self.root_float.add_widget(self.drawer_overlay)
        self.add_widget(self.root_float)

        # Clock ticks for live clock update
        Clock.schedule_interval(self._tick_clock, 1.0)
        self._tick_clock(0)

        # Build initial dock
        self.rebuild_dock()

    def _update_bg(self, inst, val):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size

    def _tick_clock(self, dt):
        now = datetime.datetime.now()
        self.lbl_time.text = now.strftime("%H:%M")
        self.lbl_date.text = now.strftime("%A, %B %d")

    def show_toast(self, message):
        self.lbl_toast.text = message

    def toggle_app_drawer(self, open_drawer):
        self.drawer_open = open_drawer
        target_y = 0.0 if open_drawer else -1.0
        anim = Animation(pos_hint={'x': 0, 'y': target_y}, duration=0.22, t='out_quad')
        anim.start(self.drawer_overlay)
        if open_drawer and self.app_manager.hardware:
            self.app_manager.hardware.vibrate(20)

    def set_drawer_category(self, category):
        if category == "HUB":
            CommunityHubModal(self.app_manager).open()
            return

        self.active_category = category
        for cat, btn in self.cat_chip_btns.items():
            if cat == category:
                btn.background_color = ColorSystem.PRIMARY
                btn.color = ColorSystem.BG_DARK
            else:
                btn.background_color = ColorSystem.SURFACE
                btn.color = ColorSystem.TEXT_MUTED
        self.rebuild_drawer_grid()

    def on_search_query_change(self, inst, text):
        self.rebuild_drawer_grid(query=text.strip().lower())

    def update_all_modules(self, permanent, scratch):
        self.permanent_tools = permanent
        self.scratch_tools = scratch
        
        self.all_descriptors = {}
        for d in permanent:
            self.all_descriptors[d.id] = d
        for d in scratch:
            self.all_descriptors[d.id] = d

        self.rebuild_home_grid()
        self.rebuild_drawer_grid()
        self.rebuild_dock()

    def rebuild_dock(self):
        """Builds the 4 primary bottom dock icons."""
        self.dock_bar.clear_widgets()
        dock_items = self.layout_mgr.layout_data.get("dock_apps", [])
        
        for item in dock_items:
            i_type = item.get("type", "system")
            i_id = item.get("id")
            
            if i_type == "module" and i_id in self.all_descriptors:
                desc = self.all_descriptors[i_id]
                icon_w = AppIconWidget(descriptor=desc, launcher_screen=self, is_home=True)
            else:
                icon_w = AppIconWidget(system_shortcut=item, launcher_screen=self, is_home=True)
            
            self.dock_bar.add_widget(icon_w)

    def rebuild_home_grid(self):
        """Renders the pinned apps on the Home Screen grid."""
        self.home_grid.clear_widgets()
        pinned_ids = self.layout_mgr.get_pinned_apps()
        
        for mod_id in pinned_ids:
            if mod_id in self.all_descriptors:
                desc = self.all_descriptors[mod_id]
                icon_w = AppIconWidget(descriptor=desc, launcher_screen=self, is_home=True)
                self.home_grid.add_widget(icon_w)

    def rebuild_drawer_grid(self, query=""):
        """Renders all available tools into the App Drawer grid."""
        self.drawer_grid.clear_widgets()
        
        all_list = self.permanent_tools + self.scratch_tools
        for desc in all_list:
            if query and query not in desc.name.lower() and query not in desc.id.lower():
                continue
            
            if self.active_category == "SCRATCH" and not desc.is_scratch:
                continue
            elif self.active_category != "ALL" and self.active_category != "SCRATCH":
                if desc.category.upper() != self.active_category:
                    continue
            
            icon_w = AppIconWidget(descriptor=desc, launcher_screen=self, is_home=False)
            self.drawer_grid.add_widget(icon_w)

    # ----------------------------------------------------
    # DRAG & DROP ORCHESTRATION
    # ----------------------------------------------------
    def start_drag(self, icon_widget, touch_pos):
        self.active_drag_source = icon_widget
        
        # Show top remove drop zone
        anim_remove = Animation(opacity=1.0, duration=0.15)
        anim_remove.start(self.remove_drop_zone)

        # If dragging from drawer, animate drawer down to peek home screen
        if not icon_widget.is_home and self.drawer_open:
            Animation(pos_hint={'x': 0, 'y': -0.75}, duration=0.2).start(self.drawer_overlay)

        # Spawn Floating Ghost Icon on root FloatLayout
        if self.ghost_widget:
            self.root_float.remove_widget(self.ghost_widget)
        
        self.ghost_widget = FloatingGhostIcon(meta=icon_widget.meta)
        self.ghost_widget.pos = (touch_pos[0] - dp(34), touch_pos[1] - dp(34))
        self.root_float.add_widget(self.ghost_widget)

    def update_drag_ghost(self, touch_pos):
        if self.ghost_widget:
            self.ghost_widget.pos = (touch_pos[0] - dp(34), touch_pos[1] - dp(34))

    def finish_drag(self, icon_widget, touch_pos):
        # Hide top remove drop zone
        Animation(opacity=0.0, duration=0.15).start(self.remove_drop_zone)
        
        if self.ghost_widget:
            self.root_float.remove_widget(self.ghost_widget)
            self.ghost_widget = None

        # Check if dropped onto the Remove bar at top
        if self.remove_drop_zone.collide_point(*touch_pos):
            if icon_widget.descriptor and icon_widget.is_home:
                self.layout_mgr.unpin_app(icon_widget.descriptor.id)
                self.show_toast(f"Removed '{icon_widget.descriptor.name}' from Home")
                self.rebuild_home_grid()
                if self.app_manager.hardware:
                    self.app_manager.hardware.vibrate(40)
            return

        # If dragged from drawer onto Home Screen:
        if not icon_widget.is_home:
            # Check if dropped over the Home Screen area
            if touch_pos[1] > dp(130):
                if icon_widget.descriptor:
                    self.layout_mgr.pin_app(icon_widget.descriptor.id)
                    self.show_toast(f"Pinned '{icon_widget.descriptor.name}' to Home Screen")
                    self.rebuild_home_grid()
                    if self.app_manager.hardware:
                        self.app_manager.hardware.vibrate(50)
            # Restore drawer position or close it
            self.toggle_app_drawer(False)
        else:
            # If dragged on Home Screen without moving to remove, open context menu
            AppContextModal(icon_widget.descriptor, is_pinned=True, launcher_screen=self).open()

    # ----------------------------------------------------
    # QUICK AI CREATION & ACTIONS
    # ----------------------------------------------------
    def on_quick_create_submit(self, *args):
        prompt = self.txt_create_quick.text.strip()
        if not prompt:
            return
        
        self.btn_quick_create.text = "WAIT..."
        self.show_toast(f"Generating '{prompt}'...")
        self.current_generating_prompt = prompt
        self.forge.generate(prompt)

    def on_forge_generated_module(self, instance, action, code, explanation):
        if action != "generate":
            return
        self.btn_quick_create.text = "⚡ FORGE"
        prompt_text = getattr(self, 'current_generating_prompt', 'tool')
        self.txt_create_quick.text = ""
        self.show_toast(f"Created: {explanation}")

        desc = self.app_manager.module_mgr.create_scratch(code, prompt=prompt_text)
        self.layout_mgr.pin_app(desc.id, index=0)
        Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)
        Clock.schedule_once(lambda dt, d=desc: self.app_manager.launch_module(d), 0.05)

    def on_forge_error(self, instance, action, error_msg):
        self.btn_quick_create.text = "⚡ FORGE"
        self.show_toast(f"Forge error: {error_msg}")

    def edit_module(self, descriptor):
        try:
            code = self.app_manager.module_mgr.read_code(descriptor)
            forge_screen = self.manager.get_screen('forge')
            forge_screen.load_descriptor_for_editing(descriptor, code)
            setattr(self.manager, 'current', 'forge')
        except Exception as e:
            self.show_toast(f"❌ Edit error: {e}")

    def fork_module(self, descriptor):
        try:
            new_desc = self.app_manager.module_mgr.fork(descriptor)
            self.show_toast(f"📑 Forked '{descriptor.name}'")
            self.layout_mgr.pin_app(new_desc.id, index=0)
            Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)
            Clock.schedule_once(lambda dt, d=new_desc: self.app_manager.launch_module(d), 0.05)
        except Exception as e:
            self.show_toast(f"❌ Fork error: {e}")

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
                self.show_toast(f"💾 Saved '{final_name}' to Toolbox")
                Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)
            except Exception as e:
                print(f"[Launcher] Error promoting module: {e}")
            popup.dismiss()
            
        btn_ok.bind(on_release=confirm_save)
        btn_row.add_widget(btn_ok)
        content.add_widget(btn_row)
        popup.open()

    def on_update_check_result(self, has_update, update_info, error):
        if error:
            return
        if has_update and update_info:
            modal = UpdateModal(update_info, self.app_manager.updater)
            modal.open()

    def on_nav_update_pressed(self, *args):
        updater = self.app_manager.updater
        if updater.latest_update_info:
            UpdateModal(updater.latest_update_info, updater).open()
        else:
            SettingsModal(updater, self.on_update_check_result, app_manager=self.app_manager).open()
