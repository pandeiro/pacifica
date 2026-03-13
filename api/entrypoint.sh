#!/bin/bash
set -e

# Configure logging based on environment
export PYTHONUNBUFFERED=1

# Wait for PostgreSQL to be ready
python3 /app/wait_for_postgres.py

# Run migrations and seed data
python3 /app/run_migrations.py

# Start the API server
exec uvicorn main:app --host 0.0.0.0 --port 4900 --log-level info