"""Live cams API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import LiveCam, Location, get_db
from logging_config import get_logger

router = APIRouter()
logger = get_logger("routes.live_cams")


class LiveCamResponse(BaseModel):
    id: int
    name: str
    location_id: int
    location_name: str | None
    embed_type: str
    embed_url: str
    source_name: str
    is_active: bool
    sort_order: int


@router.get("/api/live-cams", response_model=list[LiveCamResponse])
async def get_live_cams(db: AsyncSession = Depends(get_db)) -> list[LiveCamResponse]:
    """Return all active live cams with location names, ordered by sort_order."""
    logger.info("live_cams_requested")
    result = await db.execute(
        select(LiveCam, Location.name.label("location_name"))
        .join(Location, LiveCam.location_id == Location.id, isouter=True)
        .where(LiveCam.is_active == True)  # noqa: E712
        .order_by(LiveCam.sort_order)
    )
    rows = result.all()
    return [
        LiveCamResponse(
            id=cam.id,
            name=cam.name,
            location_id=cam.location_id,
            location_name=location_name,
            embed_type=cam.embed_type,
            embed_url=cam.embed_url,
            source_name=cam.source_name,
            is_active=cam.is_active,
            sort_order=cam.sort_order,
        )
        for cam, location_name in rows
    ]
