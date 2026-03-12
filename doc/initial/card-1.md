# Card 01 — Scraper Base Class & Infrastructure

## Goal
Define and implement the `BaseScraper` abstract class, shared data contracts, retry logic, deduplication, LLM extraction helper, and scrape logging. All individual scrapers inherit from this. Nothing else should be built until this card is done.

---

## Deliverables

1. `scrapers/base.py` — `BaseScraper` abstract class + all supporting types
2. `scrapers/db.py` — upsert helpers for each record type
3. `scrapers/llm.py` — LLM extraction client with fallback
4. `scrapers/http.py` — shared HTTP client with retry logic
5. Database migration — unique constraints and indexes required for upsert

---

## Data Contracts

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class SightingRecord:
    location_id: int
    species: str
    timestamp: datetime
    source: str
    source_url: str | None = None       # used as primary dedup key when present
    count: int | None = None
    confidence: str = "medium"          # "high" | "medium" | "low"
    raw_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ConditionRecord:
    location_id: int
    condition_type: str                 # "visibility" | "water_temp" | "swell_height" | etc.
    value: float
    unit: str
    timestamp: datetime
    source: str
    source_url: str | None = None
    raw_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ScrapeResult:
    scraper_name: str
    started_at: datetime
    finished_at: datetime
    status: str                         # "success" | "failure" | "partial"
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    error_message: str | None = None
```

---

## BaseScraper Contract

```python
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    name: str                           # must be set on subclass, matches scrape_logs.scraper_name
    schedule: str                       # cron expression, e.g. "0 */6 * * *"
    source_url_base: str | None = None  # informational

    # Injected at construction time
    def __init__(self, db, http_client, llm_client):
        self.db = db
        self.http = http_client
        self.llm = llm_client

    @abstractmethod
    async def fetch(self) -> Any:
        """Fetch raw data from source. Should raise on unrecoverable error."""
        ...

    @abstractmethod
    async def process(self, raw_data: Any) -> list[SightingRecord | ConditionRecord]:
        """
        Transform raw data into records. May call self.llm.extract() for
        natural language sources. Should not write to DB — return records only.
        """
        ...

    async def run(self) -> ScrapeResult:
        """
        Orchestrates fetch → process → upsert → log.
        Called by the scheduler. Do not override in subclasses.
        """
        ...  # implemented in base class, see Orchestration section below
```

**Rule**: Subclasses implement `fetch()` and `process()` only. All retry, dedup, logging, and error handling lives in `run()` on the base class.

---

## HTTP Client & Retry Logic

Wrap `httpx.AsyncClient` in a shared factory. Configure once, inject into all scrapers.

**Retry policy** (applies to `fetch()` only, not `process()`):
- Maximum 3 attempts
- Exponential backoff: 2s, 4s, 8s (with ±10% jitter)
- Retry on: network errors (`httpx.NetworkError`, `httpx.TimeoutException`), HTTP 429, HTTP 5xx
- Do NOT retry on: HTTP 4xx (except 429), parsing errors, LLM errors
- On 429: respect `Retry-After` header if present, otherwise use backoff schedule

```python
# scrapers/http.py
async def make_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": "Pacific/1.0 (coastal dashboard; contact@yourdomain.com)"},
        follow_redirects=True,
    )
```

Retry logic should be implemented with `tenacity`:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception(is_retryable),
)
async def fetch_with_retry(self) -> Any:
    return await self.fetch()
```

Where `is_retryable(exc)` returns `True` for network errors, 429, and 5xx.

---

## LLM Extraction Client

```python
# scrapers/llm.py

class LLMClient:
    def __init__(self, service_url: str | None):
        self.available = service_url is not None
        self.url = service_url

    async def extract(
        self,
        raw_text: str,
        schema: dict,           # JSON schema describing expected output fields
        fallback_fn: Callable[[str], dict] | None = None,
    ) -> dict:
        """
        Call LLM service to extract structured data from raw_text.
        If service unavailable or call fails, calls fallback_fn(raw_text) if provided.
        If no fallback, returns empty dict — caller must handle partial data gracefully.
        """
        if not self.available:
            return fallback_fn(raw_text) if fallback_fn else {}
        try:
            # POST to LLM_SERVICE_URL/v1/extract
            # Body: {"text": raw_text, "schema": schema}
            # Response: {"fields": {...}}
            ...
        except Exception:
            logger.warning(f"LLM extraction failed, using fallback")
            return fallback_fn(raw_text) if fallback_fn else {}
```

Each scraper that uses LLM extraction must also provide a `fallback_fn` — a simple regex/pattern function that extracts what it can. The fallback returning an empty or partial dict is acceptable; the record still gets written with whatever fields were populated plus `raw_text` preserved for later reprocessing.

---

## Deduplication & Upsert

### Sightings

**Primary key** (used when `source_url` is present):
```sql
UNIQUE (source, source_url)
```

**Fallback key** (used when `source_url` is NULL):
```sql
UNIQUE (source, location_id, species, date_trunc('hour', timestamp))
```

Implement as two partial unique indexes:
```sql
CREATE UNIQUE INDEX sightings_dedup_url
  ON sightings (source, source_url)
  WHERE source_url IS NOT NULL;

CREATE UNIQUE INDEX sightings_dedup_fallback
  ON sightings (source, location_id, species, date_trunc('hour', timestamp))
  WHERE source_url IS NULL;
```

**Upsert behavior** — "richer" means non-null beats null, higher count beats lower:
```sql
INSERT INTO sightings (...) VALUES (...)
ON CONFLICT DO UPDATE SET
  count = GREATEST(EXCLUDED.count, sightings.count),
  confidence = CASE WHEN EXCLUDED.confidence = 'high' THEN 'high'
                    WHEN sightings.confidence = 'high' THEN 'high'
                    ELSE EXCLUDED.confidence END,
  raw_text = COALESCE(sightings.raw_text, EXCLUDED.raw_text),
  metadata = sightings.metadata || EXCLUDED.metadata  -- merge, existing keys win
```

### Conditions

Conditions are time-series — same source + location + type + timestamp is a dupe:
```sql
CREATE UNIQUE INDEX conditions_dedup
  ON conditions (source, location_id, condition_type, timestamp);
```

Upsert: replace entirely on conflict (newer scrape wins).

---

## Orchestration (`run()`)

```python
async def run(self) -> ScrapeResult:
    started_at = datetime.utcnow()
    result = ScrapeResult(scraper_name=self.name, started_at=started_at, ...)

    try:
        raw_data = await self.fetch_with_retry()   # retries up to 3x
    except Exception as e:
        result.status = "failure"
        result.error_message = str(e)
        result.finished_at = datetime.utcnow()
        await self.db.log_scrape(result)
        logger.error(f"[{self.name}] fetch failed: {e}")
        return result                               # fail fast, don't proceed to process

    try:
        records = await self.process(raw_data)
    except Exception as e:
        result.status = "failure"
        result.error_message = f"process() failed: {e}"
        result.finished_at = datetime.utcnow()
        await self.db.log_scrape(result)
        logger.error(f"[{self.name}] process failed: {e}")
        return result

    # Upsert all records; count created vs updated
    for record in records:
        outcome = await self.db.upsert(record)     # returns "created" | "updated" | "skipped"
        if outcome == "created": result.records_created += 1
        elif outcome == "updated": result.records_updated += 1
        else: result.records_skipped += 1

    result.status = "success" if not result.error_message else "partial"
    result.finished_at = datetime.utcnow()
    await self.db.log_scrape(result)
    logger.info(f"[{self.name}] done: {result.records_created} created, {result.records_updated} updated")
    return result
```

---

## Logging

Use Python's `structlog` for structured logging throughout the scraper worker.

Every log line must include:
- `scraper`: scraper name
- `level`: standard log level
- `event`: human-readable message

Output format: JSON in production, pretty-printed in development (controlled by `LOG_FORMAT=json|pretty` env var).

```python
import structlog
logger = structlog.get_logger().bind(scraper=self.name)
logger.info("fetch complete", records=len(raw_data))
logger.warning("llm extraction failed, using fallback", url=url)
logger.error("fetch failed after retries", error=str(e))
```

Do not use `print()` anywhere in scraper code.

---

## Scrape Logging & Stale Detection

Write a row to `scrape_logs` at the end of every `run()`, success or failure.

A scraper is **stale** when: `now() - last_successful_run > 2 * schedule_interval`

The `schedule_interval` for each scraper is derived from its cron expression and stored in a `scrapers` registry dict at startup:

```python
SCRAPER_REGISTRY = {
    "noaa_tides":        {"class": NOAATidesScraper,       "interval_minutes": 1440},
    "harbor_breeze":     {"class": HarborBreezeScraper,    "interval_minutes": 720},
    "south_coast_divers":{"class": SouthCoastDiversScraper,"interval_minutes": 720},
    # etc.
}
```

The `/api/health/scrapers` endpoint queries `scrape_logs` and uses this registry to compute `stale: bool` per scraper.

**Alerting**: The health monitor (runs every 5 minutes) checks for newly stale scrapers and sends a Telegram notification on first detection. It does not re-alert until the scraper recovers and goes stale again.

---

## Constraints & Validation

Enforce in the DB, not just in Python:

```sql
ALTER TABLE sightings ADD CONSTRAINT confidence_valid
  CHECK (confidence IN ('high', 'medium', 'low'));

ALTER TABLE activity_scores ADD CONSTRAINT score_range
  CHECK (score >= 0 AND score <= 100);

ALTER TABLE conditions ADD CONSTRAINT condition_type_valid
  CHECK (condition_type IN (
    'visibility', 'water_temp', 'air_temp',
    'swell_height', 'swell_period', 'wind_speed', 'wind_direction'
  ));
```

---

## What's Out of Scope for This Card

- Any individual scraper implementation (those come after this card is merged)
- LLM service itself (separate repo)
- Scheduler wiring (APScheduler setup is a separate card)

---

## Acceptance Criteria

- [ ] `BaseScraper` is abstract; instantiating it directly raises `TypeError`
- [ ] A minimal test scraper subclass (returning fixture data) passes through `run()` and writes to `scrape_logs`
- [ ] A failing `fetch()` writes a `failure` row to `scrape_logs` and does not call `process()`
- [ ] Upserting the same sighting twice results in one row, not two
- [ ] Upserting a sighting with a higher `count` updates the existing row
- [ ] LLM unavailable → fallback is called → record still written with partial data
- [ ] All log output is valid JSON when `LOG_FORMAT=json`
- [ ] pytest coverage for: retry logic, both dedup paths, upsert merge behavior, LLM fallback path
