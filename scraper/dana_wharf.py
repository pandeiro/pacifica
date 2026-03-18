"""Dana Wharf Scraper - Fetches whale sightings from Dana Wharf website.

Uses Playwright to render JS-heavy pages. Inspects DOM to find daily log.
Annual totals may be available in static HTML.

Card 21 from roadmap.
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


DANA_WHARF_URL = "https://danawharf.com/whale-watching/"
SCHEDULE = "30 6 * * *"


class DanaWharfScraper(BaseScraper):
    """Dana Wharf whale sightings scraper implementation."""

    schedule = SCHEDULE
    url = DANA_WHARF_URL
    location_slug = "dana_point"

    def __init__(self):
        super().__init__("dana_wharf")

    async def scrape(self) -> List[dict[str, Any]]:
        """Fetch and process whale sightings from Dana Wharf website."""
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

        log_content = self._extract_log_section(html_content)
        print(f"[{self.name}] Extracted log section ({len(log_content)} chars)")

        if not log_content:
            print(f"[{self.name}] No log content found")
            return []

        sightings = await self._parse_log_with_llm(log_content, location.id)
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

                log_section = await page.query_selector(
                    "#log, .log, [id*='log'], [class*='log']"
                )
                if log_section:
                    content = await log_section.inner_html()
                else:
                    content = await page.content()

                await browser.close()

                return content
        except Exception as e:
            print(f"[{self.name}] Playwright fetch failed: {e}")
            return ""

    def _extract_log_section(self, html_content: str) -> str:
        """Extract the daily log section from HTML content."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        log_selectors = [
            "#log",
            ".log",
            "[id*='log']",
            "[class*='log']",
            ".daily-log",
            ".sightings-log",
            ".whale-log",
            "article",
            ".entry-content",
        ]

        for selector in log_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(separator=" ", strip=True)
                if text and len(text) > 100:
                    if any(
                        word in text.lower()
                        for word in [
                            "whale",
                            "dolphin",
                            "sighting",
                            "saw",
                            "gray",
                            "blue",
                            "fin",
                        ]
                    ):
                        return text

        main_content = (
            soup.find("main") or soup.find("div", class_="content") or soup.body
        )
        if main_content:
            return main_content.get_text(separator=" ", strip=True)[:2000]

        return ""

    async def _parse_log_with_llm(
        self, log_content: str, location_id: int
    ) -> List[dict[str, Any]]:
        """Parse log content using LLM to extract sightings."""
        sightings = []
        timestamp = datetime.now(timezone.utc)

        async with LLMClient() as llm:
            try:
                result = await llm.extract(
                    log_content,
                    profile="default",
                    fallback_fn=None,
                )

                if result and "sightings" in result:
                    for sighting in result["sightings"]:
                        species = sighting.get("species")
                        count = sighting.get("count")

                        if species:
                            record = {
                                "timestamp": timestamp,
                                "location_id": location_id,
                                "species": species,
                                "count": count if count else None,
                                "source": "dana_wharf",
                                "source_url": self.url,
                                "confidence": "high",
                                "raw_text": log_content[:500] if log_content else None,
                                "metadata": {},
                            }
                            sightings.append(record)

            except Exception as e:
                print(f"[{self.name}] LLM extraction failed: {e}")

        return sightings


if __name__ == "__main__":
    asyncio.run(DanaWharfScraper().run())
