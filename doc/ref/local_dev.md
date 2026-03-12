# Technical Reference: Local Development

## 1. Overview
Local development uses Docker Compose to run the full stack on your machine. The setup mirrors production architecture with scraper direct-write access and API read-only access.

## 2. Quick Start

```bash
# Start the full stack
docker compose up -d

# Run migrations
make migrate

# Seed initial data
make seed

# Tail logs
docker compose logs -f
```

### Default Ports
| Service | Port | Access |
|---------|------|--------|
| Postgres | 5432 | `localhost:5432` |
| API Server | 3000 | `http://localhost:3000` (exposed for dev) |
| Frontend | 5173 | `http://localhost:5173` (Vite dev server) |

### Production vs. Development

**Development:**
- Vite dev server serves the SPA at `localhost:5173`
- API server exposed at `localhost:3000`
- No nginx involved (direct browser → API communication)

**Production:**
- Nginx (on host) serves static SPA from `/var/www/pacifica/prod/`
- Nginx proxies `/api` requests to `localhost:3000` (not publicly exposed)
- Nginx handles WebSocket upgrades at `wss://pch.onl/api/ws`

## 3. Database Access

### Connection String
```
DATABASE_URL=postgresql+asyncpg://pacifica:password@localhost:5432/pacifica
```

### Environment Variables (`.env`)
```env
# Database
DATABASE_URL=postgresql+asyncpg://pacifica:password@localhost:5432/pacifica

# Home location (for drive time calculations)
HOME_LAT=33.XXXX
HOME_LNG=-118.XXXX

# API Keys (local development)
GOOGLE_MAPS_API_KEY=...

# Optional services
LLM_SERVICE_URL=http://localhost:3000/v1
```

### Docker Network
All services join a shared `pacifica_default` network. Scrapers connect directly to `postgres:5432` (internal hostname), while the API server also connects via the same internal hostname.

## 4. Schema Migrations

### Migration Runner
Migrations are managed via `db/run_migrations.sh`:

```bash
#!/bin/bash
set -e
MIGRATIONS_DIR="$(dirname "$0")/migrations"
for file in "$MIGRATIONS_DIR"/*.sql; do
    echo "Running migration: $(basename "$file")"
    psql "$DATABASE_URL" -f "$file"
done
```

### Makefile Target
```makefile
.PHONY: migrate
migrate:
	docker compose exec postgres /bin/sh -c "cd /migrations && for f in *.sql; do psql -f $$f; done"
```

### Migration Order
1. `001_tables.sql` — Create base tables
2. `002_hypertables.sql` — Convert to TimescaleDB hypertables
3. `003_indexes.sql` — Add indexes and unique constraints
4. `004_constraints.sql` — Add CHECK constraints
5. `005_retention_policies.sql` — Set TimescaleDB retention
6. `006_compression_policies.sql` — Set compression policies

## 5. Seed Data

Initial data is loaded via SQL scripts in `db/seed/`:

```bash
# Seed locations
psql "$DATABASE_URL" -f db/seed/001_locations.sql

# Seed live cams
psql "$DATABASE_URL" -f db/seed/002_live_cams.sql

# Seed seasonal events
psql "$DATABASE_URL" -f db/seed/003_seasonal_events.sql
```

### Makefile Target
```makefile
.PHONY: seed
seed:
	docker compose exec postgres /bin/sh -c "cd /seed && for f in *.sql; do psql -f $$f; done"
```

## 6. Testing Database

### Isolated Test Environment
Integration tests use a separate, ephemeral database:

```yaml
# docker-compose.test.yml
services:
  postgres-test:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: pacifica_test
      POSTGRES_USER: pacifica
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data  # In-memory, disposable
```

### Running Tests
```bash
# Start test database
docker compose -f docker-compose.test.yml up -d

# Run integration tests
TEST_DATABASE_URL=postgresql+asyncpg://pacifica:test@localhost:5433/pacifica_test pytest -m integration

# Cleanup
docker compose -f docker-compose.test.yml down
```

## 7. Development Workflow

### Typical Session
1. Pull latest: `git pull origin main`
2. Start stack: `docker compose up -d`
3. Run migrations: `make migrate`
4. Run seed: `make seed`
5. Develop with hot reload (Vite for frontend, `--reload` for API)
6. Test locally: `make test-fast`
7. Commit when done (do not push unless told)

### Docker Compose Profiles
```bash
# Full stack (default)
docker compose up -d

# Test environment only
docker compose -f docker-compose.test.yml up -d

# API + DB only (no scrapers)
docker compose --profile dev-api up -d
```

## 8. Troubleshooting

### Database Connection Issues
```bash
# Check if Postgres is running
docker compose ps postgres

# View logs
docker compose logs postgres

# Restart
docker compose restart postgres
```

### Migration Failures
```bash
# Drop and recreate (DESTRUCTIVE - local only)
docker compose down -v
docker compose up -d
make migrate
make seed
```

### Permission Issues
Ensure your user has access to the Docker socket:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```