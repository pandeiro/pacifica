-- 010_sightings_rekey.sql
-- Sightings re-key: migrate from URL-based dedupe to business-key dedupe.
--
-- The sightings table was recreated in 001_tables.sql (this migration) with
-- sighting_date as a proper column. Old data is discarded — all scrapers must
-- provide sighting_date explicitly on insert. The hypertable is partitioned by
-- timestamp, so unique indexes must include timestamp. The business-key dedupe
-- is enforced via unique partial indexes that include timestamp (see 003_indexes).
--
-- Steps:
--   1. Drop old URL-based dedupe index (003_indexes)
--   2. Create new business-key unique constraint with timestamp

BEGIN;

-- ── 1. Drop old URL-based dedupe index ───────────────────────────────────────
-- This was the index definition in 003_indexes.sql (line 13-15).
DROP INDEX IF EXISTS sightings_dedup_url;

-- ── 2. Create new business-key unique constraint ─────────────────────────────
-- One row per (source, location_id, sighting_date, species, timestamp).
-- Includes timestamp to satisfy TimescaleDB's partitioning requirement.
-- Handles NULL location_id (iNat-sourced region-level sightings).
CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_biz
    ON sightings (source, location_id, sighting_date, species, timestamp)
    WHERE location_id IS NOT NULL;

-- Partial index for rows without a location (iNat regional aggregates)
CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_biz_noloc
    ON sightings (source, sighting_date, species, timestamp)
    WHERE location_id IS NULL;

COMMIT;
