# Card 02 — WebSocket Protocol

## Goal
Define and implement the WebSocket connection between the API server and the dashboard frontend. Covers server-side connection management, message envelope format, heartbeat, and client-side reconnection. This card does not implement any tile-specific logic — it establishes the wire protocol that all tiles use.

---

## Deliverables

1. `api/ws.py` — WebSocket connection manager + broadcast logic
2. `api/routes/ws.py` — FastAPI WebSocket endpoint
3. `api/messages.py` — message type definitions (Pydantic models)
4. `frontend/src/lib/useWebSocket.ts` — React hook for WS connection + reconnection
5. `frontend/src/lib/wsStore.ts` — Zustand store that receives and distributes WS messages

---

## Endpoint

```
ws://[host]/api/ws
wss://[host]/api/ws  (in production, via nginx TLS termination)
```

No authentication for MVP (single-user, private deployment). If basic auth is added to nginx later, the WebSocket upgrade will inherit it.

---

## Message Envelope

Every message in both directions is a JSON object with this envelope:

```typescript
interface WSMessage {
  type: string;          // identifies the message kind (see Message Types below)
  timestamp: string;     // ISO 8601 UTC, set by sender
  payload: object;       // type-specific data
}
```

**Rules:**
- `type` is always a namespaced string: `{domain}.{event}`, e.g. `sightings.created`
- `timestamp` is always UTC, always ISO 8601 with milliseconds: `"2025-03-01T14:23:05.123Z"`
- `payload` shape is defined per message type (see below)
- Unknown `type` values must be silently ignored by both client and server

---

## Message Types

### Server → Client

**`sightings.upserted`**
Emitted after a scraper upserts one or more sighting records.
```json
{
  "type": "sightings.upserted",
  "timestamp": "2025-03-01T14:23:05.123Z",
  "payload": {
    "records": [
      {
        "id": 4821,
        "location_id": 7,
        "location_name": "Dana Point",
        "species": "Gray whale",
        "count": 3,
        "confidence": "high",
        "source": "harbor_breeze",
        "source_url": "https://2seewhales.com/trip-report/...",
        "timestamp": "2025-03-01T13:45:00.000Z"
      }
    ],
    "scraper": "harbor_breeze"
  }
}
```

**`conditions.upserted`**
Emitted after a scraper upserts one or more condition records.
```json
{
  "type": "conditions.upserted",
  "timestamp": "2025-03-01T14:23:05.123Z",
  "payload": {
    "records": [
      {
        "id": 9103,
        "location_id": 3,
        "location_name": "Shaw's Cove",
        "condition_type": "visibility",
        "value": 13.0,
        "unit": "ft",
        "source": "south_coast_divers",
        "timestamp": "2025-03-01T08:00:00.000Z"
      }
    ],
    "scraper": "south_coast_divers"
  }
}
```

**`scores.updated`**
Emitted after activity scores are recalculated for any location.
```json
{
  "type": "scores.updated",
  "timestamp": "2025-03-01T14:23:05.123Z",
  "payload": {
    "scores": [
      {
        "location_id": 3,
        "location_name": "Shaw's Cove",
        "activity_type": "snorkeling",
        "score": 78,
        "summary_text": "Solid vis and calm conditions — worth the drive.",
        "timestamp": "2025-03-01T14:23:00.000Z"
      }
    ]
  }
}
```

**`scraper.status`**
Emitted at the end of every scraper run (success or failure). Drives the health indicator in the UI if one exists.
```json
{
  "type": "scraper.status",
  "timestamp": "2025-03-01T14:23:05.123Z",
  "payload": {
    "scraper": "harbor_breeze",
    "status": "success",
    "records_created": 4,
    "records_updated": 1,
    "error_message": null
  }
}
```

**`ping`**
Sent by server every 30 seconds to keep the connection alive.
```json
{
  "type": "ping",
  "timestamp": "2025-03-01T14:23:05.123Z",
  "payload": {}
}
```

### Client → Server

**`pong`**
Client responds to every `ping`. If server does not receive a `pong` within 10 seconds of sending a `ping`, the connection is considered dead and closed server-side.
```json
{
  "type": "pong",
  "timestamp": "2025-03-01T14:23:05.456Z",
  "payload": {}
}
```

That's it. The client sends nothing else for MVP. No subscriptions, no filtering — the server broadcasts everything to all connected clients.

---

## Server Implementation

### Connection Manager (`api/ws.py`)

```python
class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: dict):
        """Send to all connected clients. Remove dead connections silently."""
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self.active -= dead

manager = ConnectionManager()  # module-level singleton
```

### WebSocket Endpoint (`api/routes/ws.py`)

```python
@router.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_json(), timeout=40.0)
                if data.get("type") == "pong":
                    pass  # connection confirmed alive, nothing to do
                # all other client messages silently ignored for MVP
            except asyncio.TimeoutError:
                # client hasn't sent pong in 40s — close connection
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)
```

### Heartbeat Task

Start a background task when the API server starts:

```python
async def heartbeat_task():
    while True:
        await asyncio.sleep(30)
        await manager.broadcast({
            "type": "ping",
            "timestamp": utcnow_iso(),
            "payload": {}
        })
```

Register in FastAPI lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(heartbeat_task())
    yield
```

### Broadcasting from Scrapers

The scraper worker is a **separate container** — it cannot call `manager.broadcast()` directly. Instead, it notifies the API server via an internal HTTP call after each successful upsert:

```
POST http://api:8000/internal/broadcast
Body: { "type": "sightings.upserted", "timestamp": "...", "payload": { ... } }
```

This internal endpoint is not exposed through nginx (internal Docker network only) and requires a shared secret header:
```
X-Internal-Token: {INTERNAL_BROADCAST_TOKEN}
```

The API server receives this POST and calls `manager.broadcast()`. This keeps the WS state entirely within the API container.

---

## Client Implementation

### Reconnection Hook (`frontend/src/lib/useWebSocket.ts`)

- On mount: open connection to `wss://[host]/api/ws`
- On close or error: wait then reconnect with exponential backoff
  - Attempts: immediate, 2s, 4s, 8s, 16s, cap at 30s
  - Jitter: ±20% on each interval
  - No maximum attempt limit — keep trying indefinitely
- On `ping` received: immediately send `pong`
- On any other message: parse envelope, dispatch to Zustand store
- Expose `status: "connecting" | "connected" | "disconnected"` for UI indicator

```typescript
// Usage in app root
const { status } = useWebSocket();
```

The hook should be instantiated **once** at the app root, not per tile.

### Zustand Store (`frontend/src/lib/wsStore.ts`)

Tiles do not consume the WebSocket directly. They subscribe to the Zustand store.

```typescript
interface WSStore {
  lastSighting: SightingRecord | null;
  lastConditions: ConditionRecord[] | null;
  lastScores: ScoreRecord[] | null;
  connectionStatus: "connecting" | "connected" | "disconnected";

  // Called by useWebSocket hook on each message
  handleMessage: (msg: WSMessage) => void;
}
```

`handleMessage` routes by `msg.type` and updates the appropriate store slice. Tiles subscribe to individual slices — a conditions update does not re-render the wildlife tile.

**Store slices map to message types:**
| Store slice | Updated by |
|---|---|
| `lastSighting` | `sightings.upserted` |
| `lastConditions` | `conditions.upserted` |
| `lastScores` | `scores.updated` |
| `connectionStatus` | set by `useWebSocket` hook |

---

## Connection Status Indicator

A small dot in the dashboard header (or tile chrome) shows WebSocket status:
- 🟢 `connected`
- 🟡 `connecting` / reconnecting
- 🔴 `disconnected` (after 3+ failed reconnection attempts)

Implemented as a simple component subscribed to `connectionStatus` in the Zustand store.

---

## nginx Configuration

nginx proxies WebSocket upgrades to the API server:

```nginx
location /api/ws {
    proxy_pass http://api:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 60s;   # must exceed heartbeat interval (30s)
}
```

---

## What's Out of Scope for This Card

- Any tile-specific store slices beyond the four listed above
- REST endpoints (separate card)
- Score calculation logic (Card 03)
- The `internal/broadcast` endpoint security hardening beyond the shared secret

---

## Acceptance Criteria

- [ ] Two browser tabs connected simultaneously both receive broadcast messages
- [ ] Closing one tab does not affect the other
- [ ] Client disconnecting and reconnecting resumes receiving broadcasts within 30s
- [ ] Server sends `ping` every 30 seconds; client responds with `pong`
- [ ] A client that stops responding to pings is disconnected by the server within 40s
- [ ] Scraper worker POSTing to `/internal/broadcast` results in message reaching connected frontend clients
- [ ] POST to `/internal/broadcast` without correct token returns 401
- [ ] Unknown message `type` on either side does not throw or crash
- [ ] `connectionStatus` in Zustand store accurately reflects actual connection state
- [ ] nginx WebSocket proxy passes `upgrade` headers correctly (verify with `wscat`)
