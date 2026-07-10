"""
Scheduled (recurring) scrape database operations.
"""
from typing import Dict, List, Optional
from psycopg.types.json import Jsonb
from app.db.database import get_connection


def create_tables():
    """Create the scheduled_scrapes table if it doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_scrapes (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    industry VARCHAR(255) NOT NULL,
                    locations JSONB NOT NULL,
                    limit_per_location INT NOT NULL DEFAULT -1,
                    interval_hours INT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    last_run_at TIMESTAMP,
                    next_run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    print("✅ PostgreSQL Table 'scheduled_scrapes' initialized.")


def create_schedule(name: str, industry: str, locations: List[str], limit_per_location: int, interval_hours: int) -> Optional[Dict]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO scheduled_scrapes (name, industry, locations, limit_per_location, interval_hours)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                ''', (name, industry, Jsonb(locations), limit_per_location, interval_hours))
                result = cur.fetchone()
                conn.commit()
                return result
    except Exception as e:
        print(f"❌ Schedule Create Error: {e}")
        return None


def get_schedule(schedule_id: int) -> Optional[Dict]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM scheduled_scrapes WHERE id = %s", (schedule_id,))
                return cur.fetchone()
    except Exception as e:
        print(f"❌ Schedule Fetch Error: {e}")
        return None


def list_schedules() -> List[Dict]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM scheduled_scrapes ORDER BY created_at DESC")
                return cur.fetchall()
    except Exception as e:
        print(f"❌ Schedule Fetch Error: {e}")
        return []


def update_schedule(schedule_id: int, fields: Dict) -> Optional[Dict]:
    """Update a schedule. `fields` may contain any subset of the updatable columns."""
    updatable = ("name", "industry", "locations", "limit_per_location", "interval_hours", "enabled")
    updates = {k: v for k, v in fields.items() if k in updatable}
    if not updates:
        return get_schedule(schedule_id)

    set_parts = []
    values = []
    for col, val in updates.items():
        set_parts.append(f"{col} = %s")
        values.append(Jsonb(val) if col == "locations" else val)
    values.append(schedule_id)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE scheduled_scrapes SET {', '.join(set_parts)} WHERE id = %s RETURNING *",
                    values
                )
                result = cur.fetchone()
                conn.commit()
                return result
    except Exception as e:
        print(f"❌ Schedule Update Error: {e}")
        return None


def delete_schedule(schedule_id: int) -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM scheduled_scrapes WHERE id = %s RETURNING id", (schedule_id,))
                result = cur.fetchone()
                conn.commit()
                return result is not None
    except Exception as e:
        print(f"❌ Schedule Delete Error: {e}")
        return False


def get_due_schedules() -> List[Dict]:
    """Enabled schedules whose next_run_at has arrived. Polled by the scheduler loop."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM scheduled_scrapes
                    WHERE enabled = TRUE AND next_run_at <= CURRENT_TIMESTAMP
                """)
                return cur.fetchall()
    except Exception as e:
        print(f"❌ Due Schedules Error: {e}")
        return []


def mark_schedule_ran(schedule_id: int, interval_hours: int) -> bool:
    """
    Record that a schedule just ran and push next_run_at forward by
    `interval_hours`. The offset is computed in SQL (relative to Postgres's own
    CURRENT_TIMESTAMP), not in Python — a Python-side `datetime.now()` is in
    local time, which drifted against Postgres's UTC clock and made schedules
    silently never come due when the app server's timezone wasn't UTC. A
    negative `interval_hours` is valid too — useful in tests to force a
    schedule into the past ("already due") without touching Python's clock.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE scheduled_scrapes
                    SET last_run_at = CURRENT_TIMESTAMP,
                        next_run_at = CURRENT_TIMESTAMP + (%s * INTERVAL '1 hour')
                    WHERE id = %s
                    RETURNING id
                """, (interval_hours, schedule_id))
                result = cur.fetchone()
                conn.commit()
                return result is not None
    except Exception as e:
        print(f"❌ Schedule Mark Ran Error: {e}")
        return False
