# Pacifica - Roadmap

This roadmap tracks the vertical slices of the Pacifica dashboard. Each slice is a functional unit from database to UI.

## 0. Infrastructure Setup
- [ ] **Card 00: Frontend Scaffold** — Initialize React/Vite/TypeScript project, basic tile layout shell
- [ ] **Card 01: Services & Docker Compose** — Scaffold Python FastAPI app, scraper structure, docker-compose.yml
- [ ] **Card 02: GitHub Actions** — CI/CD pipeline that builds and deploys to staging/prod

## 1. Core Foundation
- [ ] **Card 03: Database Schema Migrations** — All table definitions, TimescaleDB hypertables
- [ ] **Card 04: Scraper Base Class** — BaseScraper abstract class, retry logic, LLM extraction
- [x] **Card 05: APScheduler Wiring** — Scheduler setup in scraper container, auto-discovery of scrapers, cron scheduling
- [ ] **Card 06: WebSocket Protocol** — Connection manager, message types, client hook
- [ ] **Card 07: Activity Score Formulas** — Scoring algorithms for all activities
- [ ] **Card 08: Data Retention & TTL** — TimescaleDB retention/compression policies
- [ ] **Card 09: Testing Infrastructure** — pytest, Vitest, agent-browser setup

## 2. Slice A — Tides & Sun
- [x] **Card 10: NOAA Tides Scraper** — Fetches tide data from NOAA CO-OPS API, persists to DB
- [x] **Card 11: Tides API Endpoint**
- [x] **Card 12: Tides Frontend Tile** — Visual tide curve, next high/low predictions, location dropdown
- [x] **Card 13: Sun Events Scraper + Sun Tile** — Fetches sunrise/sunset data from sunrise-sunset.org API, persists to DB + compact Sun tile with location dropdown

## 3. Slice B — Conditions
- [x] **Card 14: NOAA Water Temp Scraper**
- [ ] **Card 15: South Coast Divers Scraper**
- [ ] **Card 16: Conditions API Endpoint**
- [ ] **Card 17: Conditions Frontend Tile**

## 4. Slice C — Wildlife Sightings
- [ ] **Card 18: iNaturalist Scraper**
- [ ] **Card 19: Harbor Breeze Scraper**
- [ ] **Card 20: Davey's Locker Scraper**
- [ ] **Card 21: Dana Wharf Scraper**
- [ ] **Card 22: Island Packers Scraper**
- [ ] **Card 23: Twitter/X Scrapers**
- [ ] **Card 24: Sightings API Endpoint**
- [ ] **Card 25: Wildlife Intelligence Frontend Tile**

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
