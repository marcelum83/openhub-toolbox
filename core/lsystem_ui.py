"""
OpenHub L-System Generative UI Engine
Recursively transforms declarative JSON hardware "seeds" (axioms) into live,
interactive Kivy widget trees via registered production rules.
"""
import copy
import json
import math
import os
import random
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget

from ui.themes import ColorSystem


def _bind_card_bg(widget, bg_color, border_color=None, radius=10):
    """Draws a rounded surface background and optional border onto a widget."""
    with widget.canvas.before:
        bg_c = Color(*bg_color)
        bg_rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
        border_c = None
        border_line = None
        if border_color is not None:
            border_c = Color(*border_color)
            border_line = Line(
                rounded_rectangle=(widget.x, widget.y, widget.width, widget.height, dp(radius)),
                width=1.1,
            )

    def _sync(*_args):
        bg_rect.pos = widget.pos
        bg_rect.size = widget.size
        if border_line is not None:
            border_line.rounded_rectangle = (
                widget.x,
                widget.y,
                widget.width,
                widget.height,
                dp(radius),
            )

    widget.bind(pos=_sync, size=_sync)
    return bg_c, border_c


def _resolve_endpoint(endpoint, base_url=None):
    """Resolves a full URL or relative path against an optional base_url."""
    if not endpoint:
        return None
    if endpoint.startswith(("http://", "https://")):
        return endpoint
    if base_url:
        return urllib.parse.urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))
    return endpoint


def _http_request(url, method="GET", payload=None, timeout=1.5):
    """Performs a synchronous HTTP request (intended for worker threads)."""
    data = None
    headers = {"User-Agent": "OpenHub-LSystem/1.0"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace").strip()
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"value": raw}


def _extract_value(response_obj, value_key="value"):
    """Extracts a scalar readout from a decoded HTTP payload."""
    if isinstance(response_obj, dict):
        if value_key in response_obj:
            return response_obj[value_key]
        for fallback_key in ("value", "reading", "state", "status", "data"):
            if fallback_key in response_obj:
                return response_obj[fallback_key]
        if len(response_obj) == 1:
            return next(iter(response_obj.values()))
        return json.dumps(response_obj)
    return response_obj


def _substitute_params(obj, params):
    """Recursively substitutes `$key` placeholders in strings inside dicts/lists."""
    if not params:
        return obj
    if isinstance(obj, str):
        def _repl(match):
            key = match.group(1)
            return str(params[key]) if key in params else match.group(0)
        return re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", _repl, obj)
    if isinstance(obj, list):
        return [_substitute_params(item, params) for item in obj]
    if isinstance(obj, dict):
        return {k: _substitute_params(v, params) for k, v in obj.items()}
    return obj


def expand_seed(node, rules=None, depth=0, max_generations=8):
    """
    Expands parametric L-system rules, `symbol` macros, and `repeat`/`items`
    templates into a concrete widget-tree seed dictionary.
    """
    if depth > max_generations:
        return node
    if isinstance(node, list):
        out = []
        for item in node:
            expanded = expand_seed(item, rules=rules, depth=depth, max_generations=max_generations)
            if isinstance(expanded, list):
                out.extend(expanded)
            elif expanded is not None:
                out.append(expanded)
        return out
    if not isinstance(node, dict):
        return node

    active_rules = dict(rules or {})
    if isinstance(node.get("rules"), dict):
        active_rules.update(node["rules"])

    # 1. Symbol macro expansion: {"symbol": "relay_card", "params": {"i": 1}}
    sym = node.get("symbol")
    if sym and sym in active_rules:
        template = copy.deepcopy(active_rules[sym])
        params = dict(node.get("params") or {})
        merged = _substitute_params(template, params)
        if isinstance(merged, dict):
            for k, v in node.items():
                if k not in ("symbol", "params", "rules"):
                    merged.setdefault(k, v)
        return expand_seed(merged, rules=active_rules, depth=depth + 1, max_generations=max_generations)

    result = copy.deepcopy(node)

    # 2. Parametric repeat / items expansion on containers
    children = list(result.get("children") or [])
    if "template" in result and ("repeat" in result or "items" in result):
        tpl = result.pop("template")
        if "items" in result and isinstance(result["items"], list):
            items = result.pop("items")
            start = int(result.pop("start", 1))
            for idx, item_val in enumerate(items):
                p = {"idx": idx, "i": start + idx, "item": item_val}
                if isinstance(item_val, dict):
                    p.update(item_val)
                children.append(_substitute_params(copy.deepcopy(tpl), p))
        else:
            count = max(0, min(64, int(result.pop("repeat", 0))))
            start = int(result.pop("start", 1))
            for idx in range(count):
                p = {"idx": idx, "i": start + idx}
                children.append(_substitute_params(copy.deepcopy(tpl), p))

    if children or "children" in result:
        result["children"] = expand_seed(children, rules=active_rules, depth=depth + 1, max_generations=max_generations)

    return result


def evaluate_hysteresis(reading, currently_triggered, operator, threshold, hysteresis=0.0):
    """
    Evaluates a threshold condition with hysteresis to prevent relay chatter.
    Supported operators: '<', '<=', '>', '>='.
    """
    val = float(reading)
    thresh = float(threshold)
    hyst = max(0.0, float(hysteresis))

    eps = 1e-9
    if operator in ("<", "<="):
        trigger = val < thresh if operator == "<" else val <= thresh
        clear = (val + eps) >= (thresh + hyst) if operator == "<" else val > (thresh + hyst + eps)
    elif operator in (">", ">="):
        trigger = val > thresh if operator == ">" else val >= thresh
        clear = (val - eps) <= (thresh - hyst) if operator == ">" else val < (thresh - hyst - eps)
    else:
        return False

    if currently_triggered:
        return not clear
    return trigger


def _attach_sensor_poller(ctx, data, fallback_key, on_reading):
    """
    Shared async HTTP GET + offline simulation poller for sensor-backed widgets.
    Calls `on_reading(value, is_sim=bool, offline=bool)` on the Kivy main thread.
    """
    value_key = data.get("value_key", "value")
    raw_ep = data.get("data_endpoint") or data.get("sensor_endpoint")
    endpoint = _resolve_endpoint(raw_ep, ctx.base_url)
    sim_key = data.get("sim_key") or endpoint or fallback_key
    in_flight = {"busy": False}

    def _poll(_dt):
        if not ctx._alive or in_flight["busy"]:
            return
        if ctx.force_sim or not endpoint:
            val = ctx.next_simulated_value(sim_key, data)
            ctx.report_mode("SIM")
            on_reading(val, is_sim=True, offline=False)
            return

        in_flight["busy"] = True

        def _worker():
            try:
                resp = _http_request(endpoint, method="GET", timeout=1.2)
                val = _extract_value(resp, value_key=value_key)
                try:
                    val = float(val) if not isinstance(val, (bool, int, float)) else val
                except (TypeError, ValueError):
                    pass

                def _apply(_dt2):
                    in_flight["busy"] = False
                    if ctx._alive:
                        ctx.report_mode("LIVE")
                        on_reading(val, is_sim=False, offline=False)

                Clock.schedule_once(_apply, 0)
            except Exception:
                def _fallback(_dt2):
                    in_flight["busy"] = False
                    if not ctx._alive:
                        return
                    if ctx.simulate_offline:
                        val = ctx.next_simulated_value(sim_key, data)
                        ctx.report_mode("SIM")
                        on_reading(val, is_sim=True, offline=False)
                    else:
                        ctx.report_mode("OFFLINE")
                        on_reading(None, is_sim=False, offline=True)

                Clock.schedule_once(_fallback, 0)

        threading.Thread(target=_worker, daemon=True).start()

    ctx.register_poller(data.get("poll_interval", ctx.default_poll), _poll)


class LSystemContext:
    """Shared runtime context passed through recursive production rule expansion."""

    def __init__(
        self,
        host_api=None,
        base_url=None,
        simulate_offline=True,
        force_sim=False,
        default_poll=2.5,
        visited_seed_urls=None,
    ):
        self.host_api = host_api
        self.base_url = base_url
        self.simulate_offline = simulate_offline
        self.force_sim = force_sim
        self.default_poll = float(default_poll)
        self.visited_seed_urls = set(visited_seed_urls or ())
        self.sim_state = {}
        self._poll_specs = []
        self._scheduled_events = []
        self._cleanup_callbacks = []
        self._status_listeners = []
        self._child_contexts = []
        self._last_mode = "SIM" if force_sim else "LIVE"
        self._alive = False

    def create_child(self, base_url=None, simulate_offline=None, default_poll=None, seed_url=None):
        """Creates a lifecycle-linked child context for a docked remote node."""
        visited = set(self.visited_seed_urls)
        if seed_url:
            visited.add(seed_url)
        child = LSystemContext(
            host_api=self.host_api,
            base_url=base_url if base_url is not None else self.base_url,
            simulate_offline=self.simulate_offline if simulate_offline is None else simulate_offline,
            force_sim=self.force_sim,
            default_poll=self.default_poll if default_poll is None else default_poll,
            visited_seed_urls=visited,
        )
        for listener in self._status_listeners:
            child.add_status_listener(listener)
        self._child_contexts.append(child)
        return child

    def register_poller(self, interval, callback):
        """Registers a periodic callback managed by the root widget lifecycle."""
        self._poll_specs.append((max(0.4, float(interval)), callback))

    def register_cleanup(self, callback):
        """Registers a cleanup callback invoked on pause/unload."""
        self._cleanup_callbacks.append(callback)

    def add_status_listener(self, callback):
        """Subscribes to transport mode changes ('LIVE', 'SIM', 'OFFLINE')."""
        self._status_listeners.append(callback)

    def report_mode(self, mode):
        if mode == self._last_mode:
            return
        self._last_mode = mode
        for cb in list(self._status_listeners):
            try:
                cb(mode)
            except Exception:
                pass

    def start(self):
        """Starts all registered polling schedules and docked child contexts."""
        self.stop()
        self._alive = True
        for interval, cb in self._poll_specs:
            # Fire an immediate initial read, then schedule interval
            ev_once = Clock.schedule_once(lambda _dt, fn=cb: fn(0), 0.05)
            ev_int = Clock.schedule_interval(cb, interval)
            self._scheduled_events.extend([ev_once, ev_int])
        for child in list(self._child_contexts):
            child.force_sim = self.force_sim
            child.start()

    def stop(self):
        """Stops all active polling schedules, docked child contexts, and pending timers."""
        self._alive = False
        for child in list(self._child_contexts):
            child.stop()
        for ev in self._scheduled_events:
            try:
                ev.cancel()
            except Exception:
                pass
        self._scheduled_events.clear()
        for cb in list(self._cleanup_callbacks):
            try:
                cb()
            except Exception:
                pass

    def next_simulated_value(self, key, data):
        """Produces smooth deterministic-plus-jitter simulated telemetry."""
        if key in self.sim_state:
            val = self.sim_state[key]
            if isinstance(val, (int, float)):
                lo, hi = data.get("sim_range", [val * 0.95, val * 1.05])
                span = max(0.01, float(hi) - float(lo))
                drift = math.sin(time.time() * 0.7 + hash(key) % 10) * (span * 0.04)
                jitter = random.uniform(-span * 0.02, span * 0.02)
                nxt = max(float(lo), min(float(hi), float(val) + drift + jitter))
                self.sim_state[key] = nxt
                return nxt
            return val

        if "sim_value" in data:
            val = data["sim_value"]
        elif "sim_range" in data and len(data["sim_range"]) >= 2:
            lo, hi = float(data["sim_range"][0]), float(data["sim_range"][1])
            val = (lo + hi) / 2.0
        else:
            val = 0.0
        self.sim_state[key] = val
        return val


class UI_Rules:
    """Built-in Kivy production rules for L-system hardware seeds."""

    @staticmethod
    def _build_children_into(layout, children, grow_function, ctx, depth):
        for child_seed in children:
            child_widget = grow_function(child_seed, ctx=ctx, depth=depth + 1)
            if child_widget is not None:
                layout.add_widget(child_widget)

    @staticmethod
    def build_container(data, grow_function, ctx, depth=0):
        """Generates a vertical card container and recursively grows children inside it."""
        is_root = depth == 0
        box = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(12), dp(12), dp(12), dp(12)],
            size_hint_y=None,
        )
        box.bind(minimum_height=box.setter("height"))

        bg = ColorSystem.BG_DARK if is_root else ColorSystem.SURFACE
        border = None if is_root else ColorSystem.SURFACE_BORDER
        _bind_card_bg(box, bg, border_color=border, radius=12)

        title = data.get("title")
        subtitle = data.get("subtitle")
        if title:
            header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(8))
            lbl_title = Label(
                text=str(title),
                font_size="16sp" if is_root else "14sp",
                bold=True,
                color=ColorSystem.PRIMARY if is_root else ColorSystem.TEXT_PRIMARY,
                halign="left",
                valign="middle",
            )
            lbl_title.bind(size=lbl_title.setter("text_size"))
            header.add_widget(lbl_title)

            if subtitle:
                lbl_sub = Label(
                    text=str(subtitle),
                    font_size="11sp",
                    color=ColorSystem.TEXT_MUTED,
                    halign="right",
                    valign="middle",
                    size_hint_x=0.55,
                )
                lbl_sub.bind(size=lbl_sub.setter("text_size"))
                header.add_widget(lbl_sub)

            box.add_widget(header)

        UI_Rules._build_children_into(box, data.get("children", []), grow_function, ctx, depth)
        return box

    @staticmethod
    def build_row(data, grow_function, ctx, depth=0):
        """Generates a horizontal row container and recursively grows children inside it."""
        row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(data.get("height", 84)),
        )
        for child_seed in data.get("children", []):
            child_widget = grow_function(child_seed, ctx=ctx, depth=depth + 1)
            if child_widget is not None:
                # Allow side-by-side children to fill the row height cleanly
                if child_widget.size_hint_y is None and child_widget.height < row.height:
                    child_widget.size_hint_y = 1
                row.add_widget(child_widget)
        return row

    @staticmethod
    def build_grid(data, grow_function, ctx, depth=0):
        """Generates a multi-column grid container and recursively grows children inside it."""
        cols = max(1, int(data.get("cols", 2)))
        grid = GridLayout(
            cols=cols,
            spacing=dp(8),
            size_hint_y=None,
        )
        grid.bind(minimum_height=grid.setter("height"))
        UI_Rules._build_children_into(grid, data.get("children", []), grow_function, ctx, depth)
        return grid

    @staticmethod
    def build_sensor(data, ctx):
        """Generates a passive async-polled sensor readout card."""
        card = BoxLayout(
            orientation="vertical",
            padding=[dp(10), dp(8), dp(10), dp(8)],
            spacing=dp(2),
            size_hint_y=None,
            height=dp(72),
        )
        _bind_card_bg(card, ColorSystem.SURFACE_HOVER, ColorSystem.SURFACE_BORDER, radius=10)

        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(20))
        lbl_name = Label(
            text=str(data.get("label", "Sensor")),
            font_size="12sp",
            color=ColorSystem.TEXT_MUTED,
            halign="left",
            valign="middle",
        )
        lbl_name.bind(size=lbl_name.setter("text_size"))

        lbl_badge = Label(
            text="...",
            font_size="10sp",
            bold=True,
            color=ColorSystem.TEXT_HINT,
            halign="right",
            valign="middle",
            size_hint_x=None,
            width=dp(56),
        )
        lbl_badge.bind(size=lbl_badge.setter("text_size"))
        top.add_widget(lbl_name)
        top.add_widget(lbl_badge)

        lbl_val = Label(
            text="--",
            font_size="20sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            halign="left",
            valign="middle",
        )
        lbl_val.bind(size=lbl_val.setter("text_size"))

        card.add_widget(top)
        card.add_widget(lbl_val)

        unit = data.get("unit", "")
        precision = int(data.get("precision", 1))
        warn_low = data.get("warn_low")
        warn_high = data.get("warn_high")

        def _render_value(raw_val, is_sim=False, offline=False):
            if offline:
                lbl_val.text = "OFFLINE"
                lbl_val.color = ColorSystem.DANGER
                lbl_badge.text = "ERR"
                lbl_badge.color = ColorSystem.DANGER
                return

            display_val = raw_val
            val_color = ColorSystem.PRIMARY
            if isinstance(raw_val, bool):
                display_val = "ON" if raw_val else "OFF"
                val_color = ColorSystem.SUCCESS if raw_val else ColorSystem.TEXT_MUTED
            elif isinstance(raw_val, (int, float)):
                display_val = f"{raw_val:.{precision}f}" if isinstance(raw_val, float) or precision > 0 else str(raw_val)
                if warn_low is not None and raw_val < float(warn_low):
                    val_color = ColorSystem.WARNING
                elif warn_high is not None and raw_val > float(warn_high):
                    val_color = ColorSystem.DANGER
                else:
                    val_color = ColorSystem.SUCCESS if data.get("accent") == "success" else ColorSystem.PRIMARY

            suffix = f" {unit}".rstrip() if unit else ""
            lbl_val.text = f"{display_val}{suffix}" if suffix else str(display_val)
            lbl_val.color = val_color
            lbl_badge.text = "SIM" if is_sim else "LIVE"
            lbl_badge.color = ColorSystem.WARNING if is_sim else ColorSystem.SUCCESS

        _attach_sensor_poller(ctx, data, f"sensor:{data.get('label', id(card))}", _render_value)
        return card

    @staticmethod
    def build_actuator_slider(data, ctx):
        """Generates a debounced slider control bound to an HTTP control endpoint."""
        min_val, max_val = data.get("range", [0, 100])
        step = float(data.get("step", 1))
        initial = float(data.get("initial", min_val))
        unit = data.get("unit", "")
        label_txt = str(data.get("label", "Control"))
        endpoint = _resolve_endpoint(data.get("control_endpoint"), ctx.base_url)
        method = data.get("method", "POST")
        payload_key = data.get("payload_key", "value")
        sim_key = data.get("sim_key") or endpoint or f"slider:{label_txt}"

        card = BoxLayout(
            orientation="vertical",
            padding=[dp(10), dp(8), dp(10), dp(8)],
            spacing=dp(4),
            size_hint_y=None,
            height=dp(84),
        )
        _bind_card_bg(card, ColorSystem.SURFACE_HOVER, ColorSystem.SURFACE_BORDER, radius=10)

        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(24))
        lbl_name = Label(
            text=label_txt,
            font_size="13sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            halign="left",
            valign="middle",
        )
        lbl_name.bind(size=lbl_name.setter("text_size"))

        def _fmt(v):
            num = f"{int(round(v))}" if step >= 1 else f"{v:.1f}"
            return f"{num}{unit}"

        lbl_val = Label(
            text=_fmt(initial),
            font_size="13sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            halign="right",
            valign="middle",
            size_hint_x=None,
            width=dp(84),
        )
        lbl_val.bind(size=lbl_val.setter("text_size"))
        top.add_widget(lbl_name)
        top.add_widget(lbl_val)

        slider = Slider(
            min=float(min_val),
            max=float(max_val),
            step=step,
            value=initial,
            cursor_size=(dp(20), dp(20)),
        )
        card.add_widget(top)
        card.add_widget(slider)

        pending_ev = {"ev": None}

        def _dispatch(val):
            ctx.sim_state[sim_key] = val
            if ctx.force_sim or not endpoint:
                ctx.report_mode("SIM")
                lbl_val.text = f"{_fmt(val)} [SIM]"
                return

            def _worker():
                try:
                    _http_request(endpoint, method=method, payload={payload_key: val}, timeout=1.5)
                    Clock.schedule_once(lambda _dt: _on_done(True), 0)
                except Exception:
                    Clock.schedule_once(lambda _dt: _on_done(False), 0)

            def _on_done(ok):
                if not ctx._alive:
                    return
                if ok:
                    ctx.report_mode("LIVE")
                    lbl_val.text = _fmt(val)
                    lbl_val.color = ColorSystem.PRIMARY
                elif ctx.simulate_offline:
                    ctx.report_mode("SIM")
                    lbl_val.text = f"{_fmt(val)} [SIM]"
                    lbl_val.color = ColorSystem.WARNING
                else:
                    ctx.report_mode("OFFLINE")
                    lbl_val.text = f"{_fmt(val)} [ERR]"
                    lbl_val.color = ColorSystem.DANGER

            threading.Thread(target=_worker, daemon=True).start()

        def _on_value(_inst, val):
            lbl_val.text = _fmt(val)
            if pending_ev["ev"] is not None:
                pending_ev["ev"].cancel()
            pending_ev["ev"] = Clock.schedule_once(lambda _dt, v=val: _dispatch(v), 0.12)

        def _cleanup():
            if pending_ev["ev"] is not None:
                pending_ev["ev"].cancel()
                pending_ev["ev"] = None

        slider.bind(value=_on_value)
        ctx.register_cleanup(_cleanup)
        return card

    @staticmethod
    def build_actuator_toggle(data, ctx):
        """Generates a stateful ON/OFF toggle button bound to an HTTP endpoint."""
        label_txt = str(data.get("label", "Switch"))
        on_label = str(data.get("on_label", "ON"))
        off_label = str(data.get("off_label", "OFF"))
        endpoint = _resolve_endpoint(data.get("control_endpoint"), ctx.base_url)
        method = data.get("method", "POST")
        payload_key = data.get("payload_key", "state")
        sim_key = data.get("sim_key") or endpoint or f"toggle:{label_txt}"
        state = {"active": bool(data.get("initial", False))}

        row = BoxLayout(
            orientation="horizontal",
            padding=[dp(10), dp(8), dp(10), dp(8)],
            spacing=dp(10),
            size_hint_y=None,
            height=dp(58),
        )
        _bind_card_bg(row, ColorSystem.SURFACE_HOVER, ColorSystem.SURFACE_BORDER, radius=10)

        lbl = Label(
            text=label_txt,
            font_size="14sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            halign="left",
            valign="middle",
        )
        lbl.bind(size=lbl.setter("text_size"))

        btn = Button(
            text=on_label if state["active"] else off_label,
            size_hint_x=None,
            width=dp(96),
            background_normal="",
            bold=True,
            font_size="13sp",
        )

        def _paint(suffix=""):
            is_on = state["active"]
            btn.text = f"{on_label if is_on else off_label}{suffix}"
            btn.background_color = ColorSystem.SUCCESS if is_on else ColorSystem.SURFACE
            btn.color = ColorSystem.TEXT_PRIMARY if is_on else ColorSystem.TEXT_MUTED

        _paint()

        def _on_press(_inst):
            next_state = not state["active"]
            state["active"] = next_state
            ctx.sim_state[sim_key] = next_state
            if ctx.force_sim or not endpoint:
                ctx.report_mode("SIM")
                _paint(" •")
                return

            btn.text = "..."

            def _worker():
                try:
                    _http_request(endpoint, method=method, payload={payload_key: next_state}, timeout=1.5)
                    Clock.schedule_once(lambda _dt: _finish(True), 0)
                except Exception:
                    Clock.schedule_once(lambda _dt: _finish(False), 0)

            def _finish(ok):
                if not ctx._alive:
                    return
                if ok:
                    ctx.report_mode("LIVE")
                    _paint("")
                elif ctx.simulate_offline:
                    ctx.report_mode("SIM")
                    _paint(" •")
                else:
                    ctx.report_mode("OFFLINE")
                    state["active"] = not next_state
                    _paint(" !")

            threading.Thread(target=_worker, daemon=True).start()

        btn.bind(on_release=_on_press)
        row.add_widget(lbl)
        row.add_widget(btn)
        return row

    @staticmethod
    def build_action_button(data, ctx):
        """Generates a one-shot action trigger button bound to an HTTP endpoint."""
        label_txt = str(data.get("label", "Trigger"))
        endpoint = _resolve_endpoint(data.get("control_endpoint"), ctx.base_url)
        method = data.get("method", "POST")
        payload = data.get("payload", {"action": "trigger"})
        tone = data.get("tone", "primary")
        tone_map = {
            "primary": ColorSystem.PRIMARY,
            "secondary": ColorSystem.SECONDARY,
            "success": ColorSystem.SUCCESS,
            "warning": ColorSystem.WARNING,
            "danger": ColorSystem.DANGER,
        }
        btn_bg = tone_map.get(tone, ColorSystem.PRIMARY)

        btn = Button(
            text=label_txt,
            size_hint_y=None,
            height=dp(46),
            background_normal="",
            background_color=btn_bg,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="13sp",
        )

        def _on_press(_inst):
            if ctx.force_sim or not endpoint:
                ctx.report_mode("SIM")
                btn.text = f"{label_txt} [SIM ✓]"
                Clock.schedule_once(lambda _dt: setattr(btn, "text", label_txt), 1.0)
                return

            btn.text = f"{label_txt} ..."

            def _worker():
                try:
                    _http_request(endpoint, method=method, payload=payload, timeout=1.5)
                    Clock.schedule_once(lambda _dt: _done(True), 0)
                except Exception:
                    Clock.schedule_once(lambda _dt: _done(False), 0)

            def _done(ok):
                if not ctx._alive:
                    return
                if ok:
                    ctx.report_mode("LIVE")
                    btn.text = f"{label_txt} ✓"
                elif ctx.simulate_offline:
                    ctx.report_mode("SIM")
                    btn.text = f"{label_txt} [SIM ✓]"
                else:
                    ctx.report_mode("OFFLINE")
                    btn.text = f"{label_txt} [ERR]"
                Clock.schedule_once(lambda _dt: setattr(btn, "text", label_txt), 1.2)

            threading.Thread(target=_worker, daemon=True).start()

        btn.bind(on_release=_on_press)
        return btn

    @staticmethod
    def build_status_banner(data, ctx):
        """Generates a compact informational banner or note block."""
        box = BoxLayout(
            orientation="horizontal",
            padding=[dp(10), dp(8), dp(10), dp(8)],
            size_hint_y=None,
            height=dp(42),
        )
        _bind_card_bg(box, ColorSystem.SURFACE, ColorSystem.SURFACE_BORDER, radius=8)
        lbl = Label(
            text=str(data.get("text") or data.get("label") or ""),
            font_size="12sp",
            color=ColorSystem.TEXT_MUTED,
            halign="left",
            valign="middle",
        )
        lbl.bind(size=lbl.setter("text_size"))
        box.add_widget(lbl)
        return box

    @staticmethod
    def build_gauge_bar(data, ctx):
        """Generates a horizontal progress gauge bar bound to a sensor endpoint."""
        min_val, max_val = data.get("range", [0, 100])
        min_val, max_val = float(min_val), float(max_val)
        span = max(1e-6, max_val - min_val)
        unit = data.get("unit", "%")
        precision = int(data.get("precision", 0))
        warn_low = data.get("warn_low")
        warn_high = data.get("warn_high")

        card = BoxLayout(
            orientation="vertical",
            padding=[dp(10), dp(8), dp(10), dp(10)],
            spacing=dp(6),
            size_hint_y=None,
            height=dp(64),
        )
        _bind_card_bg(card, ColorSystem.SURFACE_HOVER, ColorSystem.SURFACE_BORDER, radius=10)

        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(20))
        lbl_name = Label(
            text=str(data.get("label", "Level")),
            font_size="12sp",
            bold=True,
            color=ColorSystem.TEXT_MUTED,
            halign="left",
            valign="middle",
        )
        lbl_name.bind(size=lbl_name.setter("text_size"))

        lbl_val = Label(
            text="--",
            font_size="13sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            halign="right",
            valign="middle",
            size_hint_x=None,
            width=dp(96),
        )
        lbl_val.bind(size=lbl_val.setter("text_size"))
        top.add_widget(lbl_name)
        top.add_widget(lbl_val)

        track = Widget(size_hint_y=None, height=dp(14))
        ratio_state = {"ratio": 0.0, "color": ColorSystem.PRIMARY}
        with track.canvas:
            Color(*ColorSystem.BG_DARK)
            track_bg = RoundedRectangle(pos=track.pos, size=track.size, radius=[dp(7)])
            fill_c = Color(*ColorSystem.PRIMARY)
            fill_rect = RoundedRectangle(pos=track.pos, size=(0, track.height), radius=[dp(7)])

        def _redraw(*_args):
            track_bg.pos = track.pos
            track_bg.size = track.size
            fill_c.rgba = ratio_state["color"]
            fill_w = max(0.0, min(1.0, ratio_state["ratio"])) * track.width
            fill_rect.pos = track.pos
            fill_rect.size = (fill_w, track.height)

        track.bind(pos=_redraw, size=_redraw)
        card.add_widget(top)
        card.add_widget(track)

        def _on_reading(raw_val, is_sim=False, offline=False):
            if offline or not isinstance(raw_val, (int, float)):
                lbl_val.text = "OFFLINE" if offline else str(raw_val)
                lbl_val.color = ColorSystem.DANGER if offline else ColorSystem.TEXT_MUTED
                ratio_state["ratio"] = 0.0
                ratio_state["color"] = ColorSystem.DANGER
                _redraw()
                return

            pct = max(0.0, min(1.0, (float(raw_val) - min_val) / span))
            bar_color = ColorSystem.PRIMARY
            if warn_low is not None and raw_val < float(warn_low):
                bar_color = ColorSystem.WARNING
            elif warn_high is not None and raw_val > float(warn_high):
                bar_color = ColorSystem.DANGER
            elif data.get("accent") == "success":
                bar_color = ColorSystem.SUCCESS

            num_str = f"{raw_val:.{precision}f}" if precision > 0 else f"{int(round(raw_val))}"
            suffix = f" {unit}".rstrip() if unit else ""
            sim_tag = " [SIM]" if is_sim else ""
            lbl_val.text = f"{num_str}{suffix}{sim_tag}"
            lbl_val.color = bar_color
            ratio_state["ratio"] = pct
            ratio_state["color"] = bar_color
            _redraw()

        _attach_sensor_poller(ctx, data, f"gauge:{data.get('label', id(card))}", _on_reading)
        return card

    @staticmethod
    def build_sparkline_chart(data, ctx):
        """Generates a rolling real-time sparkline chart bound to a sensor endpoint."""
        max_points = max(5, int(data.get("max_points", 30)))
        unit = data.get("unit", "")
        precision = int(data.get("precision", 1))
        line_color = ColorSystem.SUCCESS if data.get("accent") == "success" else ColorSystem.PRIMARY
        history = []

        card = BoxLayout(
            orientation="vertical",
            padding=[dp(10), dp(8), dp(10), dp(10)],
            spacing=dp(6),
            size_hint_y=None,
            height=dp(118),
        )
        _bind_card_bg(card, ColorSystem.SURFACE_HOVER, ColorSystem.SURFACE_BORDER, radius=10)

        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(22))
        lbl_name = Label(
            text=str(data.get("label", "Telemetry Trend")),
            font_size="12sp",
            bold=True,
            color=ColorSystem.TEXT_MUTED,
            halign="left",
            valign="middle",
        )
        lbl_name.bind(size=lbl_name.setter("text_size"))

        lbl_val = Label(
            text="--",
            font_size="14sp",
            bold=True,
            color=line_color,
            halign="right",
            valign="middle",
            size_hint_x=None,
            width=dp(110),
        )
        lbl_val.bind(size=lbl_val.setter("text_size"))
        top.add_widget(lbl_name)
        top.add_widget(lbl_val)

        plot = Widget()
        with plot.canvas:
            Color(*ColorSystem.BG_DARK)
            plot_bg = RoundedRectangle(pos=plot.pos, size=plot.size, radius=[dp(6)])
            Color(line_color[0], line_color[1], line_color[2], 0.25)
            mid_line = Line(points=[], width=1.0)
            spark_c = Color(*line_color)
            spark_line = Line(points=[], width=1.8)

        def _redraw(*_args):
            plot_bg.pos = plot.pos
            plot_bg.size = plot.size
            if plot.width <= 4 or plot.height <= 4:
                return
            mid_y = plot.y + plot.height * 0.5
            mid_line.points = [plot.x + dp(4), mid_y, plot.right - dp(4), mid_y]

            if len(history) < 2:
                spark_line.points = []
                return

            pad_x = dp(6)
            pad_y = dp(6)
            usable_w = max(1.0, plot.width - 2 * pad_x)
            usable_h = max(1.0, plot.height - 2 * pad_y)
            lo = min(history)
            hi = max(history)
            if hi - lo < 1e-6:
                lo -= 0.5
                hi += 0.5

            pts = []
            denom = max(1, len(history) - 1)
            for idx, val in enumerate(history):
                px = plot.x + pad_x + (idx / denom) * usable_w
                py = plot.y + pad_y + ((val - lo) / (hi - lo)) * usable_h
                pts.extend([px, py])
            spark_line.points = pts

        plot.bind(pos=_redraw, size=_redraw)
        card.add_widget(top)
        card.add_widget(plot)

        def _on_reading(raw_val, is_sim=False, offline=False):
            if offline or not isinstance(raw_val, (int, float)):
                lbl_val.text = "OFFLINE" if offline else "--"
                lbl_val.color = ColorSystem.DANGER if offline else ColorSystem.TEXT_MUTED
                return

            history.append(float(raw_val))
            if len(history) > max_points:
                del history[0 : len(history) - max_points]

            num_str = f"{raw_val:.{precision}f}" if precision > 0 else f"{int(round(raw_val))}"
            suffix = f" {unit}".rstrip() if unit else ""
            sim_tag = " [SIM]" if is_sim else ""
            lbl_val.text = f"{num_str}{suffix}{sim_tag}"
            lbl_val.color = ColorSystem.WARNING if is_sim else line_color
            spark_c.rgba = line_color
            _redraw()

        _attach_sensor_poller(ctx, data, f"spark:{data.get('label', id(card))}", _on_reading)
        return card

    @staticmethod
    def build_homeostasis_rule(data, ctx):
        """
        Generates an autonomous homeostatic feedback loop card with hysteresis.
        Monitors `sensor_endpoint` and dispatches `target_payload` (or `restore_payload`
        on recovery) to `target_endpoint` on state transitions.
        """
        label_txt = str(data.get("label", "Homeostatic Reflex"))
        operator = str(data.get("operator", "<"))
        threshold = float(data.get("threshold", 0.0))
        hysteresis = float(data.get("hysteresis", 0.0))
        unit = data.get("unit", "")
        target_raw = data.get("target_endpoint")
        target_ep = _resolve_endpoint(target_raw, ctx.base_url)
        target_payload = data.get("target_payload", {"state": True})
        restore_payload = data.get("restore_payload")
        rule_id = data.get("id") or label_txt.lower().replace(" ", "_")
        arm_ep = _resolve_endpoint(data.get("control_endpoint"), ctx.base_url)

        state = {
            "enabled": bool(data.get("enabled", True)),
            "triggered": False,
            "last_val": None,
        }

        card = BoxLayout(
            orientation="horizontal",
            padding=[dp(10), dp(8), dp(10), dp(8)],
            spacing=dp(10),
            size_hint_y=None,
            height=dp(72),
        )
        _bind_card_bg(card, ColorSystem.SURFACE_HOVER, ColorSystem.SURFACE_BORDER, radius=10)

        info_col = BoxLayout(orientation="vertical", spacing=dp(2))
        lbl_title = Label(
            text=label_txt,
            font_size="13sp",
            bold=True,
            color=ColorSystem.TEXT_PRIMARY,
            halign="left",
            valign="middle",
        )
        lbl_title.bind(size=lbl_title.setter("text_size"))

        cond_str = f"If {operator} {threshold:g}{(' ' + unit) if unit else ''} → {target_raw or 'local'}"
        lbl_cond = Label(
            text=cond_str,
            font_size="11sp",
            color=ColorSystem.TEXT_MUTED,
            halign="left",
            valign="middle",
        )
        lbl_cond.bind(size=lbl_cond.setter("text_size"))
        info_col.add_widget(lbl_title)
        info_col.add_widget(lbl_cond)

        btn_arm = Button(
            text="ARMED" if state["enabled"] else "PAUSED",
            size_hint_x=None,
            width=dp(96),
            background_normal="",
            bold=True,
            font_size="11sp",
        )

        def _paint_state(is_sim=False):
            if not state["enabled"]:
                btn_arm.text = "PAUSED"
                btn_arm.background_color = ColorSystem.SURFACE
                btn_arm.color = ColorSystem.TEXT_MUTED
                return
            if state["triggered"]:
                btn_arm.text = "ACTIVE!" if not is_sim else "ACTIVE [S]"
                btn_arm.background_color = ColorSystem.WARNING
                btn_arm.color = ColorSystem.BG_DARK
            else:
                btn_arm.text = "ARMED" if not is_sim else "ARMED [S]"
                btn_arm.background_color = ColorSystem.SUCCESS
                btn_arm.color = ColorSystem.TEXT_PRIMARY

        _paint_state()

        def _dispatch_reflex(payload):
            if not target_ep or ctx.force_sim:
                ctx.sim_state[f"reflex:{rule_id}"] = payload
                return

            def _worker():
                try:
                    _http_request(target_ep, method="POST", payload=payload, timeout=1.5)
                except Exception:
                    pass

            threading.Thread(target=_worker, daemon=True).start()

        def _on_toggle_arm(_inst):
            state["enabled"] = not state["enabled"]
            if not state["enabled"]:
                state["triggered"] = False
            _paint_state(is_sim=ctx.force_sim)
            if arm_ep and not ctx.force_sim:
                def _worker():
                    try:
                        _http_request(arm_ep, method="POST", payload={"id": rule_id, "enabled": state["enabled"]}, timeout=1.5)
                    except Exception:
                        pass
                threading.Thread(target=_worker, daemon=True).start()

        btn_arm.bind(on_release=_on_toggle_arm)

        def _on_reading(raw_val, is_sim=False, offline=False):
            if offline or not isinstance(raw_val, (int, float)):
                lbl_cond.text = f"{cond_str} (OFFLINE)" if offline else cond_str
                return

            state["last_val"] = float(raw_val)
            lbl_cond.text = f"{cond_str} [{raw_val:.1f}{unit}]"
            if not state["enabled"]:
                _paint_state(is_sim=is_sim)
                return

            next_trig = evaluate_hysteresis(
                raw_val,
                currently_triggered=state["triggered"],
                operator=operator,
                threshold=threshold,
                hysteresis=hysteresis,
            )
            if next_trig != state["triggered"]:
                state["triggered"] = next_trig
                if next_trig:
                    _dispatch_reflex(target_payload)
                elif restore_payload is not None:
                    _dispatch_reflex(restore_payload)
            _paint_state(is_sim=is_sim)

        card.add_widget(info_col)
        card.add_widget(btn_arm)
        _attach_sensor_poller(ctx, data, f"rule:{rule_id}", _on_reading)
        return card

    @staticmethod
    def build_node_graft(data, grow_function, ctx, depth=0):
        """
        Docks a remote organism's JSON seed (`seed_url`) into the current L-system tree.
        If unreachable, displays DETACHED status and optionally grows `fallback_seed`.
        """
        title = str(data.get("title", "Remote Organism"))
        seed_url = _resolve_endpoint(data.get("seed_url"), ctx.base_url)
        fallback_seed = data.get("fallback_seed")

        card = BoxLayout(
            orientation="vertical",
            padding=[dp(10), dp(10), dp(10), dp(10)],
            spacing=dp(8),
            size_hint_y=None,
        )
        card.bind(minimum_height=card.setter("height"))
        _bind_card_bg(card, ColorSystem.SURFACE, ColorSystem.SECONDARY, radius=12)

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30), spacing=dp(8))
        lbl_title = Label(
            text=f"🔌 {title}",
            font_size="14sp",
            bold=True,
            color=ColorSystem.SECONDARY,
            halign="left",
            valign="middle",
        )
        lbl_title.bind(size=lbl_title.setter("text_size"))

        lbl_status = Label(
            text="DOCKING...",
            font_size="10sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            size_hint_x=None,
            width=dp(84),
            halign="right",
            valign="middle",
        )
        lbl_status.bind(size=lbl_status.setter("text_size"))

        btn_retry = Button(
            text="↻ DOCK",
            size_hint_x=None,
            width=dp(68),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.PRIMARY,
            bold=True,
            font_size="11sp",
        )
        header.add_widget(lbl_title)
        header.add_widget(lbl_status)
        header.add_widget(btn_retry)
        card.add_widget(header)

        body = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))
        card.add_widget(body)

        active_child = {"ctx": None}

        def _clear_child():
            if active_child["ctx"] is not None:
                active_child["ctx"].stop()
                if active_child["ctx"] in ctx._child_contexts:
                    ctx._child_contexts.remove(active_child["ctx"])
                active_child["ctx"] = None
            body.clear_widgets()

        def _mount_seed(remote_seed, is_fallback=False):
            _clear_child()
            parsed = urllib.parse.urlparse(seed_url or "")
            derived_base = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ctx.base_url
            child_ctx = ctx.create_child(
                base_url=remote_seed.get("base_url") or derived_base,
                simulate_offline=remote_seed.get("simulate_offline", ctx.simulate_offline),
                default_poll=remote_seed.get("poll_interval", ctx.default_poll),
                seed_url=seed_url,
            )
            active_child["ctx"] = child_ctx
            grown = grow_function(remote_seed, ctx=child_ctx, depth=depth + 1)
            if grown is not None:
                body.add_widget(grown)
            if ctx._alive:
                child_ctx.start()
            lbl_status.text = "FALLBACK" if is_fallback else "DOCKED"
            lbl_status.color = ColorSystem.WARNING if is_fallback else ColorSystem.SUCCESS

        def _show_detached(reason):
            _clear_child()
            if isinstance(fallback_seed, dict):
                _mount_seed(fallback_seed, is_fallback=True)
                return
            lbl_status.text = "DETACHED"
            lbl_status.color = ColorSystem.TEXT_HINT
            note = Label(
                text=f"Offline ({seed_url or 'no seed_url'}): {reason}",
                font_size="11sp",
                color=ColorSystem.TEXT_MUTED,
                size_hint_y=None,
                height=dp(28),
                halign="left",
                valign="middle",
            )
            note.bind(size=note.setter("text_size"))
            body.add_widget(note)

        def _attempt_dock(*_args):
            if not seed_url:
                _show_detached("missing seed_url")
                return
            if seed_url in ctx.visited_seed_urls:
                _show_detached("cycle detected")
                return
            if ctx.force_sim:
                if isinstance(fallback_seed, dict):
                    _mount_seed(fallback_seed, is_fallback=True)
                else:
                    _show_detached("SIM mode")
                return

            lbl_status.text = "DOCKING..."
            lbl_status.color = ColorSystem.PRIMARY

            def _worker():
                try:
                    remote_seed = _http_request(seed_url, method="GET", timeout=1.5)
                    if not isinstance(remote_seed, dict) or "node_type" not in remote_seed:
                        raise ValueError("Invalid remote seed payload")
                    Clock.schedule_once(lambda _dt: _mount_seed(remote_seed, is_fallback=False), 0)
                except Exception as exc:
                    Clock.schedule_once(lambda _dt, err=str(exc): _show_detached(err), 0)

            threading.Thread(target=_worker, daemon=True).start()

        btn_retry.bind(on_release=_attempt_dock)
        _attempt_dock()
        return card

    @staticmethod
    def build_edge_dock(data, grow_function, ctx, depth=0):
        """
        Zero-config LAN Hardware Dock: discovers Pi/ESP32 edge nodes on Wi-Fi
        and grafts each discovered node's `/seed.json` UI into this container.
        """
        title = str(data.get("title", "LAN Edge Hardware Dock"))
        ports = tuple(int(p) for p in data.get("ports", [8090]))
        extra_hosts = data.get("extra_hosts")

        card = BoxLayout(
            orientation="vertical",
            padding=[dp(10), dp(10), dp(10), dp(10)],
            spacing=dp(8),
            size_hint_y=None,
        )
        card.bind(minimum_height=card.setter("height"))
        _bind_card_bg(card, ColorSystem.SURFACE, ColorSystem.PRIMARY, radius=12)

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(32), spacing=dp(8))
        lbl_title = Label(
            text=f"🛰️ {title}",
            font_size="14sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            halign="left",
            valign="middle",
        )
        lbl_title.bind(size=lbl_title.setter("text_size"))

        btn_scan = Button(
            text="🔍 SCAN LAN",
            size_hint_x=None,
            width=dp(106),
            background_normal="",
            background_color=ColorSystem.PRIMARY,
            color=ColorSystem.BG_DARK,
            bold=True,
            font_size="11sp",
        )
        header.add_widget(lbl_title)
        header.add_widget(btn_scan)
        card.add_widget(header)

        lbl_status = Label(
            text="Scanning Wi-Fi for edge nodes...",
            font_size="11sp",
            color=ColorSystem.TEXT_MUTED,
            size_hint_y=None,
            height=dp(22),
            halign="left",
            valign="middle",
        )
        lbl_status.bind(size=lbl_status.setter("text_size"))
        card.add_widget(lbl_status)

        body = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))
        card.add_widget(body)

        def _on_nodes_found(nodes):
            body.clear_widgets()
            if not nodes:
                lbl_status.text = "No live edge nodes found. Start tools/pi_node_server.py --port 8090 or check Wi-Fi."
                lbl_status.color = ColorSystem.WARNING
                return
            lbl_status.text = f"Discovered {len(nodes)} edge node(s) — grafting seeds:"
            lbl_status.color = ColorSystem.SUCCESS
            for item in nodes:
                graft_seed = {
                    "node_type": "node_graft",
                    "title": item.get("name", item.get("ip", "Edge Node")),
                    "seed_url": item.get("seed_url"),
                }
                w = grow_function(graft_seed, ctx=ctx, depth=depth + 1)
                if w is not None:
                    body.add_widget(w)

        def _run_scan(*_args):
            lbl_status.text = "Scanning Wi-Fi (UDP 8091 + HTTP /seed.json)..."
            lbl_status.color = ColorSystem.PRIMARY
            try:
                from core.discovery import discover_edge_nodes
                discover_edge_nodes(timeout=1.2, ports=ports, callback=_on_nodes_found, extra_hosts=extra_hosts)
            except Exception as e:
                lbl_status.text = f"Scan error: {e}"
                lbl_status.color = ColorSystem.DANGER

        btn_scan.bind(on_release=_run_scan)
        _run_scan()
        return card


# Grammar Registry: maps `node_type` -> (builder_fn, is_container)
PRODUCTION_RULES = {
    "module_container": (UI_Rules.build_container, True),
    "row_container": (UI_Rules.build_row, True),
    "grid_container": (UI_Rules.build_grid, True),
    "node_graft": (UI_Rules.build_node_graft, True),
    "edge_dock": (UI_Rules.build_edge_dock, True),
    "sensor_readout": (UI_Rules.build_sensor, False),
    "actuator_slider": (UI_Rules.build_actuator_slider, False),
    "actuator_toggle": (UI_Rules.build_actuator_toggle, False),
    "action_button": (UI_Rules.build_action_button, False),
    "status_banner": (UI_Rules.build_status_banner, False),
    "gauge_bar": (UI_Rules.build_gauge_bar, False),
    "sparkline_chart": (UI_Rules.build_sparkline_chart, False),
    "homeostasis_rule": (UI_Rules.build_homeostasis_rule, False),
}


def register_rule(node_type, builder_fn, is_container=False):
    """Registers or overrides a production rule in the global L-system grammar."""
    PRODUCTION_RULES[node_type] = (builder_fn, is_container)


def grow_ui_from_seed(seed_data, ctx=None, depth=0, max_depth=16):
    """
    Recursively interprets a JSON seed (axiom) into a Kivy widget tree.
    """
    if not isinstance(seed_data, dict):
        return None
    if depth == 0:
        seed_data = expand_seed(seed_data)
    if depth > max_depth:
        return Label(
            text="Max L-system recursion depth reached",
            size_hint_y=None,
            height=dp(32),
            color=ColorSystem.WARNING,
            font_size="12sp",
        )

    if ctx is None:
        ctx = LSystemContext(
            base_url=seed_data.get("base_url"),
            simulate_offline=seed_data.get("simulate_offline", True),
            force_sim=seed_data.get("force_sim", False),
            default_poll=seed_data.get("poll_interval", 2.5),
        )

    node_type = seed_data.get("node_type")
    entry = PRODUCTION_RULES.get(node_type)

    if not entry:
        print(f"[LSystemUI] Unknown node_type '{node_type}'. Skipping.")
        return Label(
            text=f"Unknown node_type: {node_type}",
            size_hint_y=None,
            height=dp(28),
            color=ColorSystem.TEXT_HINT,
            font_size="11sp",
        )

    rule_fn, is_container = entry
    if is_container:
        return rule_fn(seed_data, grow_function=grow_ui_from_seed, ctx=ctx, depth=depth)
    return rule_fn(seed_data, ctx=ctx)


class LSystemRootWidget(BoxLayout):
    """
    OpenHub host-compatible root widget that grows a Kivy UI from a JSON seed
    inside a ScrollView and manages async polling lifecycle.
    """

    def __init__(self, seed_data=None, seed_path=None, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.host_api = None
        self.seed_path = seed_path
        self.seed_data = seed_data or {}
        self.ctx = None

        # Top status bar (mode indicator + SIM/LIVE toggle + re-grow button)
        self.toolbar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            padding=[dp(12), dp(6), dp(12), dp(6)],
            spacing=dp(8),
        )
        _bind_card_bg(self.toolbar, ColorSystem.SURFACE, ColorSystem.SURFACE_BORDER, radius=0)

        self.lbl_mode = Label(
            text="● GROWING",
            font_size="12sp",
            bold=True,
            color=ColorSystem.PRIMARY,
            halign="left",
            valign="middle",
        )
        self.lbl_mode.bind(size=self.lbl_mode.setter("text_size"))

        self.btn_mode = Button(
            text="MODE: AUTO",
            size_hint_x=None,
            width=dp(106),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.TEXT_PRIMARY,
            bold=True,
            font_size="11sp",
        )
        self.btn_mode.bind(on_release=self._toggle_force_sim)

        self.btn_regrow = Button(
            text="↻ RE-GROW",
            size_hint_x=None,
            width=dp(96),
            background_normal="",
            background_color=ColorSystem.SURFACE_HOVER,
            color=ColorSystem.PRIMARY,
            bold=True,
            font_size="11sp",
        )
        self.btn_regrow.bind(on_release=self._on_regrow_pressed)

        self.toolbar.add_widget(self.lbl_mode)
        self.toolbar.add_widget(self.btn_mode)
        self.toolbar.add_widget(self.btn_regrow)
        self.add_widget(self.toolbar)

        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.tree_host = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(8), dp(8), dp(8), dp(16)])
        self.tree_host.bind(minimum_height=self.tree_host.setter("height"))
        self.scroll.add_widget(self.tree_host)
        self.add_widget(self.scroll)

        self._force_sim_override = None
        if self.seed_data:
            self.rebuild(self.seed_data, start_polling=False)

    @classmethod
    def from_file(cls, seed_path):
        with open(seed_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(seed_data=data, seed_path=seed_path)

    def _on_mode_change(self, mode):
        if mode == "LIVE":
            self.lbl_mode.text = "● LIVE"
            self.lbl_mode.color = ColorSystem.SUCCESS
        elif mode == "SIM":
            self.lbl_mode.text = "● SIMULATED"
            self.lbl_mode.color = ColorSystem.WARNING
        else:
            self.lbl_mode.text = "● OFFLINE"
            self.lbl_mode.color = ColorSystem.DANGER

    def _toggle_force_sim(self, _inst):
        if self._force_sim_override is None:
            self._force_sim_override = True
            self.btn_mode.text = "MODE: SIM"
        elif self._force_sim_override is True:
            self._force_sim_override = False
            self.btn_mode.text = "MODE: LIVE"
        else:
            self._force_sim_override = None
            self.btn_mode.text = "MODE: AUTO"
        self.rebuild(self.seed_data, start_polling=True)

    def _on_regrow_pressed(self, _inst):
        seed_url = self.seed_data.get("seed_url")
        if seed_url:
            self.lbl_mode.text = "● FETCHING SEED..."
            self.lbl_mode.color = ColorSystem.PRIMARY

            def _worker():
                try:
                    remote_seed = _http_request(seed_url, method="GET", timeout=2.0)
                    if isinstance(remote_seed, dict) and "node_type" in remote_seed:
                        Clock.schedule_once(lambda _dt: self.rebuild(remote_seed, start_polling=True), 0)
                        return
                except Exception:
                    pass
                Clock.schedule_once(lambda _dt: self._regrow_from_local(), 0)

            threading.Thread(target=_worker, daemon=True).start()
            return
        self._regrow_from_local()

    def _regrow_from_local(self):
        if self.seed_path and os.path.exists(self.seed_path):
            try:
                with open(self.seed_path, "r", encoding="utf-8") as f:
                    self.seed_data = json.load(f)
            except Exception as e:
                self.lbl_mode.text = f"SEED ERR: {e}"
                self.lbl_mode.color = ColorSystem.DANGER
                return
        self.rebuild(self.seed_data, start_polling=True)

    def rebuild(self, seed_data, start_polling=True):
        """Clears the current widget tree and re-grows it from `seed_data`."""
        if self.ctx is not None:
            self.ctx.stop()

        self.seed_data = seed_data or {}
        force_sim = (
            self._force_sim_override
            if self._force_sim_override is not None
            else bool(self.seed_data.get("force_sim", False))
        )
        self.ctx = LSystemContext(
            host_api=self.host_api,
            base_url=self.seed_data.get("base_url"),
            simulate_offline=self.seed_data.get("simulate_offline", True),
            force_sim=force_sim,
            default_poll=self.seed_data.get("poll_interval", 2.5),
        )
        self.ctx.add_status_listener(self._on_mode_change)
        self._on_mode_change("SIM" if force_sim else "LIVE")

        self.tree_host.clear_widgets()
        grown = grow_ui_from_seed(self.seed_data, ctx=self.ctx, depth=0)
        if grown is not None:
            self.tree_host.add_widget(grown)

        if start_polling:
            self.ctx.start()

    def on_load(self, host_api):
        self.host_api = host_api
        if self.ctx is not None:
            self.ctx.host_api = host_api

    def on_resume(self):
        if self.ctx is not None:
            self.ctx.start()

    def on_pause(self):
        if self.ctx is not None:
            self.ctx.stop()

    def on_unload(self):
        self.on_pause()

    def on_parent(self, _instance, parent):
        if parent is None:
            self.on_pause()


def build_widget_from_seed_file(seed_path, host_api=None):
    """Convenience entrypoint for ModuleLoader to grow a UI from a JSON seed file."""
    widget = LSystemRootWidget.from_file(seed_path)
    if host_api is not None:
        widget.on_load(host_api)
    return widget
