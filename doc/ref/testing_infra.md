# Technical Reference: Testing Infrastructure

## 1. Backend (pytest)
- **Unit Tests**: Logic and transformation tests (fast, no I/O).
- **Integration Tests**: Database operations using a dedicated `postgres-test` container.
- **Scraper Tests**: Use **VCR.py** (via `pytest-recording`) to record and replay HTTP interactions.
    - Recordings are stored in `tests/fixtures/`.
    - `pytest --record-mode=new_episodes` captures fresh data.

## 2. Frontend (Vitest & agent-browser)
- **Component Tests (Vitest)**: Testing individual tile rendering and state logic using JSDOM and MSW.
- **E2E Tests (agent-browser)**: Using `agent-browser`, an agent-friendly wrapper around Playwright, for end-to-end testing.
    - The agent-browser library simplifies page navigation, element selection, and assertion patterns.
    - Run against the Vite dev server in CI or against deployed preview environments.

## 3. Automation
Tests are integrated into the GitHub Actions pipeline:
- **Lint/Type-check**: Runs on every push.
- **Unit/Scraper Tests**: Runs on every push.
- **Integration/E2E**: Runs on Pull Requests and merges to `main`.
