#!/usr/bin/env bash
# ==============================================================================
# 🌌 OpenHub Workstation Server & Auto-Discovery Bridge
# Automatically detects dynamic hotspot IPs, configures USB/Wi-Fi routes,
# verifies Ollama, and broadcasts LAN auto-discovery beacons to your Pixel 7a.
# ==============================================================================
set -e
cd "$(dirname "$0")"

# 1. Detect Active LAN / Wi-Fi Hotspot IP
IP_ADDR=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' || hostname -I | awk '{print $1}')
if [ -z "$IP_ADDR" ]; then
    IP_ADDR="127.0.0.1"
fi
PORT=8080

# Clean up any stale sync_server holding port 8080
if fuser 8080/tcp >/dev/null 2>&1; then
    fuser -k 8080/tcp >/dev/null 2>&1 || true
    sleep 0.5
fi

# 2. Check and start Ollama if not running
if ! pgrep -f "ollama serve" > /dev/null 2>&1; then
    echo "⚙️ Starting Ollama local model service..."
    ollama serve > /dev/null 2>&1 &
    sleep 1
fi

# 3. Check for USB-connected Android device (ADB Reverse)
ADB_ATTACHED=false
if command -v adb >/dev/null 2>&1; then
    # Start server if needed
    adb start-server > /dev/null 2>&1 || true
    DEV_COUNT=$(adb devices | grep -v "List of devices" | grep "device$" | wc -l)
    if [ "$DEV_COUNT" -gt 0 ]; then
        adb reverse tcp:8080 tcp:8080 2>/dev/null || true
        adb reverse tcp:11434 tcp:11434 2>/dev/null || true
        adb reverse tcp:8089 tcp:8089 2>/dev/null || true
        ADB_ATTACHED=true
    fi
fi

# 4. Update settings.json so desktop tools and default configs match
python3 -c "
import json, os
s_path = 'settings.json'
data = {}
if os.path.exists(s_path):
    try:
        with open(s_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        pass
data['server_host'] = '${IP_ADDR}:${PORT}'
with open(s_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
"

# 5. Display Clean Terminal Dashboard
echo "=================================================================="
echo "🌌 OPENHUB DESKTOP SERVER & BRIDGE ACTIVE"
echo "=================================================================="
echo "📡 Hotspot / Wi-Fi Address: http://${IP_ADDR}:${PORT}"
echo "🤖 Local Ollama Endpoint:   http://${IP_ADDR}:11434"
if [ "$ADB_ATTACHED" = true ]; then
echo "🔌 USB Tethering (ADB):     CONNECTED (localhost:8080 & 11434)"
else
echo "🔌 USB Tethering:           Not connected (using wireless hotspot)"
fi
echo "🔍 LAN Auto-Discovery:      BROADCASTING on UDP 8089"
echo "=================================================================="
echo "👉 Simply open OpenHub on your Pixel 7a!"
echo "   It will auto-discover this desktop server over Wi-Fi."
echo "   Press Ctrl+C to stop the server."
echo "=================================================================="
echo ""

TELEPATHY_PID=""
FIREBASE_KEY="/home/mike/Documents/nexus-core/nexus_portfolio/engine/firebase_admin_key.json"
if [ ! -f "$FIREBASE_KEY" ] && [ -f "/home/mike/Documents/Nexus_Core/ACE/simple_agent/firebase_admin_key.json" ]; then
    FIREBASE_KEY="/home/mike/Documents/Nexus_Core/ACE/simple_agent/firebase_admin_key.json"
fi

PYTHON_BIN="python3"
if [ -f "/home/mike/Documents/main/ACE/.venv_nexus/bin/python" ]; then
    PYTHON_BIN="/home/mike/Documents/main/ACE/.venv_nexus/bin/python"
fi

if [ -f "$FIREBASE_KEY" ] && [ -f "$PYTHON_BIN" ]; then
    $PYTHON_BIN desktop_telepathy_daemon.py > telepathy.log 2>&1 &
    TELEPATHY_PID=$!
    echo "🛰️ Cloud Telepathy Relay:   ACTIVE (PID $TELEPATHY_PID, listening on nexus-ops-2026)"
fi

cleanup() {
    if [ -n "$TELEPATHY_PID" ]; then
        kill $TELEPATHY_PID 2>/dev/null || true
    fi
    exit 0
}
trap cleanup INT TERM EXIT

# 6. Run Central Sync & Auto-Discovery Server
$PYTHON_BIN core/sync_server.py --host "$IP_ADDR" --port "$PORT"

