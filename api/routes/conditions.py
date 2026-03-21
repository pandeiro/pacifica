"""Conditions API routes."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Location, Condition, NOAAStation
from schemas import (
    WaterTemperatureReading,
    WaterTemperatureResponse,
    StationInfo,
    VisibilityResponse,
    VisibilityHistoryItem,
)
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
    # Use DISTINCT ON to deduplicate any existing duplicate records
    result = await db.execute(
        select(Condition)
        .distinct(Condition.timestamp)
        .where(Condition.source == f"noaa_{nearest_station.station_id}")
        .where(Condition.condition_type == "water_temp")
        .where(Condition.timestamp >= start_time)
        .where(Condition.timestamp <= now)
        .order_by(Condition.timestamp, desc(Condition.timestamp))
    )
    conditions = result.scalars().all()

    # Convert to Pydantic models and sort by timestamp desc (most recent first)
    history = [
        WaterTemperatureReading(
            timestamp=cond.timestamp,
            temperature_f=float(cond.value),
            source=cond.source,
            source_url=cond.source_url,
        )
        for cond in conditions
    ]
    history.sort(key=lambda x: x.timestamp, reverse=True)

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


@router.get("/conditions/visibility", response_model=VisibilityResponse)
async def get_visibility(
    location_id: int = Query(3, description="Location ID (default: 3 = Santa Monica)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get water visibility for a specific location.

    Returns the most recent visibility report from dive conditions.
    Falls back to the latest visibility data from any location if
    the requested location has no data (South Coast Divers is global).
    """
    logger.info(
        "Visibility endpoint called",
        location_id=location_id,
    )

    location_result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = location_result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=404,
            detail=f"Location not found: {location_id}",
        )

    vis_result = await db.execute(
        select(Condition)
        .where(Condition.location_id == location_id)
        .where(Condition.condition_type == "visibility")
        .order_by(desc(Condition.timestamp))
        .limit(1)
    )
    visibility_record = vis_result.scalar_one_or_none()

    if not visibility_record:
        vis_result = await db.execute(
            select(Condition)
            .where(Condition.condition_type == "visibility")
            .where(Condition.source == "south_coast_divers")
            .order_by(desc(Condition.timestamp))
            .limit(1)
        )
        visibility_record = vis_result.scalar_one_or_none()

    visibility_min = None
    visibility_max = None
    swell_min = None
    swell_max = None
    source = None
    source_url = None
    last_updated = None

    if visibility_record:
        meta = visibility_record.meta or {}
        visibility_min = meta.get("visibility_min")
        visibility_max = meta.get("visibility_max")
        source = visibility_record.source
        source_url = visibility_record.source_url
        last_updated = visibility_record.timestamp

        if visibility_record.timestamp:
            swell_result = await db.execute(
                select(Condition)
                .where(Condition.condition_type == "swell")
                .where(Condition.source == visibility_record.source)
                .where(Condition.timestamp == visibility_record.timestamp)
                .limit(1)
            )
            swell_record = swell_result.scalar_one_or_none()
            if swell_record:
                swell_meta = swell_record.meta or {}
                swell_min = swell_meta.get("swell_min")
                swell_max = swell_meta.get("swell_max")

    # Fetch history for chart (last 30 visibility readings)
    history_result = await db.execute(
        select(Condition)
        .where(Condition.condition_type == "visibility")
        .where(Condition.source == "south_coast_divers")
        .order_by(desc(Condition.timestamp))
        .limit(30)
    )
    history_records = history_result.scalars().all()
    history = [
        VisibilityHistoryItem(
            timestamp=record.timestamp,
            visibility_max=record.meta.get("visibility_max", int(record.value))
            if record.meta
            else int(record.value),
        )
        for record in reversed(history_records)  # Oldest first for chart
        if record.timestamp and record.value is not None
    ]

    return VisibilityResponse(
        location_id=location_id,
        location_name=location.name,
        visibility_min=visibility_min,
        visibility_max=visibility_max,
        swell_min=swell_min,
        swell_max=swell_max,
        source=source,
        source_url=source_url,
        last_updated=last_updated,
        history=history,
    )

    location_result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = location_result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=404,
            detail=f"Location not found: {location_id}",
        )

    vis_result = await db.execute(
        select(Condition)
        .where(Condition.location_id == location_id)
        .where(Condition.condition_type == "visibility")
        .order_by(desc(Condition.timestamp))
        .limit(1)
    )
    visibility_record = vis_result.scalar_one_or_none()

    visibility_feet = None
    swell_feet = None
    confidence = None
    source = None
    source_url = None
    last_updated = None

    if visibility_record:
        visibility_feet = (
            int(visibility_record.value) if visibility_record.value else None
        )
        meta = visibility_record.meta or {}
        confidence = meta.get("confidence")
        source = visibility_record.source
        source_url = visibility_record.source_url
        last_updated = visibility_record.timestamp

        if visibility_record.timestamp:
            swell_result = await db.execute(
                select(Condition)
                .where(Condition.location_id == location_id)
                .where(Condition.condition_type == "swell")
                .where(Condition.timestamp == visibility_record.timestamp)
                .limit(1)
            )
            swell_record = swell_result.scalar_one_or_none()
            if swell_record:
                swell_feet = int(swell_record.value) if swell_record.value else None

    return VisibilityResponse(
        location_id=location_id,
        location_name=location.name,
        visibility_feet=visibility_feet,
        swell_feet=swell_feet,
        confidence=confidence,
        source=source,
        source_url=source_url,
        last_updated=last_updated,
    )
