"""Database configuration and models for Pacifica API."""

import os
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://pacifica:password@postgres:5432/pacifica"
)

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for models
Base = declarative_base()


# SQLAlchemy Models
class Location(Base):
    """Coastal location (Point of Interest) model."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    slug = Column(Text, nullable=False, unique=True)
    lat = Column(Numeric(9, 6), nullable=False)
    lng = Column(Numeric(9, 6), nullable=False)
    location_type = Column(Text, nullable=False)
    region = Column(Text, nullable=False)
    noaa_station_id = Column(Text)  # Legacy: direct station mapping
    coastline_bearing = Column(Numeric(5, 2))
    description = Column(Text)
    show_in_dropdown = Column(Text, nullable=False, server_default=text("'true'"))
    nearest_noaa_station_id = Column(Integer)  # FK to noaa_stations
    meta = Column("metadata", JSONB, nullable=False, server_default=text("'{}'"))


class NOAAStation(Base):
    """NOAA tide/water temperature station model."""

    __tablename__ = "noaa_stations"

    id = Column(Integer, primary_key=True)
    station_id = Column(Text, nullable=False, unique=True)  # e.g., '9410840'
    name = Column(Text, nullable=False)
    lat = Column(Numeric(9, 6), nullable=False)
    lng = Column(Numeric(9, 6), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))


class Tide(Base):
    """Tide prediction/observation model."""

    __tablename__ = "tides"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    station_id = Column(Text, nullable=False)
    type = Column(Text, nullable=False)  # high | low | predicted
    height_ft = Column(Numeric(6, 3), nullable=False)
    source = Column(Text, nullable=False, server_default=text("'noaa'"))


class SunEvent(Base):
    """Sun events (sunrise, sunset, golden hour) model."""

    __tablename__ = "sun_events"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True), nullable=False)
    location_id = Column(Integer, nullable=False)
    sunrise = Column(DateTime(timezone=True), nullable=False)
    sunset = Column(DateTime(timezone=True), nullable=False)
    golden_hour_morning_start = Column(DateTime(timezone=True), nullable=False)
    golden_hour_morning_end = Column(DateTime(timezone=True), nullable=False)
    golden_hour_evening_start = Column(DateTime(timezone=True), nullable=False)
    golden_hour_evening_end = Column(DateTime(timezone=True), nullable=False)
    is_calculated = Column(Boolean, server_default=text("true"))


class Condition(Base):
    """Environmental conditions (water temp, wind, etc.) model."""

    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    location_id = Column(Integer, nullable=False)
    condition_type = Column(
        Text, nullable=False
    )  # water_temp | wind_speed | air_temp | visibility
    value = Column(Numeric(10, 3), nullable=False)
    unit = Column(Text, nullable=False)  # fahrenheit | mph | knots | feet
    source = Column(Text, nullable=False)
    source_url = Column(Text)
    raw_text = Column(Text)
    meta = Column("metadata", JSONB, nullable=False, server_default=text("'{}'"))


class Sighting(Base):
    """Wildlife sighting model."""

    __tablename__ = "sightings"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    sighting_date = Column(Date, nullable=False)
    location_id = Column(Integer, nullable=True)
    species = Column(Text, nullable=False)
    count = Column(Integer, nullable=True)
    source = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    confidence = Column(Text, nullable=False, server_default=text("'medium'"))
    meta = Column("metadata", JSONB, nullable=False, server_default=text("'{}'"))


class LiveCam(Base):
    """Live coastal webcam model."""

    __tablename__ = "live_cams"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    location_id = Column(Integer, nullable=False)
    embed_type = Column(Text, nullable=False)  # youtube | iframe
    embed_url = Column(Text, nullable=False)
    source_name = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    sort_order = Column(Integer, nullable=False, server_default=text("0"))


class SeasonalEvent(Base):
    """Seasonal coastal event model (migrations, spawning, blooms, etc.)."""

    __tablename__ = "seasonal_events"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    slug = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    typical_start_month = Column(Integer, nullable=False)
    typical_start_day = Column(Integer, nullable=False)
    typical_end_month = Column(Integer, nullable=False)
    typical_end_day = Column(Integer, nullable=False)
    species = Column(Text)
    category = Column(Text, nullable=False)
    conditions_type = Column(Text)
    conditions_text = Column(Text)
    meta = Column("metadata", JSONB, nullable=False, server_default=text("'{}'"))


class ScrapeLog(Base):
    """Scraper execution audit log model."""

    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True)
    scraper_name = Column(Text, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    status = Column(Text, nullable=False)
    records_created = Column(Integer, nullable=False, server_default=text("0"))
    records_updated = Column(Integer, nullable=False, server_default=text("0"))
    records_skipped = Column(Integer, nullable=False, server_default=text("0"))
    error_message = Column(Text)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
