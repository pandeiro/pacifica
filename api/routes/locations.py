"""Locations API routes."""

import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Location, NOAAStation
from logging_config import get_logger

router = APIRouter(prefix="/api", tags=["locations"])
logger = get_logger("api.locations")


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in miles between two coordinates using Haversine formula."""
    R = 3959  # Earth's radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_direction(lat1: float, lng1: float, lat2: float, lng2: float) -> str:
    """Get cardinal direction from point 1 to point 2."""
    delta_lat = lat2 - lat1
    delta_lng = lng2 - lng1

    # Calculate bearing
    bearing = math.atan2(delta_lng, delta_lat)
    bearing_deg = math.degrees(bearing)

    # Convert to cardinal direction
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(bearing_deg / 45) % 8
    return directions[index]


def get_station_info(loc: Location, station: Optional[NOAAStation]) -> Optional[dict]:
    """Get station info for a location, returning None if at the same location."""
    if not station:
        return None

    distance = calculate_distance(
        float(loc.lat), float(loc.lng), float(station.lat), float(station.lng)
    )

    # Only return info if there's actual distance (> 0.1 miles)
    if distance < 0.1:
        return None

    return {
        "name": station.name,
        "distance_miles": round(distance, 1),
        "direction": get_direction(
            float(loc.lat), float(loc.lng), float(station.lat), float(station.lng)
        ),
    }


@router.get("/locations")
async def get_locations(dropdown_only: bool = True, db: AsyncSession = Depends(get_db)):
    """
    Get coastal locations.

    Args:
        dropdown_only: If True, only return locations that should appear in dropdown

    Returns a list of locations with their metadata including coordinates,
    region, and nearest NOAA station information.
    """
    logger.info("Locations endpoint called", dropdown_only=dropdown_only)

    # Build query
    query = select(Location).order_by(Location.name)
    if dropdown_only:
        query = query.where(Location.show_in_dropdown == True)

    result = await db.execute(query)
    locations = result.scalars().all()

    # Fetch all stations for reference
    stations_result = await db.execute(select(NOAAStation))
    stations = {s.id: s for s in stations_result.scalars().all()}

    return [
        {
            "id": loc.id,
            "name": loc.name,
            "slug": loc.slug,
            "lat": float(loc.lat),
            "lng": float(loc.lng),
            "location_type": loc.location_type,
            "region": loc.region,
            "noaa_station_id": loc.noaa_station_id,
            "nearest_noaa_station_id": loc.nearest_noaa_station_id,
            "coastline_bearing": float(loc.coastline_bearing)
            if loc.coastline_bearing
            else None,
            "description": loc.description,
            "station_info": get_station_info(
                loc, stations.get(loc.nearest_noaa_station_id)
            ),
        }
        for loc in locations
    ]


@router.get("/locations/{location_id}")
async def get_location(location_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific location by ID."""
    result = await db.execute(select(Location).where(Location.id == location_id))
    loc = result.scalars().first()

    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    # Get station info
    station = None
    if loc.nearest_noaa_station_id:
        station_result = await db.execute(
            select(NOAAStation).where(NOAAStation.id == loc.nearest_noaa_station_id)
        )
        station = station_result.scalars().first()

    return {
        "id": loc.id,
        "name": loc.name,
        "slug": loc.slug,
        "lat": float(loc.lat),
        "lng": float(loc.lng),
        "location_type": loc.location_type,
        "region": loc.region,
        "noaa_station_id": loc.noaa_station_id,
        "nearest_noaa_station_id": loc.nearest_noaa_station_id,
        "coastline_bearing": float(loc.coastline_bearing)
        if loc.coastline_bearing
        else None,
        "description": loc.description,
        "station_info": get_station_info(loc, station),
    }
