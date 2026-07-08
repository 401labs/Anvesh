# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Anvesh's automation server: a FastAPI backend that scrapes Google Maps (via Playwright) for businesses with weak/no online presence ("blue ocean" leads), stores them in PostgreSQL, and exposes the results through an API-key-gated REST API.

## Commands

```bash
# Install dependencies
uv sync

# Run the dev server (auto-reload, http://localhost:8000)
uv run uvicorn app.main:app --reload

# Start Postgres only (via docker compose)
docker compose up -d db

# Run all tests
uv run pytest

# Run a single test file / test
uv run pytest tests/unit/test_api_keys.py
uv run pytest tests/unit/test_api_keys.py::TestClassName::test_name

# Unit vs integration only
uv run pytest tests/unit/
uv run pytest tests/integration/
```

There is no configured linter/formatter in this repo — don't assume one.

Environment variables are read from `.env.local` first, then `.env` (see `.env.example` for the full list: `DB_HOST/PORT/USER/PASSWORD/NAME`, `ADMIN_SECRET`, optional `API_KEY_PREFIX`). Tests set `ADMIN_SECRET` and `DB_NAME=lead_scraper_test` directly in `tests/conftest.py` before importing the app, so a running Postgres instance is required for the test suite (integration tests hit the app through `TestClient` and unit tests hit real DB helper functions — nothing is mocked).

## Architecture

**Request flow:** `app/main.py` builds the FastAPI app, registers a global `RequestValidationError` handler (so 422s match the standard response envelope), calls `init_db()` synchronously at import time, then mounts three routers: `automation`, `keys`, `admin`.

**Response envelope:** every endpoint returns JSON shaped like `{"success", "message", "data", "error"}` via the `api_success()` / `api_error()` helpers in `app/helpers/response.py` — do not return raw dicts or pydantic models directly from route handlers, wrap them. `STANDARD_RESPONSES` in the same file supplies the shared OpenAPI response docs (400/401/403/404/422/500) that every router attaches via `responses=STANDARD_RESPONSES`.

**Auth:** two independent schemes in `app/middleware/auth.py`, both FastAPI dependencies:
- `get_api_key` — requires `X-API-Key` header, validates against `api_keys` table (SHA-256 hash lookup), and enforces monthly quota via `check_quota()`. `get_optional_api_key` is the same but returns `None` instead of raising.
- `require_admin` — requires `X-Admin-Secret` header matching `settings.admin_secret`. Used for all `/admin/*` and key-management routes.

API keys are generated as `{prefix}{32-byte-hex}` (default prefix `anv_`), only the SHA-256 hash is persisted, and the raw key is returned exactly once at creation time (`app/db/api_keys.py::create_api_key`). Tiers (`free`/`pro`/`enterprise`) and their monthly limits/rate limits live in `config/keys.py::TIERS` — this is the single place to change quota numbers.

**Database layer** (`app/db/`): raw `psycopg` (no ORM), `dict_row` factory so query results are dicts. `database.py` owns the `leads` table and connection setup; `api_keys.py` owns `api_keys` and `usage_logs`. `init_db()` (called once at startup) creates the target database itself if missing (connects to the `postgres` system db first, retries up to 10x), then creates both sets of tables. `app/db/__init__.py` re-exports the public functions from both modules — import from `app.db`, not the submodules, in route/service code.

**Automation tasks** (`app/routers/automation.py`): tasks are tracked in a module-level in-memory dict `TASKS` (not persisted — cleared on restart, and won't work correctly across multiple server processes/workers). `POST /automation/start` kicks off `background_task_scraper` as a FastAPI `BackgroundTasks` job, which iterates `request.locations` sequentially, calling `scrape_google_maps()` once per location. Each task supports cooperative cancellation via a `stop_signal` closure checked inside the scrape loop; `POST /automation/stop` / `/automation/tasks/{id}/stop` just flip `TASKS[id]["stop"] = True`. `app/routers/admin.py` reaches into the same `TASKS` dict directly for system-wide monitoring/stop-all — the two routers are coupled through this shared state, not through the DB.

**Scraper** (`app/services/scraper.py`): a single long, imperative `scrape_google_maps()` function using sync Playwright (headless Chromium). It navigates directly to a Maps search URL (bypasses the "near me" autocomplete bias), scrolls the results feed, and for each listing card does a "click and verify name matches" loop before scraping fields (address, website, phone, rating, review count, claimed status, category) out of the detail panel. Selectors are Google Maps' internal CSS class names (e.g. `div.qBF1Pd`, `h1.DUwDvf`) — these are unstable/undocumented and the most likely thing to break if Google changes its markup. Leads are inserted into Postgres one at a time via `insert_lead()`, which dedupes on `(business_name, address)`.

**Models** (`app/models/`): pydantic request/response schemas, separated from the `APIResponse`/`ErrorResponse` envelope models in `app/helpers/response.py`. `TaskStatus` is a str enum (`idle/running/completed/stopped/error`) shared between `automation.py` and `admin.py`.

## Working in this repo

- New DB tables/queries go through `psycopg` with `dict_row`, following the existing pattern in `app/db/*.py` (explicit SQL, `conn.commit()`, wrap in try/except that prints and returns a falsy value on failure rather than raising).
- New routes should follow the existing convention: return via `api_success`/`api_error`, declare `response_model=APIResponse` and `responses=STANDARD_RESPONSES`, and write a multi-line `description=` docstring for the OpenAPI docs (this repo's docs at `docs/api/*.md` are generated/maintained from this OpenAPI spec — see `docs/api/overview.md`, `keys.md`, `automation.md`).
- Anything touching Google Maps selectors in `scraper.py` is inherently fragile — treat it as scraping-site-specific rather than general Playwright code, and expect selectors to need periodic updates.
