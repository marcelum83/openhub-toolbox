"""
OpenHub Main Launcher Screen (The Deck)
Displays discovered tools in a responsive card grid with category filtering.
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, RoundedRectangle
from ui.themes import ColorSystem

class ModuleCard(BoxLayout):
    def __init__(self, descriptor, on_launch_callback, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=110, padding=12, spacing=4, **kwargs)
        self.descriptor = descriptor
        self.on_launch = on_launch_callback
        
        with self.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[12])
            Color(*ColorSystem.SURFACE_BORDER)
            self.border_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[12])
        self.bind(size=self._update_rects, pos=self._update_rects)

        # Top row: Title + Category Tag
        top_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=26, spacing=8)
        
        # Category emoji map
        cat_emojis = {
            "Tools": "🛠️",
            "Field": "🧭",
            "Agents": "🤖",
            "Creative": "🎨",
            "Experiments": "🔬",
            "Scratch": "📝"
        }
        emoji = cat_emojis.get(descriptor.category, "📦")
        
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
        
        # Description
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
        self.all_descriptors = []
        self.active_category = "All"
        self.search_query = ""

        # Root layout
        root = BoxLayout(orientation='vertical', spacing=0)
        
        with root.canvas.before:
            Color(*ColorSystem.BG_DARK)
            self.bg_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # 1. Top Global Navigation Bar
        nav_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=56, padding=[12, 6, 12, 6], spacing=10)
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

        # Tab: Toolbox (Active)
        self.btn_tab_deck = Button(
            text="🛠️ TOOLBOX",
            size_hint_x=0.5,
            background_normal="",
            background_color=ColorSystem.PRIMARY,
            color=ColorSystem.BG_DARK,
            bold=True
        )
        nav_bar.add_widget(self.btn_tab_deck)

        # Tab: Forge (Studio)
        self.btn_tab_forge = Button(
            text="⚡ THE FORGE",
            size_hint_x=0.5,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True
        )
        self.btn_tab_forge.bind(on_release=self.switch_to_forge)
        nav_bar.add_widget(self.btn_tab_forge)

        # Refresh button
        btn_refresh = Button(
            text="🔄",
            size_hint_x=None,
            width=45,
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True
        )
        btn_refresh.bind(on_release=lambda x: self.app_manager.refresh_modules())
        nav_bar.add_widget(btn_refresh)

        root.add_widget(nav_bar)

        # 2. Search & Filter Bar
        search_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=48, padding=[12, 6, 12, 6], spacing=8)
        self.search_input = TextInput(
            hint_text="🔍 Search tools...",
            multiline=False,
            size_hint_x=1.0,
            background_color=ColorSystem.SURFACE,
            foreground_color=ColorSystem.TEXT_PRIMARY,
            hint_text_color=ColorSystem.TEXT_HINT,
            cursor_color=ColorSystem.PRIMARY,
            padding=[10, 8, 10, 8]
        )
        self.search_input.bind(text=self.on_search_text_changed)
        search_box.add_widget(self.search_input)
        root.add_widget(search_box)

        # 3. Category Filter Tabs
        self.cat_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, padding=[12, 2, 12, 6], spacing=6)
        self.categories = ["All", "Tools", "Field", "Agents", "Experiments", "Scratch"]
        self.cat_buttons = {}
        for cat in self.categories:
            btn = Button(
                text=cat,
                size_hint_x=None,
                width=80,
                background_normal="",
                background_color=ColorSystem.PRIMARY if cat == "All" else ColorSystem.SURFACE,
                color=ColorSystem.BG_DARK if cat == "All" else ColorSystem.TEXT_MUTED,
                bold=True,
                font_size="12sp"
            )
            btn.bind(on_release=lambda instance, c=cat: self.set_category_filter(c))
            self.cat_buttons[cat] = btn
            self.cat_bar.add_widget(btn)

        cat_scroll = ScrollView(size_hint_y=None, height=40, do_scroll_x=True, do_scroll_y=False)
        cat_scroll.add_widget(self.cat_bar)
        root.add_widget(cat_scroll)

        # 4. Scrollable Grid of Module Cards
        scroll = ScrollView()
        self.grid = GridLayout(cols=1, spacing=10, padding=12, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        scroll.add_widget(self.grid)
        root.add_widget(scroll)

        self.add_widget(root)

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _update_nav_rect(self, instance, value):
        self.nav_rect.pos = instance.pos
        self.nav_rect.size = instance.size

    def switch_to_forge(self, instance):
        if self.manager:
            self.manager.current = 'forge'

    def set_category_filter(self, category):
        self.active_category = category
        for cat, btn in self.cat_buttons.items():
            if cat == category:
                btn.background_color = ColorSystem.PRIMARY
                btn.color = ColorSystem.BG_DARK
            else:
                btn.background_color = ColorSystem.SURFACE
                btn.color = ColorSystem.TEXT_MUTED
        self.rebuild_grid()

    def on_search_text_changed(self, instance, value):
        self.search_query = value.strip().lower()
        self.rebuild_grid()

    def update_modules(self, descriptors):
        self.all_descriptors = descriptors
        self.rebuild_grid()

    def rebuild_grid(self):
        self.grid.clear_widgets()
        for desc in self.all_descriptors:
            # Filter by category
            if self.active_category != "All" and desc.category != self.active_category:
                continue
            # Filter by search
            if self.search_query:
                q = self.search_query
                if q not in desc.name.lower() and q not in desc.description.lower():
                    continue
            card = ModuleCard(desc, on_launch_callback=self.app_manager.launch_module)
            self.grid.add_widget(card)
            
        if not self.grid.children:
            empty_lbl = Label(
                text=f"No modules found in category '{self.active_category}'.\nTap '⚡ The Forge' to create one on the fly!",
                font_size="14sp",
                color=ColorSystem.TEXT_MUTED,
                size_hint_y=None,
                height=120,
                halign='center'
            )
            self.grid.add_widget(empty_lbl)
