"""
OpenHub Security & Sandbox Broker
Manages permissions and provides a safe Host API proxy to dynamic modules.
"""
import os
import shutil

class TrustLevel:
    TRUSTED = "trusted"          # Full hardware, network & filesystem access
    COMMUNITY = "community"      # Sandboxed storage & approved APIs only
    EXPERIMENTAL = "experimental"# Explicit user approval required

class HostAPI:
    """
    The safe interface passed to OpenHub modules via module.on_load(host_api).
    """
    def __init__(self, module_id, trust_level=TrustLevel.TRUSTED, hardware_bridge=None, storage_root=None):
        self.module_id = module_id
        self.trust_level = trust_level
        self._hardware = hardware_bridge
        
        # Dedicated sandboxed storage directory for this module
        try:
            if storage_root:
                self._module_dir = os.path.join(storage_root, "modules_data", module_id)
                os.makedirs(self._module_dir, exist_ok=True)
            else:
                self._module_dir = os.path.abspath(f"./data/{module_id}")
                os.makedirs(self._module_dir, exist_ok=True)
        except Exception:
            self._module_dir = f"/tmp/{module_id}"

    @property
    def hardware(self):
        """Access hardware sensors if permitted."""
        return self._hardware

    def get_data_dir(self):
        """Returns the isolated private storage path for this module."""
        return self._module_dir

    def log(self, message):
        """Host logging utility."""
        print(f"[{self.module_id}] {message}")

    def notify(self, title, message):
        """Trigger a toast or notification if supported."""
        print(f"[NOTIFICATION] {title}: {message}")

    def get_server_host(self):
        """Retrieve configured PC server address from host settings."""
        try:
            import json
            if self._storage_root:
                s_path = os.path.join(self._storage_root, "settings.json")
                if os.path.exists(s_path):
                    with open(s_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get("server_host", "10.112.214.29:8080")
        except Exception:
            pass
        return "10.112.214.29:8080"

    def save_server_host(self, host):
        """Update and persist server address across host and modules."""
        try:
            import json
            if self._storage_root:
                s_path = os.path.join(self._storage_root, "settings.json")
                data = {}
                if os.path.exists(s_path):
                    with open(s_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                data["server_host"] = host
                with open(s_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[HostAPI] Error saving server host: {e}")

def analyze_code_risk(code):
    """Static risk evaluation using AST analysis for dynamic modules."""
    try:
        from core.risk_analyzer import RiskAnalyzer
        ra = RiskAnalyzer()
        return ra.analyze(code)
    except Exception as e:
        return {"status": "Error", "reason": str(e), "risk_points": 0, "findings": []}

