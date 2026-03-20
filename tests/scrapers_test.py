#!/usr/bin/env python3
"""Scraper output test — shows exactly what rows would be inserted into the database.

Run from repo root:
    python tests/scrapers_test.py

Each section exercises one scraper's parsing logic with representative sample data,
prints the parsed records, and writes the results to doc/ref/scrapers_test.md.
"""

import io
import sys
import json
from datetime import datetime, timezone, timedelta, date

sys.path.insert(0, "scraper")

# ─── helpers ─────────────────────────────────────────────────────────────────

PASCIFIC = timezone(timedelta(hours=-8))
SCRAPE_TS = datetime(2026, 3, 20, 14, 0, 0, tzinfo=timezone.utc)  # fake scrape time
LOCATION_ID = 1  # dummy location_id for all tests


def ts_repr(dt):
    """Short UTC ISO repr for display."""
    if dt is None:
        return "None"
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def row_summary(record: dict) -> dict:
    """Trim a record to the fields that matter for inspection."""
    return {
        "timestamp": ts_repr(record.get("timestamp")),
        "sighting_date": str(record.get("sighting_date")),
        "location_id": record.get("location_id"),
        "species": record.get("species"),
        "count": record.get("count"),
        "source": record.get("source"),
        "confidence": record.get("confidence"),
    }


def print_records(name: str, records: list, f):
    print(f"\n{'=' * 60}", file=f)
    print(f"  {name}", file=f)
    print(f"{'=' * 60}", file=f)
    if not records:
        print("  (no records produced)", file=f)
        return
    for r in records:
        print(f"  sighting_date : {r['sighting_date']}", file=f)
        print(f"  timestamp    : {ts_repr(r.get('timestamp'))}", file=f)
        print(f"  species      : {r['species']}", file=f)
        print(f"  count       : {r['count']}", file=f)
        print(f"  source      : {r['source']}", file=f)
        print(f"  confidence  : {r['confidence']}", file=f)
        print(file=f)


# ─── 1. ACS-LA ───────────────────────────────────────────────────────────────


def test_acs_la(f):
    from acs_la import extract_structured_counts, parse_date

    print("\n[1] ACS-LA — parse_date() unit tests", file=f)
    cases = [
        (
            "ACS/LA Gray Whale Census and Behavior Project Update, Pt. Vicente Interpretive Center, 16 March 2026 - heavy fog blocked our views",
            date(2026, 3, 16),
        ),
        (
            "Update March 16, 2026 - light winds. GRAY WHALES TODAY: Southbound: 12",
            date(2026, 3, 16),
        ),
        (
            "Posted 4 days ago — ACS/LA census report",
            date(2026, 3, 16),
        ),  # relative to SCRAPE_TS (2026-03-20 Pacific)
        ("No date here. GRAY WHALES TODAY: Southbound: 5", None),
    ]
    for text, expected in cases:
        result = parse_date(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {str(expected):12s} <- {text[:60]!r}", file=f)

    # Full scrape simulation
    print("\n[1] ACS-LA — full record output", file=f)
    post = """
    ACS/LA Gray Whale Census and Behavior Project Update, Pt. Vicente Interpretive Center, 16 March 2026 - heavy fog blocked our views of the horizon.
    GRAY WHALES TODAY:
    Southbound: 23
    Northbound: 8
    Cow/calves south: 2
    Total: 33
    """
    counts = extract_structured_counts(post)
    sd = parse_date(post) or date(2026, 3, 20)
    records = []
    for direction, species in [
        ("southbound", "Gray Whale (southbound)"),
        ("northbound", "Gray Whale (northbound)"),
        ("cow_calf", "Gray Whale (cow/calf)"),
    ]:
        cnt = counts.get(
            {
                "southbound": "southbound",
                "northbound": "northbound",
                "cow_calf": "cow_calves_south",
            }.get(direction, direction),
            0,
        )
        if cnt > 0:
            records.append(
                {
                    "timestamp": SCRAPE_TS,
                    "sighting_date": sd,
                    "location_id": LOCATION_ID,
                    "species": species,
                    "count": cnt,
                    "source": "acs_la",
                    "confidence": "high",
                }
            )
    print_records("ACS-LA records", records, f)


# ─── 2. Dana Wharf ────────────────────────────────────────────────────────────


def test_dana_wharf(f):
    from dana_wharf import parse_sightings_text

    print("\n[2] Dana Wharf — parse_sightings_text() unit tests", file=f)
    cases = [
        (
            "3 Fin whales, 10 gray whales, 1 mola mola",
            [(10, "Gray Whale"), (3, "Fin Whale"), (1, "Mola Mola")],
        ),
        ("Common Dolphins", [(None, "Common Dolphin")]),
        ("1 Orca, 50 Bottlenose Dolphin", [(1, "Orca"), (50, "Bottlenose Dolphin")]),
    ]
    for text, expected in cases:
        result = parse_sightings_text(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {text[:50]!r}", file=f)

    print("\n[2] Dana Wharf — full record output", file=f)
    csv_rows = [
        ("3/18/2026", "3 Fin whales, 10 gray whales"),
        ("3/19/2026", "25 Common Dolphin"),
        ("3/20/2026", "1 Humpback, 2 Risso's Dolphins"),
    ]
    records = []
    for date_str, text in csv_rows:
        from dana_wharf import parse_date

        parsed_dt = parse_date(date_str)
        sd = parsed_dt.date() if parsed_dt else date(2026, 3, 20)
        for cnt, species in parse_sightings_text(text):
            records.append(
                {
                    "timestamp": SCRAPE_TS,
                    "sighting_date": sd,
                    "location_id": LOCATION_ID,
                    "species": species,
                    "count": cnt,
                    "source": "dana_wharf",
                    "confidence": "high",
                }
            )
    print_records("Dana Wharf records", records, f)


# ─── 3. Harbor Breeze ─────────────────────────────────────────────────────────


def test_harbor_breeze(f):
    from harbor_breeze import (
        _parse_date_from_text,
        parse_sightings_from_text,
    )

    print("\n[3] Harbor Breeze — _parse_date_from_text() unit tests", file=f)
    date_cases = [
        ("March 16, 2026 — 5 Humpback whales spotted", date(2026, 3, 16)),
        ("16 Mar 2026 — 2 Orca observed", date(2026, 3, 16)),
        ("03/17/2026 — 200 Common Dolphins", date(2026, 3, 17)),
        ("No date here — just dolphins", None),
    ]
    for text, expected in date_cases:
        result = _parse_date_from_text(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {str(expected):12s} <- {text[:50]!r}", file=f)

    print("\n[3] Harbor Breeze — parse_sightings_from_text() unit tests", file=f)
    sightings_cases = [
        (
            "500 Common Dolphins, 1 Humpback",
            [(1, "Humpback Whale"), (500, "Common Dolphin")],
        ),
        ("2 Fin whales", [(2, "Fin Whale")]),
        (
            "1,000 Bottlenose Dolphin, 3 Gray whales",
            [(3, "Gray Whale"), (1000, "Bottlenose Dolphin")],
        ),
    ]
    for text, expected in sightings_cases:
        result = parse_sightings_from_text(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {text[:50]!r}", file=f)

    print(
        "\n[3] Harbor Breeze — full record output (date in heading, then sighting lines)",
        file=f,
    )
    # Simulate the HTML text stream with heading dates and sighting lines
    html_text = """
    Long Beach Whale Watching Reports
    March 18, 2026
    500 Common Dolphins
    2 Gray whales
    March 19, 2026
    1 Humpback whale, 3 Fin whales
    """

    # We'll simulate what _extract_sightings produces: list of (date, text)
    from harbor_breeze import _parse_date_from_text

    entries = []
    pending_date = None
    for line in html_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        d = _parse_date_from_text(line)
        if d:
            pending_date = d
        if pending_date:
            sightings = parse_sightings_from_text(line)
            if sightings:
                entries.append((pending_date, line, sightings))

    records = []
    for entry_date, text, sightings in entries:
        for cnt, species in sightings:
            records.append(
                {
                    "timestamp": SCRAPE_TS,
                    "sighting_date": entry_date,
                    "location_id": LOCATION_ID,
                    "species": species,
                    "count": cnt,
                    "source": "harbor_breeze",
                    "confidence": "high",
                }
            )
    print_records("Harbor Breeze records", records, f)


# ─── 4. Davey's Locker ───────────────────────────────────────────────────────


def test_daveys_locker(f):
    from daveys_locker import parse_species_list

    print("\n[4] Davey's Locker — parse_species_list() unit tests", file=f)
    cases = [
        (
            "53 Gray Whales, 103 Bottlenose Dolphin",
            [(53, "Gray Whales"), (103, "Bottlenose Dolphin")],
        ),
        (
            "1 Fin Whale, 1100 Common Dolphin, 1 Mola Mola",
            [(1, "Fin Whale"), (1100, "Common Dolphin"), (1, "Mola Mola")],
        ),
        ("No sightings today", []),
    ]
    for text, expected in cases:
        result = parse_species_list(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {text[:50]!r}", file=f)

    print("\n[4] Davey's Locker — full record output", file=f)
    table_rows = [
        ("3/18/2026", "53 Gray Whales, 103 Bottlenose Dolphin, 625 Common Dolphin"),
        ("3/19/2026", "12 Gray Whales, 1 Fin Whale, 1100 Common Dolphin"),
    ]
    records = []
    for date_str, text in table_rows:
        from daveys_locker import parse_date

        parsed_dt = parse_date(date_str)
        sd = parsed_dt.date() if parsed_dt else date(2026, 3, 20)
        for cnt, species in parse_species_list(text):
            records.append(
                {
                    "timestamp": SCRAPE_TS,
                    "sighting_date": sd,
                    "location_id": LOCATION_ID,
                    "species": species,
                    "count": cnt,
                    "source": "daveyslocker",
                    "confidence": "high",
                }
            )
    print_records("Davey's Locker records", records, f)


# ─── 5. Island Packers ────────────────────────────────────────────────────────


def test_island_packers(f):
    from island_packers import parse_count, IslandPackersScraper

    print("\n[5] Island Packers — parse_count() unit tests", file=f)
    cases = [
        ("15", 15),
        ("1,000", 1000),
        ("", None),
        ("abc", None),
        ("0", None),
    ]
    for text, expected in cases:
        result = parse_count(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] parse_count({text!r}) = {result}", file=f)

    print("\n[5] Island Packers — full record output", file=f)
    csv_text = (
        "Date,Humpback Whales,Blue Whales,Gray Whales,Common Dolphins\n"
        '3,"5","0","0","200"\n'
        '4,"0","1","3","0"\n'
        '5,"12","0","0","50"\n'
    )
    scraper = IslandPackersScraper()
    records = scraper._parse_daily_sightings(csv_text, LOCATION_ID)
    for r in records:
        r["timestamp"] = ts_repr(r["timestamp"])
    print_records("Island Packers records", records, f)


# ─── 6. iNaturalist ───────────────────────────────────────────────────────────


def test_inaturalist(f):
    import asyncio
    import sys
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock, patch

    import scraper.db as scraper_db

    sys.modules["db"] = scraper_db

    from inaturalist import INatScraper

    print("\n[6] iNaturalist — _parse_observation() unit tests", file=f)

    scraper = INatScraper()

    async def mock_nearest(session, lat, lng, max_distance_miles=30.0):
        import math
        from scraper.db import haversine_distance

        dist = haversine_distance(34.0, -118.4, lat, lng)
        if dist <= max_distance_miles:
            return (1, None)
        return (None, None)

    cases = [
        {
            "name": "valid observation, research grade",
            "obs": {
                "id": 999,
                "geojson": {"coordinates": [-118.5, 34.0]},
                "observed_on": "2026-03-20",
                "taxon": {"preferred_common_name": "Common Dolphin"},
                "quality_grade": "research",
                "count": 5,
            },
            "expected_species": "Common Dolphin",
            "expected_confidence": "high",
            "expected_location_id": 1,
        },
        {
            "name": "no geojson → None",
            "obs": {"id": 998, "observed_on": "2026-03-20"},
            "expected": None,
        },
        {
            "name": "outside 30 mi radius → None",
            "obs": {
                "id": 997,
                "geojson": {"coordinates": [-150.0, 40.0]},
                "observed_on": "2026-03-20",
                "taxon": {"preferred_common_name": "Gray Whale"},
                "quality_grade": "research",
            },
            "expected": None,
        },
    ]

    for case in cases:
        obs = case["obs"]
        with patch(
            "inaturalist.find_nearest_location", new=AsyncMock(side_effect=mock_nearest)
        ):
            result = asyncio.run(scraper._parse_observation(obs, MagicMock()))
        if "expected" in case:
            status = "PASS" if result is case["expected"] else "FAIL"
            print(f"  [{status}] {case['name']}", file=f)
        else:
            ok = (
                result is not None
                and result["species"] == case["expected_species"]
                and result["confidence"] == case["expected_confidence"]
                and result["location_id"] == case["expected_location_id"]
            )
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {case['name']}", file=f)

    print("\n[6] iNaturalist — full aggregate record output (mock)", file=f)
    # Simulate the _aggregate path
    observations = [
        {
            "id": 1,
            "geojson": {"coordinates": [-118.5, 34.0]},
            "observed_on": "2026-03-20",
            "taxon": {"preferred_common_name": "Common Dolphin"},
            "quality_grade": "research",
            "count": 5,
        },
        {
            "id": 2,
            "geojson": {"coordinates": [-118.6, 34.1]},
            "observed_on": "2026-03-20",
            "taxon": {"preferred_common_name": "Common Dolphin"},
            "quality_grade": "needs_id",
            "count": 3,
        },
        {
            "id": 3,
            "geojson": {"coordinates": [-118.5, 34.0]},
            "observed_on": "2026-03-20",
            "taxon": {"preferred_common_name": "Gray Whale"},
            "quality_grade": "research",
            "count": 2,
        },
    ]

    @asynccontextmanager
    async def mock_get_db_session():
        mock_s = MagicMock()
        mock_s.find_nearest_location = AsyncMock(side_effect=mock_nearest)
        yield mock_s

    with (
        patch("inaturalist.get_db_session", new=mock_get_db_session),
        patch(
            "inaturalist.find_nearest_location", new=AsyncMock(side_effect=mock_nearest)
        ),
    ):
        records_raw = asyncio.run(scraper._aggregate(observations, date(2026, 3, 20)))

    for r in records_raw:
        r["timestamp"] = ts_repr(r["timestamp"])

    print_records("iNaturalist aggregate records", records_raw, f)


# ─── main ────────────────────────────────────────────────────────────────────


def main():
    output_path = "/app/ref/scrapers_test.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(output_path, "w") as f:
        print(f"# Scraper Output Test\n\nGenerated: {ts}  \n", file=f)
        print(
            "This document shows the exact records each scraper would insert into the ",
            file=f,
        )
        print(
            "`sightings` table. `timestamp` is the scrape/ingest time (fixed for these ",
            file=f,
        )
        print(
            "tests); `sighting_date` is the date parsed from the source data.", file=f
        )
        print(
            "A dummy `location_id=1` is used; `source_url` and `raw_text` omitted for brevity.",
            file=f,
        )

        test_acs_la(f)
        test_dana_wharf(f)
        test_harbor_breeze(f)
        test_daveys_locker(f)
        test_island_packers(f)
        test_inaturalist(f)

    print(f"\nResults written to {output_path}")


if __name__ == "__main__":
    main()
