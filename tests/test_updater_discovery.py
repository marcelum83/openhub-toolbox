"""Unit tests for OpenHub UpdateManager build timestamp matching and LAN discovery."""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ.setdefault("KIVY_NO_ARGS", "1")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from kivy.clock import Clock

from core.discovery import _probe_http_server
from core.updater import UpdateManager


class TestUpdaterAndDiscovery(unittest.TestCase):
    def test_bundled_build_meta_prevents_repeat_update_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ts = 1793479000
            with open(os.path.join(tmpdir, "build_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"version": "1.0.0", "build_timestamp": ts}, f)

            mgr = UpdateManager(tmpdir)
            self.assertEqual(mgr.local_build_ts, ts)

            # Spin up tiny mock /version.json server returning same ts, then newer ts
            server_ts = {"val": ts}

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/version.json":
                        body = json.dumps({
                            "version": "1.0.0",
                            "build_timestamp": server_ts["val"],
                            "apk_filename": "openhub-1.0.0-arm64-v8a-debug.apk",
                        }).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(body)

                def log_message(self, format, *args):
                    pass

            srv = HTTPServer(("127.0.0.1", 0), Handler)
            port = srv.server_address[1]
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                mgr.save_server_host(f"127.0.0.1:{port}")

                # HTTP discovery probe should detect this server
                self.assertEqual(_probe_http_server("127.0.0.1", port=port), f"127.0.0.1:{port}")

                results = []
                mgr.check_for_updates(on_result=lambda has_upd, data, err: results.append((has_upd, data, err)))
                for _ in range(30):
                    Clock.tick()
                    if results:
                        break
                    import time
                    time.sleep(0.02)

                self.assertEqual(len(results), 1)
                self.assertFalse(results[0][0], "Same build_timestamp must not prompt to re-download")
                self.assertIsNone(mgr.latest_update_info)

                # Now bump server timestamp and verify update IS detected
                server_ts["val"] = ts + 100
                results.clear()
                mgr.check_for_updates(on_result=lambda has_upd, data, err: results.append((has_upd, data, err)))
                for _ in range(30):
                    Clock.tick()
                    if results:
                        break
                    import time
                    time.sleep(0.02)

                self.assertEqual(len(results), 1)
                self.assertTrue(results[0][0], "Newer build_timestamp should prompt for update")
                self.assertIsNotNone(mgr.latest_update_info)
            finally:
                srv.shutdown()
                srv.server_close()


if __name__ == "__main__":
    unittest.main()

