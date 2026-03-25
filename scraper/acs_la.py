"""ACS-LA Gray Whale Census Scraper - Fetches daily whale counts from ACS-LA Facebook widget.

The ACS-LA Gray Whale Census runs from December through May (gray whale migration season).
Posts contain narrative text followed by structured counts.
"""

import asyncio
import re
from datetime import datetime, timedelta, timezone, date
from typing import Any, List, Optional

import httpx
from bs4 import BeautifulSoup

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

DATE_FORMATS = [
    "%d %B %Y",
    "%B %d, %Y",
    "%B %d %Y",
    "%d %b %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%b-%Y",
    "%b-%d-%Y",
]

RELATIVE_DATE_REGEX = re.compile(
    r"(\d+)\s+(day|days|hour|hours|minute|minutes|week|weeks)\s+ago",
    re.IGNORECASE,
)

HEADLINE_DATE_REGEX = re.compile(
    r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})\b",
    re.IGNORECASE,
)

ALT_DATE_REGEX = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b",
    re.IGNORECASE,
)

PASCIFIC = timezone(timedelta(hours=-8))

LLM_NARRATIVE_SPECIES = [
    ("Common Dolphin", ["common dolphin", "commons dolphin"]),
    ("Bottlenose Dolphin", ["bottlenose dolphin", "bottlenose dolphins"]),
    (
        "Pacific White-Sided Dolphin",
        [
            "pacific white-sided dolphin",
            "white-sided dolphin",
            "pacific white sided dolphin",
        ],
    ),
    (
        "Risso's Dolphin",
        ["rissos dolphin", "riso dolphin", "risso's dolphin", "rissos dolphins"],
    ),
    ("Gray Whale", ["gray whale", "grey whale"]),
    ("Humpback Whale", ["humpback whale", "humpback whales"]),
    ("Minke Whale", ["minke whale", "mink whale", "minke whales"]),
    ("Blue Whale", ["blue whale", "blue whales"]),
    ("Fin Whale", ["fin whale", "finn whale", "fin whales"]),
    ("Orca", ["orca", "killer whale", "killer whales"]),
    ("Sea Lion", ["sea lion", "sea lions", "california sea lion"]),
]

WHALE_DIRECTIONS = {
    "southbound": "southbound",
    "northbound": "northbound",
    "south bound": "southbound",
    "north bound": "northbound",
}


def normalize_llm_species(raw_species: str) -> tuple[str, str] | None:
    """Map an LLM-returned species name to canonical name + direction.

    Returns (canonical_name, direction) or None if not a known species.
    direction is 'southbound', 'northbound', or '' for non-whale species.
    """
    raw = raw_species.lower().strip()

    direction = ""
    base = raw
    for dir_key in WHALE_DIRECTIONS:
        if dir_key in raw:
            direction = WHALE_DIRECTIONS[dir_key]
            for canonical, aliases in LLM_NARRATIVE_SPECIES:
                if canonical.lower() in raw:
                    return (canonical, direction)
            break

    for canonical, aliases in LLM_NARRATIVE_SPECIES:
        if raw in aliases or raw == canonical.lower():
            return (canonical, direction)

    return None


def parse_llm_sightings(llm_result: dict) -> dict[str, int]:
    """Convert LLM extraction result into a flat dict of species → count.

    Includes direction suffixes for gray whales.
    """
    sightings: dict[str, int] = {}
    for item in llm_result.get("sightings", []):
        raw_species = item.get("species", "")
        count = item.get("count")
        if not isinstance(count, int) or count <= 0:
            continue

        normalized = normalize_llm_species(raw_species)
        if not normalized:
            continue

        canonical, direction = normalized
        if canonical == "Gray Whale" and direction:
            species_key = f"Gray Whale ({direction})"
        else:
            species_key = canonical

        sightings[species_key] = count

    return sightings


def is_gray_whale_season() -> bool:
    """Check if we're in gray whale migration season (December - May)."""
    now = datetime.now()
    return now.month >= 12 or now.month <= 5


def parse_date(text: str) -> Optional[date]:
    """Parse the sighting date from ACS-LA Facebook post text.

    Attempts three strategies in order:
      1. Scan the headline for absolute date patterns like "16 March 2026".
      2. Fall back to relative patterns like "4 days ago" (computed from
         the Pacific timezone of the post).
      3. Return None — the caller falls back to today's date.

    Handles both word-month ("March") and abbreviated month ("Mar") formats.
    """
    text_snippet = text[:500]

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text_snippet, fmt).date()
        except ValueError:
            pass

    m = HEADLINE_DATE_REGEX.search(text_snippet)
    if m:
        day, month_abbr, year = m.group(1), m.group(2), m.group(3)
        month_num = {
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
        }.get(month_abbr.lower())
        if month_num:
            try:
                return date(int(year), month_num, int(day))
            except ValueError:
                pass

    m = ALT_DATE_REGEX.search(text_snippet)
    if m:
        month_abbr, day, year = m.group(1), m.group(2), m.group(3)
        month_num = {
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
        }.get(month_abbr.lower())
        if month_num:
            try:
                return date(int(year), month_num, int(day))
            except ValueError:
                pass

    m = RELATIVE_DATE_REGEX.search(text_snippet)
    if m:
        amount = int(m.group(1))
        unit = m.group(2).lower()
        now = datetime.now(PASCIFIC)
        if unit.startswith("minute"):
            delta = timedelta(minutes=amount)
        elif unit.startswith("hour"):
            delta = timedelta(hours=amount)
        elif unit.startswith("day"):
            delta = timedelta(days=amount)
        elif unit.startswith("week"):
            delta = timedelta(weeks=amount)
        else:
            return None
        return (now - delta).date()

    return None


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
        self.logger.info(f"Starting scrape...")

        if not is_gray_whale_season():
            self.logger.info(f"Outside gray whale season (Dec-May), skipping scrape")
            return []

        async with get_db_session() as session:
            location = await get_location_by_slug(session, self.location_slug)

        if not location:
            self.logger.info(f"Location '{self.location_slug}' not found!")
            return []

        self.logger.info(f"Found location: {location.name} (ID: {location.id})")

        html_content = await self._fetch_page()
        self.logger.info(f"Fetched page ({len(html_content)} bytes)")

        posts = self._extract_facebook_posts(html_content)
        self.logger.info(f"Found {len(posts)} Facebook posts")

        if not posts:
            self.logger.warning(f"No posts found")
            return []

        latest_post = posts[0]
        self.logger.info(f"Processing latest post ({len(latest_post)} chars)")

        counts = extract_structured_counts(latest_post)
        self.logger.info(f"Regex counts: {counts}")

        llm_sightings: dict[str, int] = {}
        try:
            async with LLMClient() as llm_client:
                llm_result = await llm_client.extract(
                    latest_post,
                    profile="acs-la",
                    fallback_fn=None,
                )
                if llm_result:
                    llm_sightings = parse_llm_sightings(llm_result)
                    self.logger.info(f"LLM sightings: {llm_sightings}")
                else:
                    self.logger.info(f"LLM returned empty result")
        except Exception as e:
            self.logger.info(f"LLM extraction skipped: {e}")

        timestamp = datetime.now(timezone.utc)
        sighting_date = parse_date(latest_post)
        if sighting_date:
            self.logger.info(f"Parsed sighting date: {sighting_date}")
        else:
            sighting_date = timestamp.date()
            self.logger.info(
                f"Could not parse date from post, "
                f"falling back to scrape date: {sighting_date}"
            )

        sightings = []

        def make_record(
            species: str, count: int, confidence: str, metadata: dict
        ) -> dict:
            return {
                "timestamp": timestamp,
                "sighting_date": sighting_date,
                "location_id": location.id,
                "species": species,
                "count": count,
                "source": "acs_la",
                "source_url": self.url,
                "confidence": confidence,
                "raw_text": latest_post,
                "metadata": metadata,
            }

        gray_metadata = {
            "southbound": counts["southbound"],
            "northbound": counts["northbound"],
            "cow_calf_south": counts["cow_calves_south"],
        }
        gray_total = sum(gray_metadata.values())
        if gray_total > 0:
            sightings.append(
                make_record("Gray Whale", gray_total, "high", gray_metadata)
            )

        for species, count in llm_sightings.items():
            if species.startswith("Gray Whale"):
                continue
            if not any(s["species"] == species for s in sightings):
                sightings.append(
                    make_record(
                        species,
                        count,
                        "medium",
                        {"source": "llm_narrative"},
                    )
                )

        if sightings:
            self.logger.info(f"Persisting {len(sightings)} sightings...")
            async with get_db_session() as session:
                await insert_sightings(session, sightings)
            self.logger.info(f"Successfully persisted {len(sightings)} sightings")
        else:
            self.logger.warning(f"No counts found in post")

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
