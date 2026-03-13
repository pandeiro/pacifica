# Pacifica - Project Makefile
# Run commands from project root without cd-ing into subdirectories

.PHONY: help dev build test lint typecheck

# Default target
help:
	@echo "Pacifica commands:"
	@echo "  make dev          - Start frontend dev server"
	@echo "  make build        - Build frontend for production"
	@echo "  make test         - Run frontend tests"
	@echo "  make lint         - Run frontend linter"
	@echo "  make typecheck    - Run TypeScript type checking"

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
