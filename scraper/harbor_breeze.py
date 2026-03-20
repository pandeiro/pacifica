"""Harbor Breeze Scraper - Fetches whale sightings from 2 See Whales website.

Harbor Breeze (now 2 See Whales) publishes daily sighting reports on their
WordPress site with JetEngine dynamic content.

Card 19 from roadmap.
"""

import asyncio
import re
from datetime import datetime, timezone, timedelta, date
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

DATE_FORMATS = [
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%m/%d/%Y",
    "%d/%m/%Y",
]

DATE_PATTERNS = [
    re.compile(
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
]

PASCIFIC = timezone(timedelta(hours=-8))

_MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _parse_date_from_text(text: str) -> date | None:
    """Extract a date from text using multiple patterns.

    Returns a date object, or None if no date is found.
    """
    for pattern in DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        date_str = m.group(0)
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                pass
        m2 = re.match(
            r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
            date_str,
            re.IGNORECASE,
        )
        if m2:
            day = int(m2.group(1))
            mon = _MONTH_MAP.get(m2.group(2).lower()[:3])
            yr_m = re.search(r"\d{4}", date_str)
            if mon and yr_m:
                try:
                    return date(int(yr_m.group(0)), mon, day)
                except ValueError:
                    pass
    return None


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

    def _extract_sightings(self, html_content: str) -> List[tuple[date | None, str]]:
        """Extract (sighting_date, text) entries from HTML content.

        Harbor Breeze entries include a date in the heading or timestamp.
        We extract the date when present and fall back to None (caller uses today).
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        entries: List[tuple[date | None, str]] = []

        text = soup.get_text(separator="\n")
        lines = text.split("\n")

        sighting_pattern = re.compile(
            r"\d+[\d,]*\s+(?:Common|Bottlenose|Pacific|White|Riso|Riss|Gray|Humpback|Fin|Blue|Minke|Orca|Killer|Sperm)",
            re.IGNORECASE,
        )
        time_pattern = re.compile(r"(\d{1,2}:\d{2}\s*(?:am|pm)?)", re.IGNORECASE)

        pending_date: date | None = None

        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue

            if any(
                w in line.lower()
                for w in [
                    "cookie",
                    "accept",
                    "privacy",
                    "menu",
                    "home",
                    "contact",
                    "subscribe",
                    "copyright",
                ]
            ):
                continue

            candidate_date = _parse_date_from_text(line)
            if candidate_date:
                pending_date = candidate_date

            if sighting_pattern.search(line):
                entries.append((pending_date, line))
            elif time_pattern.search(line) and any(
                w in line.lower() for w in ["whale", "dolphin"]
            ):
                entries.append((pending_date, line))

        return entries

    def _parse_sightings(
        self, entries: List[tuple[date | None, str]], location_id: int
    ) -> List[dict]:
        """Parse sighting entries into structured records."""
        sightings = []
        timestamp = datetime.now(timezone.utc)

        for entry_date, text in entries:
            parsed = parse_sightings_from_text(text)
            sighting_date = entry_date if entry_date else timestamp.date()

            for count, species in parsed:
                record = {
                    "timestamp": timestamp,
                    "sighting_date": sighting_date,
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
