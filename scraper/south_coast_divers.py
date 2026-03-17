"""South Coast Divers Scraper - Fetches dive condition reports from southcoastdivers.com."""

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Any, Dict, Optional
import httpx
import sys
import os
from bs4 import BeautifulSoup

# Add the parent directory to the path so we can import base and db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from base import BaseScraper
    from db import (
        get_db_session,
        get_location_by_slug,
        check_duplicate_dive_report,
        insert_conditions,
    )
except ImportError:
    # Fallback for standalone execution
    from scraper.base import BaseScraper
    from scraper.db import (
        get_db_session,
        get_location_by_slug,
        check_duplicate_dive_report,
        insert_conditions,
    )


class SouthCoastDiversScraper(BaseScraper):
    """South Coast Divers dive report scraper implementation."""

    schedule = "0 */3 * * *"  # Every 3 hours
    url = "https://southcoastdivers.com/"
    location_slug = "shaws_cove"  # Laguna Beach area

    def __init__(self):
        super().__init__("south_coast_divers")

    async def scrape(self) -> List[Any]:
        """Fetch and process dive condition reports from South Coast Divers website."""
        print(f"[{self.name}] Starting scrape...")

        # Get location ID from database
        async with get_db_session() as session:
            location = await get_location_by_slug(session, self.location_slug)

        if not location:
            print(f"[{self.name}] Location '{self.location_slug}' not found in database!")
            return []

        print(f"[{self.name}] Found location: {location.name} (ID: {location.id})")

        # Fetch the webpage
        try:
            html_content = await self._fetch_page()
            print(f"[{self.name}] Fetched page ({len(html_content)} bytes)")
        except Exception as e:
            print(f"[{self.name}] Error fetching page: {e}")
            return []

        # Parse the dive report from HTML
        dive_report_text = self._extract_dive_report(html_content)

        if not dive_report_text:
            print(f"[{self.name}] No dive report found on page")
            return []

        print(f"[{self.name}] Extracted dive report ({len(dive_report_text)} chars)")

        # Check for duplicates (same content within last 96 hours)
        async with get_db_session() as session:
            is_duplicate = await check_duplicate_dive_report(
                session, location.id, dive_report_text, hours=96
            )

            if is_duplicate:
                print(f"[{self.name}] Duplicate report found (within last 96 hours), skipping")
                return []

        # Create the condition record
        timestamp = datetime.now(timezone.utc)
        record = {
            "timestamp": timestamp,
            "location_id": location.id,
            "condition_type": "dive_report",
            "value": 0,  # Placeholder - report is in raw_text
            "unit": "text",
            "source": "south_coast_divers",
            "source_url": self.url,
            "raw_text": dive_report_text,
        }

        # Persist to database
        print(f"[{self.name}] Persisting dive report to database...")
        async with get_db_session() as session:
            await insert_conditions(session, [record])

        print(f"[{self.name}] Successfully persisted dive report")
        return [record]

    async def _fetch_page(self) -> str:
        """Fetch the South Coast Divers homepage HTML."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            return response.text

    def _extract_dive_report(self, html_content: str) -> Optional[str]:
        """Extract dive report text from the first table after 'Here is the latest group post.'"""
        soup = BeautifulSoup(html_content, "html.parser")

        # Find the text node containing "Here is the latest group post."
        # BeautifulSoup doesn't directly search text, so we find all text elements
        target_text = "Here is the latest group post."
        target_element = None

        for element in soup.find_all(text=True):
            if target_text in element.strip():
                target_element = element.parent
                break

        if not target_element:
            print(f"[{self.name}] Could not find target text '{target_text}'")
            return None

        # Find the first table after this element
        # Navigate up to find a common parent, then find next table
        table = target_element.find_next("table")

        if not table:
            print(f"[{self.name}] No table found after target element")
            return None

        # Extract all text from the table, preserving some structure
        # Get text from all cells, stripping whitespace
        texts = []
        for row in table.find_all("tr"):
            row_texts = []
            for cell in row.find_all(["td", "th"]):
                cell_text = cell.get_text(strip=True)
                if cell_text:
                    row_texts.append(cell_text)
            if row_texts:
                texts.append(" | ".join(row_texts))

        if not texts:
            # Fallback: just get all text from the table
            return table.get_text(separator="\n", strip=True)

        return "\n".join(texts)


# For direct execution
if __name__ == "__main__":
    import asyncio

    async def main():
        scraper = SouthCoastDiversScraper()
        try:
            data = await scraper.run()
            print(f"Successfully scraped {len(data)} records")
            if data:
                print(f"Sample record:\n{data[0]['raw_text'][:500]}...")
        except Exception as e:
            print(f"Error running scraper: {e}")
            raise

    asyncio.run(main())
