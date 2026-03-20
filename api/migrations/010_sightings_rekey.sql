-- 010_sightings_rekey.sql
-- Sightings re-key: TRUNCATE + add sighting_date column.
--
-- The CREATE TABLE IF NOT EXISTS in 001_tables.sql skipped the existing table,
-- so the column doesn't exist. This migration clears the table and adds the
-- new column with no DEFAULT (no DEFAULT avoids PostgreSQL column self-reference
-- rejection on DEFAULT timestamp::date).
--
-- All scrapers must provide sighting_date explicitly on insert.
-- TimescaleDB hypertables require the partitioning column (timestamp) in all
-- unique indexes, enforced via partial unique indexes below.

BEGIN;

-- ── 1. Clear existing sightings ───────────────────────────────────────────────
TRUNCATE sightings;

-- ── 2. Add sighting_date column ───────────────────────────────────────────────
-- NO DEFAULT — the original bug was DEFAULT timestamp::date which PostgreSQL
-- rejects as column self-reference.
ALTER TABLE sightings ADD COLUMN sighting_date DATE NOT NULL;

-- ── 3. Replace simple PK with composite PK (id, timestamp) ──────────────────
-- TimescaleDB hypertables require partitioning column in the primary key.
ALTER TABLE sightings DROP CONSTRAINT IF EXISTS sightings_pkey;
ALTER TABLE sightings ADD PRIMARY KEY (id, timestamp);

-- ── 4. Drop old URL-based dedupe index (from 003_indexes) ────────────────────
DROP INDEX IF EXISTS sightings_dedup_url;

-- ── 5. Create business-key dedupe indexes (includes timestamp) ───────────────
-- Partial unique indexes — one per location_id case — required because
-- TimescaleDB hypertables cannot have NULLs in unique indexes.
CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_biz
    ON sightings (source, location_id, sighting_date, species, timestamp)
    WHERE location_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_biz_noloc
    ON sightings (source, sighting_date, species, timestamp)
    WHERE location_id IS NULL;

COMMIT;
