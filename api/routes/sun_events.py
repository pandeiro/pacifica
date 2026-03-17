"""Sun events API routes."""

from datetime import date, datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Location, SunEvent
from logging_config import get_logger
from utils.sun_calculator import calculate_sun_events_for_days

router = APIRouter(prefix="/api", tags=["sun-events"])
logger = get_logger("api.sun_events")


@router.get("/sun-events")
async def get_sun_events(
    location_id: int, days: int = 7, db: AsyncSession = Depends(get_db)
):
    """
    Get sunrise, sunset, and golden hour events for a location.

    Calculates mathematically if not cached, stores results for future requests.

    Args:
        location_id: Location ID
        days: Number of days to fetch (default 7)
    """
    logger.info("Sun events endpoint called", location_id=location_id, days=days)

    # Get location
    location_result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = location_result.scalars().first()

    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Calculate date range
    today = date.today()
    end_date = today + timedelta(days=days)

    # Check cache for existing calculated events
    cache_result = await db.execute(
        select(SunEvent)
        .where(
            SunEvent.location_id == location_id,
            SunEvent.date >= today,
            SunEvent.date < end_date,
            SunEvent.is_calculated == True,
        )
        .order_by(SunEvent.date)
    )
    cached_events = cache_result.scalars().all()

    # Build set of dates we have cached
    cached_dates = {e.date for e in cached_events}

    # Find missing dates
    missing_dates = []
    for i in range(days):
        check_date = today + timedelta(days=i)
        if check_date not in cached_dates:
            missing_dates.append(check_date)

    # Calculate missing events
    if missing_dates:
        logger.info(f"Calculating sun events for {len(missing_dates)} dates")

        lat = float(location.lat)
        lng = float(location.lng)

        for calc_date in missing_dates:
            events = calculate_sun_events_for_days(lat, lng, calc_date, days=1)[0]

            # Create SunEvent record
            sun_event = SunEvent(
                date=events["date"],
                location_id=location_id,
                sunrise=events["sunrise"],
                sunset=events["sunset"],
                golden_hour_morning_start=events["golden_hour_morning_start"],
                golden_hour_morning_end=events["golden_hour_morning_end"],
                golden_hour_evening_start=events["golden_hour_evening_start"],
                golden_hour_evening_end=events["golden_hour_evening_end"],
                is_calculated=True,
            )
            db.add(sun_event)

        await db.commit()

        # Re-fetch all events including newly calculated ones
        cache_result = await db.execute(
            select(SunEvent)
            .where(
                SunEvent.location_id == location_id,
                SunEvent.date >= today,
                SunEvent.date < end_date,
                SunEvent.is_calculated == True,
            )
            .order_by(SunEvent.date)
        )
        cached_events = cache_result.scalars().all()

    # Convert to response format
    events_list = []
    for event in cached_events:
        events_list.append(
            {
                "date": event.date.isoformat(),
                "sunrise": event.sunrise.isoformat() if event.sunrise else None,
                "sunset": event.sunset.isoformat() if event.sunset else None,
                "golden_hour": {
                    "morning": {
                        "start": event.golden_hour_morning_start.isoformat()
                        if event.golden_hour_morning_start
                        else None,
                        "end": event.golden_hour_morning_end.isoformat()
                        if event.golden_hour_morning_end
                        else None,
                    },
                    "evening": {
                        "start": event.golden_hour_evening_start.isoformat()
                        if event.golden_hour_evening_start
                        else None,
                        "end": event.golden_hour_evening_end.isoformat()
                        if event.golden_hour_evening_end
                        else None,
                    },
                },
            }
        )

    return {
        "location_id": location_id,
        "location_name": location.name,
        "events": events_list,
    }
