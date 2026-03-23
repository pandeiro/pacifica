"""Seasonal events API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import SeasonalEvent, Location, get_db
from logging_config import get_logger

router = APIRouter()
logger = get_logger("routes.seasonal_events")


class EventLocation(BaseModel):
    id: int
    name: str
    slug: str


class SeasonalEventResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    typical_start_month: int
    typical_start_day: int
    typical_end_month: int
    typical_end_day: int
    species: str | None
    category: str
    conditions_type: str | None
    conditions_text: str | None
    locations: list[EventLocation]


@router.get("/api/seasonal-events", response_model=list[SeasonalEventResponse])
async def get_seasonal_events(
    db: AsyncSession = Depends(get_db),
) -> list[SeasonalEventResponse]:
    """Return all seasonal events with locations, ordered by start month/day."""
    logger.info("seasonal_events_requested")

    # Fetch events
    result = await db.execute(
        select(SeasonalEvent).order_by(
            SeasonalEvent.typical_start_month, SeasonalEvent.typical_start_day
        )
    )
    events = result.scalars().all()

    # Fetch all event-location mappings in one query
    from sqlalchemy import text as sa_text

    mappings_result = await db.execute(
        sa_text(
            "SELECT sel.event_id, l.id, l.name, l.slug "
            "FROM seasonal_event_locations sel "
            "JOIN locations l ON sel.location_id = l.id "
            "ORDER BY l.name"
        )
    )
    # Build a dict of event_id -> [locations]
    locations_by_event: dict[int, list[EventLocation]] = {}
    for row in mappings_result:
        eid = row[0]
        loc = EventLocation(id=row[1], name=row[2], slug=row[3])
        locations_by_event.setdefault(eid, []).append(loc)

    return [
        SeasonalEventResponse(
            id=event.id,
            name=event.name,
            slug=event.slug,
            description=event.description,
            typical_start_month=event.typical_start_month,
            typical_start_day=event.typical_start_day,
            typical_end_month=event.typical_end_month,
            typical_end_day=event.typical_end_day,
            species=event.species,
            category=event.category,
            conditions_type=event.conditions_type,
            conditions_text=event.conditions_text,
            locations=locations_by_event.get(event.id, []),
        )
        for event in events
    ]
