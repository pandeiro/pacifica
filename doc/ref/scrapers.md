# Technical Reference: Scraper Infrastructure

## 1. BaseScraper Contract
All scrapers must inherit from `BaseScraper`. It handles the orchestration of:
- **`fetch()`**: Network I/O to retrieve raw data.
- **`process()`**: Transformation into structured database records.
- **`run()`**: Orchestration, error handling, and logging.

## 2. Shared Infrastructure
- **HTTP Client**: A shared `httpx.AsyncClient` with custom User-Agents and connection pooling.
- **Retry Logic**: Exponential backoff (2s, 4s, 8s) for network errors, 429s, and 5xx responses using `tenacity`.
- **Deduplication**: Handled at the database level via `ON CONFLICT` upserts.

## 3. LLM Extraction
For semi-structured sources (blog posts, trip logs), scrapers use a local LLM service for extraction.
- **Schema-Driven**: Scrapers provide a JSON schema for the expected fields.
- **Fallback Heuristics**: Every LLM-enabled scraper must provide a regex-based fallback function for when the service is unavailable.
- **Raw Text Preservation**: Original text is always stored in the `raw_text` column for future reprocessing.

## 4. Monitoring & Freshness
- Scraper status is logged to `scrape_logs`.
- **Stale Detection**: A scraper is considered "stale" if it hasn't run successfully within 2x its expected interval.
- **Alerts**: Notifications are sent via Telegram when a scraper transitions to a stale state.
