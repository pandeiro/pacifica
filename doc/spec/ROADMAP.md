# Pacifica - Roadmap

This roadmap tracks the vertical slices of the Pacifica dashboard. Each slice is a functional unit from database to UI.

## 0. Infrastructure Setup
- [x] **Card 00: Frontend Scaffold** — Initialize React/Vite/TypeScript project, basic tile layout shell
- [x] **Card 01: Services & Docker Compose** — Scaffold Python FastAPI app, scraper structure, docker-compose.yml
- [x] **Card 02: GitHub Actions** — CI/CD pipeline that builds and deploys to staging/prod

## 1. Core Foundation
- [x] **Card 03: Database Schema Migrations** — All table definitions, TimescaleDB hypertables
- [x] **Card 04: Scraper Base Class** — BaseScraper abstract class, retry logic, LLM extraction
- [x] **Card 05: APScheduler Wiring** — Scheduler setup in scraper container, auto-discovery of scrapers, cron scheduling
- ~~[ ] **Card 06: WebSocket Protocol**~~ — Skipped for now
- ~~[ ] **Card 07: Activity Score Formulas**~~ — Skipped for now
- ~~[ ] **Card 08: Data Retention & TTL**~~ — Skipped for now
- ~~[ ] **Card 09: Testing Infrastructure**~~ — Skipped for now

## 2. Slice A — Tides & Sun
- [x] **Card 10: NOAA Tides Scraper** — Fetches tide data from NOAA CO-OPS API, persists to DB
- [x] **Card 11: Tides API Endpoint**
- [x] **Card 12: Tides Frontend Tile** — Visual tide curve, next high/low predictions, location dropdown
- [x] **Card 13: Sun Events Scraper + Sun Tile** — Fetches sunrise/sunset data from sunrise-sunset.org API, persists to DB + compact Sun tile with location dropdown

## 3. Slice B — Conditions
- [x] **Card 14: NOAA Water Temp Scraper**
- [x] **Card 15: South Coast Divers Scraper**
- [x] **Card 15b: Water Visibility Tile** — LLM extraction of visibility/swell from dive reports, visibility endpoint, VisibilityTile component
- [x] **Card 16: Conditions API Endpoint** — Water temperature only (NOAA data), latest + historical data per location
- [x] **Card 17: WaterTempsTile** — Refactored from ConditionsTile with 7-day sparkline, moved to right column
- [x] **Card 17b: Tides Tile Bug Fix & Interpolation** — Fixed timezone handling, cosine interpolation, hover tooltips
- [x] **Card 17c: Station Source Transparency** — Added tide station info below location dropdown

## 4. Slice C — Wildlife Sightings
- [x] **Card 23a: LLM Client Infrastructure** — `scraper/llm.py`, Ollama/OpenAI-compat wrapper, env vars; prerequisite for 18b, 19, 23
- [x] **Card 18: iNaturalist Scraper** — REST API, 30-min schedule, haversine location resolution
- [x] **Card 18b: ACS-LA Gray Whale Census Scraper** — HTML + Facebook feed widget, regex extraction for TODAY counts, seasonal (Dec–May)
- [ ] **Card 18c: Whale Alert Scraper** — BLOCKED: whale-alert.io is crypto service; whalealert.org requires data access agreement (contact info@whalealert.org)
- [x] **Card 19: Harbor Breeze Scraper** — Playwright headless, JetEngine dynamic content, Long Beach
- [x] **Card 21: Dana Wharf Scraper** — Public Google Sheet CSV export, regex parse, daily
- [x] **Card 22: Island Packers Scraper** — Public Google Sheet CSV export, structured daily counts
- [x] **Card 20: Davey's Locker Scraper** — Plain HTML table, regex parse, daily
- [ ] **Card 23: Nitter/Twitter Scrapers** — Research accounts first; NITTER_API_URL env var, LLM extraction
- [ ] **Card 24: Sightings API Endpoint** — `GET /api/sightings`, taxon_group derivation server-side
- [ ] **Card 25: Wildlife Intelligence Frontend Tile** — Filter pills, source badges, 15-min poll, type updates

## 5. Slice D — Activity Scores
- [ ] **Card 26: Activity Score Worker**
- [ ] **Card 27: Activity Scores API Endpoint**
- [ ] **Card 28: Activity Scores Frontend Tile**

## 6. Slice E — Map
- [ ] **Card 29: Locations Seed Data**
- [ ] **Card 30: Map Frontend Tile**
- [ ] **Card 31: Drive Times (Google Maps)**

## 7. Slice F — Live Cams
- [ ] **Card 32: Live Cams Seed Data**
- [ ] **Card 33: Live Cam Frontend Tile**

## 8. Slice G — Seasonal Timeline
- [ ] **Card 34: Seasonal Events Seed Data**
- [ ] **Card 35: Seasonal Timeline Frontend Tile**

## 9. Slice H — LLM Extraction
- [ ] **Card 36: LLM Extraction Schemas**
