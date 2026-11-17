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
EDGE_DISCOVERY_PORT = 8091
EDGE_PROBE_MESSAGE = b"OPENHUB_EDGE_DISCOVER"


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


def _is_private_ipv4(ip):
    if not ip or "." not in ip or ip.startswith("127."):
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    return a == 10 or (a == 192 and b == 168) or (a == 172 and 16 <= b <= 31)


def _get_local_ipv4s():
    """Returns active non-loopback local IPv4 addresses, prioritizing Wi-Fi/Hotspot RFC1918 IPs."""
    ips = []

    # 1. Android NetworkInterface enumeration (captures wlan0 / ap0 / rndis0 even without cellular interference)
    try:
        from kivy.utils import platform
        if platform == "android":
            from jnius import autoclass
            NetworkInterface = autoclass("java.net.NetworkInterface")
            Inet4Address = autoclass("java.net.Inet4Address")
            en = NetworkInterface.getNetworkInterfaces()
            while en and en.hasMoreElements():
                ni = en.nextElement()
                name = (ni.getName() or "").lower()
                if "rmnet" in name or "ccmni" in name:
                    continue
                addrs = ni.getInetAddresses()
                while addrs and addrs.hasMoreElements():
                    addr = addrs.nextElement()
                    if isinstance(addr, Inet4Address) and not addr.isLoopbackAddress():
                        ip = addr.getHostAddress()
                        if ip and ip not in ips:
                            ips.append(ip)
    except Exception:
        pass

    # 2. UDP route-table probes across RFC1918 + public (never sends packets)
    for target in ("10.255.255.255", "192.168.255.255", "172.16.255.255", "8.8.8.8"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.15)
            s.connect((target, 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
        except Exception:
            pass

    # Put RFC1918 private LAN/hotspot IPs first
    private = [ip for ip in ips if _is_private_ipv4(ip)]
    other = [ip for ip in ips if ip not in private]
    return private + other


def _get_local_ipv4():
    """Returns the primary local Wi-Fi/LAN IPv4 address."""
    ips = _get_local_ipv4s()
    return ips[0] if ips else None


def _probe_http_server(ip, port=8080, timeout=0.45):
    """Checks whether an OpenHub sync server is listening at ip:port."""
    try:
        # Fast TCP handshake check first to fail dead IPs in <=0.22s
        with socket.create_connection((ip, int(port)), timeout=min(0.25, timeout)):
            pass
        import urllib.request
        url = f"http://{ip}:{port}/version.json"
        req = urllib.request.Request(url, headers={"User-Agent": "OpenHub-Discovery"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and ("apk_filename" in data or "version" in data):
                    return f"{ip}:{port}"
    except Exception:
        pass
    return None


def _build_subnet_candidates(local_ips, extra_hosts=None):
    """Builds ordered candidate IP list across active /24 subnets."""
    if isinstance(local_ips, str):
        local_ips = [local_ips]
    local_ips = [ip for ip in (local_ips or []) if ip]

    candidates = []
    if extra_hosts:
        for h in extra_hosts:
            if h:
                host_ip = str(h).split(":")[0].strip()
                if host_ip:
                    candidates.append(host_ip)
    candidates.append("127.0.0.1")

    seen_prefixes = set()
    for local_ip in local_ips:
        if "." in local_ip and not local_ip.startswith("127."):
            prefix = ".".join(local_ip.split(".")[:3])
            if prefix in seen_prefixes:
                continue
            seen_prefixes.add(prefix)
            priority = [f"{prefix}.1", f"{prefix}.2", f"{prefix}.29"]
            rest = [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" not in priority and f"{prefix}.{i}" != local_ip]
            candidates.extend(priority + rest)

    return list(dict.fromkeys(candidates))


def _build_udp_targets(local_ips):
    """Builds broadcast + neighbor UDP probe targets."""
    targets = ["255.255.255.255"]
    for local_ip in local_ips:
        if "." in local_ip:
            prefix = ".".join(local_ip.split(".")[:3])
            targets.extend([f"{prefix}.255", f"{prefix}.1"])
    try:
        if os.path.exists("/proc/net/arp"):
            with open("/proc/net/arp", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) > 0 and parts[0] != "IP":
                        targets.append(parts[0])
    except Exception:
        pass
    return list(dict.fromkeys(targets))


def _http_subnet_scan(local_ips, port=8080, extra_hosts=None):
    """Fast concurrent TCP+HTTP /version.json scan across active local /24 subnets."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    candidates = _build_subnet_candidates(local_ips, extra_hosts=extra_hosts)
    if not candidates:
        return None

    pool = ThreadPoolExecutor(max_workers=64)
    try:
        futures = [pool.submit(_probe_http_server, ip, port) for ip in candidates]
        for fut in as_completed(futures, timeout=3.0):
            try:
                res = fut.result()
                if res:
                    return res
            except Exception:
                pass
    except Exception:
        pass
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return None


def discover_server(timeout=1.5, callback=None, extra_hosts=None):
    """
    Runs on Mobile. Discovers the OpenHub Desktop Server using:
    1. Directed + global UDP probes (on an unbound reply socket) and beacon listening.
    2. Fast TCP+HTTP /version.json subnet sweep fallback across Wi-Fi/Hotspot /24s.
    Dispatches callback(discovered_server_host_str or None).
    """
    def _worker():
        discovered = None
        local_ips = _get_local_ipv4s()

        # 1. UDP Discovery (unbound probe socket avoids receiving our own broadcast!)
        try:
            probe_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            probe_sock.settimeout(0.25)

            beacon_sock = None
            try:
                beacon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                beacon_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                beacon_sock.bind(("", DISCOVERY_PORT))
                beacon_sock.settimeout(0.05)
            except Exception:
                if beacon_sock:
                    beacon_sock.close()
                beacon_sock = None

            targets = _build_udp_targets(local_ips)

            start_t = time.time()
            udp_budget = min(1.0, float(timeout))
            while time.time() - start_t < udp_budget and not discovered:
                for t in targets:
                    try:
                        probe_sock.sendto(PROBE_MESSAGE, (t, DISCOVERY_PORT))
                    except Exception:
                        pass

                for s in (probe_sock, beacon_sock):
                    if s is None:
                        continue
                    try:
                        while True:
                            data, _addr = s.recvfrom(1024)
                            if PROBE_MESSAGE in data:
                                continue
                            info = json.loads(data.decode("utf-8"))
                            if info.get("service") == "openhub_desktop":
                                discovered = info.get("server_host")
                                break
                    except (socket.timeout, BlockingIOError):
                        pass
                    except Exception:
                        pass
                    if discovered:
                        break

                if not discovered:
                    time.sleep(0.08)

            probe_sock.close()
            if beacon_sock:
                beacon_sock.close()
        except Exception as e:
            print(f"[LANDiscovery] UDP probe notice: {e}")

        # 2. Fast HTTP /version.json subnet scan fallback
        if not discovered:
            try:
                discovered = _http_subnet_scan(local_ips, port=8080, extra_hosts=extra_hosts)
            except Exception as e:
                print(f"[LANDiscovery] HTTP scan error: {e}")

        if callback:
            try:
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: callback(discovered), 0)
            except Exception:
                callback(discovered)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def _probe_edge_seed(ip, port=8090, timeout=0.45):
    """Checks whether an OpenHub edge node serves /seed.json at ip:port."""
    try:
        with socket.create_connection((ip, int(port)), timeout=min(0.22, timeout)):
            pass
        import urllib.request
        url = f"http://{ip}:{port}/seed.json"
        req = urllib.request.Request(url, headers={"User-Agent": "OpenHub-EdgeDiscovery"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and "node_type" in data:
                    return {
                        "service": "openhub_edge",
                        "name": data.get("title", f"Edge Node ({ip})"),
                        "ip": ip,
                        "port": int(port),
                        "seed_url": url,
                    }
    except Exception:
        pass
    return None


def discover_edge_nodes(timeout=1.4, ports=(8090,), callback=None, extra_hosts=None):
    """
    Discovers OpenHub L-system Edge Hardware Nodes (Van Pi, Shed Solar, Greenhouse)
    via UDP beacon probes on port 8091, with fast HTTP /seed.json subnet scan fallback.
    Dispatches callback(list_of_node_dicts).
    """
    def _worker():
        found = {}
        local_ips = _get_local_ipv4s()

        # 1. UDP Edge Node Discovery on EDGE_DISCOVERY_PORT (8091)
        try:
            probe_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            probe_sock.settimeout(0.2)

            beacon_sock = None
            try:
                beacon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                beacon_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                beacon_sock.bind(("", EDGE_DISCOVERY_PORT))
                beacon_sock.settimeout(0.05)
            except Exception:
                if beacon_sock:
                    beacon_sock.close()
                beacon_sock = None

            targets = _build_udp_targets(local_ips)
            start_t = time.time()
            udp_budget = min(0.9, float(timeout))
            while time.time() - start_t < udp_budget:
                for t in targets:
                    try:
                        probe_sock.sendto(EDGE_PROBE_MESSAGE, (t, EDGE_DISCOVERY_PORT))
                    except Exception:
                        pass
                for s in (probe_sock, beacon_sock):
                    if s is None:
                        continue
                    try:
                        while True:
                            data, addr = s.recvfrom(1024)
                            if EDGE_PROBE_MESSAGE in data:
                                continue
                            info = json.loads(data.decode("utf-8"))
                            if info.get("service") == "openhub_edge" and info.get("seed_url"):
                                seed_url = info["seed_url"]
                                found[seed_url] = {
                                    "service": "openhub_edge",
                                    "name": info.get("name", f"Edge ({addr[0]})"),
                                    "ip": info.get("ip", addr[0]),
                                    "port": info.get("port", 8090),
                                    "seed_url": seed_url,
                                }
                    except (socket.timeout, BlockingIOError):
                        pass
                    except Exception:
                        pass
                if found:
                    break
                time.sleep(0.08)

            probe_sock.close()
            if beacon_sock:
                beacon_sock.close()
        except Exception as e:
            print(f"[EdgeDiscovery] UDP probe notice: {e}")

        # 2. HTTP /seed.json subnet scan fallback if UDP found nothing
        if not found:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            candidates = _build_subnet_candidates(local_ips, extra_hosts=extra_hosts)
            pool = ThreadPoolExecutor(max_workers=64)
            try:
                futures = [
                    pool.submit(_probe_edge_seed, ip, p)
                    for p in ports
                    for ip in candidates
                ]
                for fut in as_completed(futures, timeout=2.5):
                    try:
                        res = fut.result()
                        if res and res["seed_url"] not in found:
                            found[res["seed_url"]] = res
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                pool.shutdown(wait=False, cancel_futures=True)

        nodes_list = list(found.values())
        if callback:
            try:
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: callback(nodes_list), 0)
            except Exception:
                callback(nodes_list)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
