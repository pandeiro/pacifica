"""Database utilities for Pacifica scrapers.

Scrapers use the same SQLAlchemy models as the API for consistency.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import models from API
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.database import Location, Tide, SunEvent, Condition, Base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://pacifica:password@postgres:5432/pacifica"
)

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create session factory
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_db_session():
    """Get a database session context manager."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_locations(session: AsyncSession) -> List[Location]:
    """Fetch all locations from the database."""
    result = await session.execute(select(Location).order_by(Location.name))
    return result.scalars().all()


async def get_locations_with_noaa_stations(session: AsyncSession) -> List[Location]:
    """Fetch locations that have NOAA station IDs."""
    result = await session.execute(
        select(Location)
        .where(Location.noaa_station_id.isnot(None))
        .order_by(Location.name)
    )
    return result.scalars().all()


async def insert_tides(session: AsyncSession, records: List[Dict[str, Any]]):
    """Insert tide records into the database.

    Uses merge/upsert logic to handle duplicate entries gracefully.
    If a record with the same (timestamp, station_id, type) exists,
    it updates the height_ft and source values.
    """
    for record in records:
        # Check if record exists
        existing = await session.execute(
            select(Tide).where(
                Tide.timestamp == record["timestamp"],
                Tide.station_id == record["station_id"],
                Tide.type == record["type"],
            )
        )
        existing_tide = existing.scalar_one_or_none()

        if existing_tide:
            # Update existing record
            existing_tide.height_ft = record["height_ft"]
            existing_tide.source = record.get("source", "noaa")
        else:
            # Create new record
            tide = Tide(
                timestamp=record["timestamp"],
                station_id=record["station_id"],
                type=record["type"],
                height_ft=record["height_ft"],
                source=record.get("source", "noaa"),
            )
            session.add(tide)

    await session.flush()


async def insert_sun_events(session: AsyncSession, records: List[Dict[str, Any]]):
    """Insert sun event records into the database.

    Uses ON CONFLICT DO UPDATE to refresh data if it already exists.
    """
    for record in records:
        # Check if record exists
        existing = await session.execute(
            select(SunEvent).where(
                SunEvent.date == record["date"],
                SunEvent.location_id == record["location_id"],
            )
        )
        existing_event = existing.scalar_one_or_none()

        if existing_event:
            # Update existing record
            existing_event.sunrise = record["sunrise"]
            existing_event.sunset = record["sunset"]
            existing_event.golden_hour_morning_start = record[
                "golden_hour_morning_start"
            ]
            existing_event.golden_hour_morning_end = record["golden_hour_morning_end"]
            existing_event.golden_hour_evening_start = record[
                "golden_hour_evening_start"
            ]
            existing_event.golden_hour_evening_end = record["golden_hour_evening_end"]
        else:
            # Create new record
            sun_event = SunEvent(
                date=record["date"],
                location_id=record["location_id"],
                sunrise=record["sunrise"],
                sunset=record["sunset"],
                golden_hour_morning_start=record["golden_hour_morning_start"],
                golden_hour_morning_end=record["golden_hour_morning_end"],
                golden_hour_evening_start=record["golden_hour_evening_start"],
                golden_hour_evening_end=record["golden_hour_evening_end"],
            )
            session.add(sun_event)

    await session.flush()


async def insert_conditions(session: AsyncSession, records: List[Dict[str, Any]]):
    """Insert condition records into the database.

    Stores hourly averages of environmental conditions like water temperature.
    """
    for record in records:
        condition = Condition(
            timestamp=record["timestamp"],
            location_id=record["location_id"],
            condition_type=record["condition_type"],
            value=record["value"],
            unit=record["unit"],
            source=record.get("source", "noaa"),
            source_url=record.get("source_url"),
            raw_text=record.get("raw_text"),
        )
        session.add(condition)

    await session.flush()


async def get_location_by_slug(session: AsyncSession, slug: str) -> Optional[Location]:
    """Fetch a location by its slug."""
    result = await session.execute(select(Location).where(Location.slug == slug))
    return result.scalar_one_or_none()


async def check_duplicate_dive_report(
    session: AsyncSession, location_id: int, raw_text: str, hours: int = 96
) -> bool:
    """Check if a dive report with the same content exists within the specified hours.

    Returns True if a duplicate is found, False otherwise.
    """
    # Calculate the cutoff time
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Check for existing record with same content
    result = await session.execute(
        select(Condition)
        .where(
            Condition.location_id == location_id,
            Condition.condition_type == "dive_report",
            Condition.source == "south_coast_divers",
            Condition.timestamp >= cutoff,
        )
        .order_by(Condition.timestamp.desc())
    )

    existing = result.scalars().all()

    # Check if any existing record has the same content
    for record in existing:
        if record.raw_text == raw_text:
            return True

    return False
