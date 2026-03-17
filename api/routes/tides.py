"""Tides API routes."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Location, Tide
from schemas import TideEvent, TidesResponse
from logging_config import get_logger

router = APIRouter(prefix="/api", tags=["tides"])
logger = get_logger("api.tides")


def interpolate_current_height(
    events: list[TideEvent], now: datetime
) -> Optional[float]:
    """
    Interpolate current tide height from surrounding high/low events.

    Uses linear interpolation between the tide event immediately before now
    and the one immediately after.
    """
    # Sort events by timestamp
    sorted_events = sorted(events, key=lambda e: e.timestamp)

    # Find events before and after now
    before = [e for e in sorted_events if e.timestamp <= now]
    after = [e for e in sorted_events if e.timestamp > now]

    if not before or not after:
        return None

    e0, e1 = before[-1], after[0]

    # Calculate interpolation factor (0 to 1)
    total_duration = (e1.timestamp - e0.timestamp).total_seconds()
    elapsed = (now - e0.timestamp).total_seconds()

    if total_duration == 0:
        return float(e0.height_ft)

    t = elapsed / total_duration

    # Linear interpolation
    interpolated = float(e0.height_ft) + t * (float(e1.height_ft) - float(e0.height_ft))
    return round(interpolated, 2)


@router.get("/tides", response_model=TidesResponse)
async def get_tides(
    location_id: int = Query(..., description="Location ID"),
    hours: int = Query(48, description="Hours of data to return", ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """
    Get tide events for a specific location.

    Returns tide events (high/low) for the requested time window,
    along with the next upcoming high and low tides, and an
    interpolated current tide height.
    """
    logger.info("Tides endpoint called", location_id=location_id, hours=hours)

    # Get location info
    location_result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = location_result.scalars().first()

    if not location:
        raise HTTPException(
            status_code=404, detail=f"No location found for ID: {location_id}"
        )

    # Get the NOAA station ID for this location
    from database import NOAAStation

    station_result = await db.execute(
        select(NOAAStation).where(NOAAStation.id == location.nearest_noaa_station_id)
    )
    station = station_result.scalars().first()

    if not station:
        raise HTTPException(
            status_code=404,
            detail=f"No NOAA station found for location: {location.name}",
        )

    station_id = station.station_id

    # Calculate time window
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(hours=hours)

    # Query tide events for this station in the time window
    tide_result = await db.execute(
        select(Tide)
        .where(Tide.station_id == station_id)
        .where(Tide.timestamp >= now)
        .where(Tide.timestamp <= end_time)
        .order_by(Tide.timestamp)
    )
    tides = tide_result.scalars().all()

    # Deduplicate events by timestamp and type (multiple locations may share the same station)
    seen = set()
    unique_tides = []
    for tide in tides:
        key = (tide.timestamp, tide.type)
        if key not in seen:
            seen.add(key)
            unique_tides.append(tide)

    # Convert to Pydantic models
    events = [
        TideEvent(
            timestamp=tide.timestamp, type=tide.type, height_ft=float(tide.height_ft)
        )
        for tide in unique_tides
    ]

    # Find next low and next high
    future_events = [e for e in events if e.timestamp > now]
    next_low = next((e for e in future_events if e.type == "low"), None)
    next_high = next((e for e in future_events if e.type == "high"), None)

    # Interpolate current height
    # Include some past events for interpolation
    past_result = await db.execute(
        select(Tide)
        .where(Tide.station_id == station_id)
        .where(Tide.timestamp < now)
        .order_by(Tide.timestamp.desc())
    )
    all_past_tides = past_result.scalars().all()

    # Deduplicate past tides by timestamp and type
    seen_past = set()
    past_tides = []
    for tide in all_past_tides:
        key = (tide.timestamp, tide.type)
        if key not in seen_past:
            seen_past.add(key)
            past_tides.append(tide)
        if len(past_tides) >= 2:
            break

    all_events_for_interpolation = [
        TideEvent(
            timestamp=tide.timestamp, type=tide.type, height_ft=float(tide.height_ft)
        )
        for tide in past_tides
    ] + events

    current_height = interpolate_current_height(all_events_for_interpolation, now)

    # Determine data_through timestamp
    data_through = end_time
    if events:
        data_through = max(e.timestamp for e in events)

    return TidesResponse(
        station_id=station_id,
        location_name=location.name,
        events=events,
        next_low=next_low,
        next_high=next_high,
        current_height_ft=current_height,
        data_through=data_through,
    )
