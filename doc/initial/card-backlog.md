# Pacific — Card Backlog

Cards are grouped by slice. Each slice is a vertical cut through the stack — schema through frontend tile — and can be built and verified independently. The tides slice (cards 05–09) is fully specced and serves as the template for all subsequent slices.

Cards within a slice should be executed in order. Slices themselves can be parallelized once the foundation (cards 05–06) is in place.

---

## Foundation (prerequisite for all slices)

| # | Title | Description |
|---|-------|-------------|
| 05 | Database Schema Migrations 001–004 | All table definitions, hypertable creation, indexes, FK constraints, and check constraints. Prerequisite for every slice. |
| 06 | Testing Infrastructure | pytest + Vitest setup, Docker Compose test profile, VCR fixture pattern, Playwright config, and CI integration. Establishes the feedback loop all agents use. |

---

## Slice A — Tides (fully specced, cards 07–10)

| # | Title | Description |
|---|-------|-------------|
| 07 | NOAA Tides Scraper | Fetches tide predictions and verified observations from NOAA CO-OPS API, writes to `tides` hypertable. First concrete implementation of `BaseScraper`. |
| 08 | Tides API Endpoint | REST endpoint returning tide data for a given station/location, plus WebSocket broadcast wiring for new tide records. |
| 09 | Tides & Sun Frontend Tile | D3 tide curve visualization, next high/low display, sunrise/sunset/golden hour, location-aware NOAA station selection. |
| 10 | Sun Events Scraper + Endpoint | Fetches sunrise/sunset/golden hour from sunrise-sunset.org, writes to `sun_events`, serves via the tides endpoint. Bundled with tides tile. |

---

## Slice B — Conditions

| # | Title | Description |
|---|-------|-------------|
| 11 | NOAA Water Temp Scraper | Fetches water temperature from NOAA buoy data, writes to `conditions` hypertable. |
| 12 | South Coast Divers Scraper | Scrapes southcoastdivers.com dive reports, uses LLM extraction to parse visibility, temp, swell into condition records. |
| 13 | Conditions API Endpoint | REST endpoint for current and historical conditions at a location, with sparkline data for 7-day trends. |
| 14 | Conditions Frontend Tile | Displays water temp, visibility, swell, wind, air temp with source attribution and D3 sparklines. |

---

## Slice C — Wildlife Sightings

| # | Title | Description |
|---|-------|-------------|
| 15 | iNaturalist Scraper | Fetches wildlife sightings from iNaturalist API filtered by species list and SoCal bounding box. |
| 16 | Harbor Breeze Scraper | Scrapes whale watch trip reports from 2seewhales.com using LLM extraction for species, counts, and locations. |
| 17 | Davey's Locker Scraper | Scrapes daveyslocker.com trip reports, same LLM extraction pattern as Harbor Breeze. |
| 18 | Dana Wharf Scraper | Scrapes danawharf.com trip reports, same pattern. |
| 19 | Island Packers Scraper | Scrapes islandpackers.com sightings log, same pattern. |
| 20 | Twitter/X Scrapers | Fetches posts from park and wildlife accounts via the Twitter JSON API proxy; two scrapers (parks, wildlife). |
| 21 | Sightings API Endpoint | REST endpoint for recent sightings with filtering by species category, location, and time window. |
| 22 | Wildlife Intelligence Frontend Tile | Scrollable sightings feed with species icons, counts, source attribution, and "hot" indicator for notable sightings. |

---

## Slice D — Activity Scores

| # | Title | Description |
|---|-------|-------------|
| 23 | Activity Score Worker | Implements the five scoring functions from Card 03, wired to `SCRAPER_SCORE_TRIGGERS`, writes to `activity_scores` hypertable and broadcasts via WebSocket. |
| 24 | Activity Scores API Endpoint | REST endpoint returning current scores per activity per location, with `factors` breakdown. |
| 25 | Activity Scores Frontend Tile | Score display with Poor/Fair/Good/Great/Epic labels, expandable factors breakdown, top recommended location per activity. |

---

## Slice E — Map

| # | Title | Description |
|---|-------|-------------|
| 26 | Locations Seed Data | SQL seed file for all named locations (beaches, tidepools, viewpoints, harbors) with lat/lng, region, coastline_bearing, and NOAA station ID where applicable. |
| 27 | Map Frontend Tile | Leaflet map rotated to align with coastline, toggleable layers for location types and recent sightings, click-to-detail popup. |
| 28 | Drive Times — Google Maps Integration | On-demand drive time fetching from Google Maps Directions API, displayed as map layer and standalone tile. |

---

## Slice F — Live Cams

| # | Title | Description |
|---|-------|-------------|
| 29 | Live Cams Seed Data + API Endpoint | Seed data for initial cam list, REST endpoint serving cam records from `live_cams` table. |
| 30 | Live Cam Frontend Tile | YouTube iframe embed with feed switcher, maximize button, live status indicator. |

---

## Slice G — Seasonal Timeline

| # | Title | Description |
|---|-------|-------------|
| 31 | Seasonal Events Seed Data + API Endpoint | SQL seed for the full seasonal calendar, REST endpoint serving events with current/upcoming highlighting. |
| 32 | Seasonal Timeline Frontend Tile | D3 full-width 12-month timeline with current date marker, color-coded event bars, hover detail. |

---

## Slice H — LLM Extraction

| # | Title | Description |
|---|-------|-------------|
| 33 | LLM Extraction Schemas | Per-scraper JSON schemas passed to the LLM service, plus fallback regex functions, for all natural-language scrapers (Harbor Breeze, Davey's Locker, Dana Wharf, Island Packers, South Coast Divers). |

---

## Infrastructure & Operations

| # | Title | Description |
|---|-------|-------------|
| 34 | CI/CD Pipeline | `.gitlab-ci.yml` implementing lint → test → build → deploy → verify, with automatic rollback on health check failure. |
| 35 | nginx Configuration | Full nginx config: TLS termination, static file serving, API proxy, WebSocket upgrade headers, internal network isolation. |
| 36 | Health Check Endpoints | `/api/health` and `/api/health/scrapers` endpoints, stale detection logic, and 5-minute monitoring cron with Telegram alerting. |
| 37 | APScheduler Wiring | Scheduler setup in scraper worker container, SCRAPER_REGISTRY integration, per-scraper cron expressions, graceful shutdown. |

---

## Total: 33 remaining cards (05–37)

**Immediately executable**: Cards 05 and 06 (foundation)
**Executable after foundation**: Cards 07–10 (tides slice, fully specced)
**Executable after tides slice is proven**: All remaining slices in parallel
