"""Tests for the extended Python Library Explorer & Visual Kivy/L-System Studio."""
import ast
import json
import os
import sys
import unittest

os.environ.setdefault("KIVY_NO_ARGS", "1")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.lsystem_ui import grow_ui_from_seed
from core.runner import ModuleLoader
from core.scanner import ModuleScanner
from core.security import HostAPI
from modules.lib_explorer.main import (
    WIDGET_CATALOG,
    extract_nodes_from_seed,
    generate_lsystem_seed_data,
    generate_python_module_code,
)


class TestLibExplorerBuilder(unittest.TestCase):
    def test_module_loads_and_switches_modes(self):
        scanner = ModuleScanner(os.path.join(ROOT_DIR, "modules"))
        permanent, _ = scanner.scan_all()
        desc = next((m for m in permanent if m.id == "lib_explorer"), None)
        self.assertIsNotNone(desc)

        host = HostAPI(module_id=desc.id, storage_root=ROOT_DIR)
        mod = ModuleLoader.load_module_widget(desc, host)
        self.assertEqual(mod.mode, "inspect")
        mod.inspect_module("kivy.uix.button")
        self.assertIn("Button", mod.lbl_details.text)

        mod.set_mode("builder")
        self.assertEqual(mod.mode, "builder")
        self.assertGreaterEqual(len(mod.nodes), 2)

        # Add node with custom script and run in live test mode
        btn_node = mod.add_node_from_spec(WIDGET_CATALOG[0])
        btn_node["label"] = "Pulse"
        btn_node["script"] = 'state["ran"] = True\nlog("Executed Pulse!")'
        mod._toggle_test_mode()
        self.assertTrue(mod.test_mode)

        live_btn = mod.canvas_list.children[0]
        live_btn.dispatch("on_release")
        self.assertTrue(mod.runtime_state.get("ran"))
        self.assertEqual(mod.lbl_console.text, "Executed Pulse!")

    def test_generate_python_module_code_is_valid_and_runnable(self):
        nodes = [
            {
                "kind": "button",
                "label": "Ping",
                "script": 'state["pinged"] = True\nlog("PONG")',
            },
            {
                "kind": "toggle",
                "label": "Pump",
                "script": 'state["pump"] = value\nlog(f"pump={value}")',
            },
            {
                "kind": "slider",
                "label": "Dimmer",
                "script": 'state["dim"] = int(value)',
            },
        ]
        code = generate_python_module_code(nodes, title="Test Deck")
        ast.parse(code)

        ns = {}
        exec(compile(code, "<generated_test>", "exec"), ns)
        inst = ns["OpenHubModule"]()
        inst._on_node_0(None, True)
        inst._on_node_1(None, True)
        inst._on_node_2(None, 75)
        self.assertTrue(inst.state["pinged"])
        self.assertTrue(inst.state["pump"])
        self.assertEqual(inst.state["dim"], 75)
        self.assertEqual(inst.lbl_log.text, "pump=True")

    def test_generate_lsystem_seed_grows_cleanly(self):
        nodes = [
            {"kind": "button", "label": "Reset", "endpoint": "/reset"},
            {"kind": "toggle", "label": "Fan", "endpoint": "/fan"},
            {"kind": "slider", "label": "Lights", "endpoint": "/lights"},
            {"kind": "gauge", "label": "Tank", "endpoint": "/tank"},
        ]
        seed = generate_lsystem_seed_data(nodes, title="Studio Seed")
        encoded = json.dumps(seed)
        parsed = json.loads(encoded)
        widget = grow_ui_from_seed(parsed)
        self.assertIsNotNone(widget)
        self.assertGreaterEqual(len(widget.children), 4)

    def test_extract_nodes_from_existing_seed_and_reorder(self):
        seed_path = os.path.join(ROOT_DIR, "modules", "van_microgrid", "seed.json")
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_data = json.load(f)
        extracted = extract_nodes_from_seed(seed_data)
        self.assertGreaterEqual(len(extracted), 6)
        kinds = {n["kind"] for n in extracted}
        self.assertIn("sparkline", kinds)
        self.assertIn("homeostasis", kinds)

        host = HostAPI(module_id="lib_explorer", storage_root=ROOT_DIR)
        mod = ModuleLoader.load_module_widget(
            next(m for m in ModuleScanner(os.path.join(ROOT_DIR, "modules")).scan_all()[0] if m.id == "lib_explorer"),
            host,
        )
        mod.load_seed_file(seed_path)
        self.assertEqual(mod.txt_tool_title.text, "Van Micro-Grid")
        self.assertTrue(any(n.get("is_container") for n in mod.nodes), "Nested grid/row containers should be preserved")
        first_label = mod.nodes[0]["label"]
        mod._move_node(0, 1)
        self.assertEqual(mod.nodes[1]["label"], first_label)

    def test_nested_container_codegen_and_seed_roundtrip(self):
        nodes = [
            {
                "kind": "grid",
                "is_container": True,
                "label": "Sensors",
                "color": (0.7, 0.5, 0.9, 1.0),
                "children": [
                    {"kind": "button", "label": "Ping", "endpoint": "/ping", "script": 'state["p"] = True'},
                    {"kind": "toggle", "label": "Pump", "endpoint": "/pump", "script": 'state["q"] = value'},
                ],
            },
            {
                "kind": "row",
                "is_container": True,
                "label": "Row",
                "color": (0.4, 0.7, 0.9, 1.0),
                "children": [
                    {"kind": "slider", "label": "Dim", "endpoint": "/dim", "script": "pass"},
                ],
            },
        ]
        py_code = generate_python_module_code(nodes, title="Nested Studio")
        ast.parse(py_code)
        ns = {}
        exec(compile(py_code, "<nested_gen>", "exec"), ns)
        inst = ns["OpenHubModule"]()
        self.assertIsNotNone(inst)

        seed = generate_lsystem_seed_data(nodes, title="Nested Seed")
        self.assertEqual(seed["children"][0]["node_type"], "grid_container")
        self.assertEqual(len(seed["children"][0]["children"]), 2)
        self.assertEqual(seed["children"][1]["node_type"], "row_container")
        widget = grow_ui_from_seed(seed)
        self.assertIsNotNone(widget)


if __name__ == "__main__":
    unittest.main()

