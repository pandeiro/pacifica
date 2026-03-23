"""Sightings API routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Location, Sighting
from schemas import SightingsResponse, SightingRecord
from logging_config import get_logger

router = APIRouter(prefix="/api", tags=["sightings"])
logger = get_logger("api.sightings")

# Canonical species mapping (raw -> canonical)
CANONICAL_SPECIES = {
    # Whales
    "gray whale": "Gray Whale",
    "gray whales": "Gray Whale",
    "grey whale": "Gray Whale",
    "grey whales": "Gray Whale",
    "humpback whale": "Humpback Whale",
    "humpback whales": "Humpback Whale",
    "blue whale": "Blue Whale",
    "blue whales": "Blue Whale",
    "fin whale": "Fin Whale",
    "fin whales": "Fin Whale",
    "orca": "Orca",
    "orcas": "Orca",
    "killer whale": "Orca",
    "killer whales": "Orca",
    # Dolphins
    "bottlenose dolphin": "Bottlenose Dolphin",
    "bottlenose dolphins": "Bottlenose Dolphin",
    "botllenose dolphin": "Bottlenose Dolphin",
    "common dolphin": "Common Dolphin",
    "common dolphins": "Common Dolphin",
    "pacific white-sided dolphin": "Pacific White-Sided Dolphin",
    "pacific white sided dolphin": "Pacific White-Sided Dolphin",
    "dolphin": "Dolphin",
    "dolphins": "Dolphin",
    # Sharks
    "white shark": "White Shark",
    "great white shark": "White Shark",
    "mako shark": "Mako Shark",
    "blue shark": "Blue Shark",
    "shark": "Shark",
    "sharks": "Shark",
    # Pinnipeds
    "california sea lion": "California Sea Lion",
    "sea lion": "Sea Lion",
    "harbor seal": "Harbor Seal",
    "seal": "Seal",
    "elephant seal": "Elephant Seal",
    "pinniped": "Pinniped",
    # Birds
    "brown pelican": "Brown Pelican",
    "pelican": "Pelican",
    "double-crested cormorant": "Double-Crested Cormorant",
    "cormorant": "Cormorant",
    "tern": "Tern",
    "albatross": "Albatross",
    "shearwater": "Shearwater",
    "murre": "Murre",
    "puffin": "Puffin",
    # Fish
    "garibaldi": "Garibaldi",
    "mola mola": "Mola Mola",
    "sunfish": "Sunfish",
    # Invertebrates
    "octopus": "Octopus",
    "california lilliput octopus": "Octopus",
    "two-spot octopus": "Octopus",
    # Marine Mammals
    "sea otter": "Sea Otter",
    "otter": "Sea Otter",
}


def get_taxon_group(species: str) -> str:
    """Derive taxon_group from species name (case-insensitive substring match)."""
    species_lower = species.lower()

    # Exact matches first
    if species_lower in (
        "whale",
        "orca",
        "humpback whale",
        "blue whale",
        "fin whale",
        "gray whale",
        "grey whale",
        "killer whale",
    ):
        return "whale"
    if species_lower in (
        "dolphin",
        "porpoise",
        "bottlenose dolphin",
        "common dolphin",
        "pacific white-sided dolphin",
    ):
        return "dolphin"
    if species_lower in ("shark",):
        return "shark"
    if species_lower in (
        "seal",
        "sea lion",
        "elephant seal",
        "pinniped",
        "california sea lion",
        "harbor seal",
    ):
        return "pinniped"
    if species_lower in (
        "pelican",
        "tern",
        "albatross",
        "cormorant",
        "shearwater",
        "murre",
        "puffin",
        "brown pelican",
        "double-crested cormorant",
    ):
        return "bird"

    # Substring matches (case-insensitive)
    if any(word in species_lower for word in ["whale", "orca"]):
        return "whale"
    if any(word in species_lower for word in ["dolphin", "porpoise"]):
        return "dolphin"
    if "shark" in species_lower:
        return "shark"
    if any(word in species_lower for word in ["seal", "sea lion", "pinniped"]):
        return "pinniped"
    if any(
        word in species_lower
        for word in [
            "pelican",
            "tern",
            "albatross",
            "cormorant",
            "shearwater",
            "murre",
            "puffin",
        ]
    ):
        return "bird"

    return "other"


def canonicalize_species(species: str) -> str:
    """Normalize species name to canonical form."""
    species_lower = species.lower()
    return CANONICAL_SPECIES.get(species_lower, species)


@router.get("/sightings", response_model=SightingsResponse)
async def get_sightings(
    days: int = Query(7, description="How many days back to query", ge=1, le=365),
    limit: int = Query(200, description="Max records returned", ge=1, le=1000),
    quality: str = Query(
        "high,medium", description="Confidence levels to include (comma-separated)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent wildlife sightings with optional filtering.

    Query params:
    - days: Number of days back to query (default: 7)
    - limit: Max records returned (default: 200)
    - quality: Confidence levels to include, comma-separated (default: high,medium)
    """
    logger.info(
        "Sightings endpoint called",
        days=days,
        limit=limit,
        quality=quality,
    )

    # Parse quality filter
    quality_levels = [q.strip().lower() for q in quality.split(",")]

    # Calculate time window based on sighting_date
    now = datetime.now(timezone.utc)
    today = now.date()
    start_date = today - timedelta(days=days - 1)

    # Query sightings - only past dates (not future), within date range
    # Order ASC so most recent dates come first in the results
    query = select(Sighting).where(
        Sighting.sighting_date >= start_date,
        Sighting.sighting_date <= today,
    )

    # Filter by confidence
    if quality_levels:
        query = query.where(Sighting.confidence.in_(quality_levels))

    # Order by sighting_date descending (most recent first), then by timestamp
    query = query.order_by(
        desc(Sighting.sighting_date), desc(Sighting.timestamp)
    ).limit(limit)

    result = await db.execute(query)
    sightings_db = result.scalars().all()

    # Get location names
    location_ids = {s.location_id for s in sightings_db if s.location_id}
    locations_map = {}
    if location_ids:
        locations_result = await db.execute(
            select(Location).where(Location.id.in_(location_ids))
        )
        locations = locations_result.scalars().all()
        locations_map = {loc.id: loc.name for loc in locations}

    # Build response records with taxon_group derivation
    sighting_records = []
    for sighting in sightings_db:
        canonical_species = canonicalize_species(sighting.species)
        taxon_group = get_taxon_group(canonical_species)
        location_name = (
            locations_map.get(sighting.location_id) if sighting.location_id else None
        )

        record = SightingRecord(
            id=sighting.id,
            timestamp=sighting.timestamp,
            sighting_date=sighting.sighting_date,
            species=canonical_species,
            taxon_group=taxon_group,
            count=sighting.count,
            location_id=sighting.location_id,
            location_name=location_name,
            source=sighting.source,
            source_url=sighting.source_url,
            confidence=sighting.confidence,
            raw_text=sighting.raw_text,
            metadata=sighting.meta or {},
        )
        sighting_records.append(record)

    return SightingsResponse(
        sightings=sighting_records,
        total=len(sighting_records),
        days_requested=days,
    )
