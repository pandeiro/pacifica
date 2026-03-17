"""Sun calculation utilities using the suntime library."""

from datetime import date, datetime, timedelta, timezone
from typing import Dict, Tuple
from suntime import Sun


def calculate_sun_events(
    lat: float, lng: float, target_date: date
) -> Dict[str, datetime]:
    """
    Calculate sunrise, sunset, and golden hour times for a location and date.

    Args:
        lat: Latitude
        lng: Longitude
        target_date: Date to calculate for

    Returns:
        Dictionary with sunrise, sunset, and golden hour timestamps (UTC)
    """
    sun = Sun(lat, lng)

    # Get sunrise and sunset for the date
    sunrise = sun.get_local_sunrise_time(target_date)
    sunset = sun.get_local_sunset_time(target_date)

    # Golden hour is typically defined as the hour after sunrise and hour before sunset
    # For morning: sunrise to sunrise + 1 hour
    # For evening: sunset - 1 hour to sunset
    golden_hour_duration = timedelta(hours=1)

    return {
        "sunrise": sunrise.astimezone(timezone.utc),
        "sunset": sunset.astimezone(timezone.utc),
        "golden_hour_morning_start": sunrise.astimezone(timezone.utc),
        "golden_hour_morning_end": (sunrise + golden_hour_duration).astimezone(
            timezone.utc
        ),
        "golden_hour_evening_start": (sunset - golden_hour_duration).astimezone(
            timezone.utc
        ),
        "golden_hour_evening_end": sunset.astimezone(timezone.utc),
    }


def calculate_sun_events_for_days(
    lat: float, lng: float, start_date: date, days: int = 7
) -> list:
    """
    Calculate sun events for multiple days.

    Args:
        lat: Latitude
        lng: Longitude
        start_date: Start date
        days: Number of days to calculate

    Returns:
        List of dictionaries with date and sun events
    """
    results = []
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        events = calculate_sun_events(lat, lng, current_date)
        results.append({"date": current_date, **events})
    return results
