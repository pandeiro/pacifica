# Technical Reference: Infrastructure & Deployment

## 1. Environment Strategy
The project follows a "Configuration as Code" approach, with all secrets and environment-specific settings managed outside of version control.

### Configuration
- **Environment Variables**: Used for DB URLs, API keys, and service endpoints.
- **GitHub Secrets**: Source of truth for all sensitive variables (e.g., `GOOGLE_MAPS_API_KEY`, `SSH_PRIVATE_KEY`).
- **`.env.example`**: Maintained in the repo to document all required variables.

## 2. Docker Architecture

**Important**: Nginx runs on the **host machine** (outside Docker). Docker Compose orchestrates only the application services (`api`, `postgres`, `scraper`).

### Production Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    nginx (host machine)                         │
│                    pacifica.pch.onl :443                        │
│                                                                 │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │  Static files    │  api.pch.onl (upstream)              │  │
│    │  /var/www/pacifica  │  → localhost:4900 (internal only)│  │
│    │  /prod/           │  ws://api.pch.onl                   │  │
│    └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Docker (not exposed to public)               │
│                                                                 │
│  ┌───────────────┐         ┌──────────────┐                    │
│  │  API Server   │         │  PostgreSQL  │                    │
│  │  :4900        │ ◄──────►│  + TimescaleDB│                   │
│  └───────────────┘         └──────────────┘                    │
│          │                                                     │
│  ┌───────┴───────┐                                            │
│  │  Scraper      │                                             │
│  │  (direct write)│                                            │
│  └───────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Development Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser                                                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Vite Dev Server  │  API Server (exposed port)            ││
│  │  localhost:5173    │  localhost:4900                       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Docker                                       │
│                                                                 │
│  ┌───────────────┐         ┌──────────────┐                    │
│  │  API Server   │         │  PostgreSQL  │                    │
│  │  :4900        │ ◄──────►│  + TimescaleDB│                   │
│  └───────────────┘         └──────────────┘                    │
│          │                                                     │
│  ┌───────┴───────┐                                            │
│  │  Scraper      │                                             │
│  └───────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Services (Docker Compose)

| Service | Role | Database Access | Exposed Port | Notes |
|---------|------|-----------------|--------------|-------|
| **api** | REST + WebSocket | Read-only | `:4900` | In dev: `localhost:4900`. In prod: internal only via nginx upstream |
| **postgres** | Data store | N/A | None | Docker network only |
| **scraper** | Data collection | Read-write | None | Docker network only |

### Key Design Decisions

1. **Scraper Direct Access**: Scrapers write directly to Postgres within the Docker network. This is safe because:
   - No database port is exposed externally
   - All scrapers run within the isolated Docker network

2. **API Layer (FastAPI) Responsibilities**:
   - **Read Operations**: All SELECT queries for the frontend
   - **Data Transformation**: Formatting, interpolation, aggregation
   - **WebSocket Broadcast**: Receives internal notifications from scrapers, pushes to clients
   - **Health Checks**: Exposes `/api/health` endpoints

3. **Nginx (Host) Responsibilities**:
   - **TLS Termination**: Let's Encrypt or similar
   - **Static Files**: Serves built SPA from `/var/www/pacifica/prod/` or `/staging/`
   - **Upstream Proxy**: Routes `/api` requests to `localhost:4900` (not publicly exposed)
   - **WebSocket Upgrade**: Handles WS connections for real-time updates

4. **Single Database Instance**: Production (`pch.onl`) and Staging (`staging.pch.onl`) share the same PostgreSQL instance, differentiated by separate API containers.

## 3. GitHub Actions CI/CD
The repository at `https://github.com/pandeiro/pacifica` uses GitHub Actions for automation.

### Pipelines
1. **Validation**: Linting, type-checking, and unit tests on every push.
2. **Preview (PR)**: Builds and deploys to `/staging` path on the VPS.
3. **Production (Main)**: Pushes built images to **GHCR** and deploys via SSH to the production server.

### Deployment Flow
- **Assets**: Built SPA files are synced to the VPS asset path (e.g., `/var/www/pacifica/prod/`).
- **Containers**: `docker compose pull && docker compose up -d` executed via SSH.
- **Health Verification**: Post-deployment scripts check `/api/health` before considering the deployment successful.

## 4. Staging vs. Production

| Aspect | Production | Staging |
|--------|------------|---------|
| **URL** | `https://pch.onl` | `https://staging.pch.onl` |
| **Frontend** | Served from `/prod/` | Served from `/staging/` |
| **API** | `api` container | `api-staging` container |
| **Database** | Shared (read-only) | Shared (read-only) |
| **Scrapers** | `scraper` container | `scraper-staging` container (optional) |

### Notes on Shared Database
- Staging is primarily for **UI/UX testing**, not data isolation
- Both environments see the same data
- Scrapers run once and write to the shared DB
- For true isolation, use separate schemas or database instances (future enhancement)

## 5. Testing Strategy

### Frontend Testing
- **agent-browser**: Used for high-level, agentic verification of dashboard functionality. Tests simulate user workflows and verify that tiles render correctly, data flows through WebSockets, and the UI responds to real-time updates.
- **Playwright**: Used for scraping workflows that require complex interactions (e.g., JavaScript-rendered pages, multi-step navigation). Scrapers that need full browser automation use Playwright directly.

### Backend Testing
- **pytest**: Unit tests for transformation logic, integration tests for database operations
- **VCR.py**: Records HTTP interactions for scraper tests

## 6. Local Development
See `doc/ref/local_dev.md` for local environment setup.