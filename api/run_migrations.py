#!/usr/bin/env python3
"""Database migration runner.

Executes SQL migration files in order.
"""

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def get_connection():
    """Get database connection from environment."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Fallback for docker-compose internal networking
        database_url = "postgresql://pacifica:password@postgres:5432/pacifica"

    # Convert asyncpg URL to psycopg2 format if needed
    database_url = database_url.replace("postgresql+asyncpg", "postgresql")
    database_url = database_url.replace("postgresql+psycopg2", "postgresql")

    return psycopg2.connect(database_url)


def run_migrations(migrations_dir: str = "/app/migrations"):
    """Run all SQL migration files in order."""
    migrations_path = Path(migrations_dir)

    if not migrations_path.exists():
        print(f"Migrations directory not found: {migrations_dir}")
        return

    # Get all .sql files and sort them
    sql_files = sorted(migrations_path.glob("*.sql"))

    if not sql_files:
        print("No migration files found")
        return

    print(f"Found {len(sql_files)} migration files")

    conn = get_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        for sql_file in sql_files:
            print(f"Running migration: {sql_file.name}")
            with open(sql_file, "r") as f:
                sql = f.read()
                if sql.strip():
                    cursor.execute(sql)
                    print(f"  ✓ {sql_file.name}")
                else:
                    print(f"  - {sql_file.name} (empty)")

        print("Migrations completed successfully")
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


def run_seed(seed_dir: str = "/app/seed"):
    """Run all SQL seed files in order."""
    seed_path = Path(seed_dir)

    if not seed_path.exists():
        print(f"Seed directory not found: {seed_dir}")
        return

    sql_files = sorted(seed_path.glob("*.sql"))

    if not sql_files:
        print("No seed files found")
        return

    print(f"Found {len(sql_files)} seed files")

    conn = get_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        for sql_file in sql_files:
            print(f"Running seed: {sql_file.name}")
            with open(sql_file, "r") as f:
                sql = f.read()
                if sql.strip():
                    cursor.execute(sql)
                    print(f"  ✓ {sql_file.name}")
                else:
                    print(f"  - {sql_file.name} (empty)")

        print("Seed data loaded successfully")
    except Exception as e:
        print(f"Seed failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("Running database migrations...")
    run_migrations()

    print("\nLoading seed data...")
    run_seed()

    print("\nDatabase setup complete!")
