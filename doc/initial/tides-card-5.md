# Card 05 — Database Schema Migrations

> **Slice**: Foundation
> **Depends on**: Nothing — this is the first card executed
> **Blocks**: Every other card
> **Estimated complexity**: Medium

---

## Goal

Create all database tables, hypertables, indexes, constraints, and seed scaffolding that the rest of the system builds on. This card produces a numbered sequence of migration files that run in order and leave the database in a fully initialized state.

Retention and compression policies are **not** in this card — those are Card 04, which runs after this one.

---

## Deliverables

```
db/
├── migrations/
│   ├── 001_tables.sql
│   ├── 002_hypertables.sql
│   ├── 003_indexes.sql
│   └── 004_constraints.sql
├── seed/
│   └── .gitkeep              ← seed files added per slice (locations, cams, etc.)
└── run_migrations.sh         ← idempotent migration runner
```

---

## Migration 001 — Table Definitions

```sql
-- 001_tables.sql

-- ────────────────────────────────────────────
-- Reference / static tables
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS locations (
    id                  SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    slug                TEXT NOT NULL UNIQUE,
    lat                 NUMERIC(9, 6) NOT NULL,
    lng                 NUMERIC(9, 6) NOT NULL,
    location_type       TEXT NOT NULL,         -- beach | tidepool | viewpoint | harbor | island
    region              TEXT NOT NULL,         -- south_coast | la_coast | ventura | central_coast | channel_islands
    noaa_station_id     TEXT,                  -- nullable; for tide + water temp data
    coastline_bearing   NUMERIC(5, 2),         -- degrees; used to determine onshore/offshore wind direction
    description         TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS live_cams (
    id                  SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    location_id         INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    embed_type          TEXT NOT NULL,         -- youtube | iframe | hls
    embed_url           TEXT NOT NULL,
    source_name         TEXT NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS seasonal_events (
    id                  SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    slug                TEXT NOT NULL UNIQUE,
    description         TEXT,
    typical_start_month INTEGER NOT NULL CHECK (typical_start_month BETWEEN 1 AND 12),
    typical_start_day   INTEGER NOT NULL CHECK (typical_start_day BETWEEN 1 AND 31),
    typical_end_month   INTEGER NOT NULL CHECK (typical_end_month BETWEEN 1 AND 12),
    typical_end_day     INTEGER NOT NULL CHECK (typical_end_day BETWEEN 1 AND 31),
    species             TEXT,
    category            TEXT NOT NULL,         -- migration | spawning | bloom | season | celestial | tidal | breeding | conditions
    metadata            JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS settings (
    id                  SERIAL PRIMARY KEY,
    key                 TEXT NOT NULL UNIQUE,
    value               JSONB NOT NULL,
    description         TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ────────────────────────────────────────────
-- Time-series tables (converted to hypertables in 002)
-- ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sightings (
    id                  BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL,
    location_id         INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    species             TEXT NOT NULL,
    count               INTEGER,
    source              TEXT NOT NULL,
    source_url          TEXT,
    raw_text            TEXT,
    confidence          TEXT NOT NULL DEFAULT 'medium',
    metadata            JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS conditions (
    id                  BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL,
    location_id         INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    condition_type      TEXT NOT NULL,
    value               NUMERIC NOT NULL,
    unit                TEXT NOT NULL,
    source              TEXT NOT NULL,
    source_url          TEXT,
    raw_text            TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tides (
    id                  BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL,
    station_id          TEXT NOT NULL,
    type                TEXT NOT NULL,         -- high | low | predicted
    height_ft           NUMERIC(6, 3) NOT NULL,
    source              TEXT NOT NULL DEFAULT 'noaa'
);

CREATE TABLE IF NOT EXISTS sun_events (
    id                  SERIAL PRIMARY KEY,
    date                DATE NOT NULL,
    location_id         INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    sunrise             TIMESTAMPTZ NOT NULL,
    sunset              TIMESTAMPTZ NOT NULL,
    golden_hour_morning_start   TIMESTAMPTZ NOT NULL,
    golden_hour_morning_end     TIMESTAMPTZ NOT NULL,
    golden_hour_evening_start   TIMESTAMPTZ NOT NULL,
    golden_hour_evening_end     TIMESTAMPTZ NOT NULL,
    UNIQUE (date, location_id)
);

CREATE TABLE IF NOT EXISTS activity_scores (
    id                  BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL,
    location_id         INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    activity_type       TEXT NOT NULL,         -- snorkeling | whale_watching | body_surfing | scenic_drive | tidepooling
    score               INTEGER,               -- 0-100, nullable if required inputs missing
    factors             JSONB NOT NULL DEFAULT '{}',
    summary_text        TEXT
);

CREATE TABLE IF NOT EXISTS scrape_logs (
    id                  SERIAL PRIMARY KEY,
    scraper_name        TEXT NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL,
    finished_at         TIMESTAMPTZ,
    status              TEXT NOT NULL,         -- success | failure | partial
    records_created     INTEGER NOT NULL DEFAULT 0,
    records_updated     INTEGER NOT NULL DEFAULT 0,
    records_skipped     INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT
);
```

---

## Migration 002 — Hypertables

```sql
-- 002_hypertables.sql
-- Must run after 001. TimescaleDB extension must be enabled.

CREATE EXTENSION IF NOT EXISTS timescaledb;

SELECT create_hypertable(
    'sightings', 'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'conditions', 'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'tides', 'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'activity_scores', 'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);
```

---

## Migration 003 — Indexes

```sql
-- 003_indexes.sql

-- ── Sightings ──────────────────────────────
CREATE INDEX IF NOT EXISTS idx_sightings_location_time
    ON sightings (location_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_sightings_species_time
    ON sightings (species, timestamp DESC);

-- Dedup indexes (see Card 01)
CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_url
    ON sightings (source, source_url)
    WHERE source_url IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_fallback
    ON sightings (source, location_id, species, date_trunc('hour', timestamp))
    WHERE source_url IS NULL;

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
```

---

## Migration 004 — Constraints

```sql
-- 004_constraints.sql

-- ── Sightings ──────────────────────────────
ALTER TABLE sightings
    ADD CONSTRAINT IF NOT EXISTS sightings_confidence_valid
    CHECK (confidence IN ('high', 'medium', 'low'));

-- ── Conditions ─────────────────────────────
ALTER TABLE conditions
    ADD CONSTRAINT IF NOT EXISTS conditions_type_valid
    CHECK (condition_type IN (
        'visibility', 'water_temp', 'air_temp',
        'swell_height', 'swell_period', 'wind_speed', 'wind_direction'
    ));

-- ── Tides ──────────────────────────────────
ALTER TABLE tides
    ADD CONSTRAINT IF NOT EXISTS tides_type_valid
    CHECK (type IN ('high', 'low', 'predicted'));

-- ── Activity Scores ────────────────────────
ALTER TABLE activity_scores
    ADD CONSTRAINT IF NOT EXISTS activity_scores_score_range
    CHECK (score IS NULL OR (score >= 0 AND score <= 100));

ALTER TABLE activity_scores
    ADD CONSTRAINT IF NOT EXISTS activity_scores_type_valid
    CHECK (activity_type IN (
        'snorkeling', 'whale_watching', 'body_surfing',
        'scenic_drive', 'tidepooling'
    ));

-- ── Locations ──────────────────────────────
ALTER TABLE locations
    ADD CONSTRAINT IF NOT EXISTS locations_type_valid
    CHECK (location_type IN ('beach', 'tidepool', 'viewpoint', 'harbor', 'island'));

ALTER TABLE locations
    ADD CONSTRAINT IF NOT EXISTS locations_region_valid
    CHECK (region IN (
        'south_coast', 'la_coast', 'ventura',
        'central_coast', 'channel_islands'
    ));

-- ── Scrape Logs ────────────────────────────
ALTER TABLE scrape_logs
    ADD CONSTRAINT IF NOT EXISTS scrape_logs_status_valid
    CHECK (status IN ('success', 'failure', 'partial'));

-- ── Seasonal Events ────────────────────────
ALTER TABLE seasonal_events
    ADD CONSTRAINT IF NOT EXISTS seasonal_events_category_valid
    CHECK (category IN (
        'migration', 'spawning', 'bloom', 'season',
        'celestial', 'tidal', 'breeding', 'conditions'
    ));
```

---

## Migration Runner

```bash
#!/bin/bash
# db/run_migrations.sh
# Idempotent — safe to run on every deploy.

set -e

MIGRATIONS_DIR="$(dirname "$0")/migrations"

for file in "$MIGRATIONS_DIR"/*.sql; do
    echo "Running migration: $(basename "$file")"
    psql "$DATABASE_URL" -f "$file"
done

echo "All migrations complete."
```

Run order is alphabetical by filename — the numeric prefixes enforce this. Add `set -e` so a failed migration halts the sequence.

---

## Notes

- `coastline_bearing` on `locations` is required by the body surfing wind scoring in Card 03. It is nullable at the DB level — scoring function handles missing values with a neutral default.
- `sun_events` is not a hypertable. It is a regular table with a `(date, location_id)` unique constraint. Row volume is low (~365 rows/year per location) and queries are always by exact date.
- `scrape_logs` is not a hypertable. It is append-only with low volume. Query patterns are simple (latest run per scraper) and well-served by the index on `(scraper_name, started_at DESC)`.

---

## Acceptance Criteria

- [ ] All four migrations run without error on a fresh Postgres 16 + TimescaleDB instance
- [ ] All four migrations are idempotent — running the sequence twice produces no errors
- [ ] `\dt` in psql shows all 10 tables
- [ ] `SELECT * FROM timescaledb_information.hypertables` shows 4 rows (sightings, conditions, tides, activity_scores)
- [ ] All check constraints reject invalid values (test each constraint with one invalid INSERT)
- [ ] Both sightings dedup indexes present and correct (`\di sightings*` shows both)
- [ ] Foreign key on `sightings.location_id` rejects insert with nonexistent location
- [ ] `run_migrations.sh` exits non-zero if any migration fails
