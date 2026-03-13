#!/usr/bin/env python3
"""Database migration runner with structured logging."""

import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from logging_config import configure_logging, get_logger

# Configure logging first
configure_logging()
logger = get_logger("migrations")


def get_connection():
    """Get database connection from environment."""
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://pacifica:password@postgres:5432/pacifica"
    )
    database_url = database_url.replace("postgresql+asyncpg", "postgresql")
    database_url = database_url.replace("postgresql+psycopg2", "postgresql")
    return psycopg2.connect(database_url)


def run_migrations(migrations_dir: str = "/app/migrations"):
    """Run all SQL migration files in order."""
    migrations_path = Path(migrations_dir)

    if not migrations_path.exists():
        logger.warning("Migrations directory not found", path=migrations_dir)
        return

    sql_files = sorted(migrations_path.glob("*.sql"))

    if not sql_files:
        logger.info("No migration files found")
        return

    logger.info("Running migrations", count=len(sql_files))

    conn = get_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        for sql_file in sql_files:
            logger.info("Running migration", file=sql_file.name)
            with open(sql_file, "r") as f:
                sql = f.read()
                if sql.strip():
                    cursor.execute(sql)
                    logger.info("Migration completed", file=sql_file.name)
                else:
                    logger.warning("Empty migration file", file=sql_file.name)

        logger.info("All migrations completed successfully")
    except Exception as e:
        logger.error("Migration failed", error=str(e))
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


def run_seed(seed_dir: str = "/app/seed"):
    """Run all SQL seed files in order."""
    seed_path = Path(seed_dir)

    if not seed_path.exists():
        logger.warning("Seed directory not found", path=seed_dir)
        return

    sql_files = sorted(seed_path.glob("*.sql"))

    if not sql_files:
        logger.info("No seed files found")
        return

    logger.info("Loading seed data", count=len(sql_files))

    conn = get_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    try:
        for sql_file in sql_files:
            logger.info("Running seed", file=sql_file.name)
            with open(sql_file, "r") as f:
                sql = f.read()
                if sql.strip():
                    cursor.execute(sql)
                    logger.info("Seed completed", file=sql_file.name)
                else:
                    logger.warning("Empty seed file", file=sql_file.name)

        logger.info("All seed data loaded successfully")
    except Exception as e:
        logger.error("Seed failed", error=str(e))
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    logger.info("Running database setup...")
    run_migrations()
    run_seed()
    logger.info("Database setup complete")
