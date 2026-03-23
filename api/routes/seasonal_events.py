"""Seasonal events API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import SeasonalEvent, get_db
from logging_config import get_logger

router = APIRouter()
logger = get_logger("routes.seasonal_events")


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


@router.get("/api/seasonal-events", response_model=list[SeasonalEventResponse])
async def get_seasonal_events(
    db: AsyncSession = Depends(get_db),
) -> list[SeasonalEventResponse]:
    """Return all seasonal events ordered by start month/day."""
    logger.info("seasonal_events_requested")
    result = await db.execute(
        select(SeasonalEvent).order_by(
            SeasonalEvent.typical_start_month, SeasonalEvent.typical_start_day
        )
    )
    rows = result.scalars().all()
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
        )
        for event in rows
    ]
