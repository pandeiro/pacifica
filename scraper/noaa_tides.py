"""NOAA Tides Scraper - Fetches tide predictions from NOAA CO-OPS API."""

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


# NOAA CO-OPS Station IDs mapped to location slugs
STATIONS = {
    "9410660": "dana_point",
    "9410230": "la_jolla",
    "9410840": "santa_monica",
    "9411340": "santa_barbara",
    "9412110": "morro_bay",
}


class NOAATidesScraper(BaseScraper):
    """NOAA Tides Scraper implementation."""

    def __init__(self):
        super().__init__("noaa_tides")
        # Use the shared httpx client from BaseScraper if available
        # Otherwise create a new one

    async def scrape(self) -> List[Dict[str, Any]]:
        """Fetch and process tide data from NOAA CO-OPS API."""
        print(f"[{self.name}] Starting scrape...")

        # Calculate date range for predictions (today - 1 day to today + 6 days)
        # This gives us a week of data centered around today
        today = datetime.utcnow().date()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=6)

        all_records = []

        # Fetch data for each station
        for station_id in STATIONS:
            try:
                print(
                    f"[{self.name}] Fetching data for station {station_id} ({STATIONS[station_id]})"
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

        print(
            f"[{self.name}] Scraped {len(all_records)} tide events from {len(STATIONS)} stations"
        )
        return all_records

    async def _fetch_predictions(
        self, station_id: str, start_date: datetime.date, end_date: datetime.date
    ) -> List[Dict[str, str]]:
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
        self, station_id: str, predictions: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
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
