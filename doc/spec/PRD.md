# Pacific - Product Requirements Document

## 1. Vision
Pacific is a real-time coastal intelligence dashboard for the Southern California coastline. It aggregates data from dozens of sources—official APIs, amateur dive reports, whale watch trip logs, live cams, citizen science platforms, and social media—into a single, information-dense, tiled interface.

The goal is to provide a "Mission Control" for the curious, active Southern Californian to know what's happening on their coast right now and what's coming up.

## 2. Voice Profile
All generated text and summaries should read like a **passionate, knowledgeable local**.
- **Enthusiastic but honest**: Hypes good days, stays realistic about mediocre ones.
- **Practical**: Focuses on actionable details (parking, wind windows).
- **Local vernacular**: Uses spot names locals use.
- **Amateur naturalist**: Genuinely interested in wildlife.

## 3. Geographic Scope
- **Primary area**: San Diego to San Simeon (~350 miles of coastline).
- **Key regions**: South Coast (Laguna, Dana Point), LA/OC Coast (Palos Verdes, Malibu), Ventura/Central Coast (Channel Islands, Morro Bay).

## 4. Technical Architecture
Pacific uses a multi-container architecture deployed via Docker Compose.

- **Frontend**: React (Vite/TypeScript/D3) static SPA.
- **API Server**: Python (FastAPI) serving REST and WebSockets.
- **Scraper Worker**: Python (APScheduler/httpx) running modular scrapers.
- **Database**: PostgreSQL 16 + TimescaleDB for time-series coastal data.
- **Proxy**: Nginx for reverse proxy, TLS termination, and static asset serving.

## 5. Deployment & Infrastructure
The project is hosted at `https://github.com/pandeiro/pacifica`.

### CI/CD Strategy (GitHub Actions)
- **Production**: Merges to `main` trigger a full build and deployment to the production VPS.
- **Staging/Preview**: Pull Requests trigger a build and deployment to a preview environment or a dedicated `/staging` path for verification.
- **Images**: Docker images are stored in **GitHub Container Registry (GHCR)**.

### Environments
- **Production**: Accessible at `pch.onl`.
- **Staging**: Accessible at `staging.pch.onl`.
- **Secrets**: All sensitive data (API keys, DB credentials) are managed via **GitHub Secrets** and injected as environment variables.
- **Assets**: Static assets for the SPA are built in CI and deployed to versioned or environment-specific paths (e.g., `/prod/` vs `/staging/`).

## 6. Dashboard Layout
Information-dense, tiled interface. Each tile answers a specific question (e.g., "What is the visibility?", "Where are the whales?").
- **Map**: Rotated to align with the NW-SE coastline.
- **Activity Scores**: 0–100 scores for Snorkeling, Whale Watching, Tidepooling, etc.
- **Live Cams**: Switchable feeds from coastal locations.
- **Wildlife Intel**: Recent sightings feed.
- **Tides & Sun**: Visual tide curve and solar events.

## 7. Engineering Standards
- **Testing**: Mandatory Vitest (frontend) and pytest (backend) coverage. Scrapers must use VCR recordings for reproducible tests.
- **Types**: Strict TypeScript for frontend and MyPy for backend.
- **Database**: Use TimescaleDB hypertables for all time-series data to ensure performance and easy retention management.
