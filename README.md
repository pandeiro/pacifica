# Pacifica

[![CI/CD](https://github.com/pandeiro/pacifica/actions/workflows/ci.yml/badge.svg)](https://github.com/pandeiro/pacifica/actions/workflows/ci.yml)

Real-time coastal intelligence for Southern California. A mission control dashboard aggregating tides, conditions, wildlife sightings, and live cams from San Diego to San Simeon.

## Overview

Pacifica pulls data from dozens of sources—NOAA APIs, dive reports, whale watch logs, live cams, citizen science platforms—into a single tiled interface. Know what's happening on the coast right now and what's coming up.

Built for the curious, active Southern Californian who wants actionable intel (not just raw data) on where to dive, snorkel, whale watch, or explore tidepools.

## Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, TypeScript, D3.js |
| **Backend** | Python, FastAPI, WebSockets |
| **Database** | PostgreSQL 16 + TimescaleDB |
| **Scrapers** | Python, httpx, BeautifulSoup, APScheduler |
| **Testing** | Vitest (frontend), pytest (backend), Playwright |
| **Infrastructure** | Docker Compose, GitHub Actions |

## Quick Start

```bash
# Clone and enter repo
git clone https://github.com/pandeiro/pacifica.git
cd pacifica

# Start services (Postgres + API)
make up

# Run migrations and seed data
make migrate
make seed

# In another terminal, start the frontend
make dev
```

**Access**:
- Dashboard: http://localhost:5173
- API: http://localhost:4900
- API Health: http://localhost:4900/api/health

## Development

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend dev server)
- Python 3.11+ (for running scrapers locally)

### Common Commands

```bash
# Start/stop services
make up          # Start Docker services (Postgres + API)
make up-all      # Start all services including scraper
make down        # Stop all services

# Database
make migrate     # Run database migrations
make seed        # Seed initial data

# Frontend (requires `make up` first)
make dev         # Start Vite dev server
make build       # Build for production
make test        # Run Vitest tests
make lint        # Run ESLint
make typecheck   # Run TypeScript check

# Logs
make logs        # Tail all service logs
```

### Project Structure

```
pacifica/
├── api/              # FastAPI application
├── scraper/          # Data collection scrapers
├── frontend/         # React/Vite dashboard
├── db/               # Migrations and seed data
├── tools/            # Development utilities
└── doc/              # Documentation (specs, references)
```

## Data Sources

Pacifica aggregates data from multiple sources via automated scrapers:

| Source | Data | Frequency |
|--------|------|-----------|
| **NOAA CO-OPS** | Tide predictions, water levels | Every 6 hours |
| **sunrise-sunset.org** | Sunrise, sunset, golden hour | Daily at 2:30 AM |

Scrapers run via GitHub Actions (see `.github/workflows/scrapers.yml`) and write directly to the TimescaleDB database. Each scraper is designed to be polite—respecting rate limits and using incremental backoff when needed.

## License

MIT
