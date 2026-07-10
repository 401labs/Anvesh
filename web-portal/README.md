# Anvesh Web Portal

A dashboard for operating [`automation-server`](../automation-server): start and monitor scrape tasks, browse/filter/export leads, reach out to them by email, and manage API keys — without touching curl.

Built with Next.js 16, React 19, TypeScript, and Tailwind v4, matching `docs-site`'s dark, glass, indigo-glow visual style.

## Features

- **Overview** — a dashboard of everything below in one place: lead funnel by status, hot/warm/cool prospect breakdown, outreach send stats, top industries/locations, and task health.
- **Tasks** — start scrapes, monitor status, and optionally watch one live: a real browser window if `automation-server` runs locally, or a linked noVNC view if it runs in Docker (see `automation-server/README.md`).
- **Schedules** (`/schedules`) — save a scrape config to re-run automatically on a recurring interval (daily/weekly/etc.) instead of starting it by hand every time. Pause, resume, or trigger one immediately.
- **Leads** — browse, filter (industry, location, category, website/email/claim status, minimum rating, opportunity score, and outreach status), sort by score, bulk-select, export to CSV, edit, and jump straight to a lead's Google Maps listing. Every lead shows a computed 0-100 "hot prospect" score.
- **Outreach** (`/outreach`) — manage reusable email templates, send one-off or bulk emails to leads with an address on file, view each lead's send history from the Leads page, and check for replies (auto-detected via IMAP every 2 minutes, or on demand). Needs SMTP configured on `automation-server` — without it, sends fail cleanly and log why, rather than erroring out the whole page.
- **API Keys** — create, edit, revoke, and monitor usage per key.

## How it works

The browser never talks to `automation-server` directly, and there's no login screen on the portal itself — instead, this app's own Next.js Route Handlers (`src/app/api/**`) proxy every call server-side, attaching `X-Admin-Secret` from an environment variable that's never sent to the browser. `automation-server`'s `get_api_key` dependency accepts a valid `X-Admin-Secret` in place of a per-user API key (see `automation-server/app/middleware/auth.py`), so the portal only needs one secret — no separately-generated API key to create or rotate. See `src/lib/upstream.ts` for the proxy logic.

## Setup

### Via Docker (recommended)

Run `docker compose up --build` from the repo root — it starts Postgres, `automation-server`, and this portal together, with `ADMIN_SECRET` shared between them automatically. Open [http://localhost:3000](http://localhost:3000).

### Standalone

1. **Install dependencies**
   ```bash
   bun install
   ```

2. **Configure environment**
   ```bash
   cp .env.local.example .env.local
   ```
   Set `AUTOMATION_API_URL` to where `automation-server` is running (default `http://localhost:8000`), and `ADMIN_SECRET` to match its value there.

3. **Run it**
   ```bash
   bun run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) (or whichever port Next.js picks if 3000 is taken by `docs-site`).

## Notes

- **No login gate.** This is a self-hosted internal ops tool — don't expose it to the public internet without adding one.
- **Dark-only.** No theme toggle, intentionally.
