# Technical Reference: Infrastructure & Deployment

## 1. Environment Strategy
The project follows a "Configuration as Code" approach, with all secrets and environment-specific settings managed outside of version control.

### Configuration
- **Environment Variables**: Used for DB URLs, API keys, and service endpoints.
- **GitHub Secrets**: Source of truth for all sensitive variables (e.g., `GOOGLE_MAPS_API_KEY`, `SSH_PRIVATE_KEY`).
- **`.env.example`**: Maintained in the repo to document all required variables.

## 2. Docker Architecture
Orchestrated via `docker-compose.yml`:
- **`frontend`**: Static build of the React app.
- **`api`**: FastAPI server.
- **`scraper`**: Scraper worker process.
- **`postgres`**: Database (TimescaleDB).
- **`nginx`**: Front-facing proxy and static asset server.

## 3. GitHub Actions CI/CD
The repository at `https://github.com/pandeiro/pacifica` uses GitHub Actions for automation.

### Pipelines
1. **Validation**: Linting, type-checking, and unit tests on every push.
2. **Preview (PR)**: Builds and deploys a temporary instance or to a `/staging` path on the VPS.
3. **Production (Main)**: Pushes built images to **GHCR** and deploys via SSH to the production server.

### Deployment Flow
- **Assets**: Built SPA files are synced to the VPS asset path (e.g., `/var/www/pacific/prod/`).
- **Containers**: `docker compose pull && docker compose up -d` executed via SSH.
- **Health Verification**: Post-deployment scripts check `/api/health` before considering the deployment successful.

## 4. Staging vs. Production
- **Production**: Accessible at `pch.onl`.
- **Staging**: Accessible at `staging.pch.onl`.
- **Database**: Production and Staging should use isolated databases or schemas.
