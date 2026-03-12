# Card 06 — Testing Infrastructure

> **Slice**: Foundation
> **Depends on**: Card 05 (schema migrations)
> **Blocks**: All slice cards — agents use this feedback loop to verify their work
> **Estimated complexity**: Medium

---

## Goal

Establish the testing infrastructure that all subsequent cards depend on. An agent executing any slice card should be able to run a single command and get a binary pass/fail signal. This card sets up that command, the test database, the HTTP fixture recording pattern, and the Playwright config for end-to-end tile verification.

The test suite is the agent's feedback loop. If tests pass, the card is done.

---

## Deliverables

```
backend/
├── tests/
│   ├── conftest.py              ← shared fixtures (db session, http client, llm mock)
│   ├── fixtures/
│   │   └── .gitkeep             ← VCR cassettes added per scraper card
│   └── .gitkeep
├── pyproject.toml               ← pytest config + dependencies

frontend/
├── tests/
│   ├── e2e/
│   │   └── .gitkeep             ← Playwright specs added per tile card
│   └── components/
│       └── .gitkeep             ← Vitest component tests added per tile card
├── playwright.config.ts
└── vitest.config.ts

docker-compose.test.yml          ← test environment (isolated DB, no scrapers)
Makefile                         ← test commands
```

---

## Backend: pytest Setup

### Dependencies (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "unit: fast, no I/O",
    "integration: requires test database",
    "scraper: requires HTTP fixtures",
]

[tool.coverage.run]
source = ["api", "scrapers"]
omit = ["*/migrations/*", "*/seed/*"]
```

```toml
# Dependencies
pytest
pytest-asyncio
pytest-recording        # VCR.py integration for HTTP fixtures
pytest-cov
httpx                   # for API endpoint tests
vcrpy
```

### `conftest.py`

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from httpx import AsyncClient
from api.main import app

# ── Database fixture ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """One engine per test session. Database must be running via docker-compose.test.yml."""
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db(test_engine):
    """Per-test transaction that rolls back after each test. No cleanup needed."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        async with AsyncSession(bind=conn) as session:
            yield session
            await session.rollback()

# ── API client fixture ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def api_client(db):
    """FastAPI test client with database dependency overridden to use test db."""
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

# ── LLM mock fixture ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm(mocker):
    """
    Default: LLM returns empty dict (simulates unavailable service).
    Override per-test: mock_llm.return_value = {"species": "Gray whale", "count": 2}
    """
    return mocker.patch("scrapers.llm.LLMClient.extract", return_value={})

# ── Location factory ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def dana_point(db):
    """A real-ish location row for tests that need a valid location_id FK."""
    location = Location(
        name="Dana Point",
        slug="dana-point",
        lat=33.4672,
        lng=-117.6981,
        location_type="harbor",
        region="south_coast",
        noaa_station_id="9410660",
        coastline_bearing=270.0,
    )
    db.add(location)
    await db.flush()
    return location
```

---

## Backend: HTTP Fixture Pattern (VCR)

All scraper tests use recorded HTTP responses. This means:

1. Tests run offline and in CI with no network access to real sources
2. When a source changes its HTML structure, the fixture diverges from reality — this is how you detect source drift

### Recording a fixture

```bash
# Run once with network access to capture the real response:
pytest tests/scrapers/test_harbor_breeze.py --record-mode=new_episodes

# Thereafter, run offline against the recording:
pytest tests/scrapers/test_harbor_breeze.py
```

Fixtures are stored as YAML cassettes in `tests/fixtures/`. Commit them. Update them deliberately when a source changes.

### Example scraper test using VCR

```python
import pytest

@pytest.mark.scraper
@pytest.mark.vcr("harbor_breeze_trip_report.yaml")
async def test_harbor_breeze_parses_sightings(db, dana_point, mock_llm):
    mock_llm.return_value = {
        "species": "Gray whale",
        "count": 3,
        "confidence": "high",
    }

    scraper = HarborBreezeScraper(db=db, http_client=..., llm_client=mock_llm)
    result = await scraper.run()

    assert result.status == "success"
    assert result.records_created == 1

    sighting = await db.scalar(select(Sighting).limit(1))
    assert sighting.species == "Gray whale"
    assert sighting.count == 3
    assert sighting.source == "harbor_breeze"
```

---

## Backend: Test Categories & Commands

```makefile
# Makefile

.PHONY: test test-unit test-integration test-scrapers test-all

test-unit:
	pytest -m unit --tb=short

test-integration:
	pytest -m integration --tb=short

test-scrapers:
	pytest -m scraper --tb=short

test-all:
	pytest --tb=short --cov --cov-report=term-missing

test-fast:
	pytest -m "unit or scraper" --tb=short
```

**In CI**: run `test-fast` on every push (no database required). Run `test-all` on merge to main.

---

## Docker Compose: Test Environment

```yaml
# docker-compose.test.yml
# Isolated test database. Does not start scrapers or API server.

services:
  postgres-test:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: pacific_test
      POSTGRES_USER: pacific
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"    # different port to avoid conflict with dev database
    tmpfs:
      - /var/lib/postgresql/data    # in-memory — fast, disposable
```

Start before running integration tests:
```bash
docker compose -f docker-compose.test.yml up -d
TEST_DATABASE_URL=postgresql+asyncpg://pacific:test@localhost:5433/pacific_test pytest -m integration
```

---

## Frontend: Vitest Setup

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
  },
})
```

```typescript
// tests/setup.ts
import '@testing-library/jest-dom'
import { beforeEach } from 'vitest'
import { cleanup } from '@testing-library/react'

beforeEach(() => cleanup())
```

### Component test pattern

Each tile card will include a component test. The pattern is:

```typescript
// tests/components/TidesTile.test.tsx
import { render, screen } from '@testing-library/react'
import { TidesTile } from '@/components/tiles/TidesTile'
import { mockTidesData } from '../fixtures/tides'

it('renders next high tide time', () => {
  render(<TidesTile data={mockTidesData} />)
  expect(screen.getByText(/next high/i)).toBeInTheDocument()
  expect(screen.getByText('5:23 AM')).toBeInTheDocument()
})

it('shows loading state when data is null', () => {
  render(<TidesTile data={null} />)
  expect(screen.getByRole('status')).toBeInTheDocument()
})

it('shows error state when tile throws', () => {
  render(<TileErrorBoundary><TidesTile data={undefined as any} /></TileErrorBoundary>)
  expect(screen.getByText(/data unavailable/i)).toBeInTheDocument()
})
```

---

## Frontend: Playwright Setup

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://localhost:5173',    // Vite dev server
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

### E2E test pattern

Each tile card will include a Playwright spec. The pattern is:

```typescript
// tests/e2e/tides-tile.spec.ts
import { test, expect } from '@playwright/test'

test('tides tile renders tide curve', async ({ page }) => {
  await page.goto('/')
  const tile = page.locator('[data-testid="tides-tile"]')
  await expect(tile).toBeVisible()
  await expect(tile.locator('svg')).toBeVisible()     // D3 tide curve rendered
})

test('tides tile shows next high/low tide', async ({ page }) => {
  await page.goto('/')
  const tile = page.locator('[data-testid="tides-tile"]')
  await expect(tile.locator('[data-testid="next-high"]')).toContainText(/\d:\d{2}/)
  await expect(tile.locator('[data-testid="next-low"]')).toContainText(/\d:\d{2}/)
})

test('tides tile updates when websocket pushes new data', async ({ page }) => {
  await page.goto('/')
  // Inject a mock WS message via page.evaluate
  await page.evaluate(() => {
    window.__mockWsMessage({
      type: 'conditions.upserted',
      timestamp: new Date().toISOString(),
      payload: { records: [{ condition_type: 'water_temp', value: 67.5, unit: 'F' }] }
    })
  })
  await expect(page.locator('[data-testid="water-temp"]')).toContainText('67.5')
})
```

`window.__mockWsMessage` is a test helper injected by `useWebSocket` when `VITE_TEST_MODE=true` — it bypasses the real WebSocket and allows E2E tests to simulate live updates without a running backend.

---

## Running the Full Stack for E2E Tests

Playwright tests require the API server and a seeded database. A test compose profile handles this:

```bash
# Start API + test database with seed data
docker compose -f docker-compose.test.yml --profile e2e up -d

# Run Playwright tests
npx playwright test

# Tear down
docker compose -f docker-compose.test.yml down
```

The `e2e` profile adds the API server container (but not scrapers — tile data comes from seed fixtures).

---

## Acceptance Criteria

- [ ] `make test-unit` runs with no database and exits 0 on a fresh clone
- [ ] `make test-integration` passes with `docker-compose.test.yml` running
- [ ] Per-test database transactions roll back — running the test suite twice produces identical results
- [ ] Recording a VCR cassette with `--record-mode=new_episodes` and then running without network access passes
- [ ] `mock_llm` fixture correctly intercepts `LLMClient.extract` calls
- [ ] `dana_point` fixture inserts a valid location and is cleaned up after each test
- [ ] Playwright config starts the Vite dev server and navigates to `/` without errors
- [ ] `window.__mockWsMessage` helper is accessible in test mode and does not exist in production builds
- [ ] `make test-all` runs unit + integration + scraper tests and outputs coverage summary
