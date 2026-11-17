"""Tests for slot-aware Home Grid drag-and-drop reordering in LauncherScreen."""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("KIVY_NO_ARGS", "1")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from kivy.metrics import dp
from kivy.uix.widget import Widget

from core.forge_agent import ForgeEngine
from core.home_layout import HomeLayoutManager
from core.module_manager import ModuleManager
from core.updater import UpdateManager
from ui.launcher import LauncherScreen


class _FakeAppMgr:
    def __init__(self, tmpdir):
        self.forge = ForgeEngine()
        self.module_mgr = ModuleManager(tmpdir)
        self.updater = UpdateManager(tmpdir)
        self.hardware = None

    def launch_module(self, desc):
        pass


class _FakeIcon:
    def __init__(self, mod_id, is_home=True):
        self.is_home = is_home
        self.descriptor = type("D", (), {"id": mod_id, "name": mod_id.title()})()


class TestLauncherDragDrop(unittest.TestCase):
    def test_home_grid_slot_drop_and_reorder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = _FakeAppMgr(tmpdir)
            ls = LauncherScreen(mgr, name="launcher")
            ls.size = (440, 860)
            ls.home_scroll.pos = (0, 140)
            ls.home_scroll.size = (440, 560)
            ls.layout_mgr = HomeLayoutManager(tmpdir)
            ls.layout_mgr.reorder_pinned_apps(["a", "b", "c"])

            # Populate 3 dummy children in visual order a, b, c (Kivy stores reversed)
            ls.home_grid.clear_widgets()
            w_a = Widget(pos=(10, 400), size=(82, 96))
            w_b = Widget(pos=(110, 400), size=(82, 96))
            w_c = Widget(pos=(210, 400), size=(82, 96))
            ls.home_grid.add_widget(w_a)
            ls.home_grid.add_widget(w_b)
            ls.home_grid.add_widget(w_c)

            # Drop 'a' onto slot 2 ('c') with moved_dist > dp(18) -> moves 'a' to index 2
            ls.finish_drag(_FakeIcon("a", is_home=True), (250, 440), moved_dist=dp(120))
            self.assertEqual(ls.layout_mgr.get_pinned_apps(), ["b", "c", "a"])


if __name__ == "__main__":
    unittest.main()

