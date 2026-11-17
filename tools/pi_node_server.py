#!/usr/bin/env python3
"""
OpenHub Edge Node Seed Server (Raspberry Pi / Linux Reference Server)
Zero-dependency HTTP server exposing an L-system JSON seed (/seed.json)
plus live sensor GET and actuator POST endpoints.

Usage:
    python3 tools/pi_node_server.py --port 8090
"""
import argparse
import json
import math
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _eval_hysteresis(reading, triggered, operator, threshold, hysteresis=0.0):
    val = float(reading)
    thresh = float(threshold)
    hyst = max(0.0, float(hysteresis))
    eps = 1e-9
    if operator in ("<", "<="):
        trig = val < thresh if operator == "<" else val <= thresh
        clr = (val + eps) >= (thresh + hyst) if operator == "<" else val > (thresh + hyst + eps)
    elif operator in (">", ">="):
        trig = val > thresh if operator == ">" else val >= thresh
        clr = (val - eps) <= (thresh - hyst) if operator == ">" else val < (thresh - hyst - eps)
    else:
        return False
    return (not clr) if triggered else trig


class EdgeNodeState:
    """In-memory hardware state (replace read/write hooks with GPIO/I2C calls)."""

    def __init__(self):
        self.lights_dim = 60
        self.pump_power = False
        self.fan_power = True
        self.tank_level = 76.0
        self.start_time = time.time()
        self.rules = {
            "low_batt_shed": {
                "enabled": True,
                "triggered": False,
                "operator": "<",
                "threshold": 11.9,
                "hysteresis": 0.3,
                "last_reading": None,
            },
            "thermal_vent": {
                "enabled": True,
                "triggered": False,
                "operator": ">",
                "threshold": 26.0,
                "hysteresis": 1.5,
                "last_reading": None,
            },
        }

    def step_homeostasis(self):
        """Evaluates autonomic feedback loops locally on the edge node."""
        batt = self.read_battery_v()
        temp = self.read_cabin_temp()

        r_batt = self.rules["low_batt_shed"]
        r_batt["last_reading"] = batt
        if r_batt["enabled"]:
            nxt = _eval_hysteresis(batt, r_batt["triggered"], r_batt["operator"], r_batt["threshold"], r_batt["hysteresis"])
            if nxt != r_batt["triggered"]:
                r_batt["triggered"] = nxt
                self.lights_dim = 0 if nxt else 40
                print(f"[Homeostasis] low_batt_shed={'ACTIVE' if nxt else 'CLEARED'} ({batt}V) -> lights_dim={self.lights_dim}%")

        r_temp = self.rules["thermal_vent"]
        r_temp["last_reading"] = temp
        if r_temp["enabled"]:
            nxt = _eval_hysteresis(temp, r_temp["triggered"], r_temp["operator"], r_temp["threshold"], r_temp["hysteresis"])
            if nxt != r_temp["triggered"]:
                r_temp["triggered"] = nxt
                self.fan_power = nxt
                print(f"[Homeostasis] thermal_vent={'ACTIVE' if nxt else 'CLEARED'} ({temp}C) -> fan_power={self.fan_power}")

    def read_battery_v(self):
        t = time.time() - self.start_time
        load_drop = (self.lights_dim / 100.0) * 0.15 + (0.25 if self.pump_power else 0.0)
        return round(12.95 + 0.12 * math.sin(t * 0.3) - load_drop, 2)

    def read_solar_watts(self):
        t = time.time() - self.start_time
        return round(240.0 + 65.0 * math.sin(t * 0.2), 1)

    def read_cabin_temp(self):
        t = time.time() - self.start_time
        fan_cooling = -1.2 if self.fan_power else 0.8
        return round(21.5 + fan_cooling + 0.4 * math.cos(t * 0.15), 1)

    def read_tank_level(self):
        if self.pump_power and self.tank_level > 5.0:
            self.tank_level = max(5.0, self.tank_level - 0.1)
        return round(self.tank_level, 1)

    def build_seed(self, base_url):
        return {
            "node_type": "module_container",
            "title": "Van Micro-Grid (Live Pi)",
            "subtitle": base_url.replace("http://", ""),
            "base_url": base_url,
            "seed_url": f"{base_url}/seed.json",
            "poll_interval": 1.5,
            "simulate_offline": False,
            "children": [
                {
                    "node_type": "grid_container",
                    "cols": 2,
                    "children": [
                        {
                            "node_type": "sensor_readout",
                            "label": "Leisure Battery",
                            "data_endpoint": "/batt",
                            "unit": "V",
                            "precision": 2,
                            "warn_low": 11.8,
                        },
                        {
                            "node_type": "sensor_readout",
                            "label": "Solar Input",
                            "data_endpoint": "/solar/watts",
                            "unit": "W",
                            "precision": 0,
                            "accent": "success",
                        },
                    ],
                },
                {
                    "node_type": "gauge_bar",
                    "label": "Fresh Water Tank",
                    "data_endpoint": "/tank/level",
                    "range": [0, 100],
                    "unit": "%",
                    "warn_low": 20,
                },
                {
                    "node_type": "sparkline_chart",
                    "label": "Battery Voltage Trend",
                    "data_endpoint": "/batt",
                    "unit": "V",
                    "precision": 2,
                    "max_points": 30,
                },
                {
                    "node_type": "actuator_slider",
                    "label": "Cabin Lights",
                    "control_endpoint": "/lights/dim",
                    "range": [0, 100],
                    "step": 5,
                    "initial": self.lights_dim,
                    "unit": "%",
                },
                {
                    "node_type": "actuator_toggle",
                    "label": "Water Circulation Pump",
                    "control_endpoint": "/pump/power",
                    "initial": self.pump_power,
                    "on_label": "RUNNING",
                    "off_label": "IDLE",
                },
                {
                    "node_type": "actuator_toggle",
                    "label": "Roof Vent Fan",
                    "control_endpoint": "/fan/power",
                    "initial": self.fan_power,
                },
                {
                    "node_type": "module_container",
                    "title": "Homeostatic Reflexes",
                    "subtitle": "Autonomic Loops",
                    "children": [
                        {
                            "node_type": "homeostasis_rule",
                            "id": "low_batt_shed",
                            "label": "Low-Voltage Load Shed",
                            "sensor_endpoint": "/batt",
                            "operator": "<",
                            "threshold": 11.9,
                            "hysteresis": 0.3,
                            "unit": "V",
                            "target_endpoint": "/lights/dim",
                            "target_payload": {"value": 0},
                            "restore_payload": {"value": 40},
                            "control_endpoint": "/homeostasis/toggle",
                            "enabled": self.rules["low_batt_shed"]["enabled"],
                        },
                        {
                            "node_type": "homeostasis_rule",
                            "id": "thermal_vent",
                            "label": "Thermal Vent Reflex",
                            "sensor_endpoint": "/env/temp",
                            "operator": ">",
                            "threshold": 26.0,
                            "hysteresis": 1.5,
                            "unit": "°C",
                            "target_endpoint": "/fan/power",
                            "target_payload": {"state": True},
                            "restore_payload": {"state": False},
                            "control_endpoint": "/homeostasis/toggle",
                            "enabled": self.rules["thermal_vent"]["enabled"],
                        },
                    ],
                },
            ],
        }


def make_handler(state):
    class NodeHandler(BaseHTTPRequestHandler):
        def _send_json(self, obj, status=200):
            body = json.dumps(obj, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/seed.json":
                host = self.headers.get("Host") or f"127.0.0.1:{self.server.server_port}"
                self._send_json(state.build_seed(f"http://{host}"))
            elif self.path == "/batt":
                self._send_json({"value": state.read_battery_v()})
            elif self.path == "/solar/watts":
                self._send_json({"value": state.read_solar_watts()})
            elif self.path == "/env/temp":
                self._send_json({"value": state.read_cabin_temp()})
            elif self.path == "/tank/level":
                self._send_json({"value": state.read_tank_level()})
            elif self.path == "/homeostasis":
                self._send_json(state.rules)
            else:
                self._send_json({"error": "not found"}, status=404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {}

            if self.path == "/lights/dim":
                state.lights_dim = float(payload.get("value", state.lights_dim))
                print(f"[EdgeNode] Cabin Lights -> {state.lights_dim}%")
                self._send_json({"ok": True, "lights_dim": state.lights_dim})
            elif self.path == "/pump/power":
                state.pump_power = bool(payload.get("state", state.pump_power))
                print(f"[EdgeNode] Water Pump -> {'ON' if state.pump_power else 'OFF'}")
                self._send_json({"ok": True, "pump_power": state.pump_power})
            elif self.path == "/fan/power":
                state.fan_power = bool(payload.get("state", state.fan_power))
                print(f"[EdgeNode] Roof Fan -> {'ON' if state.fan_power else 'OFF'}")
                self._send_json({"ok": True, "fan_power": state.fan_power})
            elif self.path == "/homeostasis/toggle":
                rid = payload.get("id")
                if rid in state.rules:
                    state.rules[rid]["enabled"] = bool(payload.get("enabled", True))
                    if not state.rules[rid]["enabled"]:
                        state.rules[rid]["triggered"] = False
                    self._send_json({"ok": True, "rule": state.rules[rid]})
                else:
                    self._send_json({"error": "unknown rule"}, status=404)
            elif self.path == "/mppt/reset":
                print("[EdgeNode] MPPT Charge Controller soft reset triggered")
                self._send_json({"ok": True, "reset": True})
            else:
                self._send_json({"error": "not found"}, status=404)

        def log_message(self, format, *args):
            pass

    return NodeHandler


def main():
    parser = argparse.ArgumentParser(description="OpenHub L-System Edge Node Seed Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8090, help="HTTP port (default: 8090)")
    args = parser.parse_args()

    state = EdgeNodeState()
    stop_evt = threading.Event()

    def _homeostasis_loop():
        while not stop_evt.is_set():
            try:
                state.step_homeostasis()
            except Exception:
                pass
            stop_evt.wait(1.0)

    threading.Thread(target=_homeostasis_loop, daemon=True).start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print(f"[EdgeNode] Serving L-system seed at http://127.0.0.1:{args.port}/seed.json")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[EdgeNode] Shutting down.")
        stop_evt.set()
        server.server_close()


if __name__ == "__main__":
    main()

