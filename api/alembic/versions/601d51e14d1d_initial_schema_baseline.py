"""initial schema baseline

Consolidates the original hand-written migrations (001-010) and seed data
that predate Alembic. On virgin databases this runs automatically via
`alembic upgrade head`. On production this revision was already applied
as a no-op prior to this change, so Alembic skips it.

Revision ID: 601d51e14d1d
Revises:
Create Date: 2026-03-21 02:20:59.032861

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "601d51e14d1d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 001: Tables ─────────────────────────────────────────────────────
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS timescaledb;

        CREATE TABLE IF NOT EXISTS locations (
            id                  SERIAL PRIMARY KEY,
            name                TEXT NOT NULL,
            slug                TEXT NOT NULL UNIQUE,
            lat                 NUMERIC(9, 6) NOT NULL,
            lng                 NUMERIC(9, 6) NOT NULL,
            location_type       TEXT NOT NULL,
            region              TEXT NOT NULL,
            noaa_station_id     TEXT,
            coastline_bearing   NUMERIC(5, 2),
            description         TEXT,
            metadata            JSONB NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS live_cams (
            id                  SERIAL PRIMARY KEY,
            name                TEXT NOT NULL,
            location_id         INTEGER NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
            embed_type          TEXT NOT NULL,
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
            category            TEXT NOT NULL,
            metadata            JSONB NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS settings (
            id                  SERIAL PRIMARY KEY,
            key                 TEXT NOT NULL UNIQUE,
            value               JSONB NOT NULL,
            description         TEXT,
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

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
            type                TEXT NOT NULL,
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
            activity_type       TEXT NOT NULL,
            score               INTEGER,
            factors             JSONB NOT NULL DEFAULT '{}',
            summary_text        TEXT
        );

        CREATE TABLE IF NOT EXISTS scrape_logs (
            id                  SERIAL PRIMARY KEY,
            scraper_name        TEXT NOT NULL,
            started_at          TIMESTAMPTZ NOT NULL,
            finished_at         TIMESTAMPTZ,
            status              TEXT NOT NULL,
            records_created     INTEGER NOT NULL DEFAULT 0,
            records_updated     INTEGER NOT NULL DEFAULT 0,
            records_skipped     INTEGER NOT NULL DEFAULT 0,
            error_message       TEXT
        );
        """
    )

    # ── 002: Hypertables ────────────────────────────────────────────────
    op.execute(
        """
        SELECT create_hypertable('sightings', 'timestamp',
            chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
        SELECT create_hypertable('conditions', 'timestamp',
            chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
        SELECT create_hypertable('tides', 'timestamp',
            chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
        SELECT create_hypertable('activity_scores', 'timestamp',
            chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
        """
    )

    # ── 003: Indexes ────────────────────────────────────────────────────
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sightings_location_time
            ON sightings (location_id, timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_sightings_species_time
            ON sightings (species, timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_conditions_location_type_time
            ON conditions (location_id, condition_type, timestamp DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS conditions_dedup
            ON conditions (source, location_id, condition_type, timestamp);

        CREATE INDEX IF NOT EXISTS idx_tides_station_time
            ON tides (station_id, timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_activity_scores_location_type_time
            ON activity_scores (location_id, activity_type, timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_locations_slug
            ON locations (slug);
        CREATE INDEX IF NOT EXISTS idx_locations_region
            ON locations (region);

        CREATE INDEX IF NOT EXISTS idx_scrape_logs_scraper_time
            ON scrape_logs (scraper_name, started_at DESC);
        """
    )

    # ── 004: Constraints ────────────────────────────────────────────────
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'sightings_confidence_valid'
            ) THEN
                ALTER TABLE sightings
                    ADD CONSTRAINT sightings_confidence_valid
                    CHECK (confidence IN ('high', 'medium', 'low'));
            END IF;
        END $$;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'conditions_type_valid'
            ) THEN
                ALTER TABLE conditions
                    ADD CONSTRAINT conditions_type_valid
                    CHECK (condition_type IN (
                        'visibility', 'water_temp', 'air_temp',
                        'swell_height', 'swell_period', 'wind_speed', 'wind_direction'
                    ));
            END IF;
        END $$;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'tides_type_valid'
            ) THEN
                ALTER TABLE tides
                    ADD CONSTRAINT tides_type_valid
                    CHECK (type IN ('high', 'low', 'predicted'));
            END IF;
        END $$;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'activity_scores_score_range'
            ) THEN
                ALTER TABLE activity_scores
                    ADD CONSTRAINT activity_scores_score_range
                    CHECK (score IS NULL OR (score >= 0 AND score <= 100));
            END IF;
        END $$;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'activity_scores_type_valid'
            ) THEN
                ALTER TABLE activity_scores
                    ADD CONSTRAINT activity_scores_type_valid
                    CHECK (activity_type IN (
                        'snorkeling', 'whale_watching', 'body_surfing',
                        'scenic_drive', 'tidepooling'
                    ));
            END IF;
        END $$;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'locations_type_valid'
            ) THEN
                ALTER TABLE locations
                    ADD CONSTRAINT locations_type_valid
                    CHECK (location_type IN ('beach', 'tidepool', 'viewpoint', 'harbor', 'island'));
            END IF;
        END $$;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'locations_region_valid'
            ) THEN
                ALTER TABLE locations
                    ADD CONSTRAINT locations_region_valid
                    CHECK (region IN (
                        'south_coast', 'la_coast', 'ventura',
                        'central_coast', 'channel_islands'
                    ));
            END IF;
        END $$;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'scrape_logs_status_valid'
            ) THEN
                ALTER TABLE scrape_logs
                    ADD CONSTRAINT scrape_logs_status_valid
                    CHECK (status IN ('success', 'failure', 'partial'));
            END IF;
        END $$;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'seasonal_events_category_valid'
            ) THEN
                ALTER TABLE seasonal_events
                    ADD CONSTRAINT seasonal_events_category_valid
                    CHECK (category IN (
                        'migration', 'spawning', 'bloom', 'season',
                        'celestial', 'tidal', 'breeding', 'conditions'
                    ));
            END IF;
        END $$;
        """
    )

    # ── 005: Clear sun events ───────────────────────────────────────────
    op.execute("TRUNCATE TABLE sun_events;")

    # ── 006: Dive report constraint ─────────────────────────────────────
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'conditions_type_valid'
            ) THEN
                ALTER TABLE conditions DROP CONSTRAINT conditions_type_valid;
            END IF;

            ALTER TABLE conditions
                ADD CONSTRAINT conditions_type_valid
                CHECK (condition_type IN (
                    'visibility', 'water_temp', 'air_temp',
                    'swell', 'swell_height', 'swell_period',
                    'wind_speed', 'wind_direction', 'dive_report'
                ));
        END $$;
        """
    )

    # ── 007: Station refactor ───────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS noaa_stations (
            id SERIAL PRIMARY KEY,
            station_id VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            lat DECIMAL(10, 6) NOT NULL,
            lng DECIMAL(10, 6) NOT NULL,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        ALTER TABLE locations
            ADD COLUMN IF NOT EXISTS show_in_dropdown BOOLEAN DEFAULT true,
            ADD COLUMN IF NOT EXISTS nearest_noaa_station_id INTEGER
                REFERENCES noaa_stations(id);

        INSERT INTO noaa_stations (station_id, name, lat, lng, description) VALUES
            ('9410032', 'San Clemente Island', 32.8833, -118.3167, 'NOAA tide station'),
            ('9410068', 'San Nicolas Island', 33.2333, -119.5167, 'NOAA tide station'),
            ('9410079', 'Avalon, Catalina Island', 33.35, -118.3167, 'NOAA tide station'),
            ('9410120', 'Imperial Beach', 32.5833, -117.1333, 'NOAA tide station'),
            ('9410170', 'San Diego', 32.7167, -117.1667, 'NOAA tide station'),
            ('9410230', 'La Jolla', 32.8667, -117.25, 'NOAA tide station'),
            ('9410583', 'Newport Beach', 33.6, -117.8833, 'NOAA tide station'),
            ('9410660', 'Dana Point', 33.4667, -117.7, 'NOAA tide station'),
            ('9410680', 'Long Beach', 33.7667, -118.1833, 'NOAA tide station'),
            ('9410738', 'Redondo Beach', 33.85, -118.4, 'NOAA tide station'),
            ('9410777', 'El Segundo', 33.9167, -118.4333, 'NOAA tide station'),
            ('9410840', 'Santa Monica', 34.0167, -118.5, 'NOAA tide station'),
            ('9410962', 'Bechers Bay, Santa Rosa Island', 34.0, -120.0167, 'NOAA tide station'),
            ('9410971', 'Prisoners Harbor, Santa Cruz Island', 34.0167, -119.6833, 'NOAA tide station'),
            ('9411065', 'Port Hueneme', 34.1667, -119.4, 'NOAA tide station'),
            ('9411189', 'Ventura', 34.2667, -119.2833, 'NOAA tide station'),
            ('9411340', 'Santa Barbara', 34.4, -119.6833, 'NOAA tide station'),
            ('9412110', 'Port San Luis', 35.1689, -120.7542, 'NOAA tide station at Port San Luis'),
            ('9412553', 'San Simeon', 35.65, -121.1833, 'NOAA tide station')
        ON CONFLICT (station_id) DO NOTHING;

        UPDATE locations
        SET nearest_noaa_station_id = ns.id
        FROM noaa_stations ns
        WHERE locations.noaa_station_id = ns.station_id;

        UPDATE locations
        SET show_in_dropdown = false
        WHERE slug = 'port_san_luis';

        UPDATE locations
        SET show_in_dropdown = true
        WHERE noaa_station_id IS NOT NULL
          AND slug != 'port_san_luis';
        """
    )

    # ── 008: Sun events calculated ──────────────────────────────────────
    op.execute(
        """
        ALTER TABLE sun_events
            ADD COLUMN IF NOT EXISTS is_calculated BOOLEAN DEFAULT true;

        CREATE INDEX IF NOT EXISTS idx_sun_events_calculated
            ON sun_events(location_id, date)
            WHERE is_calculated = true;

        TRUNCATE TABLE sun_events;

        COMMENT ON TABLE sun_events IS
            'Sunrise, sunset, and golden hour events calculated mathematically per location';
        COMMENT ON COLUMN sun_events.is_calculated IS
            'True if calculated mathematically, false if from external API (legacy)';
        """
    )

    # ── 009: Sightings nullable location ────────────────────────────────
    op.execute("ALTER TABLE sightings ALTER COLUMN location_id DROP NOT NULL;")

    # ── 010: Sightings rekey ────────────────────────────────────────────
    op.execute(
        """
        TRUNCATE sightings;

        ALTER TABLE sightings ADD COLUMN IF NOT EXISTS sighting_date DATE NOT NULL;

        ALTER TABLE sightings DROP CONSTRAINT IF EXISTS sightings_pkey;
        ALTER TABLE sightings ADD PRIMARY KEY (id, timestamp);

        DROP INDEX IF EXISTS sightings_dedup_url;

        CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_biz
            ON sightings (source, location_id, sighting_date, species, timestamp)
            WHERE location_id IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS sightings_dedup_biz_noloc
            ON sightings (source, sighting_date, species, timestamp)
            WHERE location_id IS NULL;
        """
    )

    # ── Seed data ───────────────────────────────────────────────────────
    op.execute(
        """
        INSERT INTO locations
            (name, slug, lat, lng, location_type, region,
             noaa_station_id, coastline_bearing, description)
        VALUES
            ('Dana Point', 'dana_point', 33.4675, -117.6986, 'harbor',
             'south_coast', '9410660', NULL,
             'Harbor and marina in south Orange County'),
            ('La Jolla', 'la_jolla', 32.8667, -117.2500, 'beach',
             'la_coast', '9410230', NULL,
             'Coastal area in north San Diego with tide pools and sea caves'),
            ('Santa Monica', 'santa_monica', 34.0117, -118.4965, 'beach',
             'la_coast', '9410840', NULL,
             'Iconic beach in Los Angeles County'),
            ('Santa Barbara', 'santa_barbara', 34.4000, -119.6970, 'harbor',
             'ventura', '9411340', NULL,
             'Harbor city on the central coast'),
            ('Morro Bay', 'morro_bay', 35.3670, -120.8510, 'harbor',
             'central_coast', '9412110', NULL,
             'Coastal harbor with iconic Morro Rock'),
            ('Shaws Cove', 'shaws_cove', 33.5458, -117.8025, 'beach',
             'south_coast', '9410660', 250.0,
             'Classic Laguna snorkeling cove just south of Crescent Bay Point'),
            ('Zuma Beach', 'zuma_beach', 34.0208, -118.8289, 'beach',
             'la_coast', '9410840', 270.0,
             'Wide sandy beach in Malibu, popular for surfing and beach days'),
            ('San Diego', 'san_diego', 32.7156, -117.1767, 'harbor',
             'south_coast', '9410170', NULL,
             'San Diego Bay at Broadway Pier, southern terminus of Pacifica coverage'),
            ('Imperial Beach', 'imperial_beach', 32.5783, -117.1350, 'beach',
             'south_coast', '9410120', 190.0,
             'Southernmost beach on the California coast, popular for surfing and birdwatching'),
            ('Newport Beach', 'newport_beach', 33.6000, -117.9000, 'harbor',
             'south_coast', '9410583', 180.0,
             'Historic pier and harbor in central Orange County, prime surf spot'),
            ('Long Beach', 'long_beach', 33.7517, -118.2270, 'harbor',
             'la_coast', '9410680', 180.0,
             'Major port and harbor at Terminal Island, busy shipping channel'),
            ('Redondo Beach', 'redondo_beach', 33.8467, -118.3980, 'harbor',
             'la_coast', '9410738', 225.0,
             'King Harbor with marina and popular beach, good for diving and kayaking'),
            ('El Segundo', 'el_segundo', 33.9083, -118.4330, 'beach',
             'la_coast', '9410777', 250.0,
             'Beach and pier near LAX, consistent surf break'),
            ('Ventura', 'ventura', 34.2667, -119.2830, 'harbor',
             'ventura', '9411189', 200.0,
             'Harbor with access to Channel Islands, popular fishing and diving launch'),
            ('Port Hueneme', 'port_hueneme', 34.1483, -119.2030, 'harbor',
             'ventura', '9411065', 190.0,
             'Deep water port and naval base, good beach access'),
            ('Avalon, Catalina Island', 'avalon_catalina', 33.3450, -118.3250,
             'harbor', 'channel_islands', '9410079', NULL,
             'Main town on Santa Catalina Island, popular snorkeling and diving destination'),
            ('Prisoners Harbor, Santa Cruz Island', 'prisoners_harbor',
             34.0200, -119.6830, 'harbor', 'channel_islands', '9410971', NULL,
             'Remote harbor on Santa Cruz Island, excellent kayaking and hiking access'),
            ('Bechers Bay, Santa Rosa Island', 'bechers_bay', 34.0083, -120.0470,
             'harbor', 'channel_islands', '9410962', NULL,
             'Sheltered anchorage on Santa Rosa Island, pristine diving and snorkeling'),
            ('San Nicolas Island', 'san_nicolas_island', 33.2667, -119.4970,
             'island', 'channel_islands', '9410068', NULL,
             'Remote Navy-owned island, known for epic surf breaks and wildlife'),
            ('San Clemente Island', 'san_clemente_island', 33.0050, -118.5570,
             'island', 'channel_islands', '9410032', NULL,
             'Navy-owned island, legendary surf breaks like Trestles nearby'),
            ('San Simeon', 'san_simeon', 35.6417, -121.1880, 'harbor',
             'central_coast', '9412553', NULL,
             'Northern reach of Pacifica coverage, Hearst Castle nearby, elephant seal rookery'),
            ('Point Arguello', 'point_arguello', 34.5833, -120.6500, 'beach',
             'central_coast', NULL, 270.0,
             'Exposed headland with famous offshore kelp beds and rugged coastline'),
            ('Point Vicente', 'point_vicente', 33.7392, -118.4156, 'beach',
             'la_coast', '9410738', 225.0,
             'ACS-LA Gray Whale Census observation point on Palos Verdes Peninsula')
        ON CONFLICT (slug) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Not reversible. Baseline migration consolidates pre-Alembic schema."""
    pass
