# Pacifica - Project Makefile
# Run commands from project root without cd-ing into subdirectories

.PHONY: help dev build test lint typecheck up down migrate logs

# Default target
help:
	@echo "Pacifica commands:"
	@echo "  make up           - Start Docker services (API + DB)"
	@echo "  make up-all       - Start all services including scraper"
	@echo "  make down         - Stop all Docker services"
	@echo "  make migrate      - Run database migrations (includes seed data)"
	@echo "  make logs         - Tail service logs"
	@echo "  make dev          - Start frontend dev server"
	@echo "  make build        - Build frontend for production"
	@echo "  make test         - Run frontend tests"
	@echo "  make lint         - Run frontend linter"
	@echo "  make typecheck    - Run TypeScript type checking"

# Docker commands
up:
	docker compose up -d

up-all:
	docker compose --profile scraper up -d

down:
	docker compose down

migrate:
	docker compose exec api alembic upgrade head
	@echo "All migrations completed."

logs:
	docker compose logs -f

# Frontend commands
dev:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

test:
	cd frontend && npm run test

lint:
	cd frontend && npm run lint

typecheck:
	cd frontend && npx tsc --noEmit