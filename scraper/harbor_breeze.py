"""Harbor Breeze Scraper - Fetches whale sightings from Harbor Breeze website.

Uses Playwright to render JS-heavy pages. Falls back to LLM extraction
for narrative trip reports.

Card 19 from roadmap.
"""

import asyncio
from datetime import datetime, timezone, timedelta
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


HARBOR_BREEZE_URL = "https://www.harbor-breeze.com/whale-watching-reports/"
SCHEDULE = "15 6 * * *"


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

        reports = self._extract_reports(html_content)
        print(f"[{self.name}] Found {len(reports)} potential report sections")

        if not reports:
            print(f"[{self.name}] No reports found")
            return []

        sightings = await self._parse_reports_with_llm(reports, location.id)
        print(
            f"[{self.name}] Parsed {len(sightings)} sightings from {len(reports)} reports"
        )

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

                await page.wait_for_timeout(2000)

                content = await page.content()

                await browser.close()

                return content
        except Exception as e:
            print(f"[{self.name}] Playwright fetch failed: {e}")
            return ""

    def _extract_reports(self, html_content: str) -> List[str]:
        """Extract trip report text sections from HTML.

        Harbor Breeze trip reports are typically narrative descriptions
        of what was seen during whale watching trips.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")
        reports = []

        article_selectors = [
            "article",
            ".trip-report",
            ".report",
            ".sighting",
            "[class*='report']",
            "[class*='sighting']",
        ]

        for selector in article_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(separator=" ", strip=True)
                if text and len(text) > 50:
                    if any(
                        word in text.lower()
                        for word in [
                            "whale",
                            "dolphin",
                            "sighting",
                            "trip",
                            "tour",
                            "saw",
                        ]
                    ):
                        reports.append(text)

        if not reports:
            main_content = (
                soup.find("main") or soup.find("div", class_="content") or soup.body
            )
            if main_content:
                paragraphs = main_content.find_all(["p", "div"])
                for p in paragraphs:
                    text = p.get_text(separator=" ", strip=True)
                    if text and len(text) > 100:
                        if any(
                            word in text.lower()
                            for word in [
                                "whale",
                                "dolphin",
                                "gray",
                                "blue",
                                "fin",
                                "humpback",
                                "orca",
                            ]
                        ):
                            reports.append(text)

        return reports[:10]

    async def _parse_reports_with_llm(
        self, reports: List[str], location_id: int
    ) -> List[dict[str, Any]]:
        """Parse trip reports using LLM to extract sightings."""
        sightings = []
        timestamp = datetime.now(timezone.utc)

        async with LLMClient() as llm:
            for report_text in reports:
                try:
                    result = await llm.extract(
                        report_text,
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
                                    "source": "harbor_breeze",
                                    "source_url": self.url,
                                    "confidence": "high",
                                    "raw_text": report_text[:500]
                                    if report_text
                                    else None,
                                    "metadata": {},
                                }
                                sightings.append(record)

                except Exception as e:
                    print(f"[{self.name}] LLM extraction failed for report: {e}")
                    continue

        return sightings


if __name__ == "__main__":
    asyncio.run(HarborBreezeScraper().run())
