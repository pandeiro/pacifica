"""ACS-LA Gray Whale Census Scraper - Fetches daily whale counts from ACS-LA Facebook widget.

The ACS-LA Gray Whale Census runs from December through May (gray whale migration season).
Posts contain narrative text followed by structured counts.
"""

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, List

import httpx
from bs4 import BeautifulSoup

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from base import BaseScraper
    from db import get_db_session, get_location_by_slug, insert_sightings
except ImportError:
    from scraper.base import BaseScraper
    from scraper.db import get_db_session, get_location_by_slug, insert_sightings


ACS_LA_URL = "https://acs-la.org/todays-whale-count/"
SCHEDULE = "0 9 * * *"  # Daily at 9 AM

PATTERN_REGEX = re.compile(
    r"(Southbound|Northbound|Cow/calves south|Total)\s*:\s*(\d+)",
    re.IGNORECASE,
)

TODAY_SECTION_REGEX = re.compile(
    r"GRAY WHALES TODAY\s*:(.*?)(?=GRAY WHALES TO DATE|$)",
    re.IGNORECASE | re.DOTALL,
)


def is_gray_whale_season() -> bool:
    """Check if we're in gray whale migration season (December - May)."""
    now = datetime.now()
    return now.month >= 12 or now.month <= 5


def extract_structured_counts(text: str) -> dict[str, int]:
    """Extract structured whale counts from the census text.

    Only extracts from the "GRAY WHALES TODAY:" section, not cumulative totals.

    Returns dict with keys: southbound, northbound, cow_calves_south, total
    """
    result = {
        "southbound": 0,
        "northbound": 0,
        "cow_calves_south": 0,
        "total": 0,
    }

    today_match = TODAY_SECTION_REGEX.search(text)
    if not today_match:
        return result

    today_section = today_match.group(1)
    matches = PATTERN_REGEX.findall(today_section)
    for label, count_str in matches:
        count = int(count_str)
        label_lower = label.lower()
        if label_lower == "southbound":
            result["southbound"] = count
        elif label_lower == "northbound":
            result["northbound"] = count
        elif "cow" in label_lower or "calf" in label_lower:
            result["cow_calves_south"] = count
        elif label_lower == "total":
            result["total"] = count

    return result


class ACSLAScraper(BaseScraper):
    """ACS-LA Gray Whale Census scraper implementation."""

    schedule = SCHEDULE
    url = ACS_LA_URL
    location_slug = "point_vicente"

    def __init__(self):
        super().__init__("acs_la")

    async def scrape(self) -> List[dict[str, Any]]:
        """Fetch and process gray whale census data from ACS-LA website."""
        print(f"[{self.name}] Starting scrape...")

        if not is_gray_whale_season():
            print(f"[{self.name}] Outside gray whale season (Dec-May), skipping scrape")
            return []

        async with get_db_session() as session:
            location = await get_location_by_slug(session, self.location_slug)

        if not location:
            print(f"[{self.name}] Location '{self.location_slug}' not found!")
            return []

        print(f"[{self.name}] Found location: {location.name} (ID: {location.id})")

        html_content = await self._fetch_page()
        print(f"[{self.name}] Fetched page ({len(html_content)} bytes)")

        posts = self._extract_facebook_posts(html_content)
        print(f"[{self.name}] Found {len(posts)} Facebook posts")

        if not posts:
            print(f"[{self.name}] No posts found")
            return []

        latest_post = posts[0]
        print(f"[{self.name}] Processing latest post ({len(latest_post)} chars)")

        counts = extract_structured_counts(latest_post)
        print(f"[{self.name}] Extracted counts: {counts}")

        timestamp = datetime.now(timezone.utc)
        sighting_date = timestamp.date()
        sightings = []

        if counts["southbound"] > 0:
            record = {
                "timestamp": timestamp,
                "sighting_date": sighting_date,
                "location_id": location.id,
                "species": "Gray Whale (southbound)",
                "count": counts["southbound"],
                "source": "acs_la",
                "source_url": self.url,
                "confidence": "high",
                "raw_text": latest_post,
                "metadata": {"direction": "southbound"},
            }
            sightings.append(record)

        if counts["northbound"] > 0:
            record = {
                "timestamp": timestamp,
                "sighting_date": sighting_date,
                "location_id": location.id,
                "species": "Gray Whale (northbound)",
                "count": counts["northbound"],
                "source": "acs_la",
                "source_url": self.url,
                "confidence": "high",
                "raw_text": latest_post,
                "metadata": {"direction": "northbound"},
            }
            sightings.append(record)

        if counts["cow_calves_south"] > 0:
            record = {
                "timestamp": timestamp,
                "sighting_date": sighting_date,
                "location_id": location.id,
                "species": "Gray Whale (cow/calf)",
                "count": counts["cow_calves_south"],
                "source": "acs_la",
                "source_url": self.url,
                "confidence": "high",
                "raw_text": latest_post,
                "metadata": {"direction": "southbound", "type": "cow_calf"},
            }
            sightings.append(record)

        if sightings:
            print(f"[{self.name}] Persisting {len(sightings)} sightings...")
            async with get_db_session() as session:
                await insert_sightings(session, sightings)
            print(f"[{self.name}] Successfully persisted {len(sightings)} sightings")
        else:
            print(f"[{self.name}] No counts found in post")

        return sightings

    async def _fetch_page(self) -> str:
        """Fetch the ACS-LA whale count page."""
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
                self.url, headers=headers, follow_redirects=True, timeout=30.0
            )
            response.raise_for_status()
            return response.text

    def _extract_facebook_posts(self, html_content: str) -> List[str]:
        """Extract post content from Facebook widget divs.

        The Facebook widget typically renders posts in elements with
        class 'cff-text' or similar. This method extracts the text content.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        posts = []

        cff_items = soup.find_all(class_="cff-text")
        for item in cff_items:
            text = item.get_text(separator="\n", strip=True)
            if text:
                posts.append(text)

        if not posts:
            cff_posts = soup.find_all(class_="cff-post")
            for post in cff_posts:
                text_elem = post.find(class_="cff-text")
                if text_elem:
                    text = text_elem.get_text(separator="\n", strip=True)
                    if text:
                        posts.append(text)

        if not posts:
            fb_posts = soup.find_all(
                "div",
                class_=lambda x: x and ("facebook" in x.lower() or "cff" in x.lower()),
            )
            for post in fb_posts:
                text = post.get_text(separator="\n", strip=True)
                if text and len(text) > 50:
                    posts.append(text)

        return posts


if __name__ == "__main__":
    asyncio.run(ACSLAScraper().run())
