-- 003_indexes.sql
-- Create indexes for performance and deduplication

-- ── Sightings ──────────────────────────────
CREATE INDEX IF NOT EXISTS idx_sightings_location_time
    ON sightings (location_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_sightings_species_time
    ON sightings (species, timestamp DESC);

-- Deduplication indexes (must include timestamp for hypertables)
-- Note: These are partial unique indexes that include timestamp for hypertable compatibility
-- Deduplication is now handled by migration 010_sightings_rekey.sql which
-- creates sightings_dedup_biz (source, location_id, sighting_date, species).
-- The old URL-based index (source, source_url, timestamp) was dropped there.

-- ── Conditions ─────────────────────────────
CREATE INDEX IF NOT EXISTS idx_conditions_location_type_time
    ON conditions (location_id, condition_type, timestamp DESC);

CREATE UNIQUE INDEX IF NOT EXISTS conditions_dedup
    ON conditions (source, location_id, condition_type, timestamp);

-- ── Tides ──────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_tides_station_time
    ON tides (station_id, timestamp DESC);

-- ── Activity Scores ────────────────────────
CREATE INDEX IF NOT EXISTS idx_activity_scores_location_type_time
    ON activity_scores (location_id, activity_type, timestamp DESC);

-- ── Locations ──────────────────────────────
CREATE INDEX IF NOT EXISTS idx_locations_slug
    ON locations (slug);

CREATE INDEX IF NOT EXISTS idx_locations_region
    ON locations (region);

-- ── Scrape Logs ────────────────────────────
CREATE INDEX IF NOT EXISTS idx_scrape_logs_scraper_time
    ON scrape_logs (scraper_name, started_at DESC);
