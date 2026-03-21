"""Scraper health monitoring endpoint.

Provides per-scraper status, last run time, and staleness detection
for Grafana dashboard panels and alerting.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import ScrapeLog, get_db
from logging_config import get_logger

logger = get_logger("api.scrapers")

router = APIRouter()

# Scraper schedule intervals in minutes (must match scraper schedule cron expressions)
SCRAPER_INTERVALS = {
    "noaa_tides": 24 * 60,  # "0 2 * * *" - daily
    "noaa_water_temp": 6 * 60,  # "0 */6 * * *" - every 6h
    "south_coast_divers": 3 * 60,  # "0 */3 * * *" - every 3h
    "acs_la": 24 * 60,  # "0 9 * * *" - daily
    "inaturalist": 24 * 60,  # "0 7 * * *" - daily
    "daveyslocker": 24 * 60,  # "0 6 * * *" - daily
    "dana_wharf": 24 * 60,  # "30 6 * * *" - daily
    "harbor_breeze": 24 * 60,  # "15 6 * * *" - daily
    "island_packers": 24 * 60,  # "45 6 * * *" - daily
}


class ScraperStatus(BaseModel):
    name: str
    last_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    last_duration_ms: Optional[int] = None
    last_records_created: int = 0
    last_records_updated: int = 0
    last_error: Optional[str] = None
    is_stale: bool = False
    minutes_since_last_success: Optional[float] = None
    consecutive_failures: int = 0


class ScraperHealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "critical"
    scrapers: list[ScraperStatus]
    total_scrapers: int
    healthy_count: int
    stale_count: int
    failed_count: int


@router.get("/api/health/scrapers", response_model=ScraperHealthResponse)
async def scraper_health(db: AsyncSession = Depends(get_db)):
    """Per-scraper health status with staleness detection.

    Returns the last run status for each scraper, whether it's stale
    (no success within 2x expected interval), and consecutive failure count.
    """
    scraper_statuses = []
    stale_count = 0
    failed_count = 0

    for scraper_name, interval_minutes in SCRAPER_INTERVALS.items():
        # Get the most recent scrape_log for this scraper
        result = await db.execute(
            select(ScrapeLog)
            .where(ScrapeLog.scraper_name == scraper_name)
            .order_by(ScrapeLog.started_at.desc())
            .limit(1)
        )
        last_log = result.scalar_one_or_none()

        # Get recent logs for consecutive failure counting
        recent_logs_result = await db.execute(
            select(ScrapeLog)
            .where(ScrapeLog.scraper_name == scraper_name)
            .order_by(ScrapeLog.started_at.desc())
            .limit(10)
        )
        recent_logs = recent_logs_result.scalars().all()

        consecutive_failures = 0
        for log in recent_logs:
            if log.status == "failure":
                consecutive_failures += 1
            else:
                break

        # Determine staleness
        is_stale = False
        minutes_since_success = None
        last_duration_ms = None

        if last_log:
            # Calculate duration from started_at/finished_at
            if last_log.finished_at and last_log.started_at:
                last_duration_ms = int(
                    (last_log.finished_at - last_log.started_at).total_seconds() * 1000
                )

            # Find last successful run
            success_result = await db.execute(
                select(ScrapeLog)
                .where(
                    ScrapeLog.scraper_name == scraper_name,
                    ScrapeLog.status == "success",
                )
                .order_by(ScrapeLog.started_at.desc())
                .limit(1)
            )
            last_success = success_result.scalar_one_or_none()

            if last_success:
                delta = datetime.now(timezone.utc) - last_success.started_at
                minutes_since_success = delta.total_seconds() / 60
                is_stale = minutes_since_success > (interval_minutes * 2)
            else:
                is_stale = True
                minutes_since_success = None

            if is_stale:
                stale_count += 1

        if last_log and last_log.status == "failure" and consecutive_failures >= 3:
            failed_count += 1

        scraper_statuses.append(
            ScraperStatus(
                name=scraper_name,
                last_run_at=last_log.started_at if last_log else None,
                last_status=last_log.status if last_log else None,
                last_duration_ms=last_duration_ms,
                last_records_created=last_log.records_created if last_log else 0,
                last_records_updated=last_log.records_updated if last_log else 0,
                last_error=last_log.error_message if last_log else None,
                is_stale=is_stale,
                minutes_since_last_success=minutes_since_success,
                consecutive_failures=consecutive_failures,
            )
        )

    # Overall status
    if stale_count == 0 and failed_count == 0:
        overall_status = "healthy"
    elif failed_count > 0 or stale_count > 3:
        overall_status = "critical"
    else:
        overall_status = "degraded"

    return ScraperHealthResponse(
        status=overall_status,
        scrapers=scraper_statuses,
        total_scrapers=len(scraper_statuses),
        healthy_count=len(scraper_statuses) - stale_count,
        stale_count=stale_count,
        failed_count=failed_count,
    )
