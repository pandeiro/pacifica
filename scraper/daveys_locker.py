"""Davey's Locker Scraper - Fetches whale/dolphin sightings from Davey's Locker website."""

import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
import sys
import os
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from base import BaseScraper
    from db import get_db_session, get_location_by_slug, insert_sightings
except ImportError:
    from scraper.base import BaseScraper
    from scraper.db import get_db_session, get_location_by_slug, insert_sightings


DAVEYS_URL = "https://daveyslocker.com/whale-dolphin-sightings/"
SCHEDULE = "0 6 * * *"

PAT_REGEX = re.compile(r"(\d+)\s+([A-Za-z][A-Za-z\s\/\-]+?)(?=,\s*\d|$)")


def parse_species_list(text: str) -> list[tuple[int, str]]:
    """Parse '53 Gray Whales, 103 Bottlenose Dolphin' into [(53, 'Gray Whales'), ...]."""
    matches = PAT_REGEX.findall(text)
    results = []
    for count_str, species in matches:
        try:
            count = int(count_str)
            species_clean = species.strip()
            results.append((count, species_clean))
        except ValueError:
            continue
    return results


def parse_date(date_str: str) -> datetime | None:
    """Parse '3/16/2026' format into UTC datetime at noon Pacific."""
    try:
        dt = datetime.strptime(date_str.strip(), "%m/%d/%Y")
        pb = timezone(timedelta(hours=-8))
        dt = dt.replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=pb)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


class DaveysLockerScraper(BaseScraper):
    """Davey's Locker whale sightings scraper implementation."""

    schedule = SCHEDULE
    url = DAVEYS_URL
    location_slug = "newport_beach"

    def __init__(self):
        super().__init__("daveyslocker")

    async def scrape(self) -> list[dict[str, Any]]:
        """Fetch and process whale sightings from Davey's Locker website."""
        print(f"[{self.name}] Starting scrape...")

        async with get_db_session() as session:
            location = await get_location_by_slug(session, self.location_slug)

        if not location:
            print(
                f"[{self.name}] Location '{self.location_slug}' not found in database!"
            )
            return []

        print(f"[{self.name}] Found location: {location.name} (ID: {location.id})")

        html_content = await self._fetch_page()
        print(f"[{self.name}] Fetched page ({len(html_content)} bytes)")

        rows = self._parse_table(html_content)
        print(f"[{self.name}] Found {len(rows)} table rows")

        sightings = []
        for date_str, mammals_text in rows:
            date_dt = parse_date(date_str)
            if not date_dt:
                print(f"[{self.name}] Could not parse date: {date_str}")
                continue

            species_list = parse_species_list(mammals_text)
            for count, species in species_list:
                source_url = f"{self.url}#{date_dt.strftime('%Y-%m-%d')}-{species.lower().replace(' ', '-')}"
                record = {
                    "timestamp": date_dt,
                    "sighting_date": date_dt.date(),
                    "location_id": location.id,
                    "species": species,
                    "count": count,
                    "source": "daveyslocker",
                    "source_url": source_url,
                    "confidence": "high",
                    "raw_text": mammals_text,
                    "metadata": {},
                }
                sightings.append(record)

        print(f"[{self.name}] Parsed {len(sightings)} sightings from {len(rows)} rows")

        if sightings:
            print(f"[{self.name}] Persisting {len(sightings)} sightings to database...")
            async with get_db_session() as session:
                await insert_sightings(session, sightings)
            print(f"[{self.name}] Successfully persisted {len(sightings)} sightings")

        return sightings

    async def _fetch_page(self) -> str:
        """Fetch the Davey's Locker sightings page."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.url, headers=headers, follow_redirects=True
            )
            response.raise_for_status()
            return response.text

    def _parse_table(self, html_content: str) -> list[tuple[str, str]]:
        """Parse HTML table and return list of (date, mammals_text) tuples."""
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        if not table:
            print(f"[{self.name}] No table found in page")
            return []

        rows = []
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) >= 3:
                date_str = tds[0].get_text(strip=True)
                mammals_text = tds[2].get_text(strip=True)
                if date_str and mammals_text:
                    rows.append((date_str, mammals_text))

        return rows


if __name__ == "__main__":
    asyncio.run(DaveysLockerScraper().run())
