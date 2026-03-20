"""Island Packers Scraper - Fetches whale sightings from Island Packers Google Sheet.

Island Packers publishes their marine mammal sightings in a public Google Spreadsheet
with structured daily and monthly counts.

Card 22 from roadmap.
"""

import asyncio
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Any, List

import httpx

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from base import BaseScraper
    from db import get_db_session, get_location_by_slug, insert_sightings
except ImportError:
    from scraper.base import BaseScraper
    from scraper.db import get_db_session, get_location_by_slug, insert_sightings


ISLAND_PACKERS_CSV_URL = "https://docs.google.com/spreadsheets/d/1VNkVLDPHWMoq3spEmHquAfhNhiomo4ncSfApHIeLCBs/export?format=csv"
SCHEDULE = "45 6 * * *"

SPECIES_COLUMNS = {
    "Humpback Whales": "Humpback Whale",
    "Blue Whales": "Blue Whale",
    "Gray Whales": "Gray Whale",
    "Orca Whales": "Orca",
    "Minke Whales": "Minke Whale",
    "Fin Whales": "Fin Whale",
    "Sperm Whale": "Sperm Whale",
    "Sperm Whales": "Sperm Whale",
    "Common Dolphins": "Common Dolphin",
    "Bottlenose Dolphins": "Bottlenose Dolphin",
    "Risso's Dolphins": "Risso's Dolphin",
    "Rissos Dolphins": "Risso's Dolphin",
    "Pacific White-Sided Dolphins": "Pacific White-Sided Dolphin",
    "Pacific White-Sided Dolphin": "Pacific White-Sided Dolphin",
    "Mola Mola": "Mola Mola",
    "Mola Mola (Sunfish)": "Mola Mola",
    "Dalls Porpoise": "Dall's Porpoise",
    "Dall's Porpoise": "Dall's Porpoise",
    "Swordfish": "Swordfish",
    "Cow/Calf Pairs": "Gray Whale Cow/Calf",
}


def parse_count(value: str) -> int | None:
    """Parse a count value, handling commas and empty strings."""
    if not value or value.strip() == "":
        return None
    try:
        cleaned = value.strip().replace(",", "")
        if cleaned == "":
            return None
        count = int(cleaned)
        return count if count > 0 else None
    except ValueError:
        return None


def parse_month_day(date_str: str, year: int = None) -> datetime | None:
    """Parse date like 'March 2026' row headers or '1', '2', etc. day numbers."""
    try:
        if year is None:
            year = datetime.now().year

        date_str = date_str.strip()

        if date_str.isdigit():
            day = int(date_str)
            pacific = timezone(timedelta(hours=-8))
            dt = datetime(year, datetime.now().month, day, 12, 0, 0)
            dt = dt.replace(tzinfo=pacific)
            return dt.astimezone(timezone.utc)

        return None
    except (ValueError, TypeError):
        return None


class IslandPackersScraper(BaseScraper):
    """Island Packers whale sightings scraper implementation."""

    schedule = SCHEDULE
    url = ISLAND_PACKERS_CSV_URL
    location_slug = "ventura"

    def __init__(self):
        super().__init__("island_packers")

    async def scrape(self) -> List[dict[str, Any]]:
        """Fetch and process whale sightings from Island Packers Google Sheet."""
        print(f"[{self.name}] Starting scrape...")

        async with get_db_session() as session:
            location = await get_location_by_slug(session, self.location_slug)

        if not location:
            print(f"[{self.name}] Location '{self.location_slug}' not found!")
            return []

        print(f"[{self.name}] Found location: {location.name} (ID: {location.id})")

        csv_content = await self._fetch_csv()
        print(f"[{self.name}] Fetched CSV ({len(csv_content)} chars)")

        daily_sightings = self._parse_daily_sightings(csv_content, location.id)
        print(f"[{self.name}] Parsed {len(daily_sightings)} daily sightings")

        if daily_sightings:
            print(f"[{self.name}] Persisting {len(daily_sightings)} sightings...")
            async with get_db_session() as session:
                await insert_sightings(session, daily_sightings)
            print(
                f"[{self.name}] Successfully persisted {len(daily_sightings)} sightings"
            )

        return daily_sightings

    async def _fetch_csv(self) -> str:
        """Fetch the CSV export from Google Sheets."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/csv,text/plain,*/*",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.url, headers=headers, follow_redirects=True, timeout=30.0
            )
            response.raise_for_status()
            return response.text

    def _parse_daily_sightings(self, csv_content: str, location_id: int) -> List[dict]:
        """Parse the daily sightings section from CSV content.

        The first sheet has daily counts with columns:
        Date, Humpback Whales, Blue Whales, Gray Whales, ...

        Uses csv module to handle multi-line fields properly.
        """
        sightings = []

        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        if len(rows) < 2:
            print(f"[{self.name}] CSV has insufficient rows")
            return sightings

        header_line = None
        header_index = 0
        for i, row in enumerate(rows):
            row_str = ",".join(row)
            if "Humpback Whales" in row_str or "Common Dolphins" in row_str:
                header_line = row
                header_index = i
                break

        if not header_line:
            print(f"[{self.name}] Could not find daily sightings header")
            return sightings

        headers = [h.strip().strip('"') for h in header_line]
        print(f"[{self.name}] Found {len(headers)} columns: {headers}")

        column_indices = {}
        for i, header in enumerate(headers):
            clean_header = header.replace("\n", " ").strip()
            for species_key, species_name in SPECIES_COLUMNS.items():
                if species_key in clean_header or clean_header in species_key:
                    column_indices[i] = species_name
                    break

        print(f"[{self.name}] Mapped column indices: {column_indices}")

        current_year = datetime.now().year
        current_month = datetime.now().month

        pacific = timezone(timedelta(hours=-8))

        for row in rows[header_index + 1 :]:
            if not row or len(row) < 2:
                continue

            date_str = row[0].strip()
            if not date_str:
                continue

            if date_str.isdigit():
                day = int(date_str)
                try:
                    timestamp = datetime(current_year, current_month, day, 12, 0, 0)
                    timestamp = timestamp.replace(tzinfo=pacific)
                    timestamp = timestamp.astimezone(timezone.utc)
                except ValueError:
                    continue

                for col_idx, species in column_indices.items():
                    if col_idx < len(row):
                        count_str = row[col_idx].strip()
                        count = parse_count(count_str)
                        if count is not None:
                            record = {
                                "timestamp": timestamp,
                                "sighting_date": timestamp.date(),
                                "location_id": location_id,
                                "species": species,
                                "count": count,
                                "source": "island_packers",
                                "source_url": "https://www.islandpackers.com/information/marine-mammal-sightings/",
                                "confidence": "high",
                                "raw_text": f"{date_str}: {count} x {species}",
                                "metadata": {},
                            }
                            sightings.append(record)

        return sightings

        header_line = None
        header_index = 0
        for i, line in enumerate(lines):
            if "Humpback Whales" in line or "Common Dolphins" in line:
                header_line = line
                header_index = i
                break

        if not header_line:
            print(f"[{self.name}] Could not find daily sightings header")
            return sightings

        headers = [h.strip().strip('"') for h in header_line.split(",")]
        print(f"[{self.name}] Found {len(headers)} columns in daily sightings")

        column_indices = {}
        for i, header in enumerate(headers):
            if header in SPECIES_COLUMNS:
                column_indices[header] = i

        current_year = datetime.now().year
        current_month = datetime.now().month

        for line in lines[header_index + 1 :]:
            if not line.strip():
                continue

            parts = [p.strip().strip('"') for p in line.split(",")]
            if len(parts) < 2:
                continue

            date_str = parts[0]
            if date_str.isdigit():
                day = int(date_str)
                pacific = timezone(timedelta(hours=-8))
                try:
                    timestamp = datetime(current_year, current_month, day, 12, 0, 0)
                    timestamp = timestamp.replace(tzinfo=pacific)
                    timestamp = timestamp.astimezone(timezone.utc)
                except ValueError:
                    continue

                for header, idx in column_indices.items():
                    if idx < len(parts):
                        count_str = parts[idx]
                        count = parse_count(count_str)
                        if count is not None:
                            species = SPECIES_COLUMNS[header]
                            record = {
                                "timestamp": timestamp,
                                "location_id": location_id,
                                "species": species,
                                "count": count,
                                "source": "island_packers",
                                "source_url": "https://www.islandpackers.com/information/marine-mammal-sightings/",
                                "confidence": "high",
                                "raw_text": f"{date_str}: {count} x {species}",
                                "metadata": {},
                            }
                            sightings.append(record)

        return sightings


if __name__ == "__main__":
    asyncio.run(IslandPackersScraper().run())
