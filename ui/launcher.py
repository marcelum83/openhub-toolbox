"""
OpenHub Home Launcher (The Deck & Fast Creation Engine)
Optimized for: Prompt → generate Kivy module → run immediately → duplicate/save/discard.
"""
import os
import shutil
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
from core.forge_agent import ForgeAgent
from core.scanner import ModuleDescriptor
from core.security import TrustLevel

class ScratchCard(BoxLayout):
    """
    Tactile card for disposable / in-development scratch experiments.
    """
    def __init__(self, descriptor, on_run, on_edit, on_duplicate, on_save, on_delete, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=105, padding=10, spacing=6, **kwargs)
        self.descriptor = descriptor
        
        with self.canvas.before:
            Color(0.12, 0.10, 0.18, 1.0) # Violet-tinted dark surface
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[10])
            Color(0.54, 0.36, 0.96, 0.5)  # Violet accent border
            self.border_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[10])
        self.bind(size=self._update_rects, pos=self._update_rects)

        # Header Row: Name + Tag
        head = BoxLayout(orientation='horizontal', size_hint_y=None, height=24, spacing=8)
        lbl_title = Label(
            text=f"🧪 {descriptor.name}",
            font_size="15sp",
            bold=True,
            color=(0.95, 0.95, 0.97, 1),
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        head.add_widget(lbl_title)
        
        lbl_tag = Label(text="DRAFT", font_size="10sp", size_hint_x=None, width=60, color=ColorSystem.SECONDARY, bold=True)
        head.add_widget(lbl_tag)
        self.add_widget(head)

        # Action Buttons Row: [▶ RUN] [✏️ EDIT] [📑 DUPLICATE] [💾 SAVE] [🗑️]
        actions = BoxLayout(orientation='horizontal', size_hint_y=None, height=36, spacing=6)
        
        btn_run = Button(
            text="▶ RUN",
            size_hint_x=0.28,
            background_normal="",
            background_color=ColorSystem.SUCCESS,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="13sp"
        )
        btn_run.bind(on_release=lambda x: on_run(descriptor))
        actions.add_widget(btn_run)

        btn_edit = Button(
            text="✏️ EDIT",
            size_hint_x=0.24,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="12sp"
        )
        btn_edit.bind(on_release=lambda x: on_edit(descriptor))
        actions.add_widget(btn_edit)

        btn_dup = Button(
            text="📑 DUP",
            size_hint_x=0.20,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="12sp"
        )
        btn_dup.bind(on_release=lambda x: on_duplicate(descriptor))
        actions.add_widget(btn_dup)

        btn_save = Button(
            text="💾 SAVE",
            size_hint_x=0.20,
            background_normal="",
            background_color=ColorSystem.PRIMARY,
            color=ColorSystem.BG_DARK,
            bold=True,
            font_size="12sp"
        )
        btn_save.bind(on_release=lambda x: on_save(descriptor))
        actions.add_widget(btn_save)

        btn_del = Button(
            text="🗑️",
            size_hint_x=None,
            width=36,
            background_normal="",
            background_color=(0.3, 0.1, 0.1, 1),
            color=ColorSystem.DANGER,
            bold=True
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
    Card for established, saved toolbox items.
    """
    def __init__(self, descriptor, on_launch, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=95, padding=12, spacing=4, **kwargs)
        self.descriptor = descriptor
        self.on_launch = on_launch
        
        with self.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[12])
            Color(*ColorSystem.SURFACE_BORDER)
            self.border_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[12])
        self.bind(size=self._update_rects, pos=self._update_rects)

        cat_emojis = {
            "Tools": "🛠️",
            "Field": "🧭",
            "Agents": "🤖",
            "Creative": "🎨",
            "Experiments": "🔬"
        }
        emoji = cat_emojis.get(descriptor.category, "📦")

        top_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=24, spacing=8)
        lbl_title = Label(
            text=f"{emoji} {descriptor.name}",
            font_size="16sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        top_row.add_widget(lbl_title)
        
        lbl_cat = Label(
            text=f"[{descriptor.category.upper()}]",
            font_size="11sp",
            size_hint_x=None,
            width=80,
            color=ColorSystem.PRIMARY,
            halign='right',
            valign='middle'
        )
        lbl_cat.bind(size=lbl_cat.setter('text_size'))
        top_row.add_widget(lbl_cat)
        self.add_widget(top_row)

        lbl_desc = Label(
            text=descriptor.description,
            font_size="12sp",
            color=ColorSystem.TEXT_MUTED,
            halign='left',
            valign='top'
        )
        lbl_desc.bind(size=lbl_desc.setter('text_size'))
        self.add_widget(lbl_desc)

    def _update_rects(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        self.border_rect.pos = instance.pos
        self.border_rect.size = instance.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.on_launch:
                self.on_launch(self.descriptor)
            return True
        return super().on_touch_down(touch)


class LauncherScreen(Screen):
    def __init__(self, app_manager, **kwargs):
        super().__init__(**kwargs)
        self.app_manager = app_manager
        self.agent = ForgeAgent()
        self.agent.bind(on_agent_result=self.on_agent_created_module)
        self.agent.bind(on_agent_error=self.on_agent_error)

        self.permanent_tools = []
        self.scratch_tools = []
        self.active_category = "All"
        self.search_query = ""

        # Root Layout
        root = BoxLayout(orientation='vertical', spacing=0)
        with root.canvas.before:
            Color(*ColorSystem.BG_DARK)
            self.bg_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # 1. Header Bar
        nav_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=52, padding=[12, 6, 12, 6], spacing=10)
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
            width=130,
            halign='left',
            valign='middle'
        )
        lbl_logo.bind(size=lbl_logo.setter('text_size'))
        nav_bar.add_widget(lbl_logo)

        # Forge Studio shortcut
        btn_forge = Button(
            text="⚡ THE FORGE (CODE)",
            size_hint_x=0.6,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="12sp"
        )
        btn_forge.bind(on_release=lambda x: setattr(self.manager, 'current', 'forge'))
        nav_bar.add_widget(btn_forge)

        # Refresh
        btn_refresh = Button(
            text="🔄",
            size_hint_x=None,
            width=42,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True
        )
        btn_refresh.bind(on_release=lambda x: self.app_manager.refresh_modules())
        nav_bar.add_widget(btn_refresh)
        root.add_widget(nav_bar)

        # 2. Main Scrollable Container
        main_scroll = ScrollView()
        self.content_box = BoxLayout(orientation='vertical', spacing=14, padding=12, size_hint_y=None)
        self.content_box.bind(minimum_height=self.content_box.setter('height'))

        # ==========================================
        # SECTION A: "WHAT SHALL WE MAKE?" CREATION BOX
        # ==========================================
        create_panel = BoxLayout(orientation='vertical', size_hint_y=None, height=130, padding=12, spacing=8)
        with create_panel.canvas.before:
            Color(0.11, 0.11, 0.17, 1.0)
            self.create_bg = RoundedRectangle(size=create_panel.size, pos=create_panel.pos, radius=[14])
            Color(0.02, 0.71, 0.83, 0.4)
            self.create_border = RoundedRectangle(size=create_panel.size, pos=create_panel.pos, radius=[14])
        create_panel.bind(size=self._update_create_rects, pos=self._update_create_rects)

        lbl_prompt_title = Label(
            text="✨ What shall we make?",
            font_size="15sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            size_hint_y=None,
            height=22,
            halign='left'
        )
        lbl_prompt_title.bind(size=lbl_prompt_title.setter('text_size'))
        create_panel.add_widget(lbl_prompt_title)

        prompt_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=44, spacing=8)
        self.txt_prompt = TextInput(
            hint_text='e.g. "Water tank volume calculator in litres and gallons"...',
            multiline=False,
            background_color=ColorSystem.SURFACE,
            foreground_color=ColorSystem.TEXT_PRIMARY,
            hint_text_color=ColorSystem.TEXT_HINT,
            cursor_color=ColorSystem.PRIMARY,
            padding=[10, 8, 10, 8]
        )
        self.txt_prompt.bind(on_text_validate=self.on_create_prompt_submit)
        prompt_row.add_widget(self.txt_prompt)

        self.btn_create = Button(
            text="⚡ CREATE & RUN",
            size_hint_x=None,
            width=135,
            background_normal="",
            background_color=ColorSystem.SECONDARY,
            color=(1, 1, 1, 1),
            bold=True,
            font_size="12sp"
        )
        self.btn_create.bind(on_release=self.on_create_prompt_submit)
        prompt_row.add_widget(self.btn_create)
        create_panel.add_widget(prompt_row)

        self.lbl_create_status = Label(
            text="Type any tool idea above to generate and test it instantly.",
            font_size="11sp",
            color=ColorSystem.TEXT_MUTED,
            size_hint_y=None,
            height=18,
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
            font_size="13sp",
            bold=True,
            color=ColorSystem.SECONDARY,
            size_hint_y=None,
            height=24,
            halign='left'
        )
        self.lbl_scratch_hdr.bind(size=self.lbl_scratch_hdr.setter('text_size'))
        self.content_box.add_widget(self.lbl_scratch_hdr)

        self.scratch_grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.scratch_grid.bind(minimum_height=self.scratch_grid.setter('height'))
        self.content_box.add_widget(self.scratch_grid)

        # ==========================================
        # SECTION C: MY SAVED TOOLS
        # ==========================================
        self.lbl_tools_hdr = Label(
            text="🛠️ MY SAVED TOOLS",
            font_size="13sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            size_hint_y=None,
            height=24,
            halign='left'
        )
        self.lbl_tools_hdr.bind(size=self.lbl_tools_hdr.setter('text_size'))
        self.content_box.add_widget(self.lbl_tools_hdr)

        # Category Filter Bar
        cat_scroll = ScrollView(size_hint_y=None, height=36, do_scroll_x=True, do_scroll_y=False)
        cat_box = BoxLayout(orientation='horizontal', size_hint_x=None, spacing=6)
        cat_box.bind(minimum_width=cat_box.setter('width'))
        self.categories = ["All", "Tools", "Field", "Agents", "Experiments"]
        self.cat_btns = {}
        for cat in self.categories:
            b = Button(
                text=cat,
                size_hint_x=None,
                width=75,
                background_normal="",
                background_color=ColorSystem.PRIMARY if cat == "All" else ColorSystem.SURFACE,
                color=ColorSystem.BG_DARK if cat == "All" else ColorSystem.TEXT_MUTED,
                bold=True,
                font_size="12sp"
            )
            b.bind(on_release=lambda inst, c=cat: self.set_category_filter(c))
            self.cat_btns[cat] = b
            cat_box.add_widget(b)
        cat_scroll.add_widget(cat_box)
        self.content_box.add_widget(cat_scroll)

        # Permanent Tools Grid
        self.tools_grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
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
        self.agent.generate_or_mutate_tool(prompt)

    def on_agent_created_module(self, instance, code, explanation):
        self.btn_create.text = "⚡ CREATE & RUN"
        prompt_text = self.txt_prompt.text.strip()
        self.txt_prompt.text = ""
        self.lbl_create_status.text = f"✨ Created: {explanation}"

        # 1. Determine next scratch filename (e.g. tmp_001_tank_calc.py)
        scratch_dir = os.path.abspath("./modules/scratch")
        os.makedirs(scratch_dir, exist_ok=True)
        
        existing = [f for f in os.listdir(scratch_dir) if f.startswith("tmp_") and f.endswith(".py")]
        next_idx = len(existing) + 1
        clean_slug = "_".join(prompt_text.lower().split()[:3]) if prompt_text else "tool"
        clean_slug = "".join([c if c.isalnum() or c == '_' else '' for c in clean_slug])
        filename = f"tmp_{next_idx:03d}_{clean_slug}.py"
        file_path = os.path.join(scratch_dir, filename)

        # 2. Write code
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)

        # 3. Refresh modules and launch immediately!
        self.app_manager.refresh_modules()
        
        desc = ModuleDescriptor(
            mod_id=os.path.splitext(filename)[0],
            name=clean_slug.replace("_", " ").title(),
            category="Scratch",
            description=f"Generated from: '{prompt_text}'",
            entrypoint=file_path,
            trust_level=TrustLevel.EXPERIMENTAL,
            is_scratch=True
        )
        self.app_manager.launch_module(desc)

    def on_agent_error(self, instance, error_msg):
        self.btn_create.text = "⚡ CREATE & RUN"
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
        # 1. Build Scratch Experiments Shelf
        self.scratch_grid.clear_widgets()
        if not self.scratch_tools:
            self.lbl_scratch_hdr.text = "🧪 LIVE EXPERIMENTS & SCRATCH (0 Active)"
        else:
            self.lbl_scratch_hdr.text = f"🧪 LIVE EXPERIMENTS & SCRATCH ({len(self.scratch_tools)} Active)"
            for desc in self.scratch_tools:
                card = ScratchCard(
                    desc,
                    on_run=self.app_manager.launch_module,
                    on_edit=self.edit_scratch_module,
                    on_duplicate=self.duplicate_scratch_module,
                    on_save=self.prompt_save_scratch,
                    on_delete=self.delete_scratch_module
                )
                self.scratch_grid.add_widget(card)

        # 2. Build Permanent Tools
        self.tools_grid.clear_widgets()
        for desc in self.permanent_tools:
            if self.active_category != "All" and desc.category != self.active_category:
                continue
            card = PermanentToolCard(desc, on_launch=self.app_manager.launch_module)
            self.tools_grid.add_widget(card)

    def edit_scratch_module(self, descriptor):
        # Read code into Forge Studio
        try:
            with open(descriptor.entrypoint, 'r', encoding='utf-8') as f:
                code = f.read()
            forge = self.manager.get_screen('forge')
            forge.load_code_for_editing(descriptor.name, code, descriptor.entrypoint)
            self.manager.current = 'forge'
        except Exception as e:
            print(f"Error opening code in editor: {e}")

    def duplicate_scratch_module(self, descriptor):
        # Copy to new tmp_NNN file
        scratch_dir = os.path.dirname(descriptor.entrypoint)
        existing = [f for f in os.listdir(scratch_dir) if f.startswith("tmp_") and f.endswith(".py")]
        next_idx = len(existing) + 1
        base = os.path.basename(descriptor.entrypoint)
        new_name = f"tmp_{next_idx:03d}_copy_{base}"
        new_path = os.path.join(scratch_dir, new_name)
        shutil.copyfile(descriptor.entrypoint, new_path)
        self.app_manager.refresh_modules()

    def prompt_save_scratch(self, descriptor):
        content = BoxLayout(orientation='vertical', spacing=10, padding=12)
        content.add_widget(Label(text=f"Save '{descriptor.name}' as Permanent Tool:"))
        name_in = TextInput(text=descriptor.name, multiline=False)
        content.add_widget(name_in)
        
        btn_row = BoxLayout(orientation='horizontal', spacing=8, size_hint_y=None, height=40)
        popup = Popup(title="Promote to Permanent Tool", content=content, size_hint=(0.85, 0.45))
        
        btn_ok = Button(text="Save to Toolbox", background_color=ColorSystem.PRIMARY)
        def confirm_save(inst):
            final_name = name_in.text.strip() or descriptor.name
            self.promote_to_permanent(descriptor, final_name)
            popup.dismiss()
            
        btn_ok.bind(on_release=confirm_save)
        btn_row.add_widget(btn_ok)
        content.add_widget(btn_row)
        popup.open()

    def promote_to_permanent(self, descriptor, name):
        mod_id = name.lower().replace(" ", "_").replace("-", "_")
        mod_dir = os.path.abspath(f"./modules/{mod_id}")
        os.makedirs(mod_dir, exist_ok=True)
        
        # Copy file to main.py
        shutil.copyfile(descriptor.entrypoint, os.path.join(mod_dir, "main.py"))
        
        # Create manifest
        import json
        manifest = {
            "id": mod_id,
            "name": name,
            "version": "1.0.0",
            "author": "mike",
            "category": "Tools",
            "description": f"Saved tool created from experiment.",
            "entrypoint": "main.py",
            "trust_level": "trusted"
        }
        with open(os.path.join(mod_dir, "manifest.json"), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)

        self.app_manager.refresh_modules()

    def delete_scratch_module(self, descriptor):
        try:
            if os.path.exists(descriptor.entrypoint):
                os.remove(descriptor.entrypoint)
        except Exception as e:
            print(f"Error removing scratch file: {e}")
        self.app_manager.refresh_modules()
