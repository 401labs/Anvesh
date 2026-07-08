# 🦅 Anvesh (अन्वेष)

> **An automated intelligence engine that hunts for high-value businesses with zero online presence.**

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-green.svg)
![Playwright](https://img.shields.io/badge/Playwright-Automation-orange.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)

**Anvesh** is a monorepo containing:

*   **[Automation Server](./automation-server)**: The core Python/FastAPI backend and scraping engine.
*   **[Web Portal](./web-portal)**: A dashboard for operating the automation server — tasks, leads, and API keys.
*   **[Docs Site](./docs-site)**: Public documentation and landing page.

## 🚀 Quick Start

There are two ways to run Anvesh — pick one. Both are verified working.

### Option A: Docker (recommended)

One command brings up everything — database, API, and the dashboard — with a shared default admin secret already wired in, no manual config needed:
```bash
docker compose up --build
```
API at [http://localhost:8000](http://localhost:8000), Web Portal at [http://localhost:3000](http://localhost:3000).

The default `ADMIN_SECRET` (`change-me-in-production`, set in `docker-compose.yml`) is fine for local use — change it in both the `automation-server` and `web-portal` service blocks together before exposing this anywhere beyond your own machine.

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
