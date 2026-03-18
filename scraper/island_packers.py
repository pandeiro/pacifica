"""Island Packers Scraper - Fetches marine mammal sightings from Island Packers website.

Uses Playwright to render JS-heavy pages. Provides Channel Islands /
Santa Barbara Channel coverage - the only source covering this region.

Card 22 from roadmap.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, List

from playwright.async_api import async_playwright

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from base import BaseScraper
    from db import get_db_session, get_location_by_slug, insert_sightings
    from llm import LLMClient
except ImportError:
    from scraper.base import BaseScraper
    from scraper.db import get_db_session, get_location_by_slug, insert_sightings
    from scraper.llm import LLMClient


ISLAND_PACKERS_URL = "https://islandpackers.com/information/marine-mammal-sightings/"
SCHEDULE = "45 6 * * *"


class IslandPackersScraper(BaseScraper):
    """Island Packers whale sightings scraper implementation."""

    schedule = SCHEDULE
    url = ISLAND_PACKERS_URL
    location_slug = "ventura"

    def __init__(self):
        super().__init__("island_packers")

    async def scrape(self) -> List[dict[str, Any]]:
        """Fetch and process whale sightings from Island Packers website."""
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

        sightings_data = self._extract_sightings_text(html_content)
        print(f"[{self.name}] Extracted {len(sightings_data)} sighting sections")

        if not sightings_data:
            print(f"[{self.name}] No sightings data found")
            return []

        sightings = await self._parse_sightings_with_llm(sightings_data, location.id)
        print(f"[{self.name}] Parsed {len(sightings)} sightings")

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

                await page.goto(self.url, wait_until="networkidle", timeout=30000)

                await page.wait_for_timeout(3000)

                content = await page.content()

                await browser.close()

                return content
        except Exception as e:
            print(f"[{self.name}] Playwright fetch failed: {e}")
            return ""

    def _extract_sightings_text(self, html_content: str) -> List[str]:
        """Extract sightings text from HTML content.

        Island Packers mentions specific islands (Anacapa, Santa Cruz, etc.)
        in their reports. We extract text sections that mention wildlife.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        sightings_data = []

        article_selectors = [
            "article",
            ".entry-content",
            ".sightings",
            "[class*='sighting']",
            "[class*='wildlife']",
            ".content",
            "main",
        ]

        for selector in article_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(separator=" ", strip=True)
                if text and len(text) > 50:
                    wildlife_keywords = [
                        "whale",
                        "dolphin",
                        "porpoise",
                        "seal",
                        "sea lion",
                        "otter",
                        "shark",
                        "blue whale",
                        "gray whale",
                        "humpback",
                        "fin whale",
                        "minke",
                        "orca",
                        "killer whale",
                        "common dolphin",
                        "bottlenose",
                        "risso",
                        "pacific white-sided",
                    ]
                    if any(keyword in text.lower() for keyword in wildlife_keywords):
                        island_match = self._extract_island_mention(text)
                        sightings_data.append(
                            {
                                "text": text,
                                "island": island_match,
                            }
                        )

        if not sightings_data:
            main_content = (
                soup.find("main") or soup.find("div", class_="content") or soup.body
            )
            if main_content:
                text = main_content.get_text(separator=" ", strip=True)
                if text:
                    sightings_data.append({"text": text[:3000], "island": None})

        return sightings_data

    def _extract_island_mention(self, text: str) -> str | None:
        """Extract island name if mentioned in the text."""
        islands = [
            "Anacapa",
            "Santa Cruz",
            "Santa Rosa",
            "San Miguel",
            "Santa Barbara Island",
            "Santa Catalina",
            "San Nicolas",
            "Cortes Bank",
            "Channel Islands",
        ]

        text_lower = text.lower()
        for island in islands:
            if island.lower() in text_lower:
                return island

        return None

    async def _parse_sightings_with_llm(
        self, sightings_data: List[dict], location_id: int
    ) -> List[dict[str, Any]]:
        """Parse sightings content using LLM to extract structured data."""
        sightings = []
        timestamp = datetime.now(timezone.utc)

        async with LLMClient() as llm:
            for data in sightings_data:
                text = data["text"]
                island = data.get("island")

                try:
                    result = await llm.extract(
                        text,
                        profile="default",
                        fallback_fn=None,
                    )

                    if result and "sightings" in result:
                        for sighting in result["sightings"]:
                            species = sighting.get("species")
                            count = sighting.get("count")

                            if species:
                                metadata = {}
                                if island:
                                    metadata["island"] = island

                                record = {
                                    "timestamp": timestamp,
                                    "location_id": location_id,
                                    "species": species,
                                    "count": count if count else None,
                                    "source": "island_packers",
                                    "source_url": self.url,
                                    "confidence": "high",
                                    "raw_text": text[:500] if text else None,
                                    "metadata": metadata,
                                }
                                sightings.append(record)

                except Exception as e:
                    print(f"[{self.name}] LLM extraction failed: {e}")
                    continue

        return sightings


if __name__ == "__main__":
    asyncio.run(IslandPackersScraper().run())
