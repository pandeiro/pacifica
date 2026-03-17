"""iNaturalist Scraper - Fetches wildlife sightings from iNaturalist API."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
import json

import httpx
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

LOOKBACK_DAYS = 3

PAGE_SIZE = 200


class INatScraper(BaseScraper):
    """iNaturalist API scraper for marine and coastal wildlife sightings."""

    schedule = "*/30 * * * *"

    def __init__(self):
        super().__init__("inaturalist")

    async def scrape(self) -> list[dict[str, Any]]:
        """Fetch observations from iNaturalist API and return sighting records."""
        print(f"[{self.name}] Starting scrape...")

        taxon_ids = ",".join(str(tid) for tid, _ in INAT_TAXA)

        d1_date = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime(
            "%Y-%m-%d"
        )

        params = {
            "taxon_id": taxon_ids,
            "swlat": SOCAL_BBOX["swlat"],
            "swlng": SOCAL_BBOX["swlng"],
            "nelat": SOCAL_BBOX["nelat"],
            "nelng": SOCAL_BBOX["nelng"],
            "quality_grade": QUALITY_GRADES,
            "d1": d1_date,
            "order_by": "created_at",
            "order": "desc",
            "per_page": PAGE_SIZE,
        }

        print(
            f"[{self.name}] Fetching observations with taxon_ids={taxon_ids}, d1={d1_date}"
        )

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
            print(
                f"[{self.name}] Page {page}: {len(results)} observations (total: {len(all_observations)})"
            )

            total_results = data.get("total_results", 0)
            if len(all_observations) >= total_results:
                break

            page += 1
            await asyncio.sleep(1)

        print(f"[{self.name}] Fetched {len(all_observations)} total observations")

        sightings = await self._process_observations(all_observations)

        if sightings:
            print(f"[{self.name}] Persisting {len(sightings)} sightings to database...")
            async with get_db_session() as session:
                await insert_sightings(session, sightings)
            print(f"[{self.name}] Successfully persisted {len(sightings)} sightings")

        return sightings

    async def _process_observations(
        self, observations: list[dict]
    ) -> list[dict[str, Any]]:
        """Process iNaturalist observations into sighting records."""
        sightings = []

        async with get_db_session() as session:
            for obs in observations:
                try:
                    sighting = await self._parse_observation(obs, session)
                    if sighting:
                        sightings.append(sighting)
                except Exception as e:
                    obs_id = obs.get("id", "unknown")
                    print(f"[{self.name}] Error parsing observation {obs_id}: {e}")
                    continue

        return sightings

    async def _parse_observation(self, obs: dict, session) -> dict[str, Any] | None:
        """Parse a single iNaturalist observation into a sighting record."""
        if not obs.get("geojson", {}).get("coordinates"):
            return None

        coords = obs["geojson"]["coordinates"]
        obs_lng, obs_lat = coords[0], coords[1]

        observed_on = obs.get("observed_on")
        time_observed = obs.get("time_observed_at")
        if time_observed:
            timestamp = datetime.fromisoformat(time_observed.replace("Z", "+00:00"))
        elif observed_on:
            timestamp = datetime.strptime(observed_on, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        else:
            return None

        species = None
        taxon = obs.get("taxon", {})
        if taxon:
            species = taxon.get("preferred_common_name") or taxon.get("name")
        if not species:
            species = "Unknown"

        count = obs.get("count")
        if count is None:
            count = obs.get("quantity", 1)

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

        metadata = {}
        if place_guess:
            metadata["place_guess"] = place_guess
        if obs.get("description"):
            metadata["description"] = obs["description"][:500]

        obs_id = obs.get("id")
        source_url = (
            f"https://www.inaturalist.org/observations/{obs_id}" if obs_id else None
        )

        return {
            "timestamp": timestamp,
            "location_id": location_id,
            "species": species,
            "count": count,
            "source": "inaturalist",
            "source_url": source_url,
            "raw_text": json.dumps(obs),
            "confidence": confidence,
            "metadata": metadata,
        }


if __name__ == "__main__":
    asyncio.run(INatScraper().run())
