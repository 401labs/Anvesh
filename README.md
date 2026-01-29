# 🦅 Anvesh (अन्वेष)

> **An automated intelligence engine that hunts for high-value businesses with zero online presence.**

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128+-green.svg)
![Playwright](https://img.shields.io/badge/Playwright-Automation-orange.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)

**Anvesh** (Sanskrit for *Investigation/Research*) is a modern, high-performance lead generation engine made with ❤️ in **Bharat**. It acts as a virtual research assistant that dives into the "Blue Ocean" of profitable businesses (Roofers, Dentists, Manufacturers) that have high revenue but **no website**. These leads are invisible to standard search tools but are high-value targets for agencies and freelancers.

## ✨ Key Features

*   **💰 Zero API Costs:** Uses Playwright to scrape data directly, bypassing expensive API subscriptions.
*   **🌍 Anti-Geoblocking:** Automatically configures browser context to block local IP bias, allowing global market research.
*   **🧠 Smart De-duplication:** Detects and ignores duplicate listings and recurring results using PostgreSQL constraints.
*   **📊 Deep Verification:** Extracts **Category, Ratings, Review Count, and Claimed Status**.
*   **🛡️ Thread-Safe Execution:** Optimized for stability on both Windows and Linux environments.
*   **🐳 Docker Ready:** Full stack setup (FastAPI + PostgreSQL) with a single command.

## 🛠️ Tech Stack

*   **Language:** Python 3.12+
*   **Framework:** FastAPI
*   **Database:** PostgreSQL (with `psycopg` binary)
*   **Automation:** Playwright (Chromium)
*   **Package Manager:** [uv](https://github.com/astral-sh/uv)

## 🚀 Installation & Setup

### Option 1: Docker (Recommended)
This is the fastest way to get started. It handles the database, browsers, and application setup.

1.  **Run the Stack**
    ```bash
    docker compose up --build
    ```
2.  **Access the API**
    The API will be available at [http://localhost:8000](http://localhost:8000).
    Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger documentation.

### Option 2: Local Development
1.  **Install Dependencies**
    ```bash
    uv sync
    ```
2.  **Setup Environment**
    Copy `.env.example` to `.env.local` and update your database credentials.
    ```bash
    cp .env.example .env.local
    ```
3.  **Run the App**
    ```bash
    uv run uvicorn app.main:app --reload
    ```

## 🧪 Testing
Run the test suite to ensure everything is working correctly:
```bash
uv run pytest
```

## 🇮🇳 Made in Bharat
Anvesh is built to empower freelancers and small agencies worldwide by providing professional-grade tools at zero cost.