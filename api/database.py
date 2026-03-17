"""Database configuration and models for Pacifica API."""

import os
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import Column, DateTime, Float, Integer, Numeric, String, Text, text
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
    """Coastal location model."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    slug = Column(Text, nullable=False, unique=True)
    lat = Column(Numeric(9, 6), nullable=False)
    lng = Column(Numeric(9, 6), nullable=False)
    location_type = Column(Text, nullable=False)
    region = Column(Text, nullable=False)
    noaa_station_id = Column(Text)
    coastline_bearing = Column(Numeric(5, 2))
    description = Column(Text)
    meta = Column("metadata", JSONB, nullable=False, server_default=text("'{}'"))


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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
