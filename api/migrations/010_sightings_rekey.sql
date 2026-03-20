-- 010_sightings_rekey.sql
-- Sightings re-key: migrate from URL-based dedupe to business-key dedupe.
--
-- Background:
-- - Old dedupe: (source, source_url, timestamp) — tied to individual page scrapes,
--   creates one row per API response per page/URL, blows up cardinality.
-- - New dedupe: (source, location_id, sighting_date, species) — one row per
--   location + day + species, matching how sources actually publish data.
--
-- Because we have only ~1 day of real data, we TRUNCATE the table and start fresh
-- rather than backfill. location_id is made nullable in 009, but the FK is removed
-- here to keep the table practical for region-level sightings (e.g. iNat aggregates).
--
-- Steps:
--   1. Truncate sightings (reset sequence)
--   2. Add sighting_date column
--   3. Drop old URL-based dedupe index
--   4. Create new business-key unique constraint
--   5. Drop unused location_id FK (keeps the column; FK was from 001)

BEGIN;

-- ── 1. Wipe existing data and reset primary key sequence ──────────────────────
TRUNCATE sightings RESTART IDENTITY;

-- ── 2. Add sighting_date column ───────────────────────────────────────────────
-- Derived from timestamp for existing (empty) rows; will be set explicitly
-- by all scrapers going forward.
ALTER TABLE sightings
    ADD COLUMN sighting_date DATE NOT NULL DEFAULT timestamp::date;

-- The DEFAULT is only needed for the zero rows left after TRUNCATE.
-- Drop it now so future inserts MUST provide sighting_date explicitly.
ALTER TABLE sightings
    ALTER COLUMN sighting_date DROP DEFAULT;

-- ── 3. Drop old URL-based dedupe index ───────────────────────────────────────
-- This was the index definition in 003_indexes.sql (line 13-15).
-- IF NOT EXISTS guards against running this migration on a fresh DB that
-- never had the old index.
DROP INDEX IF EXISTS sightings_dedup_url;

-- ── 4. Create new business-key unique constraint ─────────────────────────────
-- One row per (source, location_id, sighting_date, species).
-- Handles NULL location_id (iNat-sourced region-level sightings).
CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_biz
    ON sightings (source, location_id, sighting_date, species)
    WHERE location_id IS NOT NULL;

-- Partial index for rows without a location (iNat regional aggregates)
-- These can also collide; index on source + sighting_date + species only.
CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_biz_noloc
    ON sightings (source, sighting_date, species)
    WHERE location_id IS NULL;

-- ── 5. Drop the location_id FK (not strictly needed; keeps table practical) ─
-- The FK from 001 keeps location_id pointing to locations.id, but for aggregated
-- sources like iNat we may not have a location. We remove the FK constraint only;
-- the column stays.
-- Locate the FK name dynamically to avoid hardcoding it.
DO $$
DECLARE
    fk_name TEXT;
BEGIN
    SELECT conname INTO fk_name
    FROM pg_constraint
    WHERE conrelid = 'sightings'::regclass
      AND contype  = 'f'
      AND confkey @> ARRAY[
          (SELECT attnum FROM pg_attribute WHERE attrelid = 'sightings'::regclass AND attname = 'location_id')
      ];
    IF fk_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE sightings DROP CONSTRAINT %I', fk_name);
    END IF;
END $$;

COMMIT;
