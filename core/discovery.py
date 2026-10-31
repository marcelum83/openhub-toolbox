"""
OpenHub LAN Auto-Discovery Protocol
Enables OpenHub on mobile (Pixel 7a) and Desktop Server to find each other
automatically across dynamic Wi-Fi Hotspots with zero manual IP configuration.
"""
import os
import json
import time
import socket
import threading

DISCOVERY_PORT = 8089
PROBE_MESSAGE = b"OPENHUB_DISCOVER"


class LANDiscoveryBeacon:
    """
    Runs on Desktop. Broadcasts presence and replies to mobile discovery probes.
    """
    def __init__(self, host_ip, server_port=8080, ollama_port=11434):
        self.host_ip = host_ip
        self.server_port = server_port
        self.ollama_port = ollama_port
        self.running = False
        self._thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _run_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", DISCOVERY_PORT))
        except Exception as e:
            print(f"[DiscoveryBeacon] Warning binding port {DISCOVERY_PORT}: {e}")

        sock.settimeout(1.0)
        payload = json.dumps({
            "service": "openhub_desktop",
            "server_host": f"{self.host_ip}:{self.server_port}",
            "ip": self.host_ip,
            "port": self.server_port,
            "ollama_port": self.ollama_port
        }).encode('utf-8')

        last_broadcast = 0
        while self.running:
            now = time.time()
            # 1. Periodic broadcast beacon every 2.5s
            if now - last_broadcast > 2.5:
                last_broadcast = now
                for dest in ["255.255.255.255", "<broadcast>"]:
                    try:
                        sock.sendto(payload, (dest, DISCOVERY_PORT))
                    except Exception:
                        pass

                # If gateway is known (e.g. phone hotspot gateway), send directly to it
                try:
                    gw = os.popen("ip route get 1.1.1.1 2>/dev/null | awk '{print $3}'").read().strip()
                    if gw and gw != self.host_ip:
                        sock.sendto(payload, (gw, DISCOVERY_PORT))
                except Exception:
                    pass

            # 2. Listen for direct probes from phone
            try:
                data, addr = sock.recvfrom(1024)
                if PROBE_MESSAGE in data:
                    sock.sendto(payload, addr)
            except (socket.timeout, BlockingIOError):
                pass
            except Exception:
                pass

        sock.close()


def discover_server(timeout=1.5, callback=None):
    """
    Runs on Mobile. Broadcasts discovery probe and listens for desktop beacon response.
    Dispatches callback(discovered_server_host_str or None).
    """
    def _worker():
        discovered = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(0.35)

            # Targets: Global broadcast + local ARP neighbors (Android hotspot clients)
            targets = ["255.255.255.255"]
            try:
                if os.path.exists("/proc/net/arp"):
                    with open("/proc/net/arp", "r") as f:
                        for line in f:
                            parts = line.split()
                            if len(parts) > 0 and parts[0] != "IP":
                                targets.append(parts[0])
            except Exception:
                pass

            start_t = time.time()
            while time.time() - start_t < timeout:
                # Send probe to all targets
                for t in targets:
                    try:
                        sock.sendto(PROBE_MESSAGE, (t, DISCOVERY_PORT))
                    except Exception:
                        pass

                # Wait for response
                try:
                    data, addr = sock.recvfrom(1024)
                    info = json.loads(data.decode('utf-8'))
                    if info.get("service") == "openhub_desktop":
                        discovered = info.get("server_host")
                        break
                except (socket.timeout, BlockingIOError):
                    time.sleep(0.1)
                except Exception:
                    time.sleep(0.1)

            sock.close()
        except Exception as e:
            print(f"[LANDiscovery] Probe error: {e}")

        if callback:
            try:
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: callback(discovered), 0)
            except Exception:
                callback(discovered)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
