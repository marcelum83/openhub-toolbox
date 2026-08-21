"""
OpenHub Home Launcher (The Deck & Fast Creation Engine)
Touch-optimized for high-DPI Android screens (Pixel 7a) with density-independent scaling (dp/sp).
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
from kivy.graphics import Color, Rectangle, RoundedRectangle
from ui.themes import ColorSystem

class ScratchCard(BoxLayout):
    """
    Card for disposable scratchpad experiments.
    Large touch targets: [▶ RUN] [✏️ EDIT] [📑 FORK] [💾 SAVE] [🗑️ DELETE]
    """
    def __init__(self, descriptor, on_run, on_edit, on_fork, on_save, on_delete, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=dp(140), padding=dp(12), spacing=dp(8), **kwargs)
        self.descriptor = descriptor
        
        with self.canvas.before:
            Color(0.12, 0.10, 0.18, 1.0)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(14)])
            Color(0.54, 0.36, 0.96, 0.6)
            self.border_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(14)])
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

        # Action Buttons Row (Big touch targets)
        actions = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52), spacing=dp(8))
        
        btn_run = Button(
            text="▶ RUN",
            size_hint_x=0.30,
            background_normal="",
            background_color=ColorSystem.SUCCESS,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="15sp"
        )
        btn_run.bind(on_release=lambda x: on_run(descriptor))
        actions.add_widget(btn_run)

        btn_edit = Button(
            text="✏️ EDIT",
            size_hint_x=0.22,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp"
        )
        btn_edit.bind(on_release=lambda x: on_edit(descriptor))
        actions.add_widget(btn_edit)

        btn_fork = Button(
            text="📑 FORK",
            size_hint_x=0.22,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp"
        )
        btn_fork.bind(on_release=lambda x: on_fork(descriptor))
        actions.add_widget(btn_fork)

        btn_save = Button(
            text="💾 SAVE",
            size_hint_x=0.22,
            background_normal="",
            background_color=ColorSystem.PRIMARY,
            color=ColorSystem.BG_DARK,
            bold=True,
            font_size="13sp"
        )
        btn_save.bind(on_release=lambda x: on_save(descriptor))
        actions.add_widget(btn_save)

        btn_del = Button(
            text="🗑️",
            size_hint_x=None,
            width=dp(48),
            background_normal="",
            background_color=(0.35, 0.1, 0.1, 1),
            color=ColorSystem.DANGER,
            bold=True,
            font_size="16sp"
        )
        btn_del.bind(on_release=lambda x: on_delete(descriptor))
        actions.add_widget(btn_del)

        self.add_widget(actions)

    def _update_rects(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        self.border_rect.pos = instance.pos
        self.border_rect.size = instance.size


class PermanentToolCard(BoxLayout):
    """
    Card for established permanent tools.
    """
    def __init__(self, descriptor, on_run, on_edit, on_fork, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=dp(135), padding=dp(14), spacing=dp(6), **kwargs)
        self.descriptor = descriptor
        self.on_run = on_run
        
        with self.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(14)])
            Color(*ColorSystem.SURFACE_BORDER)
            self.border_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(14)])
        self.bind(size=self._update_rects, pos=self._update_rects)

        cat_emojis = {
            "Tools": "🛠️",
            "Field": "🌱",
            "Agents": "🤖",
            "Creative": "🎨",
            "Experiments": "🔬"
        }
        emoji = cat_emojis.get(descriptor.category, "📦")

        top_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28), spacing=dp(8))
        lbl_title = Label(
            text=f"{emoji} {descriptor.name}",
            font_size="18sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        top_row.add_widget(lbl_title)
        
        lbl_cat = Label(
            text=f"[{descriptor.category.upper()}]",
            font_size="12sp",
            size_hint_x=None,
            width=dp(90),
            color=ColorSystem.PRIMARY,
            halign='right',
            valign='middle'
        )
        lbl_cat.bind(size=lbl_cat.setter('text_size'))
        top_row.add_widget(lbl_cat)
        self.add_widget(top_row)

        lbl_desc = Label(
            text=descriptor.description,
            font_size="13sp",
            color=ColorSystem.TEXT_MUTED,
            halign='left',
            valign='top',
            size_hint_y=None,
            height=dp(22)
        )
        lbl_desc.bind(size=lbl_desc.setter('text_size'))
        self.add_widget(lbl_desc)

        # Quick Actions Row
        actions = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
        btn_run = Button(
            text="▶ RUN TOOL",
            size_hint_x=0.55,
            background_normal="",
            background_color=ColorSystem.SUCCESS,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="14sp"
        )
        btn_run.bind(on_release=lambda x: on_run(descriptor))
        actions.add_widget(btn_run)

        btn_edit = Button(
            text="✏️ CODE",
            size_hint_x=0.22,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp"
        )
        btn_edit.bind(on_release=lambda x: on_edit(descriptor))
        actions.add_widget(btn_edit)

        btn_fork = Button(
            text="📑 FORK",
            size_hint_x=0.23,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp"
        )
        btn_fork.bind(on_release=lambda x: on_fork(descriptor))
        actions.add_widget(btn_fork)

        self.add_widget(actions)

    def _update_rects(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        self.border_rect.pos = instance.pos
        self.border_rect.size = instance.size


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

        # 1. Header Bar (Generous touch height)
        nav_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(64), padding=[dp(14), dp(8), dp(14), dp(8)], spacing=dp(10))
        with nav_bar.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.nav_rect = Rectangle(size=nav_bar.size, pos=nav_bar.pos)
        nav_bar.bind(size=self._update_nav_rect, pos=self._update_nav_rect)

        lbl_logo = Label(
            text="🌌 OPENHUB",
            font_size="22sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            size_hint_x=None,
            width=dp(150),
            halign='left',
            valign='middle'
        )
        lbl_logo.bind(size=lbl_logo.setter('text_size'))
        nav_bar.add_widget(lbl_logo)

        btn_forge = Button(
            text="⚡ THE FORGE",
            size_hint_x=0.6,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="14sp"
        )
        btn_forge.bind(on_release=lambda x: setattr(self.manager, 'current', 'forge'))
        nav_bar.add_widget(btn_forge)

        btn_refresh = Button(
            text="🔄",
            size_hint_x=None,
            width=dp(52),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="18sp"
        )
        btn_refresh.bind(on_release=lambda x: self.app_manager.refresh_modules())
        nav_bar.add_widget(btn_refresh)
        root.add_widget(nav_bar)

        # 2. Main Scrollable Container
        main_scroll = ScrollView()
        self.content_box = BoxLayout(orientation='vertical', spacing=dp(16), padding=dp(14), size_hint_y=None)
        self.content_box.bind(minimum_height=self.content_box.setter('height'))

        # ==========================================
        # SECTION A: "WHAT SHALL WE MAKE?" CREATION BOX
        # ==========================================
        create_panel = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(165), padding=dp(14), spacing=dp(10))
        with create_panel.canvas.before:
            Color(0.11, 0.11, 0.17, 1.0)
            self.create_bg = RoundedRectangle(size=create_panel.size, pos=create_panel.pos, radius=[dp(16)])
            Color(0.02, 0.71, 0.83, 0.5)
            self.create_border = RoundedRectangle(size=create_panel.size, pos=create_panel.pos, radius=[dp(16)])
        create_panel.bind(size=self._update_create_rects, pos=self._update_create_rects)

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
        create_panel.add_widget(lbl_prompt_title)

        prompt_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(56), spacing=dp(10))
        self.txt_prompt = TextInput(
            hint_text='e.g. "Solar collector radiator heat calculator"...',
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
            font_size="14sp"
        )
        self.btn_create.bind(on_release=self.on_create_prompt_submit)
        prompt_row.add_widget(self.btn_create)
        create_panel.add_widget(prompt_row)

        self.lbl_create_status = Label(
            text="Type any tool idea above to generate and test it instantly.",
            font_size="13sp",
            color=ColorSystem.TEXT_MUTED,
            size_hint_y=None,
            height=dp(22),
            halign='left'
        )
        self.lbl_create_status.bind(size=self.lbl_create_status.setter('text_size'))
        create_panel.add_widget(self.lbl_create_status)
        self.content_box.add_widget(create_panel)

        # ==========================================
        # SECTION B: ACTIVE SCRATCH EXPERIMENTS
        # ==========================================
        self.lbl_scratch_hdr = Label(
            text="🧪 LIVE EXPERIMENTS & SCRATCH",
            font_size="15sp",
            bold=True,
            color=ColorSystem.SECONDARY,
            size_hint_y=None,
            height=dp(28),
            halign='left'
        )
        self.lbl_scratch_hdr.bind(size=self.lbl_scratch_hdr.setter('text_size'))
        self.content_box.add_widget(self.lbl_scratch_hdr)

        self.scratch_grid = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.scratch_grid.bind(minimum_height=self.scratch_grid.setter('height'))
        self.content_box.add_widget(self.scratch_grid)

        # ==========================================
        # SECTION C: MY SAVED TOOLS
        # ==========================================
        self.lbl_tools_hdr = Label(
            text="🛠️ MY SAVED TOOLS",
            font_size="15sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            size_hint_y=None,
            height=dp(28),
            halign='left'
        )
        self.lbl_tools_hdr.bind(size=self.lbl_tools_hdr.setter('text_size'))
        self.content_box.add_widget(self.lbl_tools_hdr)

        # Category Tabs (Touch scroll)
        cat_scroll = ScrollView(size_hint_y=None, height=dp(46), do_scroll_x=True, do_scroll_y=False)
        cat_box = BoxLayout(orientation='horizontal', size_hint_x=None, spacing=dp(8))
        cat_box.bind(minimum_width=cat_box.setter('width'))
        self.categories = ["All", "Tools", "Field", "Agents", "Creative", "Experiments"]
        self.cat_btns = {}
        for cat in self.categories:
            b = Button(
                text=cat,
                size_hint_x=None,
                width=dp(95),
                background_normal="",
                background_color=ColorSystem.PRIMARY if cat == "All" else ColorSystem.SURFACE,
                color=ColorSystem.BG_DARK if cat == "All" else ColorSystem.TEXT_MUTED,
                bold=True,
                font_size="13sp"
            )
            b.bind(on_release=lambda inst, c=cat: self.set_category_filter(c))
            self.cat_btns[cat] = b
            cat_box.add_widget(b)
        cat_scroll.add_widget(cat_box)
        self.content_box.add_widget(cat_scroll)

        # Permanent Tools Grid
        self.tools_grid = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.tools_grid.bind(minimum_height=self.tools_grid.setter('height'))
        self.content_box.add_widget(self.tools_grid)

        main_scroll.add_widget(self.content_box)
        root.add_widget(main_scroll)
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
        self.create_border.pos = instance.pos
        self.create_border.size = instance.size

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
        self.app_manager.refresh_modules()
        self.app_manager.launch_module(desc)

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
        self.rebuild_views()

    def rebuild_views(self):
        # 1. Build Scratch Shelf
        self.scratch_grid.clear_widgets()
        if not self.scratch_tools:
            self.lbl_scratch_hdr.text = "🧪 LIVE EXPERIMENTS & SCRATCH (0 Active)"
        else:
            self.lbl_scratch_hdr.text = f"🧪 LIVE EXPERIMENTS & SCRATCH ({len(self.scratch_tools)} Active)"
            for desc in self.scratch_tools:
                card = ScratchCard(
                    desc,
                    on_run=self.app_manager.launch_module,
                    on_edit=self.edit_module,
                    on_fork=self.fork_module,
                    on_save=self.prompt_save_scratch,
                    on_delete=self.delete_module
                )
                self.scratch_grid.add_widget(card)

        # 2. Build Permanent Tools Shelf
        self.tools_grid.clear_widgets()
        for desc in self.permanent_tools:
            if self.active_category != "All" and desc.category != self.active_category:
                continue
            card = PermanentToolCard(
                desc,
                on_run=self.app_manager.launch_module,
                on_edit=self.edit_module,
                on_fork=self.fork_module
            )
            self.tools_grid.add_widget(card)

    def edit_module(self, descriptor):
        try:
            code = self.app_manager.module_mgr.read_code(descriptor)
            forge_screen = self.manager.get_screen('forge')
            forge_screen.load_descriptor_for_editing(descriptor, code)
            self.manager.current = 'forge'
        except Exception as e:
            print(f"Error opening code in editor: {e}")

    def fork_module(self, descriptor):
        new_desc = self.app_manager.module_mgr.fork(descriptor)
        self.app_manager.refresh_modules()
        self.lbl_create_status.text = f"📑 Forked '{descriptor.name}' as '{new_desc.name}'"

    def prompt_save_scratch(self, descriptor):
        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(16))
        content.add_widget(Label(text=f"Save '{descriptor.name}' as Permanent Tool:", font_size="16sp"))
        name_in = TextInput(text=descriptor.name, multiline=False, font_size="16sp", size_hint_y=None, height=dp(52))
        content.add_widget(name_in)
        
        btn_row = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(52))
        popup = Popup(title="Promote to Permanent Tool", content=content, size_hint=(0.9, 0.45))
        
        btn_ok = Button(text="Save to Toolbox", background_color=ColorSystem.PRIMARY, bold=True, font_size="15sp")
        def confirm_save(inst):
            final_name = name_in.text.strip() or descriptor.name
            self.app_manager.module_mgr.promote_to_permanent(descriptor, final_name)
            self.app_manager.refresh_modules()
            popup.dismiss()
            
        btn_ok.bind(on_release=confirm_save)
        btn_row.add_widget(btn_ok)
        content.add_widget(btn_row)
        popup.open()

    def delete_module(self, descriptor):
        self.app_manager.module_mgr.delete(descriptor)
        self.app_manager.refresh_modules()
