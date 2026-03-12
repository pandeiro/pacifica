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

This voice profile should guide LLM prompts (those aimed at producing copy), template text, and any editorial content in the dashboard.

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

## Data Model

### Core Tables

**locations**
```
id, name, slug, lat, lng, location_type (beach, tidepool, viewpoint, harbor, island),
region (south_coast, la_coast, ventura, central_coast, channel_islands),
noaa_station_id (nullable, for tide data), description, metadata (jsonb)
```

**sightings** (TimescaleDB hypertable, partitioned by time)
```
id, timestamp, location_id (FK), species, count (nullable),
source (e.g. 'harbor_breeze', 'inaturalist', 'island_packers'),
source_url (nullable), raw_text (nullable), confidence (high/medium/low),
metadata (jsonb - flexible fields per source)
```

**conditions** (TimescaleDB hypertable)
```
id, timestamp, location_id (FK), condition_type (visibility, water_temp, air_temp,
swell_height, swell_period, wind_speed, wind_direction),
value (numeric), unit, source, raw_text (nullable), metadata (jsonb)
```

**tides** (TimescaleDB hypertable)
```
id, timestamp, station_id, type (high/low/predicted), height_ft, source
```

**sun_events**
```
id, date, location_id (FK), sunrise, sunset, golden_hour_start, golden_hour_end
```

**live_cams**
```
id, name, location_id (FK), embed_type (youtube, iframe, hls),
embed_url, source_name, is_active (boolean), sort_order
```

**scrape_logs**
```
id, scraper_name, started_at, finished_at, status (success/failure/partial),
records_created, error_message (nullable)
```

**seasonal_events**
```
id, name, slug, description, typical_start_month, typical_start_day,
typical_end_month, typical_end_day, species (nullable),
category (migration, spawning, bloom, season, celestial), metadata (jsonb)
```

**activity_scores** (TimescaleDB hypertable)
```
id, timestamp, location_id (FK), activity_type (snorkeling, whale_watching,
body_surfing, scenic_drive, tidepool_exploring), score (0-100),
factors (jsonb - breakdown of what contributed to score), summary_text
```

### Design Notes

- **jsonb metadata columns** on most tables allow flexible per-source fields without schema changes
- **TimescaleDB hypertables** on time-series data enable efficient historical queries ("average visibility by month") and automatic data retention policies
- **source tracking** on every record enables data quality analysis and per-source reliability scoring
- **raw_text preservation** allows re-processing with improved LLM extraction later

## Scraper Inventory

Each scraper is a Python module within the scraper worker. They share common infrastructure (HTTP client, database connection, error handling, logging) but have independent schedules and parsing logic.

### Tier 1: Structured APIs (most reliable)

| Scraper | Source | Data Type | Schedule | Notes |
|---------|--------|-----------|----------|-------|
| **noaa_tides** | NOAA CO-OPS API | Tides | Daily | Free API, predictions + verified observations |
| **noaa_water_temp** | NOAA CO-OPS API | Water temperature | Every 6 hours | Same API, buoy data |
| **sunrise_sunset** | sunrise-sunset.org API | Sun events | Daily | Free, no key needed |
| **inaturalist** | iNaturalist API | Wildlife sightings | Every 6 hours | Filter by species list + bounding box |
| **google_drive_times** | Google Maps Directions API | Drive times | On-demand (API call from frontend) | Free tier: 40k direction requests/month |

### Tier 2: Website Scraping (semi-structured)

| Scraper | Source | Data Type | Schedule | Notes |
|---------|--------|-----------|----------|-------|
| **south_coast_divers** | southcoastdivers.com | Dive conditions (vis, temp, swell) | Twice daily | Near-daily blog posts about Laguna conditions |
| **harbor_breeze** | 2seewhales.com | Whale/dolphin sightings | Twice daily | Trip reports with species and counts |
| **daveys_locker** | daveyslocker.com | Whale/dolphin sightings | Twice daily | Similar trip report format |
| **island_packers** | islandpackers.com | Marine mammal sightings | Daily | Sightings log on website |
| **dana_wharf** | danawharf.com | Whale/dolphin sightings | Twice daily | Trip reports |

### Tier 3: Social Media

| Scraper | Source | Data Type | Schedule | Notes |
|---------|--------|-----------|----------|-------|
| **twitter_parks** | X/Twitter via JSON API proxy | Park updates, closures, events | Every 4 hours | NPS, CA State Parks, county parks accounts |
| **twitter_wildlife** | X/Twitter via JSON API proxy | Sighting reports | Every 4 hours | Marine biologist accounts, whale watch accounts |

### Tier 4: Embeds (no scraping needed)

| Source | Type | Notes |
|--------|------|-------|
| **Explore.org YouTube** | Live cam embeds | Anacapa underwater, Catalina eagle nest, etc. |
| **Beach cams** | Live cam embeds | Various - Santa Monica, Hermosa, Laguna, Malibu, Zuma, Morro Bay |

### Scraper Architecture

Each scraper module implements a common interface:

```python
class BaseScraper:
    name: str
    schedule: str  # cron expression
    
    async def scrape(self) -> ScrapeResult:
        """Fetch and parse data from source."""
        ...
    
    async def process(self, raw_data) -> list[Record]:
        """Transform raw data into database records.
        May use local LLM for text extraction."""
        ...
```

- Scrapers that process natural language text (dive reports, trip logs) can optionally route through the **local LLM service** for structured data extraction
- All scrapers log their runs to `scrape_logs` for monitoring
- Failed scrapers don't block other scrapers
- Each scraper can be run independently for testing: `python -m scrapers.south_coast_divers`

### Target Species List (for iNaturalist + sighting scrapers)

**Marine Mammals**: Gray whale, Blue whale, Humpback whale, Fin whale, Minke whale, Orca, Common dolphin, Bottlenose dolphin, Sea otter, California sea lion, Harbor seal, Elephant seal

**Fish & Invertebrates**: Garibaldi, Horn shark, Leopard shark, Great white shark, Sheepshead, Mola mola (ocean sunfish), Grunion, Steelhead trout, Market squid, Octopus (multiple species), Kelp crab, Fiddler crab, Sea stars (multiple species), Lobster (California spiny)

**Other**: Brown pelican, Western snowy plover (threatened), California least tern (endangered)

### Seasonal Events Calendar

| Event | Typical Period | Category |
|-------|---------------|----------|
| Gray whale southbound migration | Dec - Feb | migration |
| Gray whale northbound migration | Feb - Apr | migration |
| Blue whale season | Jun - Oct | migration |
| Humpback whale season | Apr - Nov | migration |
| Grunion runs | Mar - Aug (peak) | spawning |
| Steelhead migration | Dec - Mar | migration |
| California spiny lobster season | Oct - Mar | season |
| Bioluminescence (dinoflagellate blooms) | Apr - Jun (variable) | bloom |
| Red tide events | Variable, spring/summer | bloom |
| Giant kelp peak growth | Spring - early summer | bloom |
| Elephant seal pupping (San Simeon) | Dec - Mar | breeding |
| Elephant seal molting (San Simeon) | Apr - Aug | breeding |
| Market squid spawning | Variable, often winter | spawning |
| Peak garibaldi nesting | Mar - Oct | breeding |
| Brown pelican nesting (Channel Islands) | Feb - Aug | breeding |
| Lowest tides of year (best tidepooling) | Nov - Mar (early morning) | tidal |
| Warmest water temps | Aug - Oct | conditions |
| Best underwater visibility | Aug - Nov | conditions |

## Dashboard Layout

### Layout Philosophy

Information-dense, tiled, no wasted space. Think mission control, not marketing page. Every tile earns its screen real estate by answering a question the user actually asks.

Tiles have a fixed default layout (no drag-and-drop for MVP) but any tile can be **maximized** to fill the viewport (especially useful for map and live cams). The layout is responsive enough to be usable on mobile (single-column stack) but is designed for a desktop/laptop screen.

### Tile Grid (Desktop)

```
┌───────────────┬──────────────────────┬──────────────────────┐
│               │  Activity Scores     │  Live Cam              │
│               │  🤿 Snorkeling: Good  │  [switchable feed]     │
│               │  🐋 Whales: Great    │  [maximize button]     │
│   MAP         │  🏄 Surf: Fair       │                        │
│               │  🚗 Scenic: Excellent│──────────────────────┤
│  (full height) │                      │  Wildlife Intel         │
│               ├──────────────────────┤  Recent sightings,     │
│  (rotated to  │  Conditions            │  species, locations    │
│   align with  │  Water: 65°F            │  source attribution    │
│   coastline)  │  Vis: 12-15ft          │                        │
│               │  Swell: 2-3ft @ 12s   ├──────────────────────┤
│               │  Wind: 5mph W          │  Tides                  │
│               │  Air: 72°F             │  Next low: 5:23am -0.2'│
│               ├──────────────────────┤  [tide curve graphic]  │
│               │  Drive Times           │  Sunrise: 6:42am       │
│               │  Laguna: 48min         │  Sunset: 5:58pm        │
│               │  Pt Vicente: 22min     │  Golden hr: 5:12pm     │
│               │  Leo Carrillo: 35min   │                        │
└───────────────┴──────────────────────┴──────────────────────┘
┌───────────────────────────────────────────────────────────┐
│  Seasonal Timeline                                           │
│  [========|=====>                                    ]       │
│  Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec │
│  🐋 gray whales    🐟 grunion     🐋 blue whales   🫞 lobster  │
└───────────────────────────────────────────────────────────┘
```

### Tile Inventory

#### 1. Map Tile
- **Position**: Left column, full viewport height
- **Tech**: Leaflet or Mapbox GL JS (free tier)
- **Features**:
  - Rotated/angled to align with the NW-SE coastline orientation
  - Toggleable layers: locations by type, recent sightings (color-coded by species category), live conditions indicators
  - "Drive time" layer: shows isochrone or labeled drive times from configured home lat/lng to each location
  - Click a location for detail popup (conditions, recent sightings, next tide)
  - On mobile: can use current GPS location for drive times instead of home
- **Data sources**: Google Maps Directions API (drive times), all location + sighting data from DB

#### 2. Activity Scores Tile
- **Position**: Top center
- **Tech**: React component with simple visual indicators
- **Activities scored**:
  - 🤿 **Snorkeling**: weighted from visibility, water temp, swell, wind, recent marine life sightings
  - 🐋 **Whale Watching**: weighted from recent sighting frequency, sea conditions, season
  - 🏄 **Body Surfing**: wave height, period, wind, water temp, hazard reports
  - 🚗 **Scenic Drive**: air temp, cloud cover, visibility, golden hour proximity
  - 🧪 **Tidepooling**: tide height (lower = better), time to next extreme low, swell (calmer = safer)
- **Score display**: 0-100 mapped to Poor / Fair / Good / Great / Epic with color coding
- **Each score expandable** to show the top recommended location for that activity and contributing factors

#### 3. Live Cam Tile
- **Position**: Top right
- **Tech**: YouTube iframe embeds, possibly HLS for non-YouTube sources
- **Features**:
  - Dropdown/tabs to switch between available live feeds
  - Maximize button to go full viewport
  - Shows cam name, location, and whether feed is currently live
  - Cam list managed in `live_cams` database table
- **Initial cam list** (to be researched and expanded):
  - Explore.org Anacapa underwater
  - Explore.org Channel Islands eagle nest
  - Santa Monica beach cam
  - Hermosa Beach cam
  - Laguna Beach cam
  - Malibu cam
  - Zuma Beach cam
  - Morro Bay cam

#### 4. Conditions Tile
- **Position**: Middle center
- **Tech**: React component, possibly small D3 sparklines for trends
- **Shows current conditions** for a selected location (or "best" location):
  - Water temperature (with 7-day sparkline)
  - Underwater visibility (with trend)
  - Swell height and period
  - Wind speed and direction
  - Air temperature
- **Location selector**: dropdown or synced with map selection
- **Source attribution**: shows which source reported each data point

#### 5. Wildlife Intelligence Tile
- **Position**: Right column, middle
- **Tech**: React component, scrollable feed
- **Shows**:
  - Recent sightings in reverse chronological order
  - Species icon/emoji, count, location, time, source
  - Filterable by species category (whales, sharks, invertebrates, etc.)
  - "Hot" indicator for unusual or notable sightings
- **Data sources**: All sighting scrapers + iNaturalist

#### 6. Tides & Sun Tile
- **Position**: Right column, bottom
- **Tech**: D3 for tide curve visualization
- **Shows**:
  - Tide curve for next 24-48 hours with current position marked
  - Next high/low tide time and height
  - Sunrise, sunset, golden hour times
  - Moon phase (useful for tide extremes and night activities)
- **Location-aware**: shows data for nearest NOAA station to selected location

#### 7. Drive Times Tile
- **Position**: Bottom center
- **Tech**: React component
- **Shows**: Estimated current drive time from home (or current location on mobile) to each saved location
- **Sorted by**: drive time ascending ("what's closest right now?")
- **Updates**: on-demand when tile is visible (to conserve API quota)
- **Google Maps API**: uses Directions API with departure_time=now for traffic-aware estimates

#### 8. Seasonal Timeline Tile
- **Position**: Bottom, full width
- **Tech**: D3 or custom SVG
- **Shows**:
  - Linear 12-month timeline with current date marker
  - Horizontal bars for each seasonal event (whale migrations, grunion, lobster season, etc.)
  - Color-coded by category (migration, spawning, bloom, season)
  - Hoverable for details
  - Visual emphasis on "what's happening now" and "what's coming up"
- **Data source**: `seasonal_events` table (mostly static, curated data)

### Tile Behavior

- **Server push**: Tiles subscribe to WebSocket channels. When the scraper writes new data, the API server pushes updates to connected clients. No polling needed for most tiles.
- **Maximize**: Any tile can be maximized to fill the viewport. Press Escape or click a close button to restore.
- **Loading states**: Each tile manages its own loading/error state independently.
- **Mobile**: Tiles stack vertically in a single column. Map tile becomes a standard (non-rotated) map at the top.

## CI/CD

### Pipeline Design

The GitLab CI/CD pipeline runs on every push to `main`. The goal is **commit-to-live in under 5 minutes** with automatic rollback if something breaks.

```
push to main
    │
    ├── [stage: lint]     frontend lint + backend lint (parallel)
    ├── [stage: test]     frontend tests + backend tests (parallel)
    ├── [stage: build]    docker build for each changed service
    ├── [stage: deploy]   docker compose pull + up on VPS via SSH
    ├── [stage: verify]   health checks against live site
    │       │
    │       ├── PASS → ✅ Telegram: "Deploy successful"
    │       └── FAIL → auto-rollback to previous images
    │                    → 🚨 Telegram: "Deploy FAILED, rolled back"
    └── done
```

### Pipeline Stages

#### Lint
- **Frontend**: ESLint + TypeScript type checking
- **Backend**: Ruff (Python linter/formatter) + mypy (type checking)
- Run in parallel, fail fast

#### Test
- **Frontend**: Vitest for unit/component tests
- **Backend**: pytest for scraper tests (with recorded HTTP fixtures), API endpoint tests, data model tests
- Run in parallel

#### Build
- Build Docker images for services that changed (detect via git diff)
- Tag images with commit SHA and `latest`
- Push to GitLab Container Registry (built into the project, free)

#### Deploy
- SSH into Hetzner VPS
- Pull new images from GitLab Container Registry
- `docker compose up -d` with the new images
- Wait for containers to report healthy

#### Verify (Post-Deploy Health Checks)
- Hit `/api/health` endpoint - checks API server + database connectivity
- Hit `/api/health/scrapers` - checks that scrapers have run recently (no stale data)
- Verify frontend loads (HTTP 200 on root)
- If any check fails: rollback to previous image tags, notify via Telegram

### Rollback Strategy

- Every successful deploy tags images as `stable` in addition to the commit SHA
- Rollback = `docker compose` with `stable` tagged images
- Rollback is automatic on health check failure, but can also be triggered manually
- The last 5 image versions are retained in the registry for manual rollback

### Branch Strategy

- **`main`**: production branch, auto-deploys on push
- **Feature branches**: used for development, CI runs lint + test but does NOT deploy
- **Merge requests**: required for feature branches into main (enforced by workflow, not branch protection for now)

### GitLab CI Configuration

The `.gitlab-ci.yml` will use:
- **GitLab Container Registry** for Docker images
- **SSH deployment** via CI/CD variables (SSH key stored as protected variable)
- **Docker-in-Docker** or **Kaniko** for building images in CI
- **Environment tracking** in GitLab for deployment history

## Health Checks

### Endpoint: `GET /api/health`

Returns overall system health:

```json
{
  "status": "healthy",
  "timestamp": "2025-02-23T10:30:00Z",
  "components": {
    "database": { "status": "healthy", "latency_ms": 3 },
    "api": { "status": "healthy", "uptime_seconds": 86400 }
  }
}
```

### Endpoint: `GET /api/health/scrapers`

Returns scraper freshness:

```json
{
  "status": "healthy",
  "scrapers": {
    "noaa_tides": { "last_run": "2025-02-23T06:00:00Z", "status": "success", "stale": false },
    "south_coast_divers": { "last_run": "2025-02-23T08:15:00Z", "status": "success", "stale": false },
    "harbor_breeze": { "last_run": "2025-02-22T18:00:00Z", "status": "failure", "stale": true }
  }
}
```

A scraper is "stale" if it hasn't run successfully within 2x its expected schedule interval.

### Ongoing Monitoring

Beyond deploy-time health checks, a lightweight cron job (or the scraper worker itself) periodically:
- Checks all health endpoints
- Verifies the frontend is reachable
- Sends Telegram alert if anything is degraded
- Frequency: every 5 minutes

## External Dependencies

### APIs (Free)

| API | Used For | Rate Limits | Key Required |
|-----|----------|-------------|-------------|
| NOAA CO-OPS | Tides, water temp, currents | Generous, no hard limit | No |
| iNaturalist | Wildlife sightings | 100 req/min (logged in) | Optional (API token for higher limits) |
| sunrise-sunset.org | Sun events | 1000 req/day | No |
| Google Maps Directions | Drive time estimates | 40k requests/month free | Yes (already have key) |

### External Services

| Service | Used For | Notes |
|---------|----------|-------|
| Twitter JSON API proxy | Scraping park/wildlife X accounts | Already running on same VPS |
| YouTube embeds | Live cam feeds | No API needed, just iframe embeds |
| GitLab Container Registry | Docker image storage | Free with GitLab project |
| Let's Encrypt | TLS certificates | Free, auto-renewal via certbot |

### Sibling Projects (Separate Repos)

| Project | Purpose | Dependency Type |
|---------|---------|----------------|
| **Telegram DevBot** | Notification service accepting webhooks, routing to Telegram | Pacific sends deploy/alert webhooks to it |
| **Local LLM Service** | Small language model for text extraction from scraped content | Pacific's scraper worker calls it over Docker network for NLP tasks |

Both are optional for MVP - Pacific should function without them, falling back to:
- Console/log-only notifications if DevBot isn't available
- Regex/heuristic text extraction if LLM service isn't available

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://pacific:password@postgres:5432/pacific

# Google Maps
GOOGLE_MAPS_API_KEY=...

# Home location (for drive time calculations)
HOME_LAT=33.XXXX
HOME_LNG=-118.XXXX

# Telegram DevBot (optional)
TELEGRAM_WEBHOOK_URL=http://devbot:8080/notify

# Local LLM (optional)
LLM_SERVICE_URL=http://172.:8000/v1

# Twitter proxy
TWITTER_PROXY_URL=http://twitter-proxy:8080

# iNaturalist (optional, for higher rate limits)
INATURALIST_API_TOKEN=...
```

### Settings Table (DB)

For settings that might change without a redeploy:

```
id, key, value (jsonb), description, updated_at
```

Examples: home location override, enabled/disabled scrapers, tile visibility, cam sort order.
