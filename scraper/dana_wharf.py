"""Dana Wharf Scraper - Fetches whale sightings from Dana Wharf Google Sheet.

Dana Wharf publishes their whale watching log in a public Google Spreadsheet.
This scraper fetches the CSV export and parses sightings.

Card 21 from roadmap.
"""

import asyncio
import re
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


DANA_WHARF_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSANLNhgWSp5QjIrnJQZgou2WPVHJM--TTN4zypY5LSSwC_Bc2gHS2laI1zTIod8sFS36feAMr02A5K/pub?gid=33795621&single=true&output=csv"
SCHEDULE = "30 6 * * *"


SPECIES_PATTERNS = [
    (r"(\d+)\s+(Gray\s*Whale)s?", "Gray Whale"),
    (r"(\d+)\s+(Fin\s*Whale)s?", "Fin Whale"),
    (r"(\d+)\s+(Humpback)s?", "Humpback Whale"),
    (r"(\d+)\s+(Blue\s*Whale)s?", "Blue Whale"),
    (r"(\d+)\s+(Minke)s?", "Minke Whale"),
    (r"(\d+)\s+(Orca|Killer\s*Whale)s?", "Orca"),
    (r"(\d+)\s+(Sperm\s*Whale)s?", "Sperm Whale"),
    (r"(\d+)\s+(Common\s*Dolphin)s?", "Common Dolphin"),
    (r"(\d+)\s+(Bottlenose\s*Dolphin)s?", "Bottlenose Dolphin"),
    (
        r"(\d+)\s+(Pacific\s*White[-\s]*Sided\s*Dolphin)s?",
        "Pacific White-Sided Dolphin",
    ),
    (r"(\d+)\s+(Risso'?s?\s*Dolphin)s?", "Risso's Dolphin"),
    (r"(\d+)\s+(Mako\s*Shark)s?", "Mako Shark"),
    (r"(\d+)\s+(Blue\s*Shark)s?", "Blue Shark"),
    (r"(\d+)\s+(Sea\s*Turtle)s?", "Sea Turtle"),
    (r"(\d+)\s+(Mola\s*Mola)s?", "Mola Mola"),
]

SINGULAR_SPECIES = [
    (r"\b(Gray\s*Whales?)\b", "Gray Whale"),
    (r"\b(Fin\s*Whales?)\b", "Fin Whale"),
    (r"\b(Humpbacks?)\b", "Humpback Whale"),
    (r"\b(Blue\s*Whales?)\b", "Blue Whale"),
    (r"\b(Minkes?)\b", "Minke Whale"),
    (r"\b(Orcas?|Killer\s*Whales?)\b", "Orca"),
    (r"\b(Common\s*Dolphins?)\b", "Common Dolphin"),
    (r"\b(Bottlenose\s*Dolphins?)\b", "Bottlenose Dolphin"),
    (r"\b(Pacific\s*White[-\s]*Sided\s*Dolphins?)\b", "Pacific White-Sided Dolphin"),
    (r"\b(Risso'?s?\s*Dolphins?)\b", "Risso's Dolphin"),
    (r"\b(Mola\s*Mola)\b", "Mola Mola"),
    (r"\b(Sea\s*Turtles?)\b", "Sea Turtle"),
]


def parse_date(date_str: str, year: int = None) -> datetime | None:
    """Parse date string like '3/17/2026' or '4/1/25' into UTC datetime at noon Pacific.

    Handles both 4-digit years (2026) and 2-digit years (25 -> 2025, 54 -> 1954).
    For 2-digit years, if the resulting year is more than 10 years in the future,
    subtract 100 to handle edge cases like '54' meant to be 1954.
    """
    try:
        date_str = date_str.strip().strip('"')
        parts = date_str.split("/")
        if len(parts) != 3:
            return None

        month, day, yr = parts
        month = int(month)
        day = int(day)
        yr = int(yr)

        current_year = datetime.now().year

        # Normalize year
        if yr > 2000:
            # 4-digit year like 2026
            final_year = yr
        elif yr < 100:
            # 2-digit year like 25 -> 2025
            final_year = 2000 + yr
            # If resulting year is more than 10 years in the future,
            # it's likely a past date like '54' meant to be 1954
            if final_year > current_year + 10:
                final_year -= 100
        else:
            # Fallback for any other case
            final_year = current_year

        dt = datetime(final_year, month, day, 12, 0, 0)

        pacific = timezone(timedelta(hours=-8))
        dt = dt.replace(tzinfo=pacific)
        return dt.astimezone(timezone.utc)
    except (ValueError, IndexError):
        return None


def parse_sightings_text(text: str) -> list[tuple[int | None, str]]:
    """Parse sightings text into list of (count, species) tuples.

    Handles formats like:
    - "3 Fin whales, 10 gray whales"
    - "Common Dolphins" (singular, count = None)
    - "1 mola mola"
    """
    sightings = []
    text = text.strip()

    for pattern, canonical_name in SPECIES_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            count = int(match.group(1))
            sightings.append((count, canonical_name))

    for pattern, canonical_name in SINGULAR_SPECIES:
        if not any(s[1] == canonical_name for s in sightings):
            if re.search(pattern, text, re.IGNORECASE):
                sightings.append((None, canonical_name))

    return sightings


class DanaWharfScraper(BaseScraper):
    """Dana Wharf whale sightings scraper implementation."""

    schedule = SCHEDULE
    url = DANA_WHARF_CSV_URL
    location_slug = "dana_point"

    def __init__(self):
        super().__init__("dana_wharf")

    async def scrape(self) -> List[dict[str, Any]]:
        """Fetch and process whale sightings from Dana Wharf Google Sheet."""
        print(f"[{self.name}] Starting scrape...")

        async with get_db_session() as session:
            location = await get_location_by_slug(session, self.location_slug)

        if not location:
            print(f"[{self.name}] Location '{self.location_slug}' not found!")
            return []

        print(f"[{self.name}] Found location: {location.name} (ID: {location.id})")

        csv_content = await self._fetch_csv()
        print(f"[{self.name}] Fetched CSV ({len(csv_content)} chars)")

        rows = self._parse_csv(csv_content)
        print(f"[{self.name}] Parsed {len(rows)} CSV rows")

        if not rows:
            print(f"[{self.name}] No rows found")
            return []

        sightings = []
        timestamp = datetime.now(timezone.utc)
        for date_str, sighting_text in rows:
            if not sighting_text or sighting_text.lower().startswith("2026 sightings"):
                continue

            parsed_dt = parse_date(date_str)
            if not parsed_dt:
                print(f"[{self.name}] Could not parse date: {date_str}")
                continue

            sighting_date = parsed_dt.date()
            parsed = parse_sightings_text(sighting_text)
            if not parsed:
                print(f"[{self.name}] No species found in: {sighting_text[:50]}...")
                continue

            for count, species in parsed:
                record = {
                    "timestamp": timestamp,
                    "sighting_date": sighting_date,
                    "location_id": location.id,
                    "species": species,
                    "count": count,
                    "source": "dana_wharf",
                    "source_url": "https://danawharf.com/whale-watching/#log",
                    "confidence": "high",
                    "raw_text": sighting_text,
                    "metadata": {},
                }
                sightings.append(record)

        print(f"[{self.name}] Parsed {len(sightings)} sightings from {len(rows)} rows")

        if sightings:
            print(f"[{self.name}] Persisting {len(sightings)} sightings...")
            async with get_db_session() as session:
                await insert_sightings(session, sightings)
            print(f"[{self.name}] Successfully persisted {len(sightings)} sightings")

        return sightings

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

    def _parse_csv(self, csv_content: str) -> List[tuple]:
        """Parse CSV content into list of (date, sighting_text) tuples.

        Handles simple CSV format:
        "3/17/2026","3 Fin whales, 10 gray whales, 1 mola mola"
        """
        rows = []
        lines = csv_content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('"') and '","' in line:
                parts = line.split('","', 1)
                if len(parts) == 2:
                    date_str = parts[0].strip('"')
                    text = parts[1].strip('"')
                    rows.append((date_str, text))
            elif "," in line:
                parts = line.split(",", 1)
                if len(parts) == 2:
                    date_str = parts[0].strip().strip('"')
                    text = parts[1].strip().strip('"')
                    rows.append((date_str, text))

        return rows


if __name__ == "__main__":
    asyncio.run(DanaWharfScraper().run())
