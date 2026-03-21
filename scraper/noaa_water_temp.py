"""NOAA Water Temperature Scraper - Fetches water temp from NOAA CO-OPS API."""

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import List, Any, Dict
import httpx
import sys
import os
from collections import defaultdict

# Add the parent directory to the path so we can import base and db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from base import BaseScraper
    from db import get_db_session, get_locations_with_noaa_stations, insert_conditions
except ImportError:
    # Fallback for standalone execution
    from scraper.base import BaseScraper
    from scraper.db import (
        get_db_session,
        get_locations_with_noaa_stations,
        insert_conditions,
    )


class NOAAWaterTempScraper(BaseScraper):
    """NOAA Water Temperature Scraper implementation."""

    schedule = "0 */6 * * *"  # Every 6 hours

    def __init__(self):
        super().__init__("noaa_water_temp")

    async def scrape(self) -> List[Any]:
        """Fetch and process water temperature data from NOAA CO-OPS API."""
        print(f"[{self.name}] Starting scrape...")

        # Fetch locations with NOAA stations from database
        async with get_db_session() as session:
            locations = await get_locations_with_noaa_stations(session)

        if not locations:
            print(f"[{self.name}] No locations with NOAA stations found in database!")
            return []

        print(f"[{self.name}] Found {len(locations)} locations with NOAA stations")

        # We'll fetch data for "today" - NOAA returns full day even with partial data
        today = datetime.utcnow().date()

        all_records = []
        stations_with_data = 0
        stations_without_data = 0

        # Fetch data for each station
        for location in locations:
            station_id = location.noaa_station_id
            try:
                print(
                    f"[{self.name}] Fetching data for station {station_id} ({location.slug})"
                )

                # Fetch today's water temperature readings
                readings = await self._fetch_water_temp(station_id, today)

                if not readings:
                    print(
                        f"[{self.name}] No water temp data available for station {station_id}"
                    )
                    stations_without_data += 1
                    continue

                print(
                    f"[{self.name}] Retrieved {len(readings)} readings for station {station_id}"
                )
                stations_with_data += 1

                # Calculate hourly averages
                hourly_records = self._calculate_hourly_averages(
                    location.id, station_id, readings
                )
                all_records.extend(hourly_records)

                # Be polite - add a small delay between requests
                await asyncio.sleep(1)

            except Exception as e:
                print(
                    f"[{self.name}] Error fetching data for station {station_id}: {e}"
                )
                # Continue with other stations even if one fails
                continue

        # Persist to database
        if all_records:
            print(
                f"[{self.name}] Persisting {len(all_records)} hourly records to database..."
            )
            async with get_db_session() as session:
                await insert_conditions(session, all_records)
            print(f"[{self.name}] Successfully persisted {len(all_records)} records")

        print(
            f"[{self.name}] Scraped {len(all_records)} hourly averages from "
            f"{stations_with_data} stations ({stations_without_data} stations without water temp sensors)"
        )
        return all_records

    async def _fetch_water_temp(
        self, station_id: str, date: datetime.date
    ) -> List[Dict[str, Any]]:
        """Fetch water temperature data for a specific station and date."""
        # NOAA water temp API only supports 'today', not specific dates
        url = (
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
            f"?product=water_temperature&station={station_id}"
            "&date=today"
            "&units=english&time_zone=lst&format=json"
            "&application=pacific_dashboard"
        )

        print(f"[{self.name}] Requesting: {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()

            # Check for error response (station doesn't have water temp sensor)
            if "error" in data:
                return []

            return data.get("data", [])

    def _calculate_hourly_averages(
        self, location_id: int, station_id: str, readings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate hourly averages from 6-minute interval readings."""
        # Group readings by hour
        hourly_readings = defaultdict(list)

        for reading in readings:
            timestamp_str = reading["t"]
            value_str = reading.get("v", "").strip()

            # Skip empty or invalid readings
            if not value_str:
                continue

            try:
                value = float(value_str)
            except (ValueError, TypeError):
                continue

            # Parse timestamp
            # NOAA returns times in local station time (LST/LDT) when using time_zone=lst
            # We need to attach the Pacific timezone, then convert to UTC for storage
            pacific_tz = ZoneInfo("America/Los_Angeles")
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
            timestamp = timestamp.replace(tzinfo=pacific_tz)
            # Create hourly bucket key (floor to the hour, in UTC)
            hour_key = timestamp.astimezone(timezone.utc).replace(
                minute=0, second=0, microsecond=0
            )

            hourly_readings[hour_key].append(value)

        # Calculate averages and create records
        records = []
        for hour, values in sorted(hourly_readings.items()):
            if not values:
                continue

            avg_temp = sum(values) / len(values)

            record = {
                "timestamp": hour,
                "location_id": location_id,
                "condition_type": "water_temp",
                "value": round(avg_temp, 2),
                "unit": "fahrenheit",
                "source": f"noaa_{station_id}",
                "source_url": f"https://tidesandcurrents.noaa.gov/stationhome.html?id={station_id}",
                "raw_text": f"Hourly average from {len(values)} readings",
            }
            records.append(record)

        return records


# For direct execution
if __name__ == "__main__":
    import asyncio

    async def main():
        scraper = NOAAWaterTempScraper()
        try:
            data = await scraper.run()
            print(f"Successfully scraped {len(data)} records")
            # Print first few records as sample
            if data:
                print(f"Sample records: {data[:3]}")
        except Exception as e:
            print(f"Error running scraper: {e}")
            raise

    asyncio.run(main())
