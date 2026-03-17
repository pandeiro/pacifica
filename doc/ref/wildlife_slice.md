# Technical Reference: Slice C — Wildlife Sightings

## 1. Overview

Slice C builds the wildlife intelligence pipeline end-to-end: scrapers that pull from multiple
sources into the `sightings` hypertable, a REST API endpoint that serves the raw feed, and a live
`WildlifeIntelTile` with taxon filter pills.

**Design philosophy**: treat each source as a distinct signal type with different spatial
precision and update cadences. Store everything in the same `sightings` table with a `source`
tag; let the API and UI surface the data uniformly.

---

## 2. Data Sources

### 2.1 iNaturalist (Card 18)

- **Type**: REST API (public, no auth required for reads)
- **Base URL**: `https://api.inaturalist.org/v1/observations`
- **Query**: Bounding box covering the full SoCal coast, filtered to marine taxa.
  Run separate queries per taxon group and combine results:
  ```
  swlat=32.5&swlng=-120.7&nelat=34.8&nelng=-117.1
  quality_grade=research,needs_id
  order_by=created_at&order=desc
  per_page=200

  taxon_id=47115   # Marine Mammals
  taxon_id=47126   # Marine Fish
  taxon_id=3       # Birds (filter further to coastal species via place_id)
  ```
  Validate these taxon IDs against the live API before shipping.
- **Schedule**: Every 30 minutes (`"*/30 * * * *"`)
- **Deduplication**: The existing UNIQUE index on `(source, source_url, timestamp)` handles
  re-fetching the same observations.
- **Mapping to `sightings`**:

  | iNat field | `sightings` column |
  |---|---|
  | `observed_on` + `time_observed_at` | `timestamp` |
  | `geojson.coordinates` | Used to find nearest `location_id` via haversine |
  | `taxon.preferred_common_name` | `species` |
  | `1` (individual observation) | `count` (or `null` if unclear) |
  | `"inaturalist"` | `source` |
  | `https://www.inaturalist.org/observations/{id}` | `source_url` |
  | Full observation JSON (serialized) | `raw_text` |

- **Confidence mapping**:
  - `quality_grade=research` → `"high"`
  - `quality_grade=needs_id` → `"medium"`
  - `quality_grade=casual` → `"low"` (exclude from default API queries)
- **Location resolution**: Haversine against all rows in `locations`; assign to the nearest
  location within 30 miles. If nothing is within 30 miles, store `location_id=NULL` and put the
  iNat `place_guess` string in `metadata.place_guess`. The 30-mile radius may need tuning for
  Channel Islands observations — revisit after first data ingestion.

### 2.2 Harbor Breeze (Card 19)

- **Type**: HTML scrape — JS-rendered; plain HTTP returns a blank body
- **URL**: `https://www.harbor-breeze.com/whale-watching-reports/`
- **Approach**: Playwright headless browser to render the page and extract trip report content
- **Schedule**: Daily at 6:15 AM (`"15 6 * * *"`)
- **Fixed location**: Long Beach / San Pedro — map to the nearest `location_id`
- **Parsing**: Trip report content is likely narrative text. Attempt regex extraction first;
  fall back to LLM extraction (see §3) when the format is too variable.
- **Confidence**: `"high"` (professional whale-watch operators)

### 2.3 Davey's Locker (Card 20)

- **Type**: Plain HTML scrape (server-rendered, no JS required)
- **URL**: `https://daveyslocker.com/whale-dolphin-sightings/`
- **Format**: An HTML `<table>` with three columns: Date | Tours | Mammals Viewed
  - Example row: `3/14/2026 | 18 | 53 Gray Whales, 103 Bottlenose Dolphin, 350 Common Dolphin`
- **Parse strategy**: BeautifulSoup table extraction + regex on the "Mammals Viewed" cell:
  ```python
  pattern = r'(\d+)\s+([A-Za-z][A-Za-z\s\/\-]+?)(?=,\s*\d|$)'
  ```
  Yields `[(count, species), ...]` per row.
- **Schedule**: Daily at 6 AM (`"0 6 * * *"`)
- **Fixed location**: Newport Beach — map to the Newport Beach `location_id`
- **One `sightings` row per species per date**: A row with "53 Gray Whales, 103 Bottlenose
  Dolphin" produces two records sharing the same date (timestamped noon Pacific), species, and
  count.
- **Deduplication**: Check for an existing record matching `source + species + DATE(timestamp)`
  before inserting, in addition to the UNIQUE index on `(source, source_url, timestamp)`.
- **Confidence**: `"high"`

### 2.4 Dana Wharf (Card 21)

- **Type**: HTML scrape — daily log likely requires Playwright; annual totals are in static HTML
- **URL**: `https://danawharf.com/whale-watching/` (anchor: `#log`)
- **Schedule**: Daily at 6:30 AM (`"30 6 * * *"`)
- **Fixed location**: Dana Point harbor
- **Approach**:
  1. First implementation: use Playwright to render the page and inspect the `#log` section.
     Document what the rendered DOM contains before writing the full parser.
  2. Fallback if daily log is inaccessible: scrape annual aggregate totals as context only
     (store in `metadata.annual_totals`; do not insert to `sightings` without a date).
- **Confidence**: `"high"`

### 2.5 Island Packers (Card 22)

- **Type**: HTML scrape — JS-rendered, plain fetch returns an empty content section
- **URL**: `https://islandpackers.com/information/marine-mammal-sightings/`
- **Approach**: Playwright headless browser
- **Schedule**: Daily at 6:45 AM (`"45 6 * * *"`)
- **Fixed location**: Ventura Harbor as the primary location; store the specific island name
  (Anacapa, Santa Cruz, etc.) in `metadata.island` if mentioned in the report.
- **Value**: The only Slice C source covering the Channel Islands / Santa Barbara Channel
  corridor — high priority despite scraping complexity.
- **Confidence**: `"high"`

### 2.6 ACS-LA Gray Whale Census (Card 18b)

- **Type**: HTML scrape of a Facebook feed widget embedded in a WordPress page
- **URL**: `https://acs-la.org/todays-whale-count/`
- **Active season**: December – May (gray whale migration). Off-season: log a skip, exit cleanly.
- **Format**: Each post is freeform narrative followed by a structured plain-text block:
  ```
  GRAY WHALES TODAY:
  Southbound: N
  Northbound: N
  Cow/calves south: N
  Total: N

  GRAY WHALES TO DATE (since 1 Dec)
  Southbound: N
  ...
  ```
- **Approach**:
  1. Fetch the page HTML (plain HTTP — the Facebook widget content is in `.cff-text` divs).
  2. Apply regex to extract the structured key-value block (consistent format).
  3. Use LLM extraction (see §3) for the narrative portion and edge cases.
  4. Store the full post text in `raw_text`.
- **Schedule**: Daily at 9 AM (`"0 9 * * *"`) — posts typically appear mid-morning.
- **Fixed location**: Point Vicente / Palos Verdes (the ACS census observation point).
- **Insertion**: One row per direction per day — species strings `"Gray Whale (southbound)"` and
  `"Gray Whale (northbound)"`, with the respective count.
- **Confidence**: `"high"` (trained volunteer observers, standardized methodology since 1979)

### 2.7 Whale Alert API (Card 18c)

- **Type**: REST API (free registration required)
- **Env var**: `WHALE_ALERT_API_KEY` (add to `.env.example`; see registration note below)
- **Schedule**: Every hour (`"0 * * * *"`)
- **Coverage**: Full SoCal coast bounding box
- **Confidence**: `"high"` (vetted reporter accounts)
- **Registration**: Obtain a free API key at https://whale-alert.io/. Add the key to
  `.env.example` as `WHALE_ALERT_API_KEY=` with a comment pointing to the registration URL.
  Confirm the exact endpoint structure and auth method after registration before implementing.

### 2.8 Nitter / Twitter Accounts (Card 23)

- **Type**: JSON API via a self-hosted Nitter instance
- **Env var**: `NITTER_API_URL` — base URL only, e.g. `https://example.com`. Construct per-account
  URLs as `{NITTER_API_URL}/{username}`. **This URL must not be committed to version control.**
  Add `NITTER_API_URL=` to `.env.example` with a comment explaining what it is.
- **Accounts**: The specific accounts to monitor should be researched as part of Card 23 — the
  SoCal whale-watch and marine science Twitter community is not fully mapped yet. Candidates
  include the official accounts of whale-watch operators, NOAA Fisheries West Coast, and active
  citizen science reporters. Compile the final list during Card 23 implementation.
- **Keyword filter**: Before attempting LLM extraction, pre-filter tweets for relevance using
  keywords: `whale`, `dolphin`, `shark`, `porpoise`, `seal`, `sea lion`, `sighting`, `spotted`,
  `orca`, `humpback`, `gray whale`, `blue whale`.
- **LLM extraction**: For tweets passing the keyword filter, use the LLM service to extract
  `{species, count, location_hint}`. Store raw tweet text in `raw_text` regardless.
- **Schedule**: Every 2 hours (`"0 */2 * * *"`)
- **Confidence**: `"medium"` for general accounts; can be elevated to `"high"` for known
  professional operators if their account is confirmed.
- **Deduplication**: On `source_url` (the tweet permalink URL).

---

## 3. LLM Extraction Infrastructure (Card 23a)

This is a prerequisite for Cards 18b, 19, and 23. Build it first.

### `scraper/llm.py`

```python
class LLMClient:
    """
    Thin async wrapper around an OpenAI-compatible chat completions API.
    Defaults to local Ollama. Falls back to regex heuristics on failure.
    """
    def __init__(self, base_url: str | None = None, model: str | None = None):
        # base_url: reads OLLAMA_API_URL from env, default http://localhost:11434
        # model: reads LLM_MODEL from env, default llama3.2:1b
        ...

    async def extract(
        self,
        raw_text: str,
        schema: dict,
        fallback_fn: Callable[[str], dict] | None = None,
    ) -> dict:
        """
        POST to {base_url}/v1/chat/completions (OpenAI-compat format).
        On any failure: call fallback_fn(raw_text) if provided, else return {}.
        raw_text is always preserved by the caller in the sightings.raw_text column.
        """
        ...
```

### Env vars (add to `.env.example`)

```
# LLM extraction service (local Ollama, OpenAI-compatible)
# OLLAMA_API_URL=http://localhost:11434
# LLM_MODEL=llama3.2:1b
```

Note: `OLLAMA_API_URL` replaces the earlier `LLM_SERVICE_URL` stub in `.env.example`.

### Sightings extraction schema

```python
SIGHTINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "sightings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "species":        {"type": "string"},
                    "count":          {"type": "integer"},
                    "location_hint":  {"type": "string"},
                    "behavior":       {"type": "string"}
                },
                "required": ["species"]
            }
        }
    }
}
```

---

## 4. Sightings API Endpoint (Card 24)

### `GET /api/sightings`

Returns a broad, recent sightings feed intended for client-side filtering.

**Query params**:

| Param | Default | Description |
|---|---|---|
| `days` | `7` | How many days back to query |
| `limit` | `200` | Max records returned |
| `quality` | `high,medium` | Confidence levels to include (comma-separated) |

**Response shape**:
```json
{
  "sightings": [
    {
      "id": 42,
      "timestamp": "2026-03-16T10:30:00Z",
      "species": "Gray Whale",
      "taxon_group": "whale",
      "count": 3,
      "location_id": 5,
      "location_name": "Palos Verdes",
      "source": "acs_la",
      "source_url": "https://acs-la.org/...",
      "confidence": "high",
      "raw_text": "...",
      "metadata": {}
    }
  ],
  "total": 47,
  "days_requested": 7
}
```

**`taxon_group` derivation**: Computed server-side from `species` (not stored in DB):

| Match (case-insensitive substring) | `taxon_group` |
|---|---|
| "whale", "orca" | `"whale"` |
| "dolphin", "porpoise" | `"dolphin"` |
| "shark" | `"shark"` |
| "seal", "sea lion", "elephant seal", "pinniped" | `"pinniped"` |
| "pelican", "tern", "albatross", "cormorant", "shearwater", "murre", "puffin" | `"bird"` |
| anything else | `"other"` |

---

## 5. Wildlife Intel Frontend Tile (Card 25)

### Component: `WildlifeIntelTile`

**Props**: `locationId: number` (passed from Dashboard; used for potential future radius
filtering — not used for filtering in v1, which shows the full coast).

**Data fetching**: `useWildlife` hook → `GET /api/sightings?days=7&limit=200`. Polls every
15 minutes. No WebSocket in this slice (deferred).

**State**:
- `sightings: SightingRecord[]` — full fetched dataset
- `activeFilter: TaxonGroup | 'all'` — active filter pill

**Filter pills** (top of tile, horizontal scroll if needed):
`All` | `Whales` | `Dolphins` | `Sharks` | `Pinnipeds` | `Birds`

Client-side filter on `taxon_group`. "All" shows everything.

**List item layout**:
```
[emoji]  [Species Name]              [count badge if count > 1]
         [Location] · [recency] · [source badge]
```

**Recency display**:
- < 2 hours: styled accent (e.g. "Just now")
- < 24 hours: "Xh ago"
- < 48 hours: "Yesterday"
- Older: short date ("Mon Mar 14")

**Source badges**: Short colored label per source:

| Source key | Label | Color |
|---|---|---|
| `inaturalist` | iNat | green |
| `daveyslocker` | Davey's | blue |
| `dana_wharf` | Dana Wharf | blue |
| `acs_la` | ACS-LA | teal |
| `harbor_breeze` | H. Breeze | blue |
| `island_packers` | Is. Packers | blue |
| `whale_alert` | Whale Alert | orange |
| `twitter` | Twitter | gray |

**Empty state**: "No sightings reported in the last 7 days."

**HOT badge**: Removed entirely. No badging system in this slice.

### TypeScript changes (`types.ts`)

Replace the existing `Sighting` interface with:

```typescript
export type TaxonGroup = 'whale' | 'dolphin' | 'shark' | 'pinniped' | 'bird' | 'other';

export interface SightingRecord {
  id: number;
  timestamp: string;              // ISO 8601 UTC
  species: string;
  taxon_group: TaxonGroup;
  count: number | null;
  location_id: number | null;
  location_name: string | null;
  source: string;
  source_url: string | null;
  confidence: 'high' | 'medium' | 'low';
  raw_text: string | null;
  metadata: Record<string, unknown>;
}
```

The old `Sighting` interface (with `emoji`, `isHot`, string `time`) is deprecated and removed
when `WildlifeIntelTile` is wired to the real API.

### Emoji mapping

Build `frontend/src/utils/speciesEmoji.ts` — a lookup table from common name (lowercase) to
emoji. Fallback: `"🐾"`. Initial entries should cover at minimum:

- Gray Whale, Humpback Whale, Blue Whale, Fin Whale, Orca → `"🐋"`
- Bottlenose Dolphin, Common Dolphin, Pacific White-Sided Dolphin → `"🐬"`
- White Shark, Mako Shark, Blue Shark → `"🦈"`
- California Sea Lion, Harbor Seal, Elephant Seal → `"🦭"`
- Brown Pelican, Double-crested Cormorant → `"🦅"` / `"🐦"`
- Garibaldi, Mola Mola → `"🐠"` / `"🐟"`

---

## 6. Playwright in Docker

The scraper service Dockerfile will need Chromium + Playwright. Add to `scraper/Dockerfile`:

```dockerfile
RUN pip install playwright && playwright install --with-deps chromium
```

This adds approximately 200 MB to the scraper image. Acceptable tradeoff for Channel Islands
and operator coverage. The API image is unaffected.

---

## 7. Revised Card List

| Card | Title | Dependency | Notes |
|------|-------|------------|-------|
| **23a** | LLM Client Infrastructure | — | `scraper/llm.py`, Ollama integration, env vars |
| **18** | iNaturalist Scraper | — | REST API, 30-min schedule, haversine location resolution |
| **18b** | ACS-LA Gray Whale Census Scraper | 23a | HTML + Facebook widget, LLM extraction, seasonal |
| **18c** | Whale Alert Scraper | — | REST API, requires free API key registration |
| **19** | Harbor Breeze Scraper | 23a, Playwright | Headless render, narrative → LLM extraction |
| **20** | Davey's Locker Scraper | — | Plain HTML table, regex parse, daily |
| **21** | Dana Wharf Scraper | Playwright | Headless render, inspect DOM before writing parser |
| **22** | Island Packers Scraper | Playwright | Headless render, Channel Islands coverage |
| **23** | Nitter / Twitter Scrapers | 23a | Research accounts first; env-var URL, LLM extraction |
| **24** | Sightings API Endpoint | Data in DB | `GET /api/sightings`, taxon_group derivation |
| **25** | Wildlife Intel Frontend Tile | Card 24 | Filter pills, source badges, 15-min poll, type updates |

**Recommended implementation order**:
1. **Card 23a** — LLM infrastructure (unblocks 18b, 19, 23)
2. **Cards 18 + 20** in parallel — iNaturalist API + Davey's HTML (no dependencies, easy wins)
3. **Cards 19 + 21 + 22** — Playwright scrapers (add Playwright to Docker first)
4. **Cards 18b + 18c + 23** — LLM-dependent and API-key-dependent scrapers
5. **Card 24** — API endpoint (needs real data in DB)
6. **Card 25** — Frontend tile (needs endpoint)

---

## 8. Open Questions / Deferred Decisions

- **Dana Wharf daily log**: Confirm existence and structure with Playwright before writing the
  full parser — annual totals are confirmed accessible but the daily log is still unverified.
- **Whale Alert API**: Register for key and confirm endpoint structure and auth method before
  implementing Card 18c.
- **iNaturalist taxon IDs**: Validate `47115`, `47126`, and `3` against the live API before
  shipping Card 18.
- **Twitter accounts for Card 23**: Requires research into the SoCal whale-watch and marine
  science Twitter community. Compile the account list as the first step of Card 23.
- **iNaturalist location resolution radius**: 30 miles chosen as starting point; may need
  adjustment for Channel Islands observations which are far offshore from any seeded location.
- **Playwright image size**: ~200 MB added to scraper image — acceptable per project decision.
  Re-evaluate if cold-start times become an issue in CI/CD.
