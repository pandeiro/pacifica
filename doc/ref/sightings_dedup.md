# Sightings Table — Deduplication Design Review

## Current State

### Schema (001_tables.sql)

```sql
CREATE TABLE IF NOT EXISTS sightings (
    id          BIGSERIAL,
    timestamp   TIMESTAMPTZ NOT NULL,
    location_id INTEGER NOT NULL REFERENCES locations(id),
    species     TEXT NOT NULL,
    count       INTEGER,
    source      TEXT NOT NULL,
    source_url  TEXT,          -- nullable
    raw_text    TEXT,
    confidence  TEXT NOT NULL DEFAULT 'medium',
    metadata    JSONB NOT NULL DEFAULT '{}'
);
```

### Indexes / constraints actually in the DB right now

```
sightings_dedup_key   UNIQUE (source, source_url, timestamp, species)
idx_sightings_location_time   btree (location_id, timestamp DESC)
idx_sightings_species_time    btree (species, timestamp DESC)
sightings_timestamp_idx       btree (timestamp DESC)
```

### What's in source control (003_indexes.sql)

The migration creates a now-dropped index:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_url
    ON sightings (source, source_url, timestamp)
    WHERE source_url IS NOT NULL;
```

`sightings_dedup_key` — the constraint currently protecting the table — **does not exist in any migration file**. It was added manually at the DB console during debugging. The live DB and the migrations are out of sync.

---

## What Each Scraper Actually Inserts

| Scraper | timestamp | source_url | dedup behavior |
|---------|-----------|------------|---------------|
| **iNaturalist** | exact observation time from API | unique observation URL `/observations/<id>` | ✅ naturally unique per row |
| **Davey's Locker** | sighting date, noon Pacific | `base_url#YYYY-MM-DD-species-slug` | ✅ works, but species encoded in URL is a hack |
| **Dana Wharf** | sighting date from CSV row | same URL for every row | ✅ works because timestamp differs per row |
| **Island Packers** | sighting date from CSV row | same URL for every row | ✅ works because timestamp differs per row |
| **ACS-LA** | scrape time (not sighting date) | same URL for every row | ⚠️ re-scraping same day creates duplicates |
| **Harbor Breeze** | scrape time (not sighting date) | same URL for every row | ❌ only 1 row per species survives per scrape |

---

## Root Problems

### 1. `source_url` is not a natural key

`source_url` was never a natural key — it's an audit/provenance field that says "where did this come from." Using it as part of a dedup key requires scrapers to artificially encode date and species into URLs, which is what Davey's Locker does and why it looks wrong.

### 2. The schema has no `sighting_date` column

The natural key for a sighting aggregation row is `(source, location_id, sighting_date, species)`. There is no `sighting_date` column. `timestamp` is used as a proxy, but scrapers that don't have a per-row date (Harbor Breeze, ACS-LA) must fall back to scrape time, which breaks dedup.

### 3. Schema drift

`sightings_dedup_key` is not in any migration. `sightings_dedup_url` was dropped from the live DB but is still in `003_indexes.sql`. Any new environment (staging, prod, a new dev machine) will get the wrong constraint.

### 4. `source_url` wastes space and adds noise

The column has 1,019 distinct values for Davey's Locker alone (one per species per day). It adds no useful information beyond what `source`, `sighting_date`, and `species` already express. iNaturalist is the only source where it's genuinely useful (the observation URL is a real reference).

---

## Recommendation

### Option A — Minimal fix (low risk, no schema change)

Keep the current table shape. Fix the migration drift and the two broken scrapers.

**Migration 010:**
```sql
-- Drop the old index if it somehow still exists
DROP INDEX IF EXISTS sightings_dedup_url;

-- Ensure correct constraint exists (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'sightings_dedup_key'
    ) THEN
        ALTER TABLE sightings
            ADD CONSTRAINT sightings_dedup_key
            UNIQUE (source, source_url, timestamp, species);
    END IF;
END $$;
```

**Scraper fixes:**
- **Harbor Breeze**: set `timestamp` = sighting date (today, noon Pacific). Already done — the actual bug is that `source_url` is identical for all rows on the same day, so the constraint `(source, source_url, timestamp, species)` already distinguishes them correctly as long as timestamp is the date, not the scrape second. ✅ No source_url hack needed.
- **ACS-LA**: same fix — set `timestamp` to today's date at a fixed time, not scrape time.

This is the fastest path to correct behavior.

---

### Option B — Proper schema redesign (recommended for the long term)

Add a `sighting_date` column as the real dedup key. Keep `source_url` but treat it as provenance only.

**Migration 010:**
```sql
-- Add sighting_date column
ALTER TABLE sightings
    ADD COLUMN IF NOT EXISTS sighting_date DATE;

-- Backfill from existing timestamp
UPDATE sightings SET sighting_date = timestamp::date WHERE sighting_date IS NULL;

-- Make it NOT NULL going forward
ALTER TABLE sightings ALTER COLUMN sighting_date SET NOT NULL;

-- Drop old constraint / index
DROP INDEX IF EXISTS sightings_dedup_url;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'sightings_dedup_key') THEN
        ALTER TABLE sightings DROP CONSTRAINT sightings_dedup_key;
    END IF;
END $$;

-- New clean constraint: one row per (source, location, date, species)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'sightings_dedup') THEN
        ALTER TABLE sightings
            ADD CONSTRAINT sightings_dedup
            UNIQUE (source, location_id, sighting_date, species);
    END IF;
END $$;
```

**Scraper changes:** every scraper sets `sighting_date` explicitly from the row data. `source_url` becomes optional provenance only — no need to encode date/species into it.

**iNaturalist count:** iNat observations are individual sightings (count=1 each), and their natural key is the observation ID. The constraint `(source, location_id, sighting_date, species)` would collapse multiple iNat observations of the same species on the same day into one row. **This is wrong for iNat.** Fix: iNat should store each observation individually, with `source_url` = the observation URL, and the unique constraint should have an exception for `source = 'inaturalist'` — or iNat should use its own observation ID as part of the key.

Simplest solution: keep `source_url` in the constraint only for iNaturalist-style sources, use `sighting_date` for the rest. Achieved by making the constraint partial:

```sql
-- For sources with unique per-observation URLs (iNaturalist)
CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_inaturalist
    ON sightings (source, source_url)
    WHERE source_url IS NOT NULL AND source = 'inaturalist';

-- For aggregated daily sources (all others)
CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_daily
    ON sightings (source, location_id, sighting_date, species)
    WHERE source != 'inaturalist';
```

---

### Option C — Add a `sighting_sources` lookup table

As raised: replace `source TEXT` with a foreign key to a `sighting_sources` table.

```sql
CREATE TABLE sighting_sources (
    id          SERIAL PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,   -- 'harbor_breeze', 'dana_wharf', etc.
    name        TEXT NOT NULL,
    url         TEXT,                   -- base URL of the source
    source_type TEXT NOT NULL           -- 'daily_aggregate' | 'individual_observation' | 'count_report'
);
```

`source_type` encodes whether the source produces individual observations (iNat) or daily aggregates (everyone else). The dedup logic can branch on this. The `source_url` column on `sightings` becomes the per-row observation URL (only populated for `individual_observation` sources).

This is the cleanest design but requires touching the `sightings` table schema, the `Sighting` SQLAlchemy model, all scrapers, and all API queries. Worthwhile but a larger migration.

---

## Recommendation Summary

| | Option A | Option B | Option C |
|--|---------|---------|---------|
| Fixes Harbor Breeze | ✅ | ✅ | ✅ |
| Fixes schema drift | ✅ | ✅ | ✅ |
| Clean natural key | ❌ still uses timestamp | ✅ sighting_date | ✅ |
| iNat handled correctly | ✅ | needs partial index | ✅ |
| Scope | 1 migration + 2 scraper fixes | 1 migration + all scrapers | larger refactor |

**Start with Option B.** It fixes the real problem cleanly, handles iNat correctly with partial indexes, and sets up a proper `sighting_date` field that the API and frontend can use directly for date-range queries. Option C can follow later as a separate card.
