-- 001_tables.sql
-- Initial database schema - Table definitions
-- Creates all tables needed for Pacifica

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

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
    sighting_date       DATE NOT NULL,
    location_id         INTEGER REFERENCES locations(id) ON DELETE RESTRICT,
    species             TEXT NOT NULL,
    count               INTEGER,
    source              TEXT NOT NULL,
    source_url          TEXT,
    raw_text            TEXT,
    confidence          TEXT NOT NULL DEFAULT 'medium',
    metadata            JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (id, timestamp)
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
