"""
Python Library Explorer & Visual Kivy / L-System Builder
1. INSPECT mode: Introspect Python stdlib, Kivy UI widgets, classes, and docstrings.
2. BUILDER mode: Drag-and-drop Kivy widgets & L-system nodes onto a live canvas,
   bind custom Python scripts per widget, test live, and export as standalone
   OpenHubModule (.py) or L-System Seed (.json) directly to Scratch/Deck.
"""
import importlib
import inspect
import json
import os
import textwrap

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

CATEGORIES = {
    "Core & Stdlib": ["os", "sys", "json", "math", "datetime", "random", "re", "time", "threading", "urllib.request"],
    "Kivy UI": [
        "kivy.uix.button",
        "kivy.uix.togglebutton",
        "kivy.uix.slider",
        "kivy.uix.label",
        "kivy.uix.textinput",
        "kivy.uix.progressbar",
        "kivy.uix.boxlayout",
        "kivy.app",
        "kivy.clock",
        "kivy.graphics",
    ],
    "Hardware / Mobile": ["jnius", "plyer", "android"],
    "Network & AI": ["requests", "urllib", "http.client", "socket", "websockets"],
}

WIDGET_CATALOG = [
    {
        "kind": "button",
        "title": "Button",
        "kivy_module": "kivy.uix.button",
        "kivy_class": "Button",
        "lsystem_type": "action_button",
        "default_label": "Run Action",
        "default_endpoint": "/action/trigger",
        "default_script": 'if host and host.hardware:\n    host.hardware.vibrate(35)\nlog("Button pressed!")',
        "color": (0.02, 0.71, 0.83, 1.0),
    },
    {
        "kind": "toggle",
        "title": "Toggle",
        "kivy_module": "kivy.uix.togglebutton",
        "kivy_class": "ToggleButton",
        "lsystem_type": "actuator_toggle",
        "default_label": "Relay Switch",
        "default_endpoint": "/relay/power",
        "default_script": 'state["active"] = bool(value)\nlog(f"Relay -> {\'ON\' if value else \'OFF\'}")',
        "color": (0.15, 0.68, 0.38, 1.0),
    },
    {
        "kind": "slider",
        "title": "Slider",
        "kivy_module": "kivy.uix.slider",
        "kivy_class": "Slider",
        "lsystem_type": "actuator_slider",
        "default_label": "Level Slider",
        "default_endpoint": "/level/set",
        "default_script": 'log(f"Slider value: {int(value)}%")',
        "color": (0.54, 0.36, 0.96, 1.0),
    },
    {
        "kind": "label",
        "title": "Sensor/Label",
        "kivy_module": "kivy.uix.label",
        "kivy_class": "Label",
        "lsystem_type": "sensor_readout",
        "default_label": "Sensor Readout",
        "default_endpoint": "/sensor/read",
        "default_script": 'log("Readout refreshed")',
        "color": (0.95, 0.61, 0.07, 1.0),
    },
    {
        "kind": "input",
        "title": "TextInput",
        "kivy_module": "kivy.uix.textinput",
        "kivy_class": "TextInput",
        "lsystem_type": "status_banner",
        "default_label": "Command Input",
        "default_endpoint": "/cmd",
        "default_script": 'log(f"Submitted: {value}")',
        "color": (0.05, 0.80, 0.75, 1.0),
    },
    {
        "kind": "gauge",
        "title": "ProgressBar",
        "kivy_module": "kivy.uix.progressbar",
        "kivy_class": "ProgressBar",
        "lsystem_type": "gauge_bar",
        "default_label": "Tank Gauge",
        "default_endpoint": "/tank/level",
        "default_script": 'log("Gauge updated")',
        "color": (0.91, 0.30, 0.24, 1.0),
    },
    {
        "kind": "sparkline",
        "title": "Sparkline",
        "kivy_module": "core.lsystem_ui",
        "kivy_class": "SparklineChart",
        "lsystem_type": "sparkline_chart",
        "default_label": "Solar Trend",
        "default_endpoint": "/solar/watts",
        "default_script": 'log("Trend point sampled")',
        "color": (0.15, 0.80, 0.55, 1.0),
    },
    {
        "kind": "homeostasis",
        "title": "ReflexRule",
        "kivy_module": "core.lsystem_ui",
        "kivy_class": "HomeostasisRule",
        "lsystem_type": "homeostasis_rule",
        "default_label": "Auto Load Shed",
        "default_endpoint": "/batt",
        "default_script": 'log("Homeostasis rule toggled")',
        "color": (0.95, 0.45, 0.15, 1.0),
    },
    {
        "kind": "row",
        "title": "Row (2-up)",
        "kivy_module": "kivy.uix.boxlayout",
        "kivy_class": "BoxLayout",
        "lsystem_type": "row_container",
        "is_container": True,
        "default_label": "Horizontal Row",
        "default_endpoint": "",
        "default_script": "",
        "color": (0.45, 0.72, 0.98, 1.0),
    },
    {
        "kind": "grid",
        "title": "Grid (2-col)",
        "kivy_module": "kivy.uix.gridlayout",
        "kivy_class": "GridLayout",
        "lsystem_type": "grid_container",
        "is_container": True,
        "default_label": "2-Col Grid",
        "default_endpoint": "",
        "default_script": "",
        "color": (0.72, 0.52, 0.98, 1.0),
    },
]

SCRIPT_PRESETS = [
    ("📳 Vibrate", 'if host and host.hardware:\n    host.hardware.vibrate(40)\nlog("Haptic pulse!")'),
    ("🔦 Torch", 't = not state.get("torch", False)\nstate["torch"] = t\nif host and host.hardware:\n    host.hardware.set_torch(t)\nlog(f"Torch: {t}")'),
    ("🌐 HTTP POST", 'import urllib.request, json\nreq = urllib.request.Request(\n    "http://van-pi.local/action",\n    data=json.dumps({"value": value}).encode(),\n    headers={"Content-Type": "application/json"},\n    method="POST",\n)\nlog(f"Prepared POST payload={value}")'),
    ("📝 Log Value", 'log(f"{widget_label}: value={value}")'),
]


def _card_bg(widget, bg_color, border_color=None, radius=10):
    with widget.canvas.before:
        Color(*bg_color)
        rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
        bdr = None
        if border_color is not None:
            Color(*border_color)
            bdr = Line(rounded_rectangle=(widget.x, widget.y, widget.width, widget.height, dp(radius)), width=1.1)

    def _sync(*_args):
        rect.pos = widget.pos
        rect.size = widget.size
        if bdr is not None:
            bdr.rounded_rectangle = (widget.x, widget.y, widget.width, widget.height, dp(radius))

    widget.bind(pos=_sync, size=_sync)


def generate_python_module_code(nodes, title="Visual Kivy Tool"):
    """Recursively compiles builder node specs (including nested containers) into an OpenHubModule."""
    lines = [
        '"""',
        f"Auto-generated by OpenHub Visual Kivy Studio: {title}",
        '"""',
        "from kivy.metrics import dp",
        "from kivy.uix.boxlayout import BoxLayout",
        "from kivy.uix.button import Button",
        "from kivy.uix.gridlayout import GridLayout",
        "from kivy.uix.label import Label",
        "from kivy.uix.progressbar import ProgressBar",
        "from kivy.uix.scrollview import ScrollView",
        "from kivy.uix.slider import Slider",
        "from kivy.uix.textinput import TextInput",
        "from kivy.uix.togglebutton import ToggleButton",
        "",
        "",
        "class OpenHubModule(BoxLayout):",
        "    def __init__(self, **kwargs):",
        "        super().__init__(orientation='vertical', padding=dp(12), spacing=dp(8), **kwargs)",
        "        self.host = None",
        "        self.state = {}",
        f"        self.add_widget(Label(text={title!r}, font_size='18sp', bold=True, size_hint_y=None, height=dp(36), color=(0.02, 0.71, 0.83, 1.0)))",
        "        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)",
        "        body = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None)",
        "        body.bind(minimum_height=body.setter('height'))",
        "        scroll.add_widget(body)",
        "        self.add_widget(scroll)",
        "",
    ]

    handler_defs = [
        "    def on_load(self, host_api):",
        "        self.host = host_api",
        "",
        "    def log(self, msg):",
        "        self.lbl_log.text = str(msg)",
        "        if self.host:",
        "            self.host.log(str(msg))",
        "",
    ]
    counter = {"n": 0}

    def _emit_nodes(node_list, parent_var):
        for node in node_list:
            idx = counter["n"]
            counter["n"] += 1
            kind = node["kind"]
            label = node.get("label", "Widget")

            if kind in ("row", "grid", "section"):
                cont_var = f"cont_{idx}"
                if kind == "row":
                    lines.append(f"        {cont_var} = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(58))")
                elif kind == "grid":
                    lines.append(f"        {cont_var} = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)")
                    lines.append(f"        {cont_var}.bind(minimum_height={cont_var}.setter('height'))")
                else:
                    lines.append(f"        {cont_var} = BoxLayout(orientation='vertical', spacing=dp(6), size_hint_y=None)")
                    lines.append(f"        {cont_var}.bind(minimum_height={cont_var}.setter('height'))")
                _emit_nodes(node.get("children") or [], cont_var)
                lines.append(f"        {parent_var}.add_widget({cont_var})")
                continue

            script = (node.get("script") or "pass").strip() or "pass"
            fn_name = f"_on_node_{idx}"

            if kind == "button":
                lines.append(
                    f"        btn_{idx} = Button(text={label!r}, size_hint_y=None, height=dp(48), background_normal='', background_color=(0.02, 0.71, 0.83, 1.0), bold=True, always_release=True)"
                )
                lines.append(f"        btn_{idx}.bind(on_release=lambda inst: self.{fn_name}(inst, True))")
                lines.append(f"        {parent_var}.add_widget(btn_{idx})")
            elif kind == "toggle":
                lines.append(
                    f"        tog_{idx} = ToggleButton(text={label!r}, size_hint_y=None, height=dp(48), bold=True)"
                )
                lines.append(f"        tog_{idx}.bind(state=lambda inst, st: self.{fn_name}(inst, st == 'down'))")
                lines.append(f"        {parent_var}.add_widget(tog_{idx})")
            elif kind == "slider":
                lines.append(f"        box_{idx} = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(58))")
                lines.append(f"        box_{idx}.add_widget(Label(text={label!r}, size_hint_y=None, height=dp(22), halign='left'))")
                lines.append(f"        sld_{idx} = Slider(min=0, max=100, value=50, size_hint_y=None, height=dp(36))")
                lines.append(f"        sld_{idx}.bind(value=lambda inst, val: self.{fn_name}(inst, val))")
                lines.append(f"        box_{idx}.add_widget(sld_{idx})")
                lines.append(f"        {parent_var}.add_widget(box_{idx})")
            elif kind == "input":
                lines.append(
                    f"        inp_{idx} = TextInput(hint_text={label!r}, multiline=False, size_hint_y=None, height=dp(44))"
                )
                lines.append(f"        inp_{idx}.bind(on_text_validate=lambda inst: self.{fn_name}(inst, inst.text))")
                lines.append(f"        {parent_var}.add_widget(inp_{idx})")
            elif kind == "gauge":
                lines.append(f"        box_{idx} = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(42))")
                lines.append(f"        box_{idx}.add_widget(Label(text={label!r}, size_hint_y=None, height=dp(20)))")
                lines.append(f"        box_{idx}.add_widget(ProgressBar(max=100, value=65, size_hint_y=None, height=dp(18)))")
                lines.append(f"        {parent_var}.add_widget(box_{idx})")
            else:
                lines.append(
                    f"        lbl_{idx} = Label(text={label!r}, size_hint_y=None, height=dp(34), bold=True, color=(0.95, 0.61, 0.07, 1.0))"
                )
                lines.append(f"        {parent_var}.add_widget(lbl_{idx})")

            handler_defs.append(f"    def {fn_name}(self, widget, value):")
            handler_defs.append("        host = self.host")
            handler_defs.append("        state = self.state")
            handler_defs.append("        log = self.log")
            handler_defs.append(f"        widget_label = {label!r}")
            for s_line in textwrap.dedent(script).splitlines():
                handler_defs.append(f"        {s_line}" if s_line.strip() else "")
            handler_defs.append("")

    _emit_nodes(nodes, "body")

    lines.extend([
        "",
        "        self.lbl_log = Label(text='Ready.', size_hint_y=None, height=dp(30), font_size='12sp', color=(0.65, 0.65, 0.75, 1.0))",
        "        self.add_widget(self.lbl_log)",
        "",
    ])
    lines.extend(handler_defs)
    return "\n".join(lines)


def _node_to_lsystem_seed(node):
    """Converts a single Builder node (recursively for containers) into L-system seed JSON."""
    kind = node["kind"]
    label = node.get("label", "Node")
    endpoint = node.get("endpoint") or "/node"

    if kind == "row":
        return {
            "node_type": "row_container",
            "height": 84,
            "children": [_node_to_lsystem_seed(c) for c in (node.get("children") or [])],
        }
    if kind == "grid":
        return {
            "node_type": "grid_container",
            "cols": 2,
            "children": [_node_to_lsystem_seed(c) for c in (node.get("children") or [])],
        }
    if kind == "section":
        return {
            "node_type": "module_container",
            "title": label,
            "children": [_node_to_lsystem_seed(c) for c in (node.get("children") or [])],
        }
    if kind == "button":
        return {
            "node_type": "action_button",
            "label": label,
            "control_endpoint": endpoint,
            "tone": "primary",
        }
    if kind == "toggle":
        return {
            "node_type": "actuator_toggle",
            "label": label,
            "control_endpoint": endpoint,
            "initial": False,
        }
    if kind == "slider":
        return {
            "node_type": "actuator_slider",
            "label": label,
            "control_endpoint": endpoint,
            "range": [0, 100],
            "step": 5,
            "initial": 50,
            "unit": "%",
        }
    if kind == "gauge":
        return {
            "node_type": "gauge_bar",
            "label": label,
            "data_endpoint": endpoint,
            "range": [0, 100],
            "unit": "%",
            "sim_value": 65,
        }
    if kind == "sparkline":
        return {
            "node_type": "sparkline_chart",
            "label": label,
            "data_endpoint": endpoint,
            "unit": "",
            "max_points": 24,
            "sim_value": 50,
            "sim_range": [10, 90],
        }
    if kind == "homeostasis":
        return {
            "node_type": "homeostasis_rule",
            "id": label.lower().replace(" ", "_"),
            "label": label,
            "sensor_endpoint": endpoint,
            "operator": "<",
            "threshold": 11.9,
            "hysteresis": 0.3,
            "target_endpoint": "/lights/dim",
            "target_payload": {"value": 0},
            "sim_value": 12.5,
            "sim_range": [11.5, 13.5],
        }
    if kind == "input":
        return {
            "node_type": "status_banner",
            "text": label,
        }
    return {
        "node_type": "sensor_readout",
        "label": label,
        "data_endpoint": endpoint,
        "unit": "",
        "sim_value": 24.0,
    }


def generate_lsystem_seed_data(nodes, title="Visual L-System Node", base_url="http://van-pi.local"):
    """Compiles builder node specs into a recursive OpenHub L-system JSON seed."""
    return {
        "node_type": "module_container",
        "title": title,
        "subtitle": "Grown from Visual Studio",
        "base_url": base_url,
        "simulate_offline": True,
        "children": [_node_to_lsystem_seed(n) for n in nodes],
    }


def extract_nodes_from_seed(seed_data):
    """Converts an L-system JSON seed tree into nested Builder node specs."""
    by_lsys = {s["lsystem_type"]: s for s in WIDGET_CATALOG}

    def _convert(node, is_root=False):
        if not isinstance(node, dict):
            return []
        nt = node.get("node_type")
        raw_children = node.get("children")
        if is_root and isinstance(raw_children, list):
            out = []
            for ch in raw_children:
                out.extend(_convert(ch, is_root=False))
            return out

        if nt in ("row_container", "grid_container") and isinstance(raw_children, list):
            spec = by_lsys[nt]
            nested = []
            for ch in raw_children:
                nested.extend(_convert(ch, is_root=False))
            return [{
                "kind": spec["kind"],
                "kivy_module": spec["kivy_module"],
                "kivy_class": spec["kivy_class"],
                "lsystem_type": nt,
                "is_container": True,
                "label": str(node.get("title") or spec["default_label"]),
                "endpoint": "",
                "script": "",
                "color": spec["color"],
                "children": nested,
            }]

        if isinstance(raw_children, list):
            out = []
            for ch in raw_children:
                out.extend(_convert(ch, is_root=False))
            return out

        spec = by_lsys.get(nt)
        if not spec:
            return []
        ep = node.get("control_endpoint") or node.get("data_endpoint") or node.get("sensor_endpoint") or spec["default_endpoint"]
        lbl = node.get("label") or node.get("text") or spec["default_label"]
        return [{
            "kind": spec["kind"],
            "kivy_module": spec["kivy_module"],
            "kivy_class": spec["kivy_class"],
            "lsystem_type": spec["lsystem_type"],
            "is_container": False,
            "label": str(lbl),
            "endpoint": str(ep),
            "script": spec["default_script"],
            "color": spec["color"],
        }]

    return _convert(seed_data, is_root=True)


class BuilderGhost(Widget):
    """Floating visual indicator shown while dragging a Kivy widget chip onto the canvas."""

    def __init__(self, spec, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(120), dp(42)), **kwargs)
        _card_bg(self, (0.09, 0.12, 0.18, 0.95), border_color=spec["color"], radius=10)
        self.lbl = Label(text=f"+ {spec['title']}", font_size="12sp", bold=True, color=spec["color"], size=self.size, pos=self.pos)
        self.add_widget(self.lbl)
        self.bind(pos=lambda *_a: setattr(self.lbl, "pos", self.pos))


class DraggablePaletteChip(Button):
    """Palette button supporting both tap-to-add and drag-and-drop onto the Builder canvas."""

    def __init__(self, spec, builder_host, **kwargs):
        super().__init__(
            text=f"+ {spec['title']}",
            size_hint_x=None,
            width=dp(102),
            background_normal="",
            background_color=(0.14, 0.16, 0.24, 1.0),
            color=spec["color"],
            bold=True,
            font_size="11sp",
            always_release=True,
            **kwargs,
        )
        self.spec = spec
        self.builder_host = builder_host
        self._touch_start = None
        self._dragging = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start = touch.pos
            self._dragging = False
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self and self._touch_start:
            dx = touch.x - self._touch_start[0]
            dy = touch.y - self._touch_start[1]
            if not self._dragging and (dx * dx + dy * dy) > dp(10) ** 2:
                self._dragging = True
                self.builder_host.start_palette_drag(self.spec, touch.pos)
            elif self._dragging:
                self.builder_host.move_palette_drag(touch.pos)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self._dragging:
                self.builder_host.end_palette_drag(self.spec, touch.pos)
            elif self.collide_point(*touch.pos):
                self.builder_host.add_node_from_spec(self.spec)
            self._touch_start = None
            self._dragging = False
            return True
        return super().on_touch_up(touch)


class WidgetScriptModal(ModalView):
    """Inspector modal to configure widget label, endpoint, and attached Python script."""

    def __init__(self, node, on_save, **kwargs):
        super().__init__(size_hint=(0.94, 0.86), auto_dismiss=True, **kwargs)
        self.node = node
        self.on_save = on_save

        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        _card_bg(root, (0.08, 0.09, 0.13, 1.0), border_color=(0.02, 0.71, 0.83, 0.8), radius=14)

        root.add_widget(
            Label(
                text=f"⚡ SCRIPT: {node['kivy_module']}.{node['kivy_class']}",
                font_size="13sp",
                bold=True,
                color=(0.02, 0.71, 0.83, 1.0),
                size_hint_y=None,
                height=dp(26),
            )
        )

        self.txt_label = TextInput(
            text=node.get("label", ""),
            hint_text="Widget label / text...",
            multiline=False,
            font_size="14sp",
            size_hint_y=None,
            height=dp(40),
            background_color=(0.13, 0.13, 0.19, 1.0),
            foreground_color=(0.95, 0.95, 0.98, 1.0),
        )
        root.add_widget(self.txt_label)

        self.txt_endpoint = TextInput(
            text=node.get("endpoint", ""),
            hint_text="Optional L-system endpoint (e.g. /pump/power)...",
            multiline=False,
            font_size="12sp",
            size_hint_y=None,
            height=dp(36),
            background_color=(0.13, 0.13, 0.19, 1.0),
            foreground_color=(0.80, 0.90, 1.0, 1.0),
        )
        root.add_widget(self.txt_endpoint)

        preset_row = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint_y=None, height=dp(34))
        preset_box = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_x=None)
        preset_box.bind(minimum_width=preset_box.setter("width"))
        for p_name, p_code in SCRIPT_PRESETS:
            b = Button(
                text=p_name,
                size_hint_x=None,
                width=dp(96),
                background_normal="",
                background_color=(0.18, 0.20, 0.30, 1.0),
                color=(0.9, 0.95, 1.0, 1.0),
                font_size="11sp",
                bold=True,
                always_release=True,
            )
            b.bind(on_release=lambda _inst, c=p_code: setattr(self.txt_script, "text", c))
            preset_box.add_widget(b)
        preset_row.add_widget(preset_box)
        root.add_widget(preset_row)

        root.add_widget(
            Label(
                text="Python Handler (vars: widget, value, host, state, log, widget_label):",
                font_size="11sp",
                color=(0.65, 0.65, 0.75, 1.0),
                size_hint_y=None,
                height=dp(18),
            )
        )

        self.txt_script = TextInput(
            text=node.get("script", ""),
            multiline=True,
            font_size="13sp",
            background_color=(0.05, 0.05, 0.08, 1.0),
            foreground_color=(0.75, 0.96, 0.78, 1.0),
            cursor_color=(0.02, 0.71, 0.83, 1.0),
        )
        root.add_widget(self.txt_script)

        btn_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(42))
        btn_cancel = Button(
            text="CANCEL",
            background_normal="",
            background_color=(0.18, 0.18, 0.26, 1.0),
            color=(0.85, 0.85, 0.92, 1.0),
            bold=True,
            always_release=True,
        )
        btn_cancel.bind(on_release=lambda *_a: self.dismiss())

        btn_save = Button(
            text="💾 APPLY SCRIPT",
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            always_release=True,
        )
        btn_save.bind(on_release=self._apply)
        btn_row.add_widget(btn_cancel)
        btn_row.add_widget(btn_save)
        root.add_widget(btn_row)
        self.add_widget(root)

    def _apply(self, *_args):
        self.node["label"] = self.txt_label.text.strip() or self.node["label"]
        self.node["endpoint"] = self.txt_endpoint.text.strip()
        self.node["script"] = self.txt_script.text
        if self.on_save:
            self.on_save()
        self.dismiss()


class CodePreviewModal(ModalView):
    """Displays generated Python or L-system JSON code."""

    def __init__(self, title, code_text, **kwargs):
        super().__init__(size_hint=(0.94, 0.86), auto_dismiss=True, **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        _card_bg(root, (0.08, 0.09, 0.13, 1.0), border_color=(0.54, 0.36, 0.96, 0.8), radius=14)
        root.add_widget(Label(text=title, font_size="14sp", bold=True, color=(0.02, 0.71, 0.83, 1.0), size_hint_y=None, height=dp(26)))
        txt = TextInput(
            text=code_text,
            readonly=True,
            font_size="12sp",
            background_color=(0.05, 0.05, 0.08, 1.0),
            foreground_color=(0.85, 0.92, 0.98, 1.0),
        )
        root.add_widget(txt)
        btn = Button(text="CLOSE", size_hint_y=None, height=dp(40), background_normal="", background_color=(0.18, 0.18, 0.26, 1.0), bold=True, always_release=True)
        btn.bind(on_release=lambda *_a: self.dismiss())
        root.add_widget(btn)
        self.add_widget(root)


class CanvasDragHandle(Button):
    """Drag handle on a Builder editor card for touch drag-to-reorder."""

    def __init__(self, idx, node, builder_host, **kwargs):
        super().__init__(
            text="≡",
            size_hint_x=None,
            width=dp(32),
            background_normal="",
            background_color=(0.16, 0.18, 0.26, 1.0),
            color=node["color"],
            bold=True,
            font_size="15sp",
            always_release=True,
            **kwargs,
        )
        self.idx = idx
        self.node = node
        self.builder_host = builder_host
        self._start_pos = None
        self._dragging = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._start_pos = touch.pos
            self._dragging = False
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self and self._start_pos:
            dy = abs(touch.y - self._start_pos[1])
            if not self._dragging and dy > dp(8):
                self._dragging = True
                self.builder_host.start_card_drag(self.idx, self.node, touch.pos)
            elif self._dragging:
                self.builder_host.move_palette_drag(touch.pos)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self._dragging:
                self.builder_host.end_card_drag(self.idx, touch.pos)
            self._start_pos = None
            self._dragging = False
            return True
        return super().on_touch_up(touch)


class LoadSeedModal(ModalView):
    """Picker modal to import an existing .json L-system seed into the Builder canvas."""

    def __init__(self, seed_entries, on_select, **kwargs):
        super().__init__(size_hint=(0.92, 0.72), auto_dismiss=True, **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        _card_bg(root, (0.08, 0.09, 0.13, 1.0), border_color=(0.02, 0.71, 0.83, 0.8), radius=14)
        root.add_widget(Label(text="📂 LOAD L-SYSTEM SEED", font_size="15sp", bold=True, color=(0.02, 0.71, 0.83, 1.0), size_hint_y=None, height=dp(28)))

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        lst = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        lst.bind(minimum_height=lst.setter("height"))
        for label, path in seed_entries:
            btn = Button(
                text=label,
                size_hint_y=None,
                height=dp(44),
                background_normal="",
                background_color=(0.14, 0.16, 0.24, 1.0),
                color=(0.95, 0.95, 0.98, 1.0),
                bold=True,
                font_size="12sp",
                always_release=True,
            )
            btn.bind(on_release=lambda _i, p=path: (on_select(p), self.dismiss()))
            lst.add_widget(btn)
        if not seed_entries:
            lst.add_widget(Label(text="No .json seed modules found.", size_hint_y=None, height=dp(40), color=(0.6, 0.6, 0.7, 1.0)))
        scroll.add_widget(lst)
        root.add_widget(scroll)

        btn_close = Button(text="CLOSE", size_hint_y=None, height=dp(38), background_normal="", background_color=(0.18, 0.18, 0.26, 1.0), bold=True, always_release=True)
        btn_close.bind(on_release=lambda *_a: self.dismiss())
        root.add_widget(btn_close)
        self.add_widget(root)


class OpenHubModule(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.host = None
        self.active_category = "Kivy UI"
        self.cat_buttons = {}
        self.mode = "inspect"
        self.test_mode = False
        self.nodes = []
        self.runtime_state = {}
        self.ghost = None

        self.main_box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8), size_hint=(1, 1))

        # 1. Top Header & Mode Switcher
        head = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(38), spacing=dp(6))
        lbl_title = Label(
            text="🔬 PYTHON & KIVY STUDIO",
            font_size="15sp",
            bold=True,
            color=(0.02, 0.71, 0.83, 1),
            halign="left",
            valign="middle",
        )
        lbl_title.bind(size=lbl_title.setter("text_size"))
        head.add_widget(lbl_title)

        self.btn_mode_inspect = Button(
            text="🔬 INSPECT",
            size_hint_x=None,
            width=dp(96),
            background_normal="",
            bold=True,
            font_size="11sp",
            always_release=True,
        )
        self.btn_mode_inspect.bind(on_release=lambda *_a: self.set_mode("inspect"))

        self.btn_mode_builder = Button(
            text="🎨 BUILDER",
            size_hint_x=None,
            width=dp(96),
            background_normal="",
            bold=True,
            font_size="11sp",
            always_release=True,
        )
        self.btn_mode_builder.bind(on_release=lambda *_a: self.set_mode("builder"))

        head.add_widget(self.btn_mode_inspect)
        head.add_widget(self.btn_mode_builder)
        self.main_box.add_widget(head)

        # 2. Content Host (swaps between Inspector and Visual Builder)
        self.content_area = BoxLayout(orientation="vertical")
        self.main_box.add_widget(self.content_area)
        self.add_widget(self.main_box)

        self._build_inspector_view()
        self._build_builder_view()
        self._seed_default_nodes()
        self.set_mode("inspect")

    def _build_inspector_view(self):
        self.inspector_view = BoxLayout(orientation="vertical", spacing=dp(8))

        cat_scroll = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint_y=None, height=dp(32))
        cat_box = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_x=None)
        cat_box.bind(minimum_width=cat_box.setter("width"))
        for cat_name in CATEGORIES.keys():
            btn = Button(
                text=cat_name,
                size_hint_x=None,
                width=dp(120),
                background_normal="",
                bold=True,
                font_size="11sp",
                always_release=True,
            )
            btn.bind(on_release=lambda _inst, c=cat_name: self.set_category(c))
            self.cat_buttons[cat_name] = btn
            cat_box.add_widget(btn)
        cat_scroll.add_widget(cat_box)
        self.inspector_view.add_widget(cat_scroll)

        self.mod_scroll = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint_y=None, height=dp(34))
        self.mod_box = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_x=None)
        self.mod_box.bind(minimum_width=self.mod_box.setter("width"))
        self.mod_scroll.add_widget(self.mod_box)
        self.inspector_view.add_widget(self.mod_scroll)

        search_box = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_y=None, height=dp(36))
        self.txt_custom = TextInput(
            hint_text="Type module (e.g. kivy.uix.switch, sqlite3)...",
            multiline=False,
            font_size="13sp",
            background_color=(0.13, 0.13, 0.19, 1.0),
            foreground_color=(0.95, 0.95, 0.98, 1.0),
        )
        search_box.add_widget(self.txt_custom)

        btn_inspect = Button(
            text="INSPECT",
            size_hint_x=None,
            width=dp(78),
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="11sp",
            always_release=True,
        )
        btn_inspect.bind(on_release=lambda *_a: self.inspect_module(self.txt_custom.text.strip()))
        search_box.add_widget(btn_inspect)

        self.btn_send_builder = Button(
            text="+ BUILDER",
            size_hint_x=None,
            width=dp(84),
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="11sp",
            always_release=True,
        )
        self.btn_send_builder.bind(on_release=self._add_inspected_kivy_module_to_builder)
        search_box.add_widget(self.btn_send_builder)
        self.inspector_view.add_widget(search_box)

        self.doc_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.lbl_details = Label(
            text="Select a module above or type a package name to inspect.",
            font_size="12sp",
            color=(0.85, 0.85, 0.92, 1.0),
            size_hint_y=None,
            halign="left",
            valign="top",
        )
        self.lbl_details.bind(
            width=lambda *x: self.lbl_details.setter("text_size")(self.lbl_details, (self.lbl_details.width, None)),
            texture_size=lambda *x: setattr(self.lbl_details, "height", self.lbl_details.texture_size[1]),
        )
        self.doc_scroll.add_widget(self.lbl_details)
        self.inspector_view.add_widget(self.doc_scroll)

        self.inspected_module_name = ""
        self.set_category(self.active_category)

    def _build_builder_view(self):
        self.builder_view = BoxLayout(orientation="vertical", spacing=dp(8))

        # Palette header + drag chips
        self.builder_view.add_widget(
            Label(
                text="Drag a Kivy component onto the canvas below (or tap to append):",
                font_size="11sp",
                color=(0.65, 0.68, 0.78, 1.0),
                size_hint_y=None,
                height=dp(18),
                halign="left",
            )
        )

        pal_scroll = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint_y=None, height=dp(42))
        pal_box = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_x=None)
        pal_box.bind(minimum_width=pal_box.setter("width"))
        for spec in WIDGET_CATALOG:
            pal_box.add_widget(DraggablePaletteChip(spec, builder_host=self))
        pal_scroll.add_widget(pal_box)
        self.builder_view.add_widget(pal_scroll)

        # Tool title + Test/Edit toggle
        meta_row = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_y=None, height=dp(36))
        self.txt_tool_title = TextInput(
            text="My Custom Deck",
            hint_text="Tool title...",
            multiline=False,
            font_size="13sp",
            background_color=(0.13, 0.13, 0.19, 1.0),
            foreground_color=(0.95, 0.95, 0.98, 1.0),
        )
        meta_row.add_widget(self.txt_tool_title)

        self.btn_test_mode = Button(
            text="▶ TEST",
            size_hint_x=None,
            width=dp(74),
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="11sp",
            always_release=True,
        )
        self.btn_test_mode.bind(on_release=self._toggle_test_mode)
        btn_load_seed = Button(
            text="📂 SEED",
            size_hint_x=None,
            width=dp(72),
            background_normal="",
            background_color=(0.18, 0.20, 0.30, 1.0),
            color=(0.02, 0.71, 0.83, 1.0),
            bold=True,
            font_size="11sp",
            always_release=True,
        )
        btn_load_seed.bind(on_release=self._open_seed_picker)
        meta_row.add_widget(btn_load_seed)
        meta_row.add_widget(self.btn_test_mode)
        self.builder_view.add_widget(meta_row)

        # Canvas Scroll Area
        self.canvas_scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        _card_bg(self.canvas_scroll, (0.06, 0.07, 0.10, 1.0), border_color=(0.20, 0.22, 0.32, 0.8), radius=12)
        self.canvas_list = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10), size_hint_y=None)
        self.canvas_list.bind(minimum_height=self.canvas_list.setter("height"))
        self.canvas_scroll.add_widget(self.canvas_list)
        self.builder_view.add_widget(self.canvas_scroll)

        # Console Output Bar
        self.lbl_console = Label(
            text="Tap any dropped widget to edit its label & attach Python script.",
            font_size="11sp",
            color=(0.02, 0.71, 0.83, 1.0),
            size_hint_y=None,
            height=dp(26),
            halign="left",
            valign="middle",
        )
        self.lbl_console.bind(size=self.lbl_console.setter("text_size"))
        self.builder_view.add_widget(self.lbl_console)

        # Bottom Export Row
        export_row = BoxLayout(orientation="horizontal", spacing=dp(4), size_hint_y=None, height=dp(40))
        btn_code = Button(
            text="👁 CODE",
            size_hint_x=0.18,
            background_normal="",
            background_color=(0.18, 0.20, 0.28, 1.0),
            color=(0.9, 0.95, 1.0, 1.0),
            bold=True,
            font_size="10sp",
            always_release=True,
        )
        btn_code.bind(on_release=self._preview_code)

        btn_save_py = Button(
            text="🐍 .PY",
            size_hint_x=0.20,
            background_normal="",
            background_color=(0.54, 0.36, 0.96, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="10sp",
            always_release=True,
        )
        btn_save_py.bind(on_release=lambda *_a: self.export_to_scratch("py"))

        btn_save_json = Button(
            text="🌱 .JSON",
            size_hint_x=0.21,
            background_normal="",
            background_color=(0.02, 0.71, 0.83, 1.0),
            color=(0.05, 0.05, 0.08, 1.0),
            bold=True,
            font_size="10sp",
            always_release=True,
        )
        btn_save_json.bind(on_release=lambda *_a: self.export_to_scratch("json"))

        btn_deck = Button(
            text="📌 DECK",
            size_hint_x=0.21,
            background_normal="",
            background_color=(0.15, 0.68, 0.38, 1.0),
            color=(1, 1, 1, 1),
            bold=True,
            font_size="10sp",
            always_release=True,
        )
        btn_deck.bind(on_release=lambda *_a: self.export_to_permanent("json"))

        btn_pub = Button(
            text="📡 PUB",
            size_hint_x=0.20,
            background_normal="",
            background_color=(0.95, 0.61, 0.07, 1.0),
            color=(0.05, 0.05, 0.08, 1.0),
            bold=True,
            font_size="10sp",
            always_release=True,
        )
        btn_pub.bind(on_release=self.publish_to_server)

        export_row.add_widget(btn_code)
        export_row.add_widget(btn_save_py)
        export_row.add_widget(btn_save_json)
        export_row.add_widget(btn_deck)
        export_row.add_widget(btn_pub)
        self.builder_view.add_widget(export_row)
        self._container_drop_targets = []

    def _seed_default_nodes(self):
        self.add_node_from_spec(WIDGET_CATALOG[0], render=False)
        self.add_node_from_spec(WIDGET_CATALOG[2], render=False)
        self._render_canvas()

    def on_load(self, host_api):
        self.host = host_api
        if self.host:
            self.host.log("Python Library Explorer & Visual Studio loaded.")

    def set_mode(self, mode):
        self.mode = mode
        self.content_area.clear_widgets()
        if mode == "builder":
            self.content_area.add_widget(self.builder_view)
            self.btn_mode_builder.background_color = (0.54, 0.36, 0.96, 1.0)
            self.btn_mode_builder.color = (1, 1, 1, 1)
            self.btn_mode_inspect.background_color = (0.15, 0.15, 0.22, 1.0)
            self.btn_mode_inspect.color = (0.8, 0.8, 0.9, 1.0)
            self._render_canvas()
        else:
            self.content_area.add_widget(self.inspector_view)
            self.btn_mode_inspect.background_color = (0.02, 0.71, 0.83, 1.0)
            self.btn_mode_inspect.color = (0.05, 0.05, 0.08, 1.0)
            self.btn_mode_builder.background_color = (0.15, 0.15, 0.22, 1.0)
            self.btn_mode_builder.color = (0.8, 0.8, 0.9, 1.0)

    def set_category(self, cat_name):
        self.active_category = cat_name
        for name, btn in self.cat_buttons.items():
            if name == cat_name:
                btn.background_color = (0.02, 0.71, 0.83, 1.0)
                btn.color = (0.05, 0.05, 0.08, 1.0)
            else:
                btn.background_color = (0.15, 0.15, 0.22, 1.0)
                btn.color = (0.8, 0.8, 0.9, 1.0)

        self.mod_box.clear_widgets()
        modules = CATEGORIES.get(cat_name, [])
        for mod in modules:
            btn_mod = Button(
                text=mod,
                size_hint_x=None,
                width=dp(len(mod) * 8 + 20),
                background_normal="",
                background_color=(0.18, 0.22, 0.32, 1.0),
                color=(0.9, 0.95, 1.0, 1.0),
                font_size="11sp",
                always_release=True,
            )
            btn_mod.bind(on_release=lambda _inst, m=mod: self.inspect_module(m))
            self.mod_box.add_widget(btn_mod)

        if modules:
            self.inspect_module(modules[0])

    def inspect_module(self, mod_name):
        if not mod_name:
            return
        self.inspected_module_name = mod_name
        try:
            mod = importlib.import_module(mod_name)
            doc = inspect.getdoc(mod) or "No docstring available."
            classes = [name for name, cls in inspect.getmembers(mod, inspect.isclass) if cls.__module__ == mod.__name__]
            functions = [name for name, fn in inspect.getmembers(mod, inspect.isfunction) if fn.__module__ == mod.__name__]
            file_path = getattr(mod, "__file__", "built-in / frozen")

            report = [
                f"📦 MODULE: {mod_name}",
                f"📁 Location: {file_path}",
                "-" * 46,
                f"📖 DOCSTRING:\n{doc}\n",
                "-" * 46,
                f"🏛️ CLASSES ({len(classes)}):\n" + (", ".join(classes[:30]) if classes else "None declared directly."),
                "\n" + "-" * 46,
                f"⚡ FUNCTIONS ({len(functions)}):\n" + (", ".join(functions[:40]) if functions else "None declared directly."),
            ]
            self.lbl_details.text = "\n".join(report)
        except Exception as e:
            self.lbl_details.text = f"❌ Failed to inspect '{mod_name}':\n\n{str(e)}"

    def _add_inspected_kivy_module_to_builder(self, *_args):
        mod_name = (self.inspected_module_name or "").lower()
        matched = next((s for s in WIDGET_CATALOG if s["kivy_module"] == mod_name), WIDGET_CATALOG[0])
        self.add_node_from_spec(matched)
        self.set_mode("builder")
        self.builder_log(f"Added {matched['kivy_class']} from {mod_name or 'palette'}")

    # --- Drag & Drop Palette Support ---

    def _calc_drop_index(self, pos):
        """Computes insertion slot index inside `self.canvas_list` from screen pos."""
        insert_idx = len(self.nodes)
        if self.canvas_list.children and not self.test_mode:
            local_y = self.canvas_list.to_widget(*pos)[1]
            ordered_cards = list(reversed(self.canvas_list.children))
            for i, card in enumerate(ordered_cards):
                if local_y > card.center_y:
                    return i
        return insert_idx

    def start_palette_drag(self, spec, pos):
        if self.ghost:
            self.remove_widget(self.ghost)
        self.ghost = BuilderGhost(spec)
        self.ghost.pos = (pos[0] - self.ghost.width * 0.5, pos[1] - self.ghost.height * 0.5)
        self.add_widget(self.ghost)

    def move_palette_drag(self, pos):
        if self.ghost:
            self.ghost.pos = (pos[0] - self.ghost.width * 0.5, pos[1] - self.ghost.height * 0.5)

    def end_palette_drag(self, spec, pos):
        if self.ghost:
            self.remove_widget(self.ghost)
            self.ghost = None

        if self.canvas_scroll.collide_point(*pos):
            # Drop inside a nested container card if pointer landed on one (and item isn't itself a container)
            if not spec.get("is_container"):
                for cont_widget, cont_node in getattr(self, "_container_drop_targets", []):
                    if cont_widget.collide_point(*cont_widget.to_widget(*pos)):
                        self.add_node_from_spec(spec, target_list=cont_node.setdefault("children", []))
                        self.builder_log(f"Dropped {spec['kivy_class']} into '{cont_node['label']}'")
                        return

            insert_idx = self._calc_drop_index(pos)
            self.add_node_from_spec(spec, index=insert_idx)
            self.builder_log(f"Dropped {spec['kivy_class']} at slot {insert_idx + 1}")

    def start_card_drag(self, idx, node, pos):
        spec = next((s for s in WIDGET_CATALOG if s["kind"] == node["kind"]), WIDGET_CATALOG[0])
        self.start_palette_drag(spec, pos)

    def end_card_drag(self, src_idx, pos):
        if self.ghost:
            self.remove_widget(self.ghost)
            self.ghost = None
        if not self.canvas_scroll.collide_point(*pos) or not (0 <= src_idx < len(self.nodes)):
            return
        target_idx = self._calc_drop_index(pos)
        if target_idx > src_idx:
            target_idx = max(0, target_idx - 1)
        if target_idx != src_idx:
            item = self.nodes.pop(src_idx)
            self.nodes.insert(min(target_idx, len(self.nodes)), item)
            self._render_canvas()
            self.builder_log(f"Moved '{item['label']}' to slot {target_idx + 1}")

    def add_node_from_spec(self, spec, index=None, render=True, target_list=None):
        node = {
            "kind": spec["kind"],
            "kivy_module": spec["kivy_module"],
            "kivy_class": spec["kivy_class"],
            "lsystem_type": spec["lsystem_type"],
            "is_container": bool(spec.get("is_container", False)),
            "label": spec["default_label"],
            "endpoint": spec["default_endpoint"],
            "script": spec["default_script"],
            "color": spec["color"],
        }
        if node["is_container"]:
            node["children"] = []
        dest = self.nodes if target_list is None else target_list
        if index is None or index >= len(dest):
            dest.append(node)
        else:
            dest.insert(max(0, index), node)
        if render:
            self._render_canvas()
        return node

    def builder_log(self, msg):
        self.lbl_console.text = str(msg)
        if self.host:
            self.host.log(str(msg))

    def _execute_node_script(self, node, widget, value):
        script = (node.get("script") or "").strip()
        if not script:
            return
        env = {
            "widget": widget,
            "value": value,
            "host": self.host,
            "state": self.runtime_state,
            "log": self.builder_log,
            "widget_label": node.get("label", ""),
        }
        try:
            exec(compile(script, f"<builder:{node.get('label', 'node')}>", "exec"), env)
        except Exception as e:
            self.builder_log(f"Script error: {e}")

    def _toggle_test_mode(self, *_args):
        self.test_mode = not self.test_mode
        if self.test_mode:
            self.btn_test_mode.text = "✏️ EDIT"
            self.btn_test_mode.background_color = (0.95, 0.61, 0.07, 1.0)
            self.builder_log("Live Test Mode: tap widgets to run scripts.")
        else:
            self.btn_test_mode.text = "▶ TEST"
            self.btn_test_mode.background_color = (0.15, 0.68, 0.38, 1.0)
            self.builder_log("Edit Mode: tap any widget card to edit script.")
        self._render_canvas()

    def _render_canvas(self):
        self._container_drop_targets = []
        self.canvas_list.clear_widgets()
        if not self.nodes:
            self.canvas_list.add_widget(
                Label(
                    text="Canvas empty — drag or tap a Kivy widget above!",
                    size_hint_y=None,
                    height=dp(64),
                    color=(0.55, 0.55, 0.68, 1.0),
                )
            )
            return

        if self.test_mode:
            for node in self.nodes:
                self.canvas_list.add_widget(self._build_live_widget(node))
            return

        for idx, node in enumerate(self.nodes):
            self.canvas_list.add_widget(self._build_editor_card(idx, node, parent_list=self.nodes, allow_drag=True))

    def _build_editor_card(self, idx, node, parent_list=None, allow_drag=False):
        target_list = self.nodes if parent_list is None else parent_list
        if node.get("is_container") or node.get("kind") in ("row", "grid", "section"):
            outer = BoxLayout(
                orientation="vertical",
                padding=[dp(8), dp(8), dp(8), dp(8)],
                spacing=dp(6),
                size_hint_y=None,
            )
            outer.bind(minimum_height=outer.setter("height"))
            _card_bg(outer, (0.09, 0.11, 0.17, 1.0), border_color=node["color"], radius=12)

            head = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_y=None, height=dp(36))
            if allow_drag:
                head.add_widget(CanvasDragHandle(idx, node, builder_host=self))
            lbl = Label(
                text=f"📦 {node['label']} ({len(node.get('children') or [])})",
                font_size="12sp",
                bold=True,
                color=node["color"],
                halign="left",
                valign="middle",
            )
            lbl.bind(size=lambda inst, _s: setattr(inst, "text_size", (inst.width, None)))
            head.add_widget(lbl)

            btn_add_in = Button(
                text="+BTN",
                size_hint_x=None,
                width=dp(46),
                background_normal="",
                background_color=(0.16, 0.24, 0.34, 1.0),
                color=(0.02, 0.71, 0.83, 1.0),
                font_size="10sp",
                bold=True,
                always_release=True,
            )
            btn_add_in.bind(on_release=lambda *_a, n=node: self.add_node_from_spec(WIDGET_CATALOG[0], target_list=n.setdefault("children", [])))

            btn_del_c = Button(
                text="✕",
                size_hint_x=None,
                width=dp(30),
                background_normal="",
                background_color=(0.35, 0.12, 0.14, 1.0),
                color=(1, 0.6, 0.6, 1),
                font_size="11sp",
                always_release=True,
            )
            btn_del_c.bind(on_release=lambda *_a, i=idx, lst=target_list: self._delete_node(i, lst))
            head.add_widget(btn_add_in)
            head.add_widget(btn_del_c)
            outer.add_widget(head)

            children = node.get("children") or []
            if not children:
                outer.add_widget(
                    Label(
                        text="Drop widgets here (or tap +BTN)",
                        size_hint_y=None,
                        height=dp(30),
                        font_size="11sp",
                        color=(0.55, 0.60, 0.72, 1.0),
                    )
                )
            else:
                for c_idx, child in enumerate(children):
                    outer.add_widget(self._build_editor_card(c_idx, child, parent_list=children, allow_drag=False))

            self._container_drop_targets.append((outer, node))
            return outer

        card = BoxLayout(
            orientation="horizontal",
            padding=[dp(8), dp(6), dp(8), dp(6)],
            spacing=dp(6),
            size_hint_y=None,
            height=dp(60),
        )
        _card_bg(card, (0.11, 0.12, 0.18, 1.0), border_color=node["color"], radius=10)

        btn_edit = Button(
            text=f"{node['label']}\n[size=11sp]{node['kivy_class']} • tap to script[/size]",
            markup=True,
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(0.95, 0.95, 0.98, 1.0),
            halign="left",
            valign="middle",
            bold=True,
            always_release=True,
        )
        btn_edit.bind(size=lambda inst, _s: setattr(inst, "text_size", (inst.width, None)))
        btn_edit.bind(on_release=lambda *_a, n=node: WidgetScriptModal(n, on_save=self._render_canvas).open())
        if allow_drag:
            card.add_widget(CanvasDragHandle(idx, node, builder_host=self))
        card.add_widget(btn_edit)

        btn_up = Button(
            text="▲",
            size_hint_x=None,
            width=dp(30),
            background_normal="",
            background_color=(0.18, 0.20, 0.28, 1.0),
            font_size="11sp",
            always_release=True,
        )
        btn_up.bind(on_release=lambda *_a, i=idx, lst=target_list: self._move_node(i, -1, lst))

        btn_dn = Button(
            text="▼",
            size_hint_x=None,
            width=dp(30),
            background_normal="",
            background_color=(0.18, 0.20, 0.28, 1.0),
            font_size="11sp",
            always_release=True,
        )
        btn_dn.bind(on_release=lambda *_a, i=idx, lst=target_list: self._move_node(i, 1, lst))

        btn_del = Button(
            text="✕",
            size_hint_x=None,
            width=dp(30),
            background_normal="",
            background_color=(0.35, 0.12, 0.14, 1.0),
            color=(1, 0.6, 0.6, 1),
            font_size="12sp",
            always_release=True,
        )
        btn_del.bind(on_release=lambda *_a, i=idx, lst=target_list: self._delete_node(i, lst))

        card.add_widget(btn_up)
        card.add_widget(btn_dn)
        card.add_widget(btn_del)
        return card

    def _build_live_widget(self, node):
        kind = node["kind"]
        label = node.get("label", "Widget")
        if kind == "row":
            row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(58))
            for ch in node.get("children") or []:
                row.add_widget(self._build_live_widget(ch))
            return row
        if kind == "grid":
            grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            for ch in node.get("children") or []:
                grid.add_widget(self._build_live_widget(ch))
            return grid
        if kind == "section":
            sec = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
            sec.bind(minimum_height=sec.setter("height"))
            for ch in node.get("children") or []:
                sec.add_widget(self._build_live_widget(ch))
            return sec
        if kind == "button":
            btn = Button(
                text=label,
                size_hint_y=None,
                height=dp(48),
                background_normal="",
                background_color=node["color"],
                bold=True,
                always_release=True,
            )
            btn.bind(on_release=lambda inst, n=node: self._execute_node_script(n, inst, True))
            return btn
        if kind == "toggle":
            tog = ToggleButton(text=label, size_hint_y=None, height=dp(48), bold=True)
            tog.bind(state=lambda inst, st, n=node: self._execute_node_script(n, inst, st == "down"))
            return tog
        if kind == "slider":
            box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(60))
            box.add_widget(Label(text=label, size_hint_y=None, height=dp(20), font_size="12sp"))
            sld = Slider(min=0, max=100, value=50, size_hint_y=None, height=dp(36))
            sld.bind(value=lambda inst, val, n=node: self._execute_node_script(n, inst, val))
            box.add_widget(sld)
            return box
        if kind == "input":
            inp = TextInput(hint_text=label, multiline=False, size_hint_y=None, height=dp(42))
            inp.bind(on_text_validate=lambda inst, n=node: self._execute_node_script(n, inst, inst.text))
            return inp
        if kind == "gauge":
            box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(44))
            box.add_widget(Label(text=label, size_hint_y=None, height=dp(20), font_size="12sp"))
            box.add_widget(ProgressBar(max=100, value=65, size_hint_y=None, height=dp(18)))
            return box
        return Label(text=label, size_hint_y=None, height=dp(34), bold=True, color=node["color"])

    def _move_node(self, idx, delta, target_list=None):
        lst = self.nodes if target_list is None else target_list
        target = idx + delta
        if 0 <= target < len(lst):
            lst[idx], lst[target] = lst[target], lst[idx]
            self._render_canvas()

    def _delete_node(self, idx, target_list=None):
        lst = self.nodes if target_list is None else target_list
        if 0 <= idx < len(lst):
            del lst[idx]
            self._render_canvas()

    def _preview_code(self, *_args):
        title = self.txt_tool_title.text.strip() or "Visual Kivy Tool"
        py_code = generate_python_module_code(self.nodes, title=title)
        seed_json = json.dumps(generate_lsystem_seed_data(self.nodes, title=title), indent=2)
        combined = f"# === PYTHON OpenHubModule ===\n{py_code}\n\n# === L-SYSTEM SEED.JSON ===\n{seed_json}"
        CodePreviewModal("Generated Python & L-System Seed", combined).open()

    def _open_seed_picker(self, *_args):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        entries = []
        mods_dir = os.path.join(root_dir, "modules")
        if os.path.isdir(mods_dir):
            for name in sorted(os.listdir(mods_dir)):
                seed_p = os.path.join(mods_dir, name, "seed.json")
                if os.path.isfile(seed_p):
                    entries.append((f"🌱 {name}", seed_p))
            scratch_dir = os.path.join(mods_dir, "scratch")
            if os.path.isdir(scratch_dir):
                for fname in sorted(os.listdir(scratch_dir)):
                    if fname.endswith(".json"):
                        entries.append((f"🧪 {fname}", os.path.join(scratch_dir, fname)))
        LoadSeedModal(entries, on_select=self.load_seed_file).open()

    def load_seed_file(self, seed_path):
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                seed_data = json.load(f)
            imported = extract_nodes_from_seed(seed_data)
            if imported:
                self.nodes = imported
                if seed_data.get("title"):
                    self.txt_tool_title.text = str(seed_data["title"])
                self.test_mode = False
                self._render_canvas()
                self.builder_log(f"Loaded {len(imported)} nodes from {os.path.basename(seed_path)}")
        except Exception as e:
            self.builder_log(f"Seed load error: {e}")

    def export_to_permanent(self, fmt="json"):
        desc = self.export_to_scratch(fmt=fmt)
        if not desc:
            return None
        title = self.txt_tool_title.text.strip() or "Visual Kivy Tool"
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            from core.module_manager import ModuleManager
            mgr = ModuleManager(root_dir)
            perm = mgr.promote_to_permanent(desc, title, category="Field" if fmt == "json" else "Tools")
            mgr.delete(desc)
            self._notify_refresh()
            self.builder_log(f"Saved permanent '{perm.name}' to Deck!")
            return perm
        except Exception as e:
            self.builder_log(f"Deck save error: {e}")
            return None

    @staticmethod
    def _notify_refresh():
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, "refresh_modules"):
                Clock.schedule_once(lambda _dt: app.refresh_modules(), 0)
        except Exception:
            pass

    def export_to_scratch(self, fmt="py"):
        title = self.txt_tool_title.text.strip() or "Visual Kivy Tool"
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            from core.module_manager import ModuleManager
            mgr = ModuleManager(root_dir)
            if fmt == "json":
                payload = json.dumps(generate_lsystem_seed_data(self.nodes, title=title), indent=2)
                desc = mgr.create_scratch(payload, prompt=title, extension=".json")
            else:
                payload = generate_python_module_code(self.nodes, title=title)
                desc = mgr.create_scratch(payload, prompt=title, extension=".py")
            self.builder_log(f"Saved to Scratch: {os.path.basename(desc.entrypoint)}")
            self._notify_refresh()
            return desc
        except Exception as e:
            self.builder_log(f"Export error: {e}")
            return None

    def publish_to_server(self, *_args):
        perm = self.export_to_permanent(fmt="json")
        if not perm:
            return
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            from core.module_manager import ModuleManager
            from core.updater import UpdateManager
            mgr = ModuleManager(root_dir)
            server_host = UpdateManager(root_dir).load_server_host()
            self.builder_log(f"Publishing '{perm.name}' to {server_host}...")

            def _cb(ok, url, err):
                if ok:
                    self.builder_log(f"Published '{perm.name}' to PC/GitHub!")
                else:
                    self.builder_log(f"Publish error: {err}")

            mgr.publish_module(perm, server_host=server_host, callback=_cb)
        except Exception as e:
            self.builder_log(f"Publish error: {e}")
