# Technical Reference: WebSocket Protocol

## 1. Protocol Overview
The dashboard uses WebSockets for real-time updates. The API server broadcasts events to all connected clients.

- **Endpoint**: `wss://[host]/api/ws`
- **Format**: JSON Message Envelope.

## 2. Message Envelope
Every message follows this structure:
```typescript
interface WSMessage {
  type: string;          // e.g., "sightings.upserted"
  timestamp: string;     // ISO 8601 UTC
  payload: object;       // Type-specific data
}
```

## 3. Core Event Types
- **`sightings.upserted`**: Broadcast when new wildlife data is written.
- **`conditions.upserted`**: Broadcast when new environmental data is written.
- **`scores.updated`**: Broadcast when activity scores are recalculated.
- **`ping/pong`**: Heartbeat mechanism (sent every 30s) to maintain connections.

## 4. Client-Side Management
- **Connection**: Managed via a single React hook at the app root.
- **Store**: Received messages update a **Zustand** store.
- **Tile Subscriptions**: Tiles subscribe to specific slices of the store to minimize re-renders.
- **Reconnection**: Automatic exponential backoff with jitter.
