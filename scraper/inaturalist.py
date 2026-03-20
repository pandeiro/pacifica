"""iNaturalist Scraper - Aggregates daily wildlife sightings from iNaturalist API.

Unlike individual trip-report sources (Harbor Breeze, Dana Wharf, etc.) which
produce one row per trip entry, iNaturalist scatters observations across the
region.  This scraper:

  1. Runs once per day (7 AM) and fetches only the **previous calendar day**.
  2. Maps each observation to the nearest known location (≤ 30 mi) or skips it.
  3. Aggregates counts by (location_id, species, sighting_date) — one row per
     location per species per day, matching the dedupe key
     (source, location_id, sighting_date, species).
  4. Stores count as the **sum of individual observations** for that bucket.

Design rationale: iNat is a citizen-science feed; one user's "1 dolphin"
is not meaningfully different from another's.  Daily aggregates keep the table
compact and the dashboard legible.  The `metadata` field records how many
raw observations were folded into each bucket.

Card 18 / Card 18b (refactored).
"""

import asyncio
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any
import json

import httpx
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from base import BaseScraper
    from db import get_db_session, find_nearest_location, insert_sightings
except ImportError:
    from scraper.base import BaseScraper
    from scraper.db import get_db_session, find_nearest_location, insert_sightings


INAT_TAXA = [
    (152871, "Cetacea"),
    (372843, "Phocoidea"),
    (41859, "Enhydra"),
    (47668, "Asteroidea"),
    (47459, "Cephalopoda"),
    (47178, "Actinopterygii"),
    (47187, "Malacostraca"),
    (116999, "Pandion haliaetus"),
    (5305, "Haliaeetus leucocephalus"),
    (4647, "Falco peregrinus"),
    (4328, "Pelecanus occidentalis"),
    (4262, "Phalacrocoracidae"),
    (4342, "Laridae"),
    (4020, "Procellariidae"),
]

INAT_API_URL = "https://api.inaturalist.org/v1/observations"

SOCAL_BBOX = {
    "swlat": 32.5,
    "swlng": -120.7,
    "nelat": 34.8,
    "nelng": -117.1,
}

QUALITY_GRADES = "research,needs_id"

PAGE_SIZE = 200


class INatScraper(BaseScraper):
    """iNaturalist API scraper — daily aggregates by location + species."""

    schedule = "0 7 * * *"

    def __init__(self):
        super().__init__("inaturalist")

    def _prior_day(self) -> date:
        return (datetime.now(timezone.utc) - timedelta(days=1)).date()

    async def scrape(self) -> list[dict[str, Any]]:
        prior = self._prior_day()
        print(f"[{self.name}] Starting scrape for {prior}...")

        taxon_ids = ",".join(str(tid) for tid, _ in INAT_TAXA)
        d1 = prior.isoformat()
        d2 = prior.isoformat()

        params = {
            "taxon_id": taxon_ids,
            "swlat": SOCAL_BBOX["swlat"],
            "swlng": SOCAL_BBOX["swlng"],
            "nelat": SOCAL_BBOX["nelat"],
            "nelng": SOCAL_BBOX["nelng"],
            "quality_grade": QUALITY_GRADES,
            "d1": d1,
            "d2": d2,
            "order_by": "observed_on",
            "order": "asc",
            "per_page": PAGE_SIZE,
        }

        print(f"[{self.name}] Fetching observations for {d1}, taxon_ids={taxon_ids}")

        all_observations = []
        page = 1

        while True:
            params["page"] = page
            response = await self.http_client.get(INAT_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                break

            all_observations.extend(results)
            total = data.get("total_results", 0)
            print(
                f"[{self.name}] Page {page}: {len(results)} obs "
                f"(total fetched: {len(all_observations)} / {total})"
            )
            if len(all_observations) >= total:
                break

            page += 1
            await asyncio.sleep(1)

        print(f"[{self.name}] Fetched {len(all_observations)} observations")

        if not all_observations:
            print(f"[{self.name}] No observations for {prior}, skipping.")
            return []

        buckets = await self._aggregate(all_observations, prior)
        print(f"[{self.name}] Aggregated into {len(buckets)} location/species buckets")

        if buckets:
            print(f"[{self.name}] Persisting {len(buckets)} aggregated rows...")
            async with get_db_session() as session:
                await insert_sightings(session, buckets)
            print(f"[{self.name}] Successfully persisted {len(buckets)} rows")

        return buckets

    async def _aggregate(
        self, observations: list[dict], sighting_date: date
    ) -> list[dict[str, Any]]:
        buckets: dict[tuple, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "obs_ids": [],
                "confidence_counts": {"high": 0, "medium": 0, "low": 0},
            }
        )

        async with get_db_session() as session:
            for obs in observations:
                result = await self._parse_observation(obs, session)
                if result is None:
                    continue

                key: tuple = (result["location_id"], result["species"])
                b = buckets[key]
                b["count"] += result.get("count") or 1
                b["obs_ids"].append(result.get("obs_id"))
                b["confidence_counts"][result.get("confidence", "medium")] += 1

        now_ts = datetime.now(timezone.utc)
        records = []
        for (loc_id, species), b in buckets.items():
            high = b["confidence_counts"]["high"]
            medium = b["confidence_counts"]["medium"]
            confidence = "high" if high > medium else "medium" if medium > 0 else "low"

            meta = {
                "obs_ids": b["obs_ids"],
                "obs_count": len(b["obs_ids"]),
                "confidence_breakdown": b["confidence_counts"],
            }

            records.append(
                {
                    "timestamp": now_ts,
                    "sighting_date": sighting_date,
                    "location_id": loc_id,
                    "species": species,
                    "count": b["count"],
                    "source": "inaturalist",
                    "source_url": None,
                    "raw_text": None,
                    "confidence": confidence,
                    "metadata": meta,
                }
            )

        return records

    async def _parse_observation(self, obs: dict, session) -> dict[str, Any] | None:
        if not obs.get("geojson", {}).get("coordinates"):
            return None

        coords = obs["geojson"]["coordinates"]
        obs_lng, obs_lat = coords[0], coords[1]

        observed_on = obs.get("observed_on")
        time_observed = obs.get("time_observed_at")
        pacific = timezone(timedelta(hours=-8))
        pacific_today = datetime.now(pacific).date()
        if time_observed:
            ts = datetime.fromisoformat(time_observed.replace("Z", "+00:00"))
            obs_date = ts.astimezone(pacific).date()
        elif observed_on:
            ts = datetime.strptime(observed_on, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            obs_date = ts.astimezone(pacific).date()
        else:
            return None
        if obs_date != pacific_today:
            return None
        sighting_date = obs_date

        taxon = obs.get("taxon", {})
        if taxon:
            species = taxon.get("preferred_common_name") or taxon.get("name")
        else:
            species = None
        if not species:
            species = "Unknown"

        cnt = obs.get("count")
        if cnt is None:
            cnt = obs.get("quantity", 1)

        quality_grade = obs.get("quality_grade", "casual")
        if quality_grade == "research":
            confidence = "high"
        elif quality_grade == "needs_id":
            confidence = "medium"
        else:
            confidence = "low"

        location_id, place_guess = await find_nearest_location(
            session, float(obs_lat), float(obs_lng), max_distance_miles=30.0
        )
        if location_id is None:
            return None
        # Build provenance and metadata for return
        obs_id = obs.get("id")
        source_url = (
            f"https://www.inaturalist.org/observations/{obs_id}" if obs_id else None
        )
        metadata = {}
        if place_guess:
            metadata["place_guess"] = place_guess
        if obs.get("description"):
            metadata["description"] = obs["description"][:500]

        return {
            "timestamp": ts,
            "sighting_date": sighting_date,
            "location_id": location_id,
            "species": species,
            "count": cnt,
            "source": "inaturalist",
            "source_url": source_url,
            "raw_text": json.dumps(obs),
            "confidence": confidence,
            "metadata": metadata,
            "obs_id": obs_id,
        }


if __name__ == "__main__":
    asyncio.run(INatScraper().run())
