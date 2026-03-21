# Agents Working on Pacifica

This file provides guidance for AI agents working on the Pacifica project.

## Project Overview

**Pacifica** is a real-time coastal intelligence dashboard for the Southern California coastline. It aggregates data from dozens of sources—official APIs, amateur dive reports, whale watch trip logs, live cams, citizen science platforms, and social media—into a single, information-dense, tiled interface.

## Documentation Structure

| Document | Purpose |
|----------|---------|
| `doc/spec/PRD.md` | Product vision, architecture, and requirements |
| `doc/spec/ROADMAP.md` | Execution checklist (Cards 00–35) |
| `doc/ref/*.md` | Detailed technical references |
| `doc/progress/SUMMARY.md` | Progress tracker (one line per completed item) |

### Progress Tracking
The `doc/progress/SUMMARY.md` file uses a simple format:
- Each line represents a completed work item
- The **last line** is always the most recent work
- To find the last item worked on, read only the last line of the file

## Tech Stack

- **Frontend**: React 18+, Vite, TypeScript, D3.js
- **Backend**: Python, FastAPI, WebSockets
- **Database**: PostgreSQL 16 + TimescaleDB
- **Scrapers**: Python, httpx, BeautifulSoup, APScheduler
- **Testing**: pytest, Vitest, agent-browser (Playwright wrapper)
- **Infrastructure**: Docker Compose, GitHub Actions

## Key Conventions

### Voice Profile
All generated content should read like a **passionate, knowledgeable local**—the person at the dive shop who always knows where the action is. Be practical, opinionated, and use local vernacular.

### UI Conventions
- **Default Location**: When a location dropdown is used in any tile or component, default to **Santa Monica** (the closest location to the primary development team).

### Code Standards
- **TypeScript**: Strict mode, no `any` without explicit justification
- **Python**: MyPy type checking, Ruff for linting
- **Testing**: All new features require tests (unit + integration)

### Environment Strategy
- All secrets live in GitHub Secrets, not in code
- Use `.env.example` to document required environment variables
- Never commit `.env` files

## Production Safety

### Destructive Operations
**Always seek explicit permission before performing destructive operations on production systems:**
- `DELETE`, `DROP`, or `TRUNCATE` database operations
- Overwriting configuration files in production
- Operations that destroy data (even "stale" or "duplicate" data may have irreplaceable metadata)

When data needs to be corrected on production, prefer **upsert/update** patterns over deletion. For example, if dive report metadata is missing, reprocess and update rather than delete.

### Remote Access
Production server access via SSH:
```bash
ssh mu@ottertime.com
```

## Workflow

### Before Starting Work
Before starting any work, run through `KICKOFF.md` to:
1. Check repo state and update progress
2. Identify the next task from the Roadmap
3. Evaluate complexity and decide on branching strategy
4. Begin work with the relevant spec loaded

### After Completing Work
- **Update project status** with a new line in doc/progress/SUMMARY.md about what work was done and its status
- **Stage and commit** your changes with a descriptive message
- **Never push** to the remote repository unless explicitly told to do so
- The user will instruct you when to push (e.g., to trigger CI/CD or share progress)

## Quick Reference

- **Repository**: https://github.com/pandeiro/pacifica
- **Production**: https://pch.onl
- **API (Production)**: https://api.pch.onl
- **API (Dev)**: http://localhost:4900
- **Staging**: https://staging.pch.onl
- **Local Dev**: Frontend runs on http://localhost:5173 (Vite dev server), API on http://localhost:4900

## Tools

### Database Migrations (Alembic)
We use [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. When you change models in `api/database.py`, generate a migration:

```bash
# Auto-generate migration from model changes
docker compose exec api alembic revision --autogenerate -m "describe your change"

# Run pending migrations
make migrate
```

### Screenshot Capture
Use `tools/screenshot.py` to capture full-page screenshots of the dashboard for UI verification:

```bash
# Local environment (default) - ensure frontend is running
python tools/screenshot.py
# Output: screenshots/dashboard_local_YYYYMMDD_HHMMSS.png

# Staging environment
python tools/screenshot.py --env staging
# Output: screenshots/dashboard_staging_YYYYMMDD_HHMMSS.png

# Production environment
python tools/screenshot.py --env prod
# Output: screenshots/dashboard_prod_YYYYMMDD_HHMMSS.png

# Custom URL
python tools/screenshot.py --url http://localhost:4902
```

Screenshots are saved to the `screenshots/` directory (gitignored). Use this after making UI changes to verify the visual result.
