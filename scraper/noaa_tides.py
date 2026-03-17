"""NOAA Tides Scraper - Fetches tide predictions from NOAA CO-OPS API."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Any
import httpx
import sys
import os

# Add the parent directory to the path so we can import base and db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from base import BaseScraper
    from db import get_db_session, get_locations_with_noaa_stations, insert_tides
except ImportError:
    # Fallback for standalone execution
    from scraper.base import BaseScraper
    from scraper.db import (
        get_db_session,
        get_locations_with_noaa_stations,
        insert_tides,
    )


class NOAATidesScraper(BaseScraper):
    """NOAA Tides Scraper implementation."""

    schedule = "0 2 * * *"  # Daily at 2:00 AM

    def __init__(self):
        super().__init__("noaa_tides")

    async def scrape(self) -> List[Any]:
        """Fetch and process tide data from NOAA CO-OPS API."""
        print(f"[{self.name}] Starting scrape...")

        # Fetch locations with NOAA stations from database
        async with get_db_session() as session:
            locations = await get_locations_with_noaa_stations(session)

        if not locations:
            print(f"[{self.name}] No locations with NOAA stations found in database!")
            return []

        print(f"[{self.name}] Found {len(locations)} locations with NOAA stations")

        # Calculate date range for predictions (today - 1 day to today + 6 days)
        # This gives us a week of data centered around today
        today = datetime.utcnow().date()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=6)

        all_records = []

        # Fetch data for each station
        for location in locations:
            station_id = location.noaa_station_id
            try:
                print(
                    f"[{self.name}] Fetching data for station {station_id} ({location.slug})"
                )

                # Fetch predictions
                predictions = await self._fetch_predictions(station_id, today, end_date)
                print(
                    f"[{self.name}] Retrieved {len(predictions)} predictions for station {station_id}"
                )

                # Process predictions into records
                records = self._process_predictions(station_id, predictions)
                all_records.extend(records)

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
            print(f"[{self.name}] Persisting {len(all_records)} records to database...")
            async with get_db_session() as session:
                await insert_tides(session, all_records)
            print(f"[{self.name}] Successfully persisted {len(all_records)} records")

        print(
            f"[{self.name}] Scraped {len(all_records)} tide events from {len(locations)} stations"
        )
        return all_records

    async def _fetch_predictions(
        self, station_id: str, start_date: datetime.date, end_date: datetime.date
    ) -> List[Any]:
        """Fetch tide predictions for a specific station."""
        url = (
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
            f"?product=predictions&station={station_id}"
            f"&begin_date={start_date.strftime('%Y%m%d')}&end_date={end_date.strftime('%Y%m%d')}"
            "&datum=MLLW&time_zone=lst&interval=hilo&units=english"
            "&application=pacific_dashboard&format=json"
        )

        print(f"[{self.name}] Requesting: {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            return data.get("predictions", [])

    def _process_predictions(
        self, station_id: str, predictions: List[Any]
    ) -> List[Any]:
        """Process raw predictions into standardized records."""
        records = []

        for prediction in predictions:
            # Convert time string to datetime object
            timestamp_str = prediction["t"]
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
            # Assume timestamps from NOAA are in UTC (they come back with LST/LDT but we'll standardize to UTC)
            timestamp = timestamp.replace(tzinfo=timezone.utc)

            # Convert height to float
            height_ft = float(prediction["v"])

            # Convert NOAA type codes to our standardized types
            noaa_type = prediction["type"]
            tide_type = (
                "high"
                if noaa_type == "H"
                else "low"
                if noaa_type == "L"
                else noaa_type.lower()
            )

            record = {
                "timestamp": timestamp,
                "station_id": station_id,
                "type": tide_type,
                "height_ft": height_ft,
                "source": "noaa_predictions",
            }

            records.append(record)

        return records


# For direct execution
if __name__ == "__main__":
    import asyncio

    async def main():
        scraper = NOAATidesScraper()
        try:
            data = await scraper.run()
            print(f"Successfully scraped {len(data)} records")
        except Exception as e:
            print(f"Error running scraper: {e}")
            raise

    asyncio.run(main())
