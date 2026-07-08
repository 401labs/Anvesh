# Anvesh Web Portal

A dashboard for operating [`automation-server`](../automation-server): start and monitor scrape tasks, browse and export leads, and manage API keys — without touching curl.

Built with Next.js 16, React 19, TypeScript, and Tailwind v4, matching `docs-site`'s dark, glass, indigo-glow visual style.

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
- Tasks are stored in-memory by `automation-server` and are lost on restart — the Tasks page detects this and shows a notice rather than a silent empty table.
