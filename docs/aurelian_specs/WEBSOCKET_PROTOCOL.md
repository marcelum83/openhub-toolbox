# 📡 Aurelian WebSocket Protocol (Antigravity Link)

This document defines the communication standard between the **Aurelian Hub (Server)** and the **Native Kivy Application (Client)**.

## 🔗 Connection Details
- **Protocol**: WebSocket (Secure or Standard)
- **Default Port**: `8888`
- **Endpoint**: `ws://[SERVER_IP]:8888`

---

## 📱 Outbound (Client -> Server)

### 1. Natural Language Intent
Sent as a plain string.
- **Example**: `"How is the project looking today?"`
- **Effect**: Distributes the message to all clients in the session history.

### 2. Aurelian Directive (@A)
Sent as a string prefixed with `@A`.
- **Example**: `"@A design a new dashboard for my smart home."`
- **Effect**: Triggers the Aurelian Agent (Control Plane) to synthesize a response or generate code.

### 3. Structured Signals
Wrapped in brackets `[]` for machine-parsing.
- **Choice Signal**: `[CHOICE_MADE: {"scene": "intro", "id": "yes", "label": "Proceed"}]`
- **Update Requested**: `[FETCH_UPDATES]` (Future)
- **Auth Packet**: `[AUTH: {"token": "..."}]` (Future)

---

## 🧠 Inbound (Server -> Client)

### 1. Chat Feed (Plain Text)
Formatted text strings for display in the message UI.
- **Format**: `[timestamp] Sender: Message`
- **Example**: `[22:05:00] 🦞 OpenClaw: I have completed the architecture nexus.`

### 2. UI Payload (Canvas)
JSON object used to render web-based visual components (Hub Dashboard).
- **Format**:
```json
{
  "type": "canvas",
  "html": "...(Rendered HTML/CSS)...",
  "timestamp": "HH:MM:SS"
}
```

### 3. Deployment Payload (Code Delivery)
JSON object specifically for the Kivy Execution Plane to trigger dynamic updates.
- **Format**:
```json
{
  "type": "deployment",
  "action": "hot_reload" | "install",
  "module": "name_of_module",
  "filename": "main.py",
  "code": "...(Python Code Content)...",
  "commit_hash": "optional_git_hash"
}
```

---

## 🔄 Interaction Flow

1. **User Request**: Kivy app sends `@A create a stopwatch`.
2. **Server Processing**: `chat_server.py` routes to Aurelian.
3. **Response Cycle**: 
   - Server sends text updates: `[Asking Aurelian...]`
   - Server sends `type: "canvas"` to update the Hub UI (Web).
   - Server sends `type: "deployment"` to the Kivy app.
4. **Execution**: Kivy app receives code, saves to local storage, and performs a native reload of the new module.
