"""Unit and integration tests for OpenHub's L-system generative UI engine."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

# Ensure project root is on sys.path and prevent Kivy from parsing unittest CLI args
os.environ.setdefault("KIVY_NO_ARGS", "1")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from kivy.clock import Clock

from core.forge_agent import ForgeEngine
from core.lsystem_ui import (
    LSystemContext,
    LSystemRootWidget,
    evaluate_hysteresis,
    grow_ui_from_seed,
    register_rule,
)
from core.module_manager import ModuleManager
from core.runner import ModuleLoader
from core.scanner import ModuleScanner
from core.security import HostAPI
from tools.pi_node_server import EdgeNodeState, make_handler


class _MockDeviceState:
    def __init__(self):
        self.battery_v = 12.95
        self.received_posts = []


def _start_mock_server():
    state = _MockDeviceState()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/batt":
                body = json.dumps({"value": state.battery_v}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            state.received_posts.append((self.path, json.loads(raw)))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port, state


class TestLSystemUI(unittest.TestCase):
    def test_scanner_and_loader_support_json_seed_module(self):
        scanner = ModuleScanner(os.path.join(ROOT_DIR, "modules"))
        permanent, _ = scanner.scan_all()
        van_desc = next((m for m in permanent if m.id == "van_microgrid"), None)
        self.assertIsNotNone(van_desc, "van_microgrid should be discovered by ModuleScanner")
        self.assertTrue(van_desc.entrypoint.endswith("seed.json"))

        host_api = HostAPI(module_id=van_desc.id, storage_root=ROOT_DIR)
        widget = ModuleLoader.load_module_widget(van_desc, host_api)
        self.assertIsInstance(widget, LSystemRootWidget)
        self.assertIs(widget.host_api, host_api)
        self.assertGreater(len(widget.tree_host.children), 0)

        # Lifecycle start/stop must clean up scheduled events
        widget.on_resume()
        self.assertGreater(len(widget.ctx._scheduled_events), 0)
        widget.on_pause()
        self.assertEqual(len(widget.ctx._scheduled_events), 0)
        self.assertFalse(widget.ctx._alive)

    def test_unknown_node_type_and_max_depth_guards(self):
        ctx = LSystemContext(force_sim=True)
        unknown_w = grow_ui_from_seed({"node_type": "quantum_flux"}, ctx=ctx)
        self.assertIn("Unknown node_type", unknown_w.text)

        deep_w = grow_ui_from_seed({"node_type": "module_container", "children": []}, ctx=ctx, depth=17, max_depth=16)
        self.assertIn("Max L-system recursion depth", deep_w.text)

    def test_custom_rule_registration(self):
        from kivy.uix.label import Label

        register_rule(
            "custom_test_badge",
            lambda data, ctx: Label(text=f"CUSTOM:{data.get('tag', '')}"),
            is_container=False,
        )
        ctx = LSystemContext(force_sim=True)
        w = grow_ui_from_seed({"node_type": "custom_test_badge", "tag": "SOLAR"}, ctx=ctx)
        self.assertEqual(w.text, "CUSTOM:SOLAR")

    def test_live_http_sensor_and_actuator_roundtrip(self):
        server, port, state = _start_mock_server()
        try:
            seed = {
                "node_type": "module_container",
                "title": "Live Test Node",
                "base_url": f"http://127.0.0.1:{port}",
                "simulate_offline": False,
                "children": [
                    {
                        "node_type": "sensor_readout",
                        "label": "Batt",
                        "data_endpoint": "/batt",
                        "unit": "V",
                        "precision": 2,
                    },
                    {
                        "node_type": "actuator_toggle",
                        "label": "Pump",
                        "control_endpoint": "/pump",
                        "initial": False,
                    },
                ],
            }
            root = LSystemRootWidget(seed_data=seed)
            root.on_resume()

            # Pump Kivy Clock briefly for initial async HTTP GET
            deadline = time.time() + 2.0
            container = root.tree_host.children[0]
            # container children are added top-to-bottom so Kivy stores reversed order
            sensor_card = container.children[1]
            toggle_row = container.children[0]
            sensor_val_lbl = sensor_card.children[0]
            toggle_btn = toggle_row.children[0]

            while time.time() < deadline and sensor_val_lbl.text == "--":
                Clock.tick()
                time.sleep(0.03)

            self.assertEqual(sensor_val_lbl.text, "12.95 V")

            # Trigger toggle button press and pump Clock for async HTTP POST
            toggle_btn.dispatch("on_release")
            deadline = time.time() + 2.0
            while time.time() < deadline and not state.received_posts:
                Clock.tick()
                time.sleep(0.03)

            self.assertEqual(state.received_posts, [("/pump", {"state": True})])
            root.on_pause()
        finally:
            server.shutdown()
            server.server_close()

    def test_gauge_bar_and_sparkline_rules(self):
        seed = {
            "node_type": "module_container",
            "title": "Visual Nodes",
            "force_sim": True,
            "children": [
                {
                    "node_type": "gauge_bar",
                    "label": "Water Tank",
                    "range": [0, 100],
                    "unit": "%",
                    "sim_value": 75,
                },
                {
                    "node_type": "sparkline_chart",
                    "label": "Solar Trend",
                    "unit": "W",
                    "sim_value": 240,
                    "sim_range": [100, 400],
                },
            ],
        }
        root = LSystemRootWidget(seed_data=seed)
        root.on_resume()
        for _ in range(3):
            Clock.tick()
            time.sleep(0.02)

        container = root.tree_host.children[0]
        gauge_card = container.children[1]
        spark_card = container.children[0]
        gauge_val_lbl = gauge_card.children[1].children[0]
        spark_val_lbl = spark_card.children[1].children[0]
        self.assertIn("%", gauge_val_lbl.text)
        self.assertIn("W", spark_val_lbl.text)
        root.on_pause()

    def test_json_fork_scan_and_promote_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ModuleManager(tmpdir)
            seed_obj = {"node_type": "module_container", "title": "Temp Node", "children": []}
            scratch_desc = mgr.create_scratch(json.dumps(seed_obj), prompt="van_seed", extension=".json")
            self.assertTrue(scratch_desc.entrypoint.endswith(".json"))

            _, scratch_list = mgr.scan()
            self.assertEqual(len(scratch_list), 1)
            self.assertTrue(scratch_list[0].entrypoint.endswith(".json"))

            perm_desc = mgr.promote_to_permanent(scratch_desc, "Van Seed Tool", category="Field")
            self.assertTrue(perm_desc.entrypoint.endswith("seed.json"))

            fork_desc = mgr.fork(perm_desc)
            self.assertTrue(fork_desc.entrypoint.endswith(".json"))

    def test_forge_json_seed_fallback_mutator(self):
        forge = ForgeEngine()
        base_seed = json.dumps({"node_type": "module_container", "title": "Van", "children": []})
        self.assertTrue(forge._looks_like_json_seed(base_seed))

        out = forge._fallback_json_mutator("Add heater toggle", base_seed)
        extracted = forge._extract_json(out)
        self.assertTrue(forge._is_valid_json_seed(extracted))
        parsed = json.loads(extracted)
        self.assertEqual(parsed["children"][0]["node_type"], "actuator_toggle")
        self.assertEqual(parsed["children"][0]["label"], "Heater Toggle")

    def test_pi_node_server_serves_seed_and_handles_actuators(self):
        state = EdgeNodeState()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
        port = server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/seed.json", timeout=2) as resp:
                seed = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(seed["node_type"], "module_container")
            self.assertEqual(seed["base_url"], f"http://127.0.0.1:{port}")

            root = LSystemRootWidget(seed_data=seed)
            root.on_resume()
            deadline = time.time() + 2.0
            while time.time() < deadline and root.ctx._last_mode != "LIVE":
                Clock.tick()
                time.sleep(0.03)
            self.assertEqual(root.ctx._last_mode, "LIVE")
            root.on_pause()
        finally:
            server.shutdown()
            server.server_close()

    def test_hysteresis_and_homeostasis_rule_trigger_and_restore(self):
        # Verify hysteresis bands prevent relay chatter
        self.assertTrue(evaluate_hysteresis(11.8, False, "<", 11.9, hysteresis=0.3))
        self.assertTrue(evaluate_hysteresis(12.0, True, "<", 11.9, hysteresis=0.3))
        self.assertFalse(evaluate_hysteresis(12.2, True, "<", 11.9, hysteresis=0.3))

        server, port, state = _start_mock_server()
        try:
            state.battery_v = 11.7  # Below 11.9V threshold -> triggers shed
            seed = {
                "node_type": "module_container",
                "title": "Homeostasis Test",
                "base_url": f"http://127.0.0.1:{port}",
                "simulate_offline": False,
                "poll_interval": 0.4,
                "children": [
                    {
                        "node_type": "homeostasis_rule",
                        "id": "low_batt",
                        "label": "Load Shed",
                        "sensor_endpoint": "/batt",
                        "operator": "<",
                        "threshold": 11.9,
                        "hysteresis": 0.3,
                        "unit": "V",
                        "target_endpoint": "/lights/dim",
                        "target_payload": {"value": 0},
                        "restore_payload": {"value": 40},
                    }
                ],
            }
            root = LSystemRootWidget(seed_data=seed)
            root.on_resume()

            deadline = time.time() + 2.0
            while time.time() < deadline and not state.received_posts:
                Clock.tick()
                time.sleep(0.03)
            self.assertEqual(state.received_posts, [("/lights/dim", {"value": 0})])

            # Recover above threshold + hysteresis (12.2V) -> dispatches restore_payload
            state.battery_v = 12.3
            deadline = time.time() + 2.0
            while time.time() < deadline and len(state.received_posts) < 2:
                Clock.tick()
                time.sleep(0.05)
            self.assertEqual(state.received_posts[1], ("/lights/dim", {"value": 40}))
            root.on_pause()
        finally:
            server.shutdown()
            server.server_close()

    def test_edge_node_autonomous_homeostasis_loop(self):
        edge = EdgeNodeState()
        edge.read_battery_v = lambda: 11.7
        edge.read_cabin_temp = lambda: 28.0
        edge.step_homeostasis()
        self.assertTrue(edge.rules["low_batt_shed"]["triggered"])
        self.assertEqual(edge.lights_dim, 0)
        self.assertTrue(edge.rules["thermal_vent"]["triggered"])
        self.assertTrue(edge.fan_power)

        # Within hysteresis deadband (12.0V < 12.2V), load shed stays active
        edge.read_battery_v = lambda: 12.0
        edge.step_homeostasis()
        self.assertTrue(edge.rules["low_batt_shed"]["triggered"])

        # Above 12.2V clears load shed and restores lights
        edge.read_battery_v = lambda: 12.4
        edge.step_homeostasis()
        self.assertFalse(edge.rules["low_batt_shed"]["triggered"])
        self.assertEqual(edge.lights_dim, 40)


if __name__ == "__main__":
    unittest.main()

