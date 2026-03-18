"""Harbor Breeze Scraper - Fetches whale sightings from 2 See Whales website.

Harbor Breeze (now 2 See Whales) publishes daily sighting reports on their
WordPress site with JetEngine dynamic content.

Card 19 from roadmap.
"""

import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Any, List

from playwright.async_api import async_playwright

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from base import BaseScraper
    from db import get_db_session, get_location_by_slug, insert_sightings
except ImportError:
    from scraper.base import BaseScraper
    from scraper.db import get_db_session, get_location_by_slug, insert_sightings


HARBOR_BREEZE_URL = "https://2seewhales.com/whale-sightings-report/"
SCHEDULE = "15 6 * * *"


def parse_sightings_from_text(text: str) -> List[tuple]:
    """Parse sighting text into list of (count, species) tuples.

    Handles formats like:
    - "500 Common Dolphins"
    - "1 humpback"
    - "5 Gray whales, 1 Humpback, 200 common dolphins"
    - "10 White-Sided Dolphins"
    """
    sightings = []

    patterns = [
        (r"(\d[\d,]*)\s+(Gray\s*Whales?)", "Gray Whale"),
        (r"(\d[\d,]*)\s+(Gray\s*Whale)", "Gray Whale"),
        (r"(\d[\d,]*)\s+(Humpback\s*Whales?)", "Humpback Whale"),
        (r"(\d[\d,]*)\s+(Humpback)", "Humpback Whale"),
        (r"(\d[\d,]*)\s+(Fin\s*Whales?)", "Fin Whale"),
        (r"(\d[\d,]*)\s+(Fin\s*Whale)", "Fin Whale"),
        (r"(\d[\d,]*)\s+(Blue\s*Whales?)", "Blue Whale"),
        (r"(\d[\d,]*)\s+(Blue\s*Whale)", "Blue Whale"),
        (r"(\d[\d,]*)\s+(Minke\s*Whales?)", "Minke Whale"),
        (r"(\d[\d,]*)\s+(Orca|Killer\s*Whale)", "Orca"),
        (r"(\d[\d,]*)\s+(Common\s*Dolphins?)", "Common Dolphin"),
        (r"(\d[\d,]*)\s+(Bottlenose\s*Dolphins?)", "Bottlenose Dolphin"),
        (
            r"(\d[\d,]*)\s+(Pacific\s*Whitesided\s*Dolphins?)",
            "Pacific White-Sided Dolphin",
        ),
        (r"(\d[\d,]*)\s+(White-?Sided\s*Dolphins?)", "Pacific White-Sided Dolphin"),
        (r"(\d[\d,]*)\s+(Risso'?s?\s*Dolphins?)", "Risso's Dolphin"),
    ]

    for pattern, species in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                count_str = match[0].replace(",", "")
                count = int(count_str)
                if count > 0:
                    sightings.append((count, species))
            except ValueError:
                continue

    return sightings


class HarborBreezeScraper(BaseScraper):
    """Harbor Breeze whale sightings scraper implementation."""

    schedule = SCHEDULE
    url = HARBOR_BREEZE_URL
    location_slug = "long_beach"

    def __init__(self):
        super().__init__("harbor_breeze")

    async def scrape(self) -> List[dict[str, Any]]:
        """Fetch and process whale sightings from Harbor Breeze website."""
        print(f"[{self.name}] Starting scrape...")

        async with get_db_session() as session:
            location = await get_location_by_slug(session, self.location_slug)

        if not location:
            print(f"[{self.name}] Location '{self.location_slug}' not found!")
            return []

        print(f"[{self.name}] Found location: {location.name} (ID: {location.id})")

        html_content = await self._fetch_page_playwright()
        if not html_content:
            print(f"[{self.name}] Failed to fetch page content")
            return []

        print(f"[{self.name}] Fetched page ({len(html_content)} chars)")

        sighting_texts = self._extract_sightings(html_content)
        print(f"[{self.name}] Found {len(sighting_texts)} sighting entries")

        if not sighting_texts:
            print(f"[{self.name}] No sightings found")
            return []

        sightings = self._parse_sightings(sighting_texts, location.id)
        print(f"[{self.name}] Parsed {len(sightings)} individual sightings")

        if sightings:
            print(f"[{self.name}] Persisting {len(sightings)} sightings...")
            async with get_db_session() as session:
                await insert_sightings(session, sightings)
            print(f"[{self.name}] Successfully persisted {len(sightings)} sightings")

        return sightings

    async def _fetch_page_playwright(self) -> str:
        """Fetch page content using Playwright headless browser."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(self.url, wait_until="domcontentloaded", timeout=90000)

                await page.wait_for_timeout(8000)

                content = await page.content()

                await browser.close()

                return content
        except Exception as e:
            print(f"[{self.name}] Playwright fetch failed: {e}")
            return ""

    def _extract_sightings(self, html_content: str) -> List[str]:
        """Extract sighting text entries from HTML content.

        Harbor Breeze displays sightings in dynamic content elements.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        sighting_texts = []

        # Get all text content
        text = soup.get_text(separator="\n")

        # Split by lines and look for sighting patterns
        lines = text.split("\n")

        sighting_pattern = re.compile(
            r"\d+\s+(?:Common|Bottlenose|Pacific|White|Riso|Gray|Humpback|Fin|Blue|Minke|Orca|Killer)",
            re.IGNORECASE,
        )

        time_pattern = re.compile(r"(\d{1,2}:\d{2}\s*(?:am|pm)?)", re.IGNORECASE)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip very short lines
            if len(line) < 10:
                continue

            # Skip cookie consent and navigation
            if any(
                word in line.lower()
                for word in ["cookie", "accept", "privacy", "menu", "home", "contact"]
            ):
                continue

            # Look for lines with sighting data
            if sighting_pattern.search(line):
                sighting_texts.append(line)
            elif time_pattern.search(line) and any(
                word in line.lower() for word in ["whale", "dolphin"]
            ):
                sighting_texts.append(line)

        return sighting_texts

    def _parse_sightings(
        self, sighting_texts: List[str], location_id: int
    ) -> List[dict]:
        """Parse sighting text entries into structured records."""
        sightings = []
        timestamp = datetime.now(timezone.utc)

        for text in sighting_texts:
            parsed = parse_sightings_from_text(text)

            for count, species in parsed:
                record = {
                    "timestamp": timestamp,
                    "location_id": location_id,
                    "species": species,
                    "count": count,
                    "source": "harbor_breeze",
                    "source_url": self.url,
                    "confidence": "high",
                    "raw_text": text[:500] if text else None,
                    "metadata": {},
                }
                sightings.append(record)

        return sightings


if __name__ == "__main__":
    asyncio.run(HarborBreezeScraper().run())
