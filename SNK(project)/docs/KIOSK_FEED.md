# Biometric Kiosk Real-Time Feed Architecture

## 1. Overview & Institutional LAN Problem Statement

In academic institutions and university campuses, biometric kiosks and digital signage screens are deployed across multiple faculty blocks, department lounges, and administrative buildings. 

These physical environments present specific networking challenges:
1. **Flaky Wi-Fi & Channel Congestion:** High device density during shift changeover (08:45 AM – 09:15 AM) causes RF packet drops, sudden socket disconnects, and intermittent packet loss.
2. **Aggressive Institutional Middleboxes & Firewalls:** State inspection proxies, captive portals, and campus edge routers terminate idle TCP connections after 30–60 seconds, breaking naive socket connections.
3. **Resource Leakage with Heavy WebSockets:** Full-duplex WebSocket connections require persistent state machines, duplex thread pooling, and complex ping/pong handshakes. On embedded mini-PCs or kiosk touchscreens running 24/7, uncaught socket errors often lead to socket exhaustion or silent zombie connections.

To solve these constraints with zero external cloud dependencies, the ERP implements a **Dual-Mode Kiosk Architecture**:
- **Primary Channel:** HTTP Server-Sent Events (SSE) via `/api/kiosk/stream`.
- **Fallback Channel:** Adaptive HTTP Polling (every 3 seconds) via `/api/kiosk/recent`.

---

## 2. Architecture Diagram

```
+-----------------------------------------------------------------------------------------+
|                                    CAMPUS NETWORK                                       |
|                                                                                         |
|  +------------------------+                                                             |
|  | Smartphone / Faculty   |                                                             |
|  | WebAuthn Punch Client  |                                                             |
|  +-----------+------------+                                                             |
|              | HTTP POST /api/punch                                                     |
|              v                                                                          |
|  +----------------------------------------------------+                                 |
|  | FastAPI Embedded Mobile Punch Server (Port 5000)   |                                 |
|  |   - Validates rotating TOTP QR Token               |                                 |
|  |   - Evaluates late minutes (09:00:00 shift)        |                                 |
|  |   - Updates MySQL / Memory Attendance Log          |                                 |
|  |   - Calls broadcast_kiosk_punch(punch_data)        |                                 |
|  +---------------------------+------------------------+                                 |
|                              |                                                          |
|          +-------------------+--------------------+                                     |
|          |                                        |                                     |
|          | (SSE Broadcast)                        | (Circular Buffer: 50)               |
|          v                                        v                                     |
|   _kiosk_subscribers Set                  _recent_kiosk_punches                         |
|   [ asyncio.Queue, ... ]                  [ punch_1, punch_2, ... ]                     |
|          |                                        |                                     |
+----------|----------------------------------------|-------------------------------------+
           |                                        |
           | GET /api/kiosk/stream                  | GET /api/kiosk/recent
           | (Primary SSE Channel)                  | (3-second Polling Fallback)
           |                                        |
+----------v----------------------------------------v-------------------------------------+
|                     DEPARTMENT KIOSK DISPLAY / MONITOR                                  |
|                                                                                         |
|  - On boot: Connects to EventSource('/api/kiosk/stream')                               |
|  - Receives 'INIT' handshake event with last 5 punches (instant display restoration)   |
|  - Receives real-time 'PUNCH' events as faculty check in                                |
|  - If EventSource encounters onerror:                                                  |
|      1. Switches automatically to polling /api/kiosk/recent every 3.0s                  |
|      2. Deduplicates incoming records via unique employee_code + timestamp             |
|      3. Re-attempts SSE handshake in background with exponential backoff               |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Engineering Safeguards & Zero-Leak Mechanics

### A. Automatic Socket Lifecycle & Cleanup
Each SSE client connection instantiates an isolated `asyncio.Queue()` that is added to the module-level subscriber set `_kiosk_subscribers`.

```python
async def event_generator():
    queue: asyncio.Queue = asyncio.Queue()
    _kiosk_subscribers.add(queue)
    try:
        ...
        while True:
            if await request.is_disconnected():
                break
            punch = await asyncio.wait_for(queue.get(), timeout=15.0)
            yield f"data: {json.dumps({'type': 'PUNCH', 'data': punch})}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _kiosk_subscribers.discard(queue)
```

**Key Guarantees:**
- **No Memory Leaks:** The `finally` block guarantees that whether the connection terminates cleanly, times out, or drops due to a broken Wi-Fi link, the queue is removed from `_kiosk_subscribers`.
- **No Dangling Tasks:** Unlike raw threads, `asyncio.wait_for(..., timeout=15.0)` wakes up every 15 seconds to evaluate `request.is_disconnected()`.
- **Proxy Keepalive:** Every 15-second timeout yields an SSE comment `: keepalive\n\n`. This prevents campus edge proxies and NAT routers from closing the TCP stream due to perceived inactivity.

### B. In-Memory Ring Buffer for Reconnection Resilience
A lightweight ring buffer (`_recent_kiosk_punches`) maintains the 50 most recent punch events. 
- When an SSE client connects, the initial packet delivers `"recent": _recent_kiosk_punches[-5:]`. Even if the kiosk terminal was rebooted during peak morning arrival, the display immediately populates the latest check-ins without querying the relational database.
- If the SSE stream drops entirely, the client's fallback poll (`GET /api/kiosk/recent`) fetches the latest punches from this memory buffer with sub-millisecond response time.

---

## 4. API Endpoints Specification

### 1. `GET /api/kiosk/stream`
- **Protocol:** HTTP/1.1 Server-Sent Events (`text/event-stream`)
- **Headers:**
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no` (disables Nginx reverse-proxy buffering)
- **Event Types:**
  - `INIT`: Sent immediately on connection. Contains `server_time` and the latest 5 punches.
  - `PUNCH`: Dispatched in real time when any faculty member logs an attendance punch.
  - `: keepalive\n\n`: Heartbeat ping emitted every 15 seconds of inactivity.

### 2. `GET /api/kiosk/recent`
- **Protocol:** HTTP GET
- **Response Format:** JSON
- **Sample Output:**
```json
{
  "status": "SUCCESS",
  "total": 4,
  "punches": [
    {
      "employee_code": "F001",
      "full_name": "Dr. Sarah Jenkins",
      "department": "MCA",
      "punch_type": "CHECK_IN",
      "punch_date": "2026-10-30",
      "punch_time": "08:55:12",
      "shift_start": "09:00:00",
      "late_minutes": 0,
      "working_hours": 0.0,
      "status": "PRESENT",
      "biometric_verified": true,
      "auth_method": "WEBAUTHN"
    }
  ]
}
```

---

## 5. Security & Isolation Considerations
1. **Read-Only Observation:** The kiosk stream and polling endpoints are strictly read-only. No write operations or identity modifications are accepted on `/api/kiosk/*`.
2. **Rate Limiting Exemption on Kiosk Loop:** While authentication (`/api/verify-credentials`) and check-in submissions (`/api/punch`) are strictly rate-limited (30 req/min), the kiosk feed endpoints allow designated local display terminals to stream continuously without artificial throttling.
3. **Data Sanitization:** Punch events broadcast employee code, name, department, arrival timestamp, and on-time status. Sensitive credentials, passwords, cryptographic private keys, and session cookies are never exposed in the broadcast payload.
