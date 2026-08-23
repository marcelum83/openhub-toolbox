"""
OpenHub Conversational Agent Chat Screen
Interactive UI for real-time conversation and 1-tap tool creation via Local Ollama & Gemini.
"""
import re
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.clock import Clock
from ui.themes import ColorSystem

class ChatBubble(BoxLayout):
    def __init__(self, role, text, tool_code=None, tool_title="Custom Tool", on_run_tool=None, on_edit_tool=None, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, spacing=dp(6), **kwargs)
        self.role = role
        self.tool_code = tool_code
        self.on_run_tool = on_run_tool
        self.on_edit_tool = on_edit_tool
        
        is_user = (role == "user")
        self.padding = [dp(14), dp(10), dp(14), dp(10)]
        self.size_hint_x = 0.88
        self.pos_hint = {'right': 0.98} if is_user else {'x': 0.02}

        # Background styling
        with self.canvas.before:
            if is_user:
                Color(0.18, 0.12, 0.28, 0.95)
            else:
                Color(0.11, 0.11, 0.17, 0.95)
            self.bg_rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(14)])
            
            if is_user:
                Color(0.54, 0.36, 0.96, 0.8)
            else:
                Color(0.02, 0.71, 0.83, 0.6)
            self.border_rect = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(14)), width=1.0)
        self.bind(size=self._update_rects, pos=self._update_rects)

        # Header tag
        tag_text = "👤 YOU" if is_user else "🤖 AGENT"
        lbl_tag = Label(
            text=tag_text,
            font_size="11sp",
            bold=True,
            color=ColorSystem.SECONDARY if is_user else ColorSystem.PRIMARY,
            size_hint_y=None,
            height=dp(18),
            halign='right' if is_user else 'left'
        )
        lbl_tag.bind(size=lbl_tag.setter('text_size'))
        self.add_widget(lbl_tag)

        # Text display (stripping raw code if tool widget is shown)
        display_text = text
        if tool_code and "```python" in display_text:
            display_text = re.sub(r'```python.*?```', '*(Executable Python Tool Generated Below)*', display_text, flags=re.DOTALL)

        lbl_content = Label(
            text=display_text.strip(),
            font_size="14sp",
            color=(0.95, 0.95, 0.97, 1.0),
            size_hint_y=None,
            halign='left',
            valign='top'
        )
        lbl_content.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        lbl_content.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
        self.add_widget(lbl_content)

        # Embedded Action Card if tool code was generated
        if tool_code:
            tool_card = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(105), padding=dp(8), spacing=dp(6))
            with tool_card.canvas.before:
                Color(0.06, 0.06, 0.10, 1.0)
                self.tc_bg = RoundedRectangle(size=tool_card.size, pos=tool_card.pos, radius=[dp(10)])
                Color(0.15, 0.68, 0.38, 0.9)
                self.tc_border = Line(rounded_rectangle=(tool_card.x, tool_card.y, tool_card.width, tool_card.height, dp(10)), width=1.2)
            tool_card.bind(size=self._update_tc, pos=self._update_tc)

            lbl_tool_head = Label(
                text=f"✨ {tool_title}",
                font_size="14sp",
                bold=True,
                color=(0.15, 0.68, 0.38, 1.0),
                size_hint_y=None,
                height=dp(22),
                halign='left'
            )
            lbl_tool_head.bind(size=lbl_tool_head.setter('text_size'))
            tool_card.add_widget(lbl_tool_head)

            btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48), spacing=dp(8))
            
            btn_run = Button(
                text="▶ RUN IN OPENHUB",
                background_normal="",
                background_color=(0.15, 0.68, 0.38, 1.0),
                color=(1, 1, 1, 1),
                bold=True,
                font_size="13sp",
                size_hint_x=0.6,
                always_release=True
            )
            btn_run.bind(on_release=lambda *a: self.on_run_tool(tool_code, tool_title) if self.on_run_tool else None)
            btn_row.add_widget(btn_run)

            btn_edit = Button(
                text="✏️ FORGE",
                background_normal="",
                background_color=(0.18, 0.18, 0.26, 1.0),
                color=(0.95, 0.95, 0.97, 1.0),
                bold=True,
                font_size="13sp",
                size_hint_x=0.4,
                always_release=True
            )
            btn_edit.bind(on_release=lambda *a: self.on_edit_tool(tool_code, tool_title) if self.on_edit_tool else None)
            btn_row.add_widget(btn_edit)

            tool_card.add_widget(btn_row)
            self.add_widget(tool_card)

        # Dynamic height calculation
        Clock.schedule_once(self._compute_height, 0.05)

    def _update_rects(self, inst, val):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size
        self.border_rect.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(14))

    def _update_tc(self, inst, val):
        self.tc_bg.pos = inst.pos
        self.tc_bg.size = inst.size
        self.tc_border.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(10))

    def _compute_height(self, dt):
        h = sum([c.height for c in self.children]) + dp(28)
        self.height = max(dp(65), h)


class AgentChatScreen(Screen):
    def __init__(self, app_manager, **kwargs):
        super().__init__(**kwargs)
        self.app_manager = app_manager
        self.agent = app_manager.agent_engine
        self.agent.bind(on_agent_message=self.on_message_received)
        self.agent.bind(on_agent_error=self.on_error_received)
        self.agent.bind(is_busy=self.on_busy_changed)

        root = BoxLayout(orientation='vertical', spacing=0)
        with root.canvas.before:
            Color(*ColorSystem.BG_DARK)
            self.bg_rect = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # 1. Header Bar
        nav_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), padding=[dp(10), dp(6), dp(10), dp(6)], spacing=dp(8))
        with nav_bar.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.nav_rect = Rectangle(size=nav_bar.size, pos=nav_bar.pos)
        nav_bar.bind(size=self._update_nav_rect, pos=self._update_nav_rect)

        btn_back = Button(
            text="⬅️ DECK",
            size_hint_x=None,
            width=dp(84),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp",
            always_release=True
        )
        btn_back.bind(on_release=lambda x: setattr(self.manager, 'current', 'launcher'))
        nav_bar.add_widget(btn_back)

        lbl_title = Label(
            text="🤖 AGENT CHAT",
            font_size="18sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            size_hint_x=0.45,
            halign='left',
            valign='middle'
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        nav_bar.add_widget(lbl_title)

        # Provider Switcher Pill
        self.btn_provider = Button(
            text="🖥️ OLLAMA (LOCAL)",
            size_hint_x=None,
            width=dp(145),
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 0.9),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="11sp",
            always_release=True
        )
        self.btn_provider.bind(on_release=self.toggle_provider)
        nav_bar.add_widget(self.btn_provider)

        btn_clear = Button(
            text="🗑️",
            size_hint_x=None,
            width=dp(42),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="15sp",
            always_release=True
        )
        btn_clear.bind(on_release=self.clear_chat)
        nav_bar.add_widget(btn_clear)
        root.add_widget(nav_bar)

        # 2. Chat Scroll Area
        self.scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            scroll_timeout=250,
            scroll_distance=dp(10),
            effect_cls='ScrollEffect'
        )
        self.chat_list = GridLayout(cols=1, spacing=dp(12), padding=dp(12), size_hint_y=None)
        self.chat_list.bind(minimum_height=self.chat_list.setter('height'))
        self.scroll.add_widget(self.chat_list)
        root.add_widget(self.scroll)

        # 3. Status Bar (Thinking / Ready)
        self.lbl_status = Label(
            text="Ready • Running on Local Workstation Ollama (RTX 3060)",
            font_size="12sp",
            color=(0.6, 0.6, 0.7, 1.0),
            size_hint_y=None,
            height=dp(22),
            halign='center'
        )
        self.lbl_status.bind(size=self.lbl_status.setter('text_size'))
        root.add_widget(self.lbl_status)

        # 4. Quick Suggestions Carousel
        chips_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(38), padding=[dp(8), 0, dp(8), 0], spacing=dp(6))
        chips = [
            ("⚡ Reaction Game", "Build a quick reaction speed test game"),
            ("☀️ Check Lux", "What is my current ambient light in lux?"),
            ("🧭 Compass Info", "Tell me my current compass heading and orientation"),
            ("⏱️ Interval Timer", "Create a HIIT interval workout timer tool")
        ]
        for chip_label, prompt_text in chips:
            b = Button(
                text=chip_label,
                background_normal="",
                background_color=(0.13, 0.13, 0.19, 1.0),
                color=(0.02, 0.71, 0.83, 1.0),
                bold=True,
                font_size="12sp",
                always_release=True
            )
            b.bind(on_release=lambda inst, p=prompt_text: self.send_prompt(p))
            chips_box.add_widget(b)
        root.add_widget(chips_box)

        # 5. Input Area
        input_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(58), padding=[dp(8), dp(6), dp(8), dp(6)], spacing=dp(6))
        with input_bar.canvas.before:
            Color(*ColorSystem.SURFACE)
            self.inp_rect = Rectangle(size=input_bar.size, pos=input_bar.pos)
        input_bar.bind(size=self._update_inp_rect, pos=self._update_inp_rect)

        self.txt_input = TextInput(
            hint_text="Ask agent or say 'Build a tool'...",
            multiline=False,
            font_size="15sp",
            background_color=(0.11, 0.11, 0.17, 1.0),
            foreground_color=(0.95, 0.95, 0.97, 1.0),
            cursor_color=ColorSystem.PRIMARY,
            padding=[dp(12), dp(10), dp(12), dp(10)]
        )
        self.txt_input.bind(on_text_validate=self.on_send_pressed)
        input_bar.add_widget(self.txt_input)

        self.btn_voice = Button(
            text="🎙️",
            size_hint_x=None,
            width=dp(46),
            background_normal="",
            background_color=(0.18, 0.20, 0.30, 1.0),
            color=(0.02, 0.71, 0.83, 1.0),
            bold=True,
            font_size="18sp",
            always_release=True
        )
        self.btn_voice.bind(on_release=self.on_voice_pressed)
        input_bar.add_widget(self.btn_voice)

        self.btn_send = Button(
            text="SEND",
            size_hint_x=None,
            width=dp(72),
            background_normal="",
            background_color=ColorSystem.PRIMARY,
            color=(0.05, 0.05, 0.08, 1.0),
            bold=True,
            font_size="13sp",
            always_release=True
        )
        self.btn_send.bind(on_release=self.on_send_pressed)
        input_bar.add_widget(self.btn_send)
        root.add_widget(input_bar)

        self.add_widget(root)

    def on_voice_pressed(self, *args):
        try:
            from core.voice import VoiceBridge
            self.lbl_status.text = "🎙️ Listening... Speak your request..."
            self.btn_voice.background_color = (0.85, 0.2, 0.2, 1.0)
            voice = VoiceBridge(on_result_callback=self.on_voice_result, on_error_callback=self.on_voice_error)
            voice.start_listening()
        except Exception as e:
            self.lbl_status.text = f"Voice error: {e}"

    def on_voice_result(self, text):
        self.btn_voice.background_color = (0.18, 0.20, 0.30, 1.0)
        self.lbl_status.text = f"🎙️ Heard: '{text}'"
        self.txt_input.text = text
        Clock.schedule_once(lambda dt: self.on_send_pressed(None), 0.3)

    def on_voice_error(self, err_msg):
        self.btn_voice.background_color = (0.18, 0.20, 0.30, 1.0)
        self.lbl_status.text = f"🎙️ {err_msg}"

        # Add initial welcome bubble
        Clock.schedule_once(lambda dt: self.add_welcome_bubble(), 0.2)

    def _update_bg(self, inst, val):
        self.bg_rect.pos = inst.pos
        self.bg_rect.size = inst.size

    def _update_nav_rect(self, inst, val):
        self.nav_rect.pos = inst.pos
        self.nav_rect.size = inst.size

    def _update_inp_rect(self, inst, val):
        self.inp_rect.pos = inst.pos
        self.inp_rect.size = inst.size

    def add_welcome_bubble(self):
        welcome_text = "👋 Welcome to OpenHub Agent! I'm your local AI physical tool architect.\n\nYou can chat with me, ask for sensor readings, or ask me to build any custom tool or game!"
        self.chat_list.add_widget(ChatBubble(role="assistant", text=welcome_text))

    def toggle_provider(self, *args):
        if self.agent.current_provider == "ollama":
            self.agent.save_config(provider="simple_agent")
            self.btn_provider.text = "🤖 SIMPLE_AGENT"
            self.btn_provider.background_color = (0.95, 0.55, 0.15, 0.9)
            self.lbl_status.text = "Ready • Connected to ACE-OS SimpleAgent (LAN)"
        elif self.agent.current_provider == "simple_agent":
            self.agent.save_config(provider="firebase")
            self.btn_provider.text = "📡 CLOUD TELEPATHY"
            self.btn_provider.background_color = (0.85, 0.25, 0.75, 0.9)
            self.lbl_status.text = "Ready • Firebase Cloud Relay ➔ Nexus Studio"
        elif self.agent.current_provider == "firebase":
            self.agent.save_config(provider="gemini")
            self.btn_provider.text = "⚡ GEMINI CLOUD"
            self.btn_provider.background_color = (0.02, 0.71, 0.83, 0.9)
            self.lbl_status.text = "Ready • Powered by Gemini 1.5 Flash Cloud"
        else:
            self.agent.save_config(provider="ollama")
            self.btn_provider.text = "🖥️ OLLAMA (LOCAL)"
            self.btn_provider.background_color = (0.54, 0.36, 0.96, 0.9)
            self.lbl_status.text = "Ready • Powered by Workstation Ollama (qwen2.5-coder)"

    def clear_chat(self, *args):
        self.agent.clear_history()
        self.chat_list.clear_widgets()
        self.add_welcome_bubble()

    def send_prompt(self, text):
        self.txt_input.text = text
        self.on_send_pressed()

    def on_send_pressed(self, *args):
        msg = self.txt_input.text.strip()
        if not msg or self.agent.is_busy:
            return
        self.txt_input.text = ""
        self.agent.send_user_message(msg)

    def on_busy_changed(self, inst, busy):
        self.btn_send.disabled = busy
        if busy:
            provider_name = "Local Workstation Ollama (RTX 3060)" if self.agent.current_provider == "ollama" else "Gemini Cloud"
            self.lbl_status.text = f"⏳ Agent is thinking on {provider_name}..."
            self.lbl_status.color = (0.02, 0.71, 0.83, 1.0)
        else:
            self.lbl_status.text = "Ready"
            self.lbl_status.color = (0.6, 0.6, 0.7, 1.0)

    def on_message_received(self, inst, role, content, tool_code, tool_title):
        bubble = ChatBubble(
            role=role,
            text=content,
            tool_code=tool_code,
            tool_title=tool_title,
            on_run_tool=self.run_generated_tool,
            on_edit_tool=self.edit_generated_tool
        )
        self.chat_list.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    def on_error_received(self, inst, error_msg):
        err_bubble = ChatBubble(role="assistant", text=f"❌ {error_msg}")
        self.chat_list.add_widget(err_bubble)
        self.lbl_status.text = f"❌ Error: {error_msg}"
        self.lbl_status.color = (0.91, 0.30, 0.24, 1.0)

    def run_generated_tool(self, code, title):
        try:
            desc = self.app_manager.module_mgr.create_scratch(code, prompt=title)
            Clock.schedule_once(lambda dt: self.app_manager.refresh_modules(), 0)
            Clock.schedule_once(lambda dt, d=desc: self.app_manager.launch_module(d), 0.1)
        except Exception as e:
            print(f"[AgentChatScreen] Run tool error: {e}")

    def edit_generated_tool(self, code, title):
        try:
            desc = self.app_manager.module_mgr.create_scratch(code, prompt=title)
            forge_screen = self.manager.get_screen('forge')
            forge_screen.load_descriptor_for_editing(desc, code)
            Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'forge'), 0)
        except Exception as e:
            print(f"[AgentChatScreen] Edit tool error: {e}")
