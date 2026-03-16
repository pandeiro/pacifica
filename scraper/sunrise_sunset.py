"""Sunrise/Sunset Scraper - Fetches sun events from sunrise-sunset.org API."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
import httpx
import sys
import os

# Add the parent directory to the path so we can import base
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scraper.base import BaseScraper
except ImportError:
    # Fallback for standalone execution
    from base import BaseScraper


# Locations with lat/lng coordinates (matches database locations table)
# These are the southern California coastal locations we track
LOCATIONS = [
    {"id": 1, "slug": "dana_point", "lat": 33.467500, "lng": -117.698600},
    {"id": 2, "slug": "la_jolla", "lat": 32.866700, "lng": -117.250000},
    {"id": 3, "slug": "santa_monica", "lat": 34.011700, "lng": -118.496500},
    {"id": 4, "slug": "santa_barbara", "lat": 34.400000, "lng": -119.697000},
    {"id": 5, "slug": "morro_bay", "lat": 35.367000, "lng": -120.851000},
    {"id": 12, "slug": "shaws_cove", "lat": 33.545800, "lng": -117.802500},
    {"id": 13, "slug": "zuma_beach", "lat": 34.020800, "lng": -118.828900},
]


class SunriseSunsetScraper(BaseScraper):
    """Sunrise/Sunset Scraper implementation using sunrise-sunset.org API."""

    schedule = "30 2 * * *"  # Daily at 2:30 AM (after NOAA tides)

    def __init__(self):
        super().__init__("sunrise_sunset")

    async def scrape(self) -> List[Dict[str, Any]]:
        """Fetch and process sun events from sunrise-sunset.org API."""
        print(f"[{self.name}] Starting scrape...")

        # Calculate date range: today + next 7 days = 8 days total
        today = datetime.utcnow().date()
        end_date = today + timedelta(days=7)

        all_records = []

        # Fetch data for each location
        for location in LOCATIONS:
            try:
                print(
                    f"[{self.name}] Fetching sun events for {location['slug']} (lat: {location['lat']}, lng: {location['lng']})"
                )

                # Fetch sun events for all days
                records = await self._fetch_location_sun_events(
                    location, today, end_date
                )
                all_records.extend(records)

                print(
                    f"[{self.name}] Retrieved {len(records)} sun events for {location['slug']}"
                )

                # Be polite - add a small delay between locations
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"[{self.name}] Error fetching data for {location['slug']}: {e}")
                # Continue with other locations even if one fails
                continue

        print(
            f"[{self.name}] Scraped {len(all_records)} sun events from {len(LOCATIONS)} locations"
        )
        return all_records

    async def _fetch_location_sun_events(
        self,
        location: Dict[str, Any],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> List[Dict[str, Any]]:
        """Fetch sun events for a specific location and date range."""
        records = []
        current_date = start_date

        while current_date <= end_date:
            url = "https://api.sunrise-sunset.org/json"
            params = {
                "lat": location["lat"],
                "lng": location["lng"],
                "date": current_date.isoformat(),
                "formatted": 0,  # Return ISO 8601 timestamps in UTC
            }

            print(
                f"[{self.name}] Requesting sun events for {location['slug']} on {current_date}"
            )

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()

                if data.get("status") != "OK":
                    print(
                        f"[{self.name}] API returned non-OK status for {location['slug']} on {current_date}: {data.get('status')}"
                    )
                    current_date += timedelta(days=1)
                    continue

                results = data.get("results", {})

                # Parse timestamps from ISO 8601 format
                # Note: sunrise-sunset.org returns times in UTC
                sunrise = self._parse_iso_timestamp(results["sunrise"])
                sunset = self._parse_iso_timestamp(results["sunset"])
                civil_twilight_begin = self._parse_iso_timestamp(
                    results["civil_twilight_begin"]
                )
                civil_twilight_end = self._parse_iso_timestamp(
                    results["civil_twilight_end"]
                )

                # Golden hour approximation:
                # Morning golden hour: civil twilight begin -> sunrise
                # Evening golden hour: sunset -> civil twilight end
                record = {
                    "date": current_date,
                    "location_id": location["id"],
                    "sunrise": sunrise,
                    "sunset": sunset,
                    "golden_hour_morning_start": civil_twilight_begin,
                    "golden_hour_morning_end": sunrise,
                    "golden_hour_evening_start": sunset,
                    "golden_hour_evening_end": civil_twilight_end,
                }

                records.append(record)

            # Be polite - small delay between date requests for same location
            await asyncio.sleep(0.1)
            current_date += timedelta(days=1)

        return records

    def _parse_iso_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO 8601 timestamp string to datetime object with UTC timezone."""
        # Handle both formats: with and without Z suffix
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        return datetime.fromisoformat(timestamp_str)


# For direct execution
if __name__ == "__main__":
    import asyncio

    async def main():
        scraper = SunriseSunsetScraper()
        try:
            data = await scraper.run()
            print(f"Successfully scraped {len(data)} records")
            # Print first record as sample
            if data:
                print(f"Sample record: {data[0]}")
        except Exception as e:
            print(f"Error running scraper: {e}")
            raise

    asyncio.run(main())
