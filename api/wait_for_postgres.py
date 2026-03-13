#!/usr/bin/env python3
"""Wait for PostgreSQL to be ready."""

import os
import sys
import time

import psycopg2

from logging_config import configure_logging, get_logger

# Configure logging first
configure_logging()
logger = get_logger("wait_for_postgres")


def get_database_url():
    """Get database URL from environment."""
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://pacifica:password@postgres:5432/pacifica"
    )
    return database_url.replace("postgresql+asyncpg", "postgresql")


def mask_password(url: str) -> str:
    """Mask password in database URL for logging."""
    try:
        parts = url.split(":")
        if len(parts) >= 3:
            password_part = parts[2].split("@")[0]
            return url.replace(password_part, "****")
    except Exception:
        pass
    return url


def wait_for_postgres(max_attempts: int = 30, sleep_seconds: int = 2):
    """Wait for PostgreSQL to accept connections."""
    database_url = get_database_url()
    masked_url = mask_password(database_url)

    logger.info(
        "Waiting for PostgreSQL", database_url=masked_url, max_attempts=max_attempts
    )

    for attempt in range(1, max_attempts + 1):
        try:
            conn = psycopg2.connect(database_url, connect_timeout=5)
            conn.close()
            logger.info("PostgreSQL is ready", attempt=attempt)
            return True
        except Exception as e:
            logger.info(
                "PostgreSQL unavailable, retrying",
                attempt=attempt,
                max_attempts=max_attempts,
                error=str(e),
            )
            if attempt < max_attempts:
                time.sleep(sleep_seconds)

    logger.error(
        "Failed to connect to PostgreSQL after max attempts", max_attempts=max_attempts
    )
    return False


if __name__ == "__main__":
    logger.info("================================")
    logger.info("Pacifica API Container Starting")
    logger.info("================================")

    if wait_for_postgres():
        logger.info("PostgreSQL is up, proceeding with startup")
        sys.exit(0)
    else:
        sys.exit(1)
