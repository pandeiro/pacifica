"""Station utility functions for calculating distances and directions."""

import math
from typing import Optional, Tuple
from database import Location, NOAAStation


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
        "station_id": station.station_id,
        "distance_miles": round(distance, 1),
        "direction": get_direction(
            float(loc.lat), float(loc.lng), float(station.lat), float(station.lng)
        ),
    }


def get_station_distance_and_direction(
    loc: Location, station: NOAAStation
) -> Tuple[float, str]:
    """Get distance and direction from location to station."""
    distance = calculate_distance(
        float(loc.lat), float(loc.lng), float(station.lat), float(station.lng)
    )
    direction = get_direction(
        float(loc.lat), float(loc.lng), float(station.lat), float(station.lng)
    )
    return distance, direction
