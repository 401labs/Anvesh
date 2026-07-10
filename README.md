# 🦅 Anvesh (अन्वेष)

> **An automated intelligence engine that hunts for high-value businesses with zero online presence.**

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-green.svg)
![Playwright](https://img.shields.io/badge/Playwright-Automation-orange.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)

**Anvesh** is a monorepo containing:

*   **[Automation Server](./automation-server)**: The core Python/FastAPI backend and scraping engine.
*   **[Web Portal](./web-portal)**: A dashboard for operating the automation server — tasks (with an optional live view), leads, email outreach, and API keys.
*   **[Docs Site](./docs-site)**: Public documentation and landing page.

## ✨ What it does

*   **Scrapes Google Maps** for businesses matching an industry + location, watchable live (headed browser locally, or a noVNC link when running in Docker) — one-off or on a **recurring schedule** (daily/weekly/etc., no manual restart needed).
*   **Scores every lead** 0-100 — high rating, many reviews, no website, unclaimed listing all push a lead up, so you know who to pitch first without eyeballing a spreadsheet.
*   **Stores and organizes leads** — filter by website/email presence, claim status, rating, score, or outreach stage; each lead keeps a direct link back to its Google Maps listing.
*   **Sends outreach email** — reusable templates with per-lead placeholders, single or bulk sends via your own SMTP (e.g. Gmail + an app password), with every attempt logged, replies auto-detected over IMAP, and a lead's status advancing through the pipeline automatically.
*   **Dashboards the whole funnel** — one view of lead status breakdown, hot/warm/cool prospects, send/reply stats, and top industries/locations.
*   **Gates access with API keys** — tiered quotas (free/pro/enterprise), usage tracking, admin controls.

## 🚀 Quick Start

There are two ways to run Anvesh — pick one. Both are verified working.

### Option A: Docker (recommended)

One command brings up everything — database, API, and the dashboard — with a shared default admin secret already wired in, no manual config needed:
```bash
./start.sh
```
(or run `docker compose up --build` directly — `start.sh` just wraps it and waits until the API and dashboard are actually responding before printing the URLs.)
API at [http://localhost:8000](http://localhost:8000), Web Portal at [http://localhost:3000](http://localhost:3000), live scrape view (noVNC) at [http://localhost:6080/vnc.html](http://localhost:6080/vnc.html) once a headed task is running.

The default `ADMIN_SECRET` and `VNC_PASSWORD` (`change-me-in-production`, set in `docker-compose.yml`) are fine for local use — change them before exposing this anywhere beyond your own machine. Outreach email is opt-in: set `SMTP_USER`/`SMTP_APP_PASSWORD` (see [automation-server/README.md](./automation-server/README.md#-outreach)) if you want to actually send; without them, sending just fails cleanly.

### Option B: Manual (no Docker for the apps)

You still need Postgres reachable somewhere — either `docker compose up -d db` (just the database container) or your own local Postgres instance.

**1. Backend:**
```bash
cd automation-server
uv sync
cp .env.example .env.local   # defaults already point at localhost:5432 / postgres / password
uv run uvicorn app.main:app --reload
```
Runs on [http://localhost:8000](http://localhost:8000).

**2. Web Portal** (in a second terminal, backend must already be running):
```bash
cd web-portal
bun install
cp .env.local.example .env.local   # ADMIN_SECRET must match automation-server's .env.local
bun run dev
```
Runs on [http://localhost:3000](http://localhost:3000). See [web-portal/README.md](./web-portal/README.md) for details.

## 📚 Documentation

See [Automation Server Docs](./automation-server/docs) for API details.

## 🇮🇳 Made in Bharat

Anvesh is built to empower freelancers and small agencies worldwide by providing professional-grade tools at zero cost.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
