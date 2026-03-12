# Technical Reference: Database

## 1. Schema Overview
Pacific uses PostgreSQL 16 with the TimescaleDB extension for time-series data.

### Core Tables
- **`locations`**: Static coastal locations (lat/lng, region, type).
- **`sightings`**: (Hypertable) Marine life sighting events.
- **`conditions`**: (Hypertable) Water temp, visibility, swell, wind.
- **`tides`**: (Hypertable) High/low tide predictions and observations.
- **`activity_scores`**: (Hypertable) Calculated 0–100 scores for various activities.
- **`sun_events`**: Sunrise, sunset, and golden hour times.
- **`live_cams`**: Registry of video feed embeds.
- **`scrape_logs`**: Audit trail of all scraper executions.

## 2. TimescaleDB Configuration
Time-series tables are partitioned into 7-day chunks.

### Retention Policies
- **`sightings`**: 2 years.
- **`conditions`**: 2 years.
- **`tides`**: 2 years.
- **`activity_scores`**: 30 days (fully derived data).

### Compression Policies
Data older than 30 days (7 days for `activity_scores`) is automatically compressed to save disk space. Segmented by `location_id`.

## 3. Data Integrity & Constraints
- **Sightings**: Unique constraint on `(source, source_url)` for deduplication.
- **Conditions**: Unique constraint on `(source, location_id, condition_type, timestamp)`.
- **Activity Scores**: Checked to stay within 0–100 range.
- **Regions**: Limited to `south_coast`, `la_coast`, `ventura`, `central_coast`, `channel_islands`.
