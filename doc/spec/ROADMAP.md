# Pacifica - Roadmap

This roadmap tracks the vertical slices of the Pacifica dashboard. Each slice is a functional unit from database to UI.

## 0. Infrastructure Setup
- [ ] **Card 00: Frontend Scaffold** — Initialize React/Vite/TypeScript project, basic tile layout shell
- [ ] **Card 01: Services & Docker Compose** — Scaffold Python FastAPI app, scraper structure, docker-compose.yml
- [ ] **Card 02: GitHub Actions** — CI/CD pipeline that builds and deploys to staging/prod

## 1. Core Foundation
- [ ] **Card 03: Database Schema Migrations** — All table definitions, TimescaleDB hypertables
- [ ] **Card 04: Scraper Base Class** — BaseScraper abstract class, retry logic, LLM extraction
- [ ] **Card 05: WebSocket Protocol** — Connection manager, message types, client hook
- [ ] **Card 06: Activity Score Formulas** — Scoring algorithms for all activities
- [ ] **Card 07: Data Retention & TTL** — TimescaleDB retention/compression policies
- [ ] **Card 08: Testing Infrastructure** — pytest, Vitest, agent-browser setup

## 2. Slice A — Tides & Sun
- [ ] **Card 09: NOAA Tides Scraper**
- [ ] **Card 10: Tides API Endpoint**
- [ ] **Card 11: Tides & Sun Frontend Tile**
- [ ] **Card 12: Sun Events Scraper**

## 3. Slice B — Conditions
- [ ] **Card 13: NOAA Water Temp Scraper**
- [ ] **Card 14: South Coast Divers Scraper**
- [ ] **Card 15: Conditions API Endpoint**
- [ ] **Card 16: Conditions Frontend Tile**

## 4. Slice C — Wildlife Sightings
- [ ] **Card 17: iNaturalist Scraper**
- [ ] **Card 18: Harbor Breeze Scraper**
- [ ] **Card 19: Davey's Locker Scraper**
- [ ] **Card 20: Dana Wharf Scraper**
- [ ] **Card 21: Island Packers Scraper**
- [ ] **Card 22: Twitter/X Scrapers**
- [ ] **Card 23: Sightings API Endpoint**
- [ ] **Card 24: Wildlife Intelligence Frontend Tile**

## 5. Slice D — Activity Scores
- [ ] **Card 25: Activity Score Worker**
- [ ] **Card 26: Activity Scores API Endpoint**
- [ ] **Card 27: Activity Scores Frontend Tile**

## 6. Slice E — Map
- [ ] **Card 28: Locations Seed Data**
- [ ] **Card 29: Map Frontend Tile**
- [ ] **Card 30: Drive Times (Google Maps)**

## 7. Slice F — Live Cams
- [ ] **Card 31: Live Cams Seed Data**
- [ ] **Card 32: Live Cam Frontend Tile**

## 8. Slice G — Seasonal Timeline
- [ ] **Card 33: Seasonal Events Seed Data**
- [ ] **Card 34: Seasonal Timeline Frontend Tile**

## 9. Slice H — LLM Extraction
- [ ] **Card 35: LLM Extraction Schemas**
