# Card 07 — NOAA Tides Scraper

> **Slice**: A — Tides
> **Depends on**: Cards 01 (base class), 05 (schema), 06 (testing infra)
> **Blocks**: Card 08 (tides API endpoint)
> **Estimated complexity**: Low — structured API, no LLM extraction needed

---

## Goal

Implement the NOAA tides scraper as the first concrete `BaseScraper` subclass. Fetches tide predictions and verified water level observations from the NOAA CO-OPS API, writes to the `tides` hypertable. This scraper is the simplest possible real implementation — use it to validate that the base class infrastructure from Card 01 works end-to-end before building more complex scrapers.

---

## Deliverables

```
scrapers/
└── noaa_tides.py

tests/
├── scrapers/
│   └── test_noaa_tides.py
└── fixtures/
    ├── noaa_tides_predictions.yaml      ← VCR cassette
    └── noaa_tides_observations.yaml     ← VCR cassette
```

---

## NOAA CO-OPS API Reference

**Base URL**: `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`

### Endpoint: Tide Predictions

```
GET /api/prod/datagetter
  ?product=predictions
  &station={station_id}
  &begin_date={YYYYMMDD}
  &end_date={YYYYMMDD}
  &datum=MLLW
  &time_zone=LST/LDT
  &interval=hilo          ← returns only high/low events, not hourly
  &units=english          ← feet
  &application=pacific_dashboard
  &format=json
```

### Endpoint: Water Level Observations

```
GET /api/prod/datagetter
  ?product=water_level
  &station={station_id}
  &begin_date={YYYYMMDD}
  &end_date={YYYYMMDD}
  &datum=MLLW
  &time_zone=LST/LDT
  &interval=h             ← hourly
  &units=english
  &application=pacific_dashboard
  &format=json
```

### Response shape (predictions)

```json
{
  "predictions": [
    { "t": "2025-03-01 06:23", "v": "-0.234", "type": "L" },
    { "t": "2025-03-01 12:45", "v": "5.123", "type": "H" }
  ]
}
```

`type`: `"H"` = high, `"L"` = low. Map to `"high"` / `"low"` in the DB.

---

## Implementation

```python
# scrapers/noaa_tides.py

from datetime import datetime, timedelta
from scrapers.base import BaseScraper, ScrapeResult
from models import TideRecord

STATIONS = {
    "9410660": "dana_point",
    "9410230": "la_jolla",
    "9410840": "santa_monica",
    "9411340": "santa_barbara",
    "9412110": "morro_bay",
}

class NOAATidesScraper(BaseScraper):
    name = "noaa_tides"
    schedule = "0 2 * * *"    # daily at 2am — fetch next 7 days of predictions

    async def fetch(self) -> dict:
        """
        Returns dict keyed by station_id, value is list of raw prediction dicts.
        Fetches today + 7 days forward for predictions.
        Fetches yesterday for verified observations (they lag by ~1 day).
        """
        today = datetime.utcnow().date()
        results = {}

        for station_id in STATIONS:
            predictions = await self._fetch_predictions(station_id, today, today + timedelta(days=7))
            observations = await self._fetch_observations(station_id, today - timedelta(days=1), today)
            results[station_id] = {
                "predictions": predictions,
                "observations": observations,
            }

        return results

    async def _fetch_predictions(self, station_id: str, start, end) -> list:
        url = (
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
            f"?product=predictions&station={station_id}"
            f"&begin_date={start.strftime('%Y%m%d')}&end_date={end.strftime('%Y%m%d')}"
            "&datum=MLLW&time_zone=LST/LDT&interval=hilo&units=english"
            "&application=pacific_dashboard&format=json"
        )
        response = await self.http.get(url)
        response.raise_for_status()
        return response.json().get("predictions", [])

    async def _fetch_observations(self, station_id: str, start, end) -> list:
        url = (
            "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
            f"?product=water_level&station={station_id}"
            f"&begin_date={start.strftime('%Y%m%d')}&end_date={end.strftime('%Y%m%d')}"
            "&datum=MLLW&time_zone=LST/LDT&interval=h&units=english"
            "&application=pacific_dashboard&format=json"
        )
        response = await self.http.get(url)
        response.raise_for_status()
        return response.json().get("data", [])    # observations key is "data" not "predictions"

    async def process(self, raw_data: dict) -> list[TideRecord]:
        records = []

        for station_id, data in raw_data.items():
            for p in data["predictions"]:
                records.append(TideRecord(
                    timestamp=datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc),
                    station_id=station_id,
                    type="high" if p["type"] == "H" else "low",
                    height_ft=float(p["v"]),
                    source="noaa_predictions",
                ))

            for o in data["observations"]:
                # Observations have no type — they're continuous readings, skip for now
                # (Hourly observations are for water temp scraper, not tide events)
                pass

        return records
```

### Notes

- NOAA does not require an API key for public data. No auth headers needed.
- Add `await asyncio.sleep(1)` between station requests as a courtesy (not rate-limited, but polite).
- Observations are fetched but not processed here — the NOAA water temp scraper (Card 11) handles those. The fetch is included to validate the endpoint works.

---

## STATIONS Registry

The `STATIONS` dict maps NOAA station IDs to location slugs. These must be cross-referenced against the `locations` seed data (Card 26) and the `noaa_station_id` field on the `locations` table. The scraper uses `station_id` directly in the `tides` table — the API endpoint (Card 08) joins to `locations` via `noaa_station_id`.

---

## Schedule

`"0 2 * * *"` — daily at 2am. Predictions are stable and don't change, so fetching daily is sufficient. The 7-day lookahead means the tides tile always has data even if the scraper misses a day.

---

## Tests

```python
# tests/scrapers/test_noaa_tides.py

@pytest.mark.scraper
@pytest.mark.vcr("noaa_tides_predictions.yaml")
async def test_noaa_tides_creates_records(db, dana_point):
    scraper = NOAATidesScraper(db=db, http_client=make_test_http_client(), llm_client=None)
    result = await scraper.run()

    assert result.status == "success"
    assert result.records_created > 0

    tides = await db.scalars(select(Tide).where(Tide.station_id == "9410660"))
    assert len(tides.all()) > 0

@pytest.mark.scraper
@pytest.mark.vcr("noaa_tides_predictions.yaml")
async def test_noaa_tides_upsert_is_idempotent(db, dana_point):
    scraper = NOAATidesScraper(db=db, http_client=make_test_http_client(), llm_client=None)
    await scraper.run()
    result = await scraper.run()    # run twice

    assert result.records_created == 0     # second run: all dupes
    assert result.records_updated > 0

@pytest.mark.scraper
async def test_noaa_tides_logs_scrape_run(db):
    scraper = NOAATidesScraper(db=db, http_client=make_test_http_client(), llm_client=None)
    await scraper.run()

    log = await db.scalar(
        select(ScrapeLog).where(ScrapeLog.scraper_name == "noaa_tides").limit(1)
    )
    assert log is not None
    assert log.status == "success"
    assert log.finished_at is not None
```

---

## Acceptance Criteria

- [ ] Scraper fetches predictions for all 5 stations in a single `run()` call
- [ ] Records written to `tides` table with correct `station_id`, `type`, `height_ft`, `timestamp`
- [ ] `type` is `"high"` or `"low"` (never `"H"` or `"L"`)
- [ ] Running the scraper twice produces no duplicate rows
- [ ] Second run correctly increments `records_updated`, not `records_created`
- [ ] A failed NOAA API request (simulated via VCR returning 500) writes a `failure` row to `scrape_logs`
- [ ] Scraper can be run directly: `python -m scrapers.noaa_tides` exits 0

---
---

# Card 08 — Tides API Endpoint

> **Slice**: A — Tides
> **Depends on**: Cards 05 (schema), 06 (testing infra), 07 (tides scraper)
> **Blocks**: Card 09 (tides frontend tile)
> **Estimated complexity**: Low

---

## Goal

Implement the REST endpoint that serves tide data to the frontend tides tile, and wire up the WebSocket broadcast so the tile updates when the scraper runs. Also serves sun events data (Card 10 adds the sun events scraper; this endpoint serves them both).

---

## Deliverables

```
api/
├── routes/
│   └── tides.py
└── schemas/
    └── tides.py             ← Pydantic response models

tests/
└── api/
    └── test_tides_endpoint.py
```

---

## Endpoints

### `GET /api/tides`

Returns tide events for a given NOAA station over a time window.

**Query parameters**:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `station_id` | string | required | NOAA station ID |
| `hours` | integer | `48` | Hours of data to return (forward from now) |

**Response**:

```json
{
  "station_id": "9410660",
  "location_name": "Dana Point",
  "events": [
    {
      "timestamp": "2025-03-01T06:23:00Z",
      "type": "low",
      "height_ft": -0.234
    },
    {
      "timestamp": "2025-03-01T12:45:00Z",
      "type": "high",
      "height_ft": 5.123
    }
  ],
  "next_low": {
    "timestamp": "2025-03-01T06:23:00Z",
    "height_ft": -0.234
  },
  "next_high": {
    "timestamp": "2025-03-01T12:45:00Z",
    "height_ft": 5.123
  },
  "current_height_ft": 2.1,       ← interpolated from surrounding events; null if unavailable
  "data_through": "2025-03-03T00:00:00Z"
}
```

**Error responses**:

| Status | Condition |
|---|---|
| `400` | Missing `station_id` |
| `404` | No data found for station in requested window |
| `200` with `events: []` | Station known but no upcoming events in window |

---

### `GET /api/sun`

Returns sun events for a given location and date.

**Query parameters**:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `location_id` | integer | required | Location ID from `locations` table |
| `date` | string (YYYY-MM-DD) | today | Date to fetch events for |

**Response**:

```json
{
  "location_id": 7,
  "location_name": "Dana Point",
  "date": "2025-03-01",
  "sunrise": "2025-03-01T06:42:00Z",
  "sunset": "2025-03-01T17:58:00Z",
  "golden_hour_morning_start": "2025-03-01T06:12:00Z",
  "golden_hour_morning_end": "2025-03-01T06:42:00Z",
  "golden_hour_evening_start": "2025-03-01T17:28:00Z",
  "golden_hour_evening_end": "2025-03-01T17:58:00Z"
}
```

**Error responses**:

| Status | Condition |
|---|---|
| `400` | Missing `location_id` |
| `404` | No sun events for this location + date (scraper hasn't run yet) |

---

## WebSocket Broadcast

After the NOAA tides scraper writes new records, it POSTs to `/internal/broadcast`:

```json
{
  "type": "conditions.upserted",
  "timestamp": "...",
  "payload": {
    "scraper": "noaa_tides",
    "records": []     ← tides are served via REST, not pushed; payload intentionally empty
  }
}
```

The frontend tides tile re-fetches via REST on receiving any `conditions.upserted` message from `noaa_tides`. This keeps the broadcast simple — no need to serialize the full tide dataset into the WebSocket message.

---

## Pydantic Models

```python
# api/schemas/tides.py

from pydantic import BaseModel
from datetime import datetime

class TideEvent(BaseModel):
    timestamp: datetime
    type: str           # "high" | "low"
    height_ft: float

class TidesResponse(BaseModel):
    station_id: str
    location_name: str
    events: list[TideEvent]
    next_low: TideEvent | None
    next_high: TideEvent | None
    current_height_ft: float | None
    data_through: datetime

class SunEventsResponse(BaseModel):
    location_id: int
    location_name: str
    date: str
    sunrise: datetime
    sunset: datetime
    golden_hour_morning_start: datetime
    golden_hour_morning_end: datetime
    golden_hour_evening_start: datetime
    golden_hour_evening_end: datetime
```

---

## Current Height Interpolation

`current_height_ft` is not stored directly — it's interpolated from the surrounding high/low events:

```python
def interpolate_current_height(events: list[TideEvent], now: datetime) -> float | None:
    """
    Find the tide events immediately before and after now.
    Linear interpolation between them.
    Returns None if surrounding events are not available.
    """
    before = [e for e in events if e.timestamp <= now]
    after = [e for e in events if e.timestamp > now]

    if not before or not after:
        return None

    e0, e1 = before[-1], after[0]
    t = (now - e0.timestamp) / (e1.timestamp - e0.timestamp)
    return round(e0.height_ft + t * (e1.height_ft - e0.height_ft), 2)
```

Note: real tidal curves are sinusoidal, not linear. Linear interpolation is a reasonable approximation for display purposes and does not need to be more precise.

---

## Tests

```python
# tests/api/test_tides_endpoint.py

@pytest.mark.integration
async def test_get_tides_returns_events(api_client, db, seed_tides):
    response = await api_client.get("/api/tides?station_id=9410660&hours=48")
    assert response.status_code == 200
    data = response.json()
    assert data["station_id"] == "9410660"
    assert len(data["events"]) > 0
    assert data["next_low"] is not None or data["next_high"] is not None

@pytest.mark.integration
async def test_get_tides_404_when_no_data(api_client, db):
    response = await api_client.get("/api/tides?station_id=9410660&hours=48")
    assert response.status_code == 404

@pytest.mark.integration
async def test_get_tides_400_missing_station(api_client):
    response = await api_client.get("/api/tides")
    assert response.status_code == 400

@pytest.mark.unit
def test_interpolate_current_height_midpoint():
    events = [
        TideEvent(timestamp=T_MINUS_6H, type="low", height_ft=0.0),
        TideEvent(timestamp=T_PLUS_6H,  type="high", height_ft=4.0),
    ]
    height = interpolate_current_height(events, now=T_NOW)
    assert height == pytest.approx(2.0, abs=0.1)
```

---

## Acceptance Criteria

- [ ] `GET /api/tides?station_id=9410660` returns 200 with at least 4 events when scraper data exists
- [ ] `next_low` and `next_high` always refer to events in the future relative to request time
- [ ] `current_height_ft` is null when surrounding events are unavailable
- [ ] `GET /api/tides` without `station_id` returns 400
- [ ] `GET /api/sun?location_id=7` returns all six sun event timestamps
- [ ] Timestamps in all responses are ISO 8601 UTC strings
- [ ] WebSocket broadcast fires after scraper run (verified by integration test asserting broadcast POST is called)

---
---

# Card 09 — Tides & Sun Frontend Tile

> **Slice**: A — Tides
> **Depends on**: Cards 02 (WebSocket), 06 (testing infra), 08 (tides endpoint)
> **Blocks**: Nothing — this is the leaf of the tides slice
> **Estimated complexity**: Medium (D3 tide curve is the hard part)

---

## Goal

Build the tides & sun tile as a fully working React component. This is the first frontend tile — it establishes the component pattern (data fetching, loading state, error boundary, WebSocket reactivity, `data-testid` attributes) that all subsequent tiles follow.

---

## Deliverables

```
frontend/src/
├── components/
│   └── tiles/
│       ├── TidesTile.tsx
│       ├── TidesCurve.tsx       ← D3 sub-component
│       └── TileErrorBoundary.tsx
├── hooks/
│   └── useTides.ts
└── lib/
    └── wsStore.ts               ← update: add tides slice (Card 02 stub → real)

tests/
├── components/
│   └── TidesTile.test.tsx
└── e2e/
    └── tides-tile.spec.ts
```

---

## Visual Design

```
┌─────────────────────────────────────────┐
│  TIDES & SUN                   Dana Pt  │
│                                         │
│  ╭─────────────────────────────────╮    │
│  │        ~tide curve svg~         │    │  ← D3, 200px tall
│  │    •                            │    │  ← current position dot
│  ╰─────────────────────────────────╯    │
│                                         │
│  Next low   5:23 AM  −0.2 ft           │
│  Next high  11:48 AM  4.8 ft           │
│                                         │
│  ───────────────────────────────────    │
│                                         │
│  Sunrise     6:42 AM                   │
│  Sunset      5:58 PM                   │
│  Golden hr   5:28 – 5:58 PM            │
│                                         │
│  🌕 Full moon · 3 days                 │
└─────────────────────────────────────────┘
```

---

## Component Structure

### `TidesTile.tsx`

Top-level tile component. Owns data fetching and state.

```typescript
interface TidesTileProps {
  locationId: number
  stationId: string
}

export function TidesTile({ locationId, stationId }: TidesTileProps) {
  const { tides, sun, isLoading, error } = useTides(locationId, stationId)

  if (isLoading) return <TileLoadingState />
  if (error)     return <TileErrorState message="Tide data unavailable" />

  return (
    <div data-testid="tides-tile" className="tile">
      <TileHeader title="Tides & Sun" location={tides.location_name} />
      <TidesCurve events={tides.events} currentHeight={tides.current_height_ft} />
      <NextTides nextLow={tides.next_low} nextHigh={tides.next_high} />
      <Divider />
      <SunEvents sun={sun} />
    </div>
  )
}
```

Wrap at usage site with `<TileErrorBoundary>` — not internally. This allows the boundary to be shared across all tiles.

---

### `useTides.ts`

Custom hook. Fetches initial data via REST, refetches when WebSocket signals new tide data.

```typescript
export function useTides(locationId: number, stationId: string) {
  const [tides, setTides] = useState<TidesResponse | null>(null)
  const [sun, setSun] = useState<SunEventsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const lastConditionsUpdate = useWsStore(s => s.lastConditions)

  const fetchData = useCallback(async () => {
    try {
      const [tidesRes, sunRes] = await Promise.all([
        fetch(`/api/tides?station_id=${stationId}&hours=48`),
        fetch(`/api/sun?location_id=${locationId}`),
      ])
      if (!tidesRes.ok) throw new Error(`Tides API error: ${tidesRes.status}`)
      setTides(await tidesRes.json())
      setSun(await sunRes.json())
    } catch (e) {
      setError(e as Error)
    } finally {
      setIsLoading(false)
    }
  }, [locationId, stationId])

  // Initial fetch
  useEffect(() => { fetchData() }, [fetchData])

  // Refetch when noaa_tides scraper broadcasts
  useEffect(() => {
    if (lastConditionsUpdate?.scraper === 'noaa_tides') {
      fetchData()
    }
  }, [lastConditionsUpdate, fetchData])

  return { tides, sun, isLoading, error }
}
```

---

### `TidesCurve.tsx`

D3 tide curve. Renders an SVG path through the tide events for the next 48 hours with a dot at the current height.

**Implementation notes**:

- Use `useRef` for the SVG element, `useEffect` for D3 rendering
- X axis: time (now → +48 hours)
- Y axis: tide height in feet, centered on 0, range auto-scaled to data
- Path: smooth curve through high/low points using `d3.curveCatmullRom`
- Current position: filled circle at `(now, current_height_ft)` — pulse animation via CSS
- High/low labels: small text annotations at each event point
- The X axis should show time labels at 6-hour intervals
- Responsive: use `ResizeObserver` to redraw on container width change

```typescript
interface TidesCurveProps {
  events: TideEvent[]
  currentHeight: number | null
}
```

All D3 rendering logic lives in a `useEffect` that depends on `[events, currentHeight, containerWidth]`. Clear and redraw on each change — do not attempt incremental D3 updates.

---

### `TileErrorBoundary.tsx`

```typescript
export class TileErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div data-testid="tile-error" className="tile tile--error">
          <span>Data unavailable</span>
        </div>
      )
    }
    return this.props.children
  }
}
```

---

## `data-testid` Attributes Required

Every element targeted by Playwright or Vitest must have a `data-testid`. Required for this tile:

| Element | `data-testid` |
|---|---|
| Tile root | `tides-tile` |
| D3 SVG element | `tides-curve` |
| Next low row | `next-low` |
| Next high row | `next-high` |
| Sunrise row | `sunrise` |
| Sunset row | `sunset` |
| Golden hour row | `golden-hour` |
| Loading state | `tile-loading` |
| Error state | `tile-error` |

---

## Component Tests (Vitest)

```typescript
// tests/components/TidesTile.test.tsx

it('renders next high and low tide times', () => {
  render(<TidesTile locationId={7} stationId="9410660" />, { wrapper: MockProviders })
  expect(screen.getByTestId('next-low')).toHaveTextContent('5:23 AM')
  expect(screen.getByTestId('next-high')).toHaveTextContent('11:48 AM')
})

it('renders D3 SVG tide curve', () => {
  render(<TidesTile locationId={7} stationId="9410660" />, { wrapper: MockProviders })
  expect(screen.getByTestId('tides-curve')).toBeInTheDocument()
  // Verify SVG path element exists (D3 rendered something)
  expect(document.querySelector('svg path')).not.toBeNull()
})

it('shows loading state before data arrives', () => {
  server.use(http.get('/api/tides', () => new Promise(() => {})))   // never resolves
  render(<TidesTile locationId={7} stationId="9410660" />, { wrapper: MockProviders })
  expect(screen.getByTestId('tile-loading')).toBeInTheDocument()
})

it('shows error state when API fails', async () => {
  server.use(http.get('/api/tides', () => HttpResponse.error()))
  render(<TidesTile locationId={7} stationId="9410660" />, { wrapper: MockProviders })
  await waitFor(() => expect(screen.getByTestId('tile-error')).toBeInTheDocument())
})
```

Use `msw` (Mock Service Worker) for request mocking in component tests.

---

## E2E Tests (Playwright)

```typescript
// tests/e2e/tides-tile.spec.ts

test('tides tile is visible on page load', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('tides-tile')).toBeVisible()
})

test('tide curve SVG renders', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('tides-curve')).toBeVisible()
  const path = await page.locator('[data-testid="tides-curve"] path').count()
  expect(path).toBeGreaterThan(0)
})

test('next high and low tides show time and height', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('next-low')).toContainText(/\d:\d{2}/)
  await expect(page.getByTestId('next-low')).toContainText(/ft/)
  await expect(page.getByTestId('next-high')).toContainText(/\d:\d{2}/)
})

test('tile refetches after websocket update', async ({ page }) => {
  await page.goto('/')
  await page.evaluate(() => window.__mockWsMessage({
    type: 'conditions.upserted',
    timestamp: new Date().toISOString(),
    payload: { scraper: 'noaa_tides', records: [] }
  }))
  // Tile should still be visible and not crash after refetch
  await expect(page.getByTestId('tides-tile')).toBeVisible()
})
```

---

## Acceptance Criteria

- [ ] Tile renders with correct next high/low time and height from API fixture data
- [ ] D3 SVG tide curve renders at least one `<path>` element
- [ ] Current position dot visible on the curve when `current_height_ft` is non-null
- [ ] Loading state shown while API request is in-flight
- [ ] Error state shown (not crash) when API returns error
- [ ] `TileErrorBoundary` catches a thrown render error and shows error state
- [ ] Tile re-fetches data when `noaa_tides` WebSocket broadcast received
- [ ] Tile does **not** re-fetch on unrelated WebSocket messages (e.g. `sightings.upserted`)
- [ ] All `data-testid` attributes present and correct
- [ ] All Vitest component tests pass
- [ ] All Playwright E2E tests pass against seeded data

---
---

# Card 10 — Sun Events Scraper

> **Slice**: A — Tides
> **Depends on**: Cards 01 (base class), 05 (schema), 06 (testing infra)
> **Blocks**: Nothing (Card 08 endpoint already handles sun events; this just populates the data)
> **Estimated complexity**: Low — simple JSON API, no parsing complexity

---

## Goal

Implement the sun events scraper using sunrise-sunset.org. Populates the `sun_events` table for all locations. Bundled with the tides slice because the tides tile displays sun data alongside tide data.

---

## Deliverables

```
scrapers/
└── sunrise_sunset.py

tests/
├── scrapers/
│   └── test_sunrise_sunset.py
└── fixtures/
    └── sunrise_sunset_dana_point.yaml    ← VCR cassette
```

---

## sunrise-sunset.org API Reference

**Base URL**: `https://api.sunrise-sunset.org/json`

```
GET /json
  ?lat={lat}
  &lng={lng}
  &date={YYYY-MM-DD}
  &formatted=0         ← returns ISO 8601 timestamps
```

**Response**:

```json
{
  "results": {
    "sunrise": "2025-03-01T14:42:00+00:00",
    "sunset": "2025-03-02T01:58:00+00:00",
    "civil_twilight_begin": "2025-03-01T14:12:00+00:00",
    "civil_twilight_end": "2025-03-02T02:28:00+00:00"
  },
  "status": "OK"
}
```

**Golden hour approximation**: Use `civil_twilight_begin` → `sunrise` for morning golden hour, `sunset` → `civil_twilight_end` for evening golden hour. Civil twilight is close enough to golden hour for this use case; an exact golden hour calculation is not needed.

**Rate limit**: 1000 requests/day. With ~30 locations fetching 7 days forward = 210 requests/run, once daily = well within limit.

---

## Implementation

```python
# scrapers/sunrise_sunset.py

class SunriseSunsetScraper(BaseScraper):
    name = "sunrise_sunset"
    schedule = "30 2 * * *"    # daily at 2:30am, after NOAA tides

    async def fetch(self) -> list[dict]:
        """
        Fetches sun events for all locations for today + next 7 days.
        Returns list of dicts with location_id + raw API response.
        """
        locations = await self.db.get_all_locations()
        results = []

        for location in locations:
            for days_ahead in range(8):    # today + 7 days
                date = (datetime.utcnow().date() + timedelta(days=days_ahead))
                await asyncio.sleep(0.1)   # 100ms courtesy delay
                response = await self.http.get(
                    "https://api.sunrise-sunset.org/json",
                    params={
                        "lat": location.lat,
                        "lng": location.lng,
                        "date": date.isoformat(),
                        "formatted": 0,
                    }
                )
                response.raise_for_status()
                data = response.json()
                if data["status"] == "OK":
                    results.append({
                        "location_id": location.id,
                        "date": date,
                        "data": data["results"],
                    })

        return results

    async def process(self, raw_data: list[dict]) -> list[SunEventRecord]:
        records = []
        for item in raw_data:
            r = item["data"]
            records.append(SunEventRecord(
                date=item["date"],
                location_id=item["location_id"],
                sunrise=datetime.fromisoformat(r["sunrise"]),
                sunset=datetime.fromisoformat(r["sunset"]),
                golden_hour_morning_start=datetime.fromisoformat(r["civil_twilight_begin"]),
                golden_hour_morning_end=datetime.fromisoformat(r["sunrise"]),
                golden_hour_evening_start=datetime.fromisoformat(r["sunset"]),
                golden_hour_evening_end=datetime.fromisoformat(r["civil_twilight_end"]),
            ))
        return records
```

---

## Upsert Behavior

`sun_events` has a `UNIQUE (date, location_id)` constraint. Upsert replaces the existing row — sunrise/sunset times for a given date don't change, but re-fetching is harmless.

`SunEventRecord` is not a time-series type — it goes through a separate upsert path in `db.py` that targets the `sun_events` table, not the hypertables.

---

## Tests

```python
@pytest.mark.scraper
@pytest.mark.vcr("sunrise_sunset_dana_point.yaml")
async def test_sunrise_sunset_creates_records(db, dana_point):
    scraper = SunriseSunsetScraper(db=db, http_client=make_test_http_client(), llm_client=None)
    result = await scraper.run()

    assert result.status == "success"
    assert result.records_created >= 8    # today + 7 days

    event = await db.scalar(
        select(SunEvent)
        .where(SunEvent.location_id == dana_point.id)
        .limit(1)
    )
    assert event.sunrise is not None
    assert event.golden_hour_morning_start < event.sunrise
    assert event.golden_hour_evening_end > event.sunset

@pytest.mark.scraper
@pytest.mark.vcr("sunrise_sunset_dana_point.yaml")
async def test_sunrise_sunset_upsert_idempotent(db, dana_point):
    scraper = SunriseSunsetScraper(db=db, http_client=make_test_http_client(), llm_client=None)
    await scraper.run()
    result = await scraper.run()
    assert result.records_created == 0
    assert result.records_updated >= 8
```

---

## Acceptance Criteria

- [ ] Records created for all locations × 8 days in a single `run()` call
- [ ] `golden_hour_morning_start` is before `sunrise` for every record
- [ ] `golden_hour_evening_end` is after `sunset` for every record
- [ ] Running twice is idempotent — no duplicate rows
- [ ] API response with `status != "OK"` is handled gracefully (logged, skipped, does not fail whole run)
- [ ] Scraper can be run directly: `python -m scrapers.sunrise_sunset` exits 0
