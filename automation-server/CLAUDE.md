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

**Request flow:** `app/main.py` builds the FastAPI app via a `lifespan` context manager (starts/cancels two background asyncio tasks — the scheduler and reply-checker loops below — for the app's lifetime), registers a global `RequestValidationError` handler (so 422s match the standard response envelope), calls `init_db()` synchronously at import time, then mounts six routers: `automation`, `keys`, `admin`, `outreach`, `stats`, `schedules`.

**Response envelope:** every endpoint returns JSON shaped like `{"success", "message", "data", "error"}` via the `api_success()` / `api_error()` helpers in `app/helpers/response.py` — do not return raw dicts or pydantic models directly from route handlers, wrap them. `STANDARD_RESPONSES` in the same file supplies the shared OpenAPI response docs (400/401/403/404/422/500) that every router attaches via `responses=STANDARD_RESPONSES`.

**Auth:** two independent schemes in `app/middleware/auth.py`, both FastAPI dependencies:
- `get_api_key` — requires `X-API-Key` header, validates against `api_keys` table (SHA-256 hash lookup), and enforces monthly quota via `check_quota()`. `get_optional_api_key` is the same but returns `None` instead of raising.
- `require_admin` — requires `X-Admin-Secret` header matching `settings.admin_secret`. Used for all `/admin/*` and key-management routes.

API keys are generated as `{prefix}{32-byte-hex}` (default prefix `anv_`), only the SHA-256 hash is persisted, and the raw key is returned exactly once at creation time (`app/db/api_keys.py::create_api_key`). Tiers (`free`/`pro`/`enterprise`) and their monthly limits/rate limits live in `config/keys.py::TIERS` — this is the single place to change quota numbers.

**Database layer** (`app/db/`): raw `psycopg` (no ORM), `dict_row` factory so query results are dicts. `database.py` owns the `leads` table and connection setup; `api_keys.py` owns `api_keys` and `usage_logs`. `init_db()` (called once at startup) creates the target database itself if missing (connects to the `postgres` system db first, retries up to 10x), then creates both sets of tables. `app/db/__init__.py` re-exports the public functions from both modules — import from `app.db`, not the submodules, in route/service code.

**Automation tasks** (`app/routers/automation.py`): tasks are persisted in the `automation_tasks` table (`app/db/tasks.py`), following the same raw-`psycopg` pattern as leads/api_keys — task history survives restarts and is safe across multiple server processes/workers. `POST /automation/start` inserts a task row via `create_task()`, then kicks off `background_task_scraper` as a FastAPI `BackgroundTasks` job, which iterates `request.locations` sequentially, calling `scrape_google_maps()` once per location. Each task supports cooperative cancellation via a `stop_signal` closure checked inside the scrape loop; the closure (`make_stop_checker()`) polls the task's `stop` column in the DB, throttled to once every 2 seconds so a stop request handled by a different worker/process is still observed without hammering the DB. `POST /automation/stop` / `/automation/tasks/{id}/stop` call `request_stop_all()` / `request_stop()`, which just flip that `stop` column. `app/routers/admin.py` reaches into the same `automation_tasks` table (via `app/db/tasks.py`'s admin-facing helpers) for system-wide monitoring/stop-all — the two routers are coupled through the DB now, not shared process memory.

**Scraper** (`app/services/scraper.py`): a single long, imperative `scrape_google_maps()` function using sync Playwright (`headless` is a caller-supplied bool, not hardcoded — see below). It navigates directly to a Maps search URL (bypasses the "near me" autocomplete bias), scrolls the results feed, and for each listing card does a "click and verify name matches" loop before scraping fields (address, website, phone, rating, review count, claimed status, category, `maps_url`) out of the detail panel. Selectors are Google Maps' internal CSS class names (e.g. `div.qBF1Pd`, `h1.DUwDvf`) — these are unstable/undocumented and the most likely thing to break if Google changes its markup. Leads are inserted into Postgres one at a time via `insert_lead()`, which dedupes on `(business_name, address)`.

`maps_url` is read directly off the search-result card's own `<a href>` (`card.query_selector('a')`), *not* `page.url` after clicking — for the first/auto-selected result, Google Maps frequently leaves the address bar on the plain search URL instead of navigating to the place URL, so `page.url` silently produces a wrong (non-place) link for that one result specifically. The card's href is correct and available before any click at all.

**Headed scrapes / live view:** `ScrapeRequest.headless` (default `True`) threads through `background_task_scraper` into `scrape_google_maps(..., headless=...)`'s `p.chromium.launch(headless=...)` call. Locally (`uv run uvicorn`), `headless=False` opens a real browser window. In Docker, there's no display, so `automation-server/docker/entrypoint.sh` instead starts a virtual one (`Xvfb :99`) plus `x11vnc` and `websockify`+noVNC before `exec`-ing uvicorn, so the same headed Chromium can be watched from `http://localhost:6080/vnc.html` — see `Dockerfile` and `docker-compose.yml`'s `VNC_PASSWORD`/port `6080`. The stop-signal closure (`make_stop_checker()` in `automation.py`) is unrelated to this — don't confuse the two.

**Outreach** (`app/routers/outreach.py`, `app/db/outreach.py`, `app/services/mailer.py`): leads carry a `status` field (`new/contacted/replied/interested/won/lost`, default `new`, filterable via `GET /automation/leads?status=`). `email_templates` store reusable subject/body pairs with `{{business_name}}`-style placeholders, rendered per-lead by `mailer.render_template()`; `outreach_logs` records every send attempt, success or failure. `POST /outreach/email/send` sends synchronously for a single lead (result returned immediately) or queues a `BackgroundTasks` job for multiple leads — same pattern as the scraper's background task, and leads with no email on file are skipped and reported rather than causing an error. Email goes out over plain `smtplib` (`app/services/mailer.py::send_email()`) — Gmail plus an app password is the intended setup (`SMTP_*` in `.env.example`), no external email service dependency, and no SMTP config just means sends fail cleanly (logged with an error) rather than crashing. A successful send auto-advances a lead's status from `new` to `contacted` (`_advance_status_if_new()` in the router).

**Reply detection** (`app/services/replies.py`): polls the same inbox `mailer.py` sends from, over IMAP (stdlib `imaplib`, reusing `SMTP_USER`/`SMTP_APP_PASSWORD` — override `IMAP_HOST`/`IMAP_PORT` only for non-Gmail). Matching is deliberately simple: an unseen inbound email's From address is looked up against `leads.email` (`get_lead_by_email()`) — no Message-ID/In-Reply-To threading. A match gets logged via `create_log()` (`status=replied`) and the lead's status advances to `replied`, then the message is marked `\Seen` over IMAP so it isn't reprocessed — this is the one place in the codebase that mutates state in a system Anvesh doesn't own (the operator's actual inbox), and it's scoped tightly: only matched replies get flagged, unmatched unseen mail is left untouched. `check_for_replies()` is the synchronous, directly-testable unit; `reply_checker_loop()` is the thin polling wrapper (every 120s) started from `main.py`'s lifespan. `POST /outreach/check-replies` triggers a check on demand.

**Lead scoring** (`app/db/database.py::LEAD_SCORE_SQL`): a 0-100 score computed *in SQL*, not stored — `rating*12 + min(review_count,500)/500*20 + (no website: +15) + (unclaimed: +5)`. Every `SELECT` in `get_leads()`/`get_all_leads()` includes it as a `score` column, `LEAD_SORT_COLUMNS["score"]` lets `sort_by=score` `ORDER BY` the same expression, and `_build_lead_filters()` supports `min_score` the same way. Computing on read (vs. a stored/backfilled column) means changing the formula or editing a lead's rating never needs a migration or recompute step.

**Scheduled scrapes** (`app/services/scheduler.py`, `app/db/schedules.py`): recurring scrape configs in the `scheduled_scrapes` table (`name`, `industry`, `locations`, `interval_hours`, `enabled`, `next_run_at`). No new dependency (no APScheduler/Celery) — `scheduler_loop()` polls `get_due_schedules()` (`WHERE enabled AND next_run_at <= CURRENT_TIMESTAMP`) every 60s from `main.py`'s lifespan, exactly the same "poll a Postgres column" philosophy as task stop-signals. `fire_schedule()` is the testable unit: builds a `ScrapeRequest`, calls `create_task()` + starts `background_task_scraper` in a plain `threading.Thread` (not asyncio's executor, so it's callable from sync test code too), then advances `next_run_at` — **computed in SQL** (`CURRENT_TIMESTAMP + (%s * INTERVAL '1 hour')`), not Python's `datetime.now()`. That distinction matters: an earlier version computed the offset in Python and schedules silently never came due whenever the app server's local timezone wasn't UTC, since Postgres's `CURRENT_TIMESTAMP` (used by the due-check) and Python's local `now()` drifted against each other. `POST /schedules/{id}/run-now` reuses `fire_schedule()` for an immediate trigger outside the poll cycle.

**Analytics dashboard** (`app/routers/stats.py`): `GET /stats` aggregates `get_lead_stats()` (counts by status/score-tier/email/website/claimed), `get_leads_by_day()`, `get_top_industries()`/`get_top_locations()` (all `app/db/database.py`), `get_outreach_stats()` (`app/db/outreach.py`), and `get_task_counts()` (`app/db/tasks.py`, already existed for admin stats) into one payload — what the web portal's Overview page renders alongside the pre-existing admin-only `/admin/automation/stats` (task-only, `require_admin`-gated). Keep these two conceptually separate: `/stats` is the general-purpose dashboard (`get_api_key`-gated, like everything else), `/admin/automation/stats` is admin-only system monitoring.

**Models** (`app/models/`): pydantic request/response schemas, separated from the `APIResponse`/`ErrorResponse` envelope models in `app/helpers/response.py`. `TaskStatus` is a str enum (`idle/running/completed/stopped/error`) shared between `automation.py` and `admin.py`; `LeadStatus` (also `automation.py`) is the lead pipeline enum. `app/models/outreach.py` (`EmailTemplateCreate/Update`, `SendEmailRequest`) and `app/models/schedule.py` (`ScheduleCreate/Update`) follow the same `Field(...)`-with-`examples` convention as the rest.

## Working in this repo

- New DB tables/queries go through `psycopg` with `dict_row`, following the existing pattern in `app/db/*.py` (explicit SQL, `conn.commit()`, wrap in try/except that prints and returns a falsy value on failure rather than raising).
- New routes should follow the existing convention: return via `api_success`/`api_error`, declare `response_model=APIResponse` and `responses=STANDARD_RESPONSES`, and write a multi-line `description=` docstring for the OpenAPI docs (this repo's docs at `docs/api/*.md` are generated/maintained from this OpenAPI spec — see `docs/api/overview.md`, `keys.md`, `automation.md`).
- Anything touching Google Maps selectors in `scraper.py` is inherently fragile — treat it as scraping-site-specific rather than general Playwright code, and expect selectors to need periodic updates.
