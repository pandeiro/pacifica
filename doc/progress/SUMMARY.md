# Progress Summary

Last line = most recent work. Each line = one completed work item.

[00] Initial documentation restructure (PRD, Roadmap, Reference library)
[01] Frontend scaffold: React/Vite/TypeScript with Vitest, Makefile for root-level commands
[02] Dashboard UI: Deep ocean aesthetic with tiled layout - Map, Activity Scores, Live Cam, Conditions, Wildlife Intel, Tides & Sun, Drive Times, Seasonal Timeline
[02b] Dashboard mockup refinements: timeline layout improved, all 8 tiles properly proportioned, screenshot captured
[03] Services scaffolding: FastAPI API (port 4900), scraper package structure, Docker Compose with postgres + api + scraper, Makefile commands updated
[03b] README: Comprehensive overview, tech stack, quick start guide, and development commands
[04] GitHub Actions CI/CD: Workflow for validation, Docker image builds, staging/production deployment, with deployment documentation
[04b] CI/CD fixes: Single API architecture, GHCR authentication, frontend VITE_API_URL configuration
[04c] CI/CD deployment: Successfully deployed to pch.onl and staging.pch.onl
[04d] Bake migrations into API image: Self-contained deployment with migrations and seed baked into Docker image, runs automatically on container startup
[09] NOAA Tides Scraper: Implemented Python scraper fetching tide predictions from NOAA CO-OPS API for 5 stations, with test coverage and Docker integration
[03] Database Schema Migrations: Created 4 migration files (001_tables, 002_hypertables, 003_indexes, 004_constraints) with TimescaleDB support, 10 tables, 4 hypertables, and location seed data for NOAA stations
[03b] Added Shaws Cove (Laguna Beach) and Zuma Beach (Malibu) to location seed data with coastline bearings and NOAA station mappings
[10] Tides API Endpoint: Implemented GET /api/tides with station_id query param, returns tide events with next_low/next_high and interpolated current_height. Created database.py with SQLAlchemy async models, schemas with Pydantic, and routes module
[11] Tides & Sun Frontend Tile: Implemented D3.js tide curve visualization with pulsing current-position dot, NextTides and SunEvents components, integrated with useTides hook for API and WebSocket updates
[12] Sun Events Scraper: Implemented sunrise-sunset.org scraper fetching sunrise, sunset, and golden hour data for 7 locations × 8 days, with polite rate limiting and error handling
README and CI/CD improvements: Added build badge, removed live site link and Voice section, added scrapers data sources section, added 20s initialization pause to GHA healthcheck
Seed data improvement: Refactored sun_events seed to use dynamic subqueries for location ID lookup instead of brittle hardcoded IDs
[05] APScheduler Wiring: Implemented scheduler.py with auto-discovery of scraper classes, APScheduler cron triggers, and container startup execution
Screenshot tool: Added --env flag for local/staging/prod environments, auto-generated filenames with timestamps, updated AGENTS.md documentation
[10-13] Tides & Sun Tiles Complete: Split combined tile into separate SunTile (top-right) and TidesTile, added location dropdowns with Santa Monica default, fixed timezone display for Pacific time, implemented scraper DB persistence with dynamic location fetching
Infrastructure improvements: Unified docker-compose.yml for local/prod, removed postgres port exposure, simplified CI/CD deployment process, fixed POSTGRES_PASSWORD env var handling
[13] Sun Events Scraper production: Scraper fetching real sunrise/sunset data from sunrise-sunset.org API and persisting to database, SunTile displaying live data with correct Pacific timezone formatting
[14] NOAA Water Temperature Scraper: Implemented scraper fetching hourly water temp averages from NOAA CO-OPS API (using 'today' parameter, not specific dates), added 15 new coastal locations to seed data (San Diego, Channel Islands, OC/LA harbors, Ventura), created Condition model and database helpers, updated README data sources table
[15] South Coast Divers Scraper: Implemented HTML scraper fetching dive condition reports from southcoastdivers.com, parsing table content after "Here is the latest group post.", mapping to Shaws Cove (Laguna Beach), storing in conditions table with 96-hour duplicate detection
[16] Conditions API Endpoint: Implemented GET /api/conditions/water-temp with location_id and hours params, returns current temp (F/C), source info, and historical readings. Removed stub endpoint, defaults to Santa Monica (location_id=3).
[17] WaterTempsTile: Refactored ConditionsTile into focused water temperature display with 7-day sparkline, moved to right column under SunTile, created shared location state for natural conditions column, removed redundant dropdowns from TidesTile
[17b] Tides Tile Bug Fix: Fixed timezone handling in NOAA scraper (lst_ldt vs LST), tide times now match authoritative sources within 5 minutes. Added station deduplication, upsert logic for duplicates. Implemented cosine interpolation for smooth tide curve and hover tooltips showing interpolated heights.
[17c] Station Source Transparency: Added tide station info below location dropdown showing actual NOAA station name, distance and direction from selected surf spot. Explains tide time discrepancies (e.g., Morro Bay uses Port San Luis station, 14.7 miles away). Added official NOAA station coordinates to API.
Roadmap update: Marked Epic 1 cards (06-09) as skipped, marked Cards 16, 17, 17b, 17c as complete
[17d] Water temp bug fix: Fixed duplicate records causing double bars in sparkline. Added upsert logic to insert_conditions() and DISTINCT to API query. Current temp now correctly shows most recent value.
[Slice C kickoff] Wildlife Sightings spec written: doc/ref/wildlife_slice.md. Roadmap updated with 11 cards (23a, 18, 18b, 18c, 19-23, 24, 25). Env vars documented for OLLAMA_API_URL, LLM_MODEL, WHALE_ALERT_API_KEY, NITTER_API_URL.
[Card 23a] LLM Client Infrastructure — Created scraper/llm.py with async LLMClient wrapper (Ollama/OpenAI-compatible), SIGHTINGS_SCHEMA, and fallback function support. Tested in Docker container; fallback works when Ollama unavailable.
[Card 23a] LLM Prompt Engineering — Tested 16 prompt/temperature variations with llama3.2:1b. Identified optimal prompts (temp 0.0, simple inline schema). Created doc/ref/llm_prompts.md to document findings. Refactored llm.py to use named extraction profiles ('default', 'acs-la') instead of ad-hoc prompts. Hardcoded Ollama URL to host.docker.internal:11434. Card complete and ready for consumption by Cards 18b, 19, 23.
