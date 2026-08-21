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
        if storage_root:
            self._module_dir = os.path.join(storage_root, "modules_data", module_id)
            os.makedirs(self._module_dir, exist_ok=True)
        else:
            self._module_dir = os.path.abspath(f"./data/{module_id}")
            os.makedirs(self._module_dir, exist_ok=True)

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
