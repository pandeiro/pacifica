# Card 04 — Data Retention & TTL

## Goal
Configure TimescaleDB automatic retention policies for all four time-series hypertables. No custom jobs, no cron — TimescaleDB's background worker handles deletion automatically. This card is a single migration file plus verification queries.

---

## Deliverables

1. `db/migrations/005_retention_policies.sql` — retention policy setup for all hypertables
2. `db/migrations/006_compression_policies.sql` — compression policy setup (see below)
3. Verification queries documented for confirming policies are active post-deploy

---

## Retention Policy: Per Table

| Table | Retention | Rationale |
|---|---|---|
| `sightings` | 2 years | Historical sighting patterns useful for seasonal comparisons |
| `conditions` | 2 years | Year-over-year condition comparisons (e.g. "how does this Aug compare to last Aug") |
| `tides` | 2 years | Tide pattern reference; predictions can be re-fetched but history is cheap to keep |
| `activity_scores` | 30 days | Fully derived — regenerated from source data on demand |

---

## Migration: Retention Policies

```sql
-- 005_retention_policies.sql

-- Sightings: 2 years
SELECT add_retention_policy(
    'sightings',
    INTERVAL '2 years',
    if_not_exists => TRUE
);

-- Conditions: 2 years
SELECT add_retention_policy(
    'conditions',
    INTERVAL '2 years',
    if_not_exists => TRUE
);

-- Tides: 2 years
SELECT add_retention_policy(
    'tides',
    INTERVAL '2 years',
    if_not_exists => TRUE
);

-- Activity scores: 30 days
SELECT add_retention_policy(
    'activity_scores',
    INTERVAL '30 days',
    if_not_exists => TRUE
);
```

TimescaleDB's retention background worker runs approximately every 24 hours. Deletion is by whole chunk — chunks are dropped, not row-by-row deletes. This is fast and does not cause table bloat.

**Chunk interval**: All four hypertables should use a 7-day chunk interval, set at hypertable creation time:
```sql
SELECT create_hypertable('sightings', 'timestamp', chunk_time_interval => INTERVAL '7 days');
-- repeat for conditions, tides, activity_scores
```

This means retention granularity is ±7 days — a row from 2 years and 3 days ago will be deleted in the next chunk drop after the 2-year mark. This is acceptable.

---

## Migration: Compression Policies

Data older than 30 days is unlikely to be queried in real time. Compress it to reduce disk footprint on the 80GB SSD.

```sql
-- 006_compression_policies.sql

-- Enable compression on each hypertable
ALTER TABLE sightings SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'location_id'
);

ALTER TABLE conditions SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'location_id, condition_type'
);

ALTER TABLE tides SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'station_id'
);

ALTER TABLE activity_scores SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'location_id, activity_type'
);

-- Compress chunks older than 30 days
SELECT add_compression_policy('sightings',      INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_compression_policy('conditions',     INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_compression_policy('tides',          INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_compression_policy('activity_scores',INTERVAL '7 days',  if_not_exists => TRUE);
```

`activity_scores` compresses after 7 days (not 30) since it's ephemeral derived data — compressing early saves space without any query performance cost given it's rarely accessed after a week.

**Expected compression ratio**: TimescaleDB typically achieves 90–95% size reduction on time-series data. Conditions table (the highest volume) at ~175k rows/year should compress from ~50MB/year to ~3–5MB/year.

---

## Disk Budget Estimate

Based on 80GB SSD with ~1.5–2GB headroom target:

| Table | Raw rows/year (est.) | Compressed size/year (est.) | 2-year total |
|---|---|---|---|
| `sightings` | ~15k | ~2MB | ~4MB |
| `conditions` | ~175k | ~4MB | ~8MB |
| `tides` | ~50k | ~1MB | ~2MB |
| `activity_scores` | ~50k (30-day rolling) | negligible | ~1MB |
| **Total time-series** | | | **~15MB** |

Time-series data is not a disk risk on this hardware. The main disk consumers will be `raw_text` in sightings (uncompressed TOAST storage) and PostgreSQL WAL. Neither requires action for MVP.

---

## Verification Queries

Run these after migration to confirm policies are registered and active:

```sql
-- Confirm retention policies
SELECT hypertable_name, older_than, schedule_interval
FROM timescaledb_information.jobs j
JOIN timescaledb_information.job_stats js USING (job_id)
WHERE proc_name = 'policy_retention'
ORDER BY hypertable_name;

-- Confirm compression policies
SELECT hypertable_name, older_than, schedule_interval
FROM timescaledb_information.jobs j
JOIN timescaledb_information.job_stats js USING (job_id)
WHERE proc_name = 'policy_compression'
ORDER BY hypertable_name;

-- Check existing chunks and their sizes
SELECT hypertable_name,
       chunk_name,
       range_start,
       range_end,
       pg_size_pretty(total_bytes) AS total_size,
       is_compressed
FROM timescaledb_information.chunks
ORDER BY hypertable_name, range_start DESC;
```

Expected output after policies are set: 4 rows in retention query, 4 rows in compression query.

---

## Migration Ordering

This card depends on the hypertables already existing. Migration order:

```
001_initial_schema.sql          ← locations, live_cams, etc.
002_hypertables.sql             ← create_hypertable() calls
003_indexes.sql                 ← spatial + time indexes
004_constraints.sql             ← check constraints (from Card 01)
005_retention_policies.sql      ← this card
006_compression_policies.sql    ← this card
```

---

## What's Out of Scope for This Card

- Postgres backups (deferred to post-MVP)
- `scrape_logs` retention (non-hypertable, negligible size — no policy needed)
- `sun_events` and `seasonal_events` retention (static/semi-static tables, no TTL needed)

---

## Acceptance Criteria

- [ ] All four retention policies visible in `timescaledb_information.jobs`
- [ ] All four compression policies visible in `timescaledb_information.jobs`
- [ ] Manually inserting a row with `timestamp = now() - INTERVAL '3 years'` and running `SELECT run_job(<retention_job_id>)` results in that row being deleted
- [ ] Chunks older than 30 days are marked `is_compressed = true` after compression job runs
- [ ] Migration is idempotent — running it twice does not error (enforced by `if_not_exists => TRUE`)
- [ ] Verification queries return expected row counts with no nulls in `older_than`
