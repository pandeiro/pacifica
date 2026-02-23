# Pacific - Project Specification

## Vision

Pacific is a real-time coastal intelligence dashboard for the Southern California coastline. It aggregates data from dozens of sources - official APIs, amateur dive reports, whale watch trip logs, live cams, citizen science platforms, and social media - into a single, information-dense, tiled interface.

The dashboard answers questions like:
- Is this weekend good to go snorkeling in Laguna? What's the visibility and water temp?
- Have they been seeing whales at Point Vicente? What kind?
- I have 45 minutes - where can I get to from here right now?
- When is the next low tide at this tidepool area I'm near?
- Where are good snorkeling spots besides Laguna Beach?
- Is bioluminescence happening anywhere right now?

Pacific is a tool for a curious, active Southern Californian who wants to know what's happening on their coast right now, what's coming up, and where to go.

## Voice Profile

All generated text, summaries, and condition reports should read like a **passionate, knowledgeable local** - the person at the dive shop who always knows where the action is.

Characteristics:
- **Enthusiastic but honest** - gets excited about good conditions, but doesn't hype mediocre days
- **Practical** - includes actionable details (timing, wind windows, parking notes)
- **Local vernacular** - uses spot names locals use, knows the neighborhoods
- **Opinionated** - will say "skip it today" or "drop everything and go"
- **Amateur naturalist** - genuinely interested in the wildlife, not just the activity

Example (good):
> Solid vis at Shaw's Cove this morning - 12-15ft, water's a comfortable 65°. Garibaldi are everywhere as usual but South Coast Divers mentioned a juvenile horn shark near the reef. Worth the drive if you can get there before the afternoon onshore picks up.

Example (bad - too robotic):
> Shaw's Cove: Visibility 12-15ft. Water temp 65°F. Species reported: Garibaldi, horn shark (juvenile). Wind: onshore expected PM.

This voice profile should guide LLM prompts, template text, and any editorial content in the dashboard.

## Geographic Scope

**Primary coverage area**: San Diego to San Simeon (~350 miles of coastline)

**Default map view**: Full coastline, displayed in a tall/narrow tile on the left side of the dashboard, potentially rotated to optimally align with the NW-SE orientation of the California coast.

**Key areas of interest** (not exhaustive):

### South Coast
- Dana Point / Dana Wharf (whale watching departure)
- Laguna Beach (Shaw's Cove, Crescent Bay, Heisler Park tidepools, Treasure Island)
- Crystal Cove State Park

### LA / Orange County Coast
- Palos Verdes Peninsula (Point Vicente, Abalone Cove, Terranea tidepools)
- Hermosa Beach / Manhattan Beach
- Santa Monica
- Malibu (Leo Carrillo, El Matador, Point Dume)
- Zuma Beach

### Ventura / Central Coast
- Channel Islands (Anacapa, Santa Cruz, Santa Rosa, San Miguel, Santa Catalina)
- Morro Bay
- San Simeon (elephant seals, Hearst Castle coast)

### Whale Watching Departure Points
- Long Beach / San Pedro (Harbor Breeze)
- Dana Point (Dana Wharf)
- Ventura / Oxnard (Island Packers)

### Tidepool Areas (to be expanded with research)
- Palos Verdes Peninsula (multiple spots)
- Malibu area
- Leo Carrillo
- Laguna Beach (Heisler Park)

## Architecture

### Overview

Pacific uses a multi-container architecture deployed via Docker Compose on a single VPS.

```
┌─────────────────────────────────────────────────────────┐
│                        nginx                            │
│              (reverse proxy + static)                    │
│         pacific.yourdomain.com :443                      │
└────────────┬──────────────────────────────┬─────────────┘
             │                              │
     ┌───────┴────────┐              ┌──────┴─────────┐
     │   Frontend     │              │   API Server    │
     │  (static build) │              │   (Python)      │
     │  React/Vite/TS  │              │   FastAPI       │
     └────────────────┘              └────────┬────────┘
                                            │
                                    ┌───────┴────────┐
                                    │   PostgreSQL    │
                                    │  + TimescaleDB  │
                                    └───────┬────────┘
                                            │
     ┌────────────────┐              ┌───────┴────────┐
     │  Scraper Worker │────────────┘  Scheduler      │
     │  (Python)       │              │  (APScheduler)  │
     │  All scrapers   │              └────────────────┘
     │  as modules     │
     └────────────────┘
```

### Containers

| Container | Role | Tech | Notes |
|-----------|------|------|-------|
| **nginx** | Reverse proxy, TLS termination, static file serving | nginx + Let's Encrypt | Serves frontend build, proxies /api to API server |
| **frontend** | Build-only container (or served directly by nginx) | React, Vite, TypeScript, D3 | Static build output mounted into nginx |
| **api** | REST + WebSocket API for the dashboard | Python, FastAPI | Serves data to frontend, WebSocket for live tile updates |
| **scraper** | Data collection worker | Python, BeautifulSoup/httpx, APScheduler | Runs all scrapers on configurable schedules, writes to Postgres |
| **postgres** | Primary data store | PostgreSQL 16 + TimescaleDB | Time-series hypertables for sightings, conditions, tides |

### Infrastructure

- **Host**: Hetzner VPS - 2 vCPU, 4GB RAM, 80GB SSD
- **Domain**: `pacific.yourdomain.com` (subdomain on existing domain)
- **TLS**: Let's Encrypt via certbot or nginx companion
- **Deployment**: Docker Compose, deployed via GitLab CI/CD
- **OS**: Linux (whatever is currently on the Hetzner box)

### Resource Budget (4GB RAM)

| Component | Estimated RAM |
|-----------|---------------|
| PostgreSQL + TimescaleDB | ~500MB-1GB |
| API Server (FastAPI) | ~100-200MB |
| Scraper Worker | ~200-400MB (spikes during scraping) |
| nginx | ~50MB |
| OS + overhead | ~500MB |
| **Headroom** | **~1.5-2GB** |

This leaves room for growth but not for heavy additions like Supabase. The local LLM service (separate project) will need its own resource planning.

### Network Topology

Other Docker Compose projects on the same host (Twitter API proxy, future LLM service) can communicate with Pacific's containers via:
- A shared Docker network (preferred - create an external network both compose files join)
- Host networking / published ports as fallback

The shared network approach keeps things clean and avoids port conflicts.

### Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Frontend | React 18+, Vite, TypeScript, D3.js |
| UI Components | Custom tiles (each tile can use its own rendering approach) |
| Maps | Leaflet or Mapbox GL JS (free tier) with Google Maps API for drive times only |
| API | Python, FastAPI, WebSockets |
| Scraping | Python, httpx, BeautifulSoup4, possibly Playwright for JS-rendered pages |
| Scheduling | APScheduler (in-process with scraper worker) |
| Database | PostgreSQL 16 + TimescaleDB |
| Reverse Proxy | nginx |
| Containerization | Docker, Docker Compose |
| CI/CD | GitLab CI/CD |
| Monitoring | Health check endpoints + Telegram notifications |
