"""
Desktop Cloud Telepathy Daemon (Nexus Bridge)
Listens to Firebase Firestore (nexus-ops-2026) for mobile agent commands dispatched from
OpenHub on Pixel 7a when away from home Wi-Fi, passes them to local Ollama (qwen2.5-coder:7b),
and writes the AI response back to the cloud.
"""
import os
import sys
import json
import time
import urllib.request
import firebase_admin
from firebase_admin import credentials, firestore

KEY_PATHS = [
    "/home/mike/Documents/Nexus_Core/ACE/simple_agent/firebase_admin_key.json",
    "/home/mike/Documents/nexus-core/nexus_portfolio/engine/firebase_admin_key.json"
]
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5-coder:7b"


def init_firebase():
    key_path = next((p for p in KEY_PATHS if os.path.exists(p)), None)
    if not key_path:
        raise FileNotFoundError(f"Firebase admin key not found in {KEY_PATHS}")
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def query_local_ollama(prompt, sensor_ctx="", model=DEFAULT_MODEL):
    """Sends prompt and live sensor telemetry to local Ollama instance on GPU."""
    sys_prompt = "You are OpenHub Assistant running on the user's desktop workstation via Cloud Telepathy. Answer clearly and concisely."
    if sensor_ctx:
        sys_prompt += f"\nLive Phone Sensors:\n{sensor_ctx}"

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.3}
    }).encode('utf-8')

    try:
        req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get("message", {}).get("content", ""), ""
    except Exception as e:
        return "", f"Local Ollama error: {e}"


def run_daemon():
    print("==================================================")
    print("📡 Nexus Cloud Telepathy Daemon Live")
    print("   Project: nexus-ops-2026")
    print("   Local GPU Model: qwen2.5-coder:7b")
    print("   Listening for remote mobile commands...")
    print("==================================================")

    db = init_firebase()
    col = db.collection("agent_commands")

    while True:
        try:
            # Query for pending mobile commands
            pending_query = col.where("status", "==", "PENDING").limit(5).stream()
            for doc in pending_query:
                doc_id = doc.id
                data = doc.to_dict()
                print(f"\n[Telepathy] 📥 Inbound command received: {doc_id}")

                # Mark as processing
                col.document(doc_id).update({"status": "PROCESSING", "started_at": int(time.time() * 1000)})

                payload = data.get("payload", {})
                user_text = payload.get("text", "")
                sensor_info = payload.get("sensor_context", "")

                if not user_text and "text" in data:
                    user_text = data.get("text", "")

                print(f"[Telepathy] 🤖 Generating response on local GPU for: '{user_text[:40]}...'")
                reply, err = query_local_ollama(user_text, sensor_info)

                if err:
                    print(f"[Telepathy] ❌ Error: {err}")
                    col.document(doc_id).update({
                        "status": "ERROR",
                        "error": err,
                        "updated_at": int(time.time() * 1000)
                    })
                else:
                    print(f"[Telepathy] ✅ Reply generated ({len(reply)} chars). Pushing to cloud...")
                    col.document(doc_id).update({
                        "status": "COMPLETED",
                        "response": reply,
                        "provider": "workstation_rtx3060_ollama",
                        "completed_at": int(time.time() * 1000)
                    })

        except Exception as e:
            print(f"[Telepathy] Loop notice: {e}")

        time.sleep(1.5)


if __name__ == "__main__":
    run_daemon()
