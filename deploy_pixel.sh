#!/usr/bin/env bash
# Build OpenHub APK and serve it on the local download server
set -e
cd "$(dirname "$0")"

# Check for --serve-only or -s flag
SERVE_ONLY=false
if [ "$1" == "--serve-only" ] || [ "$1" == "-s" ]; then
    SERVE_ONLY=true
fi

if [ "$SERVE_ONLY" = false ]; then
    source /home/mike/Documents/main/MicroProjects/VortexIDE/.venv/bin/activate
    export PATH="/home/mike/Documents/main/MicroProjects/VortexIDE/.venv/bin:$PATH"

    # Sync .txt companions for built-in modules
    for d in modules/*/; do
        if [ -f "$d/main.py" ]; then
            cp "$d/main.py" "$d/main.py.txt"
        fi
    done

    echo "=========================================="
    echo "🔨 Building OpenHub Android APK (Release/Debug)..."
    echo "=========================================="
    buildozer android debug

    # Generate version.json
    BUILD_TS=$(date +%s)
    BUILD_DATE=$(date "+%Y-%m-%d %H:%M:%S")
    cat <<EOF > bin/version.json
{
  "version": "1.0.0",
  "build_timestamp": ${BUILD_TS},
  "build_date": "${BUILD_DATE}",
  "apk_filename": "openhub-1.0.0-arm64-v8a-debug.apk",
  "changelog": "OpenHub Core with 9 Sensor Tools & Live Auto-Updater"
}
EOF

    echo ""
    echo "=========================================="
    echo "📦 APK Built Successfully in bin/:"
    ls -lh bin/*.apk
    echo "=========================================="
fi

# Find local WiFi / Hotspot IP
IP_ADDR=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' || echo "10.62.206.29")
PORT=8080

echo ""
echo "=========================================="
echo "🚀 OpenHub APK Server is LIVE!"
echo "👉 Open Chrome on your Pixel 7a and go to:"
echo "   http://${IP_ADDR}:${PORT}"
echo "=========================================="
echo "Press Ctrl+C to stop the server."
echo ""

# Start HTTP Server on all interfaces
python3 -m http.server "$PORT" --directory bin --bind 0.0.0.0
