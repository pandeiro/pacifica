# Agents Working on Pacifica

This file provides guidance for AI agents working on the Pacifica project.

## Project Overview

**Pacifica** is a real-time coastal intelligence dashboard for the Southern California coastline. It aggregates data from dozens of sources—official APIs, amateur dive reports, whale watch trip logs, live cams, citizen science platforms, and social media—into a single, information-dense, tiled interface.

## Documentation Structure

| Document | Purpose |
|----------|---------|
| `doc/spec/PRD.md` | Product vision, architecture, and requirements |
| `doc/spec/ROADMAP.md` | Execution checklist (Cards 01–37) |
| `doc/ref/*.md` | Detailed technical references |
| `doc/progress/SUMMARY.md` | Tracks completed and in-progress work |

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

### Code Standards
- **TypeScript**: Strict mode, no `any` without explicit justification
- **Python**: MyPy type checking, Ruff for linting
- **Testing**: All new features require tests (unit + integration)

### Environment Strategy
- All secrets live in GitHub Secrets, not in code
- Use `.env.example` to document required environment variables
- Never commit `.env` files

## Workflow

### Before Starting Work
Before starting any work, run through `KICKOFF.md` to:
1. Check repo state and update progress
2. Identify the next task from the Roadmap
3. Evaluate complexity and decide on branching strategy
4. Begin work with the relevant spec loaded

### After Completing Work
- **Stage and commit** your changes with a descriptive message
- **Never push** to the remote repository unless explicitly told to do so
- The user will instruct you when to push (e.g., to trigger CI/CD or share progress)

## Quick Reference

- **Repository**: https://github.com/pandeiro/pacifica
- **Production**: https://pch.onl
- **Staging**: https://staging.pch.onl