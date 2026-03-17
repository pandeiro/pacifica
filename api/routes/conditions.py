"""Conditions API routes."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Location, Condition, NOAAStation
from schemas import WaterTemperatureReading, WaterTemperatureResponse, StationInfo
from logging_config import get_logger
from utils.station_utils import calculate_distance, get_direction

router = APIRouter(prefix="/api", tags=["conditions"])
logger = get_logger("api.conditions")


def fahrenheit_to_celsius(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return round((f - 32) * 5 / 9, 1)


@router.get("/conditions/water-temp", response_model=WaterTemperatureResponse)
async def get_water_temperature(
    location_id: int = Query(3, description="Location ID (default: 3 = Santa Monica)"),
    hours: int = Query(48, description="Hours of historical data", ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """
    Get water temperature for a specific location.

    Finds the nearest station with water temp data and returns readings
    from that station along with station info.
    """
    logger.info(
        "Water temperature endpoint called",
        location_id=location_id,
        hours=hours,
    )

    # Get location info
    location_result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = location_result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=404,
            detail=f"Location not found: {location_id}",
        )

    # Calculate time window
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=hours)

    # Find all stations that have water temp data
    stations_result = await db.execute(
        select(Condition.source)
        .where(Condition.condition_type == "water_temp")
        .where(Condition.timestamp >= start_time)
        .distinct()
    )
    sources = stations_result.scalars().all()

    # Extract station IDs from sources (format: "noaa_9410840")
    station_ids = []
    for source in sources:
        if source.startswith("noaa_"):
            station_ids.append(source.replace("noaa_", ""))

    if not station_ids:
        # No water temp data available anywhere
        return WaterTemperatureResponse(
            location_id=location_id,
            location_name=location.name,
            current_temp_f=None,
            current_temp_c=None,
            source=None,
            source_url=None,
            last_updated=None,
            history=[],
            hours_requested=hours,
            readings_count=0,
            station_info=None,
        )

    # Get all NOAA stations
    all_stations_result = await db.execute(select(NOAAStation))
    all_stations = all_stations_result.scalars().all()

    # Find nearest station with water temp data
    nearest_station = None
    min_distance = float("inf")

    for station in all_stations:
        if station.station_id in station_ids:
            distance = calculate_distance(
                float(location.lat),
                float(location.lng),
                float(station.lat),
                float(station.lng),
            )
            if distance < min_distance:
                min_distance = distance
                nearest_station = station

    if not nearest_station:
        return WaterTemperatureResponse(
            location_id=location_id,
            location_name=location.name,
            current_temp_f=None,
            current_temp_c=None,
            source=None,
            source_url=None,
            last_updated=None,
            history=[],
            hours_requested=hours,
            readings_count=0,
            station_info=None,
        )

    # Query water temperature conditions for the nearest station
    result = await db.execute(
        select(Condition)
        .where(Condition.source == f"noaa_{nearest_station.station_id}")
        .where(Condition.condition_type == "water_temp")
        .where(Condition.timestamp >= start_time)
        .where(Condition.timestamp <= now)
        .order_by(desc(Condition.timestamp))
    )
    conditions = result.scalars().all()

    # Convert to Pydantic models
    history = [
        WaterTemperatureReading(
            timestamp=cond.timestamp,
            temperature_f=float(cond.value),
            source=cond.source,
            source_url=cond.source_url,
        )
        for cond in conditions
    ]

    # Get the most recent reading (current temperature)
    current = history[0] if history else None

    current_temp_f = current.temperature_f if current else None
    current_temp_c = fahrenheit_to_celsius(current_temp_f) if current_temp_f else None

    # Calculate station info
    distance = calculate_distance(
        float(location.lat),
        float(location.lng),
        float(nearest_station.lat),
        float(nearest_station.lng),
    )
    direction = get_direction(
        float(location.lat),
        float(location.lng),
        float(nearest_station.lat),
        float(nearest_station.lng),
    )

    station_info = None
    if distance >= 0.1:
        station_info = StationInfo(
            name=nearest_station.name,
            station_id=nearest_station.station_id,
            distance_miles=round(distance, 1),
            direction=direction,
        )

    return WaterTemperatureResponse(
        location_id=location_id,
        location_name=location.name,
        current_temp_f=current_temp_f,
        current_temp_c=current_temp_c,
        source=current.source if current else None,
        source_url=current.source_url if current else None,
        last_updated=current.timestamp if current else None,
        history=history,
        hours_requested=hours,
        readings_count=len(history),
        station_info=station_info,
    )
