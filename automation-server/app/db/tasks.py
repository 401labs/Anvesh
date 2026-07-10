"""
Automation task database operations.

Tasks used to live in a module-level in-memory dict (see git history of
app/routers/automation.py) — that lost all history on restart and would have
broken silently under multiple worker processes. They're now persisted here,
the same way leads and api_keys are.
"""
from typing import Dict, List, Optional
from psycopg.types.json import Jsonb
from app.db.database import get_connection


def create_tables():
    """Create the automation_tasks table if it doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS automation_tasks (
                    id TEXT PRIMARY KEY,
                    status VARCHAR(20) NOT NULL DEFAULT 'idle',
                    config JSONB NOT NULL,
                    running BOOLEAN NOT NULL DEFAULT TRUE,
                    stop BOOLEAN NOT NULL DEFAULT FALSE,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    print("✅ PostgreSQL Table 'automation_tasks' initialized.")


def create_task(task_id: str, config: Dict) -> Optional[Dict]:
    """Create a new task row (status=idle, running=true, stop=false)."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO automation_tasks (id, status, config, running, stop)
                    VALUES (%s, 'idle', %s, TRUE, FALSE)
                    RETURNING *
                ''', (task_id, Jsonb(config)))
                result = cur.fetchone()
                conn.commit()
                return result
    except Exception as e:
        print(f"❌ Task Create Error: {e}")
        return None


def get_task(task_id: str) -> Optional[Dict]:
    """Retrieve a single task by ID."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM automation_tasks WHERE id = %s", (task_id,))
                return cur.fetchone()
    except Exception as e:
        print(f"❌ Task Fetch Error: {e}")
        return None


def list_tasks(limit: int = 20, offset: int = 0) -> List[Dict]:
    """Retrieve a page of tasks, most recently created first."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT * FROM automation_tasks
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                ''', (limit, offset))
                return cur.fetchall()
    except Exception as e:
        print(f"❌ Task Fetch Error: {e}")
        return []


def count_tasks() -> int:
    """Count the total number of tasks."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM automation_tasks")
                result = cur.fetchone()
                return result["count"] if result else 0
    except Exception as e:
        print(f"❌ Task Count Error: {e}")
        return 0


def list_all_tasks() -> List[Dict]:
    """Retrieve every task, most recently created first. For admin/system-wide views."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM automation_tasks ORDER BY created_at DESC")
                return cur.fetchall()
    except Exception as e:
        print(f"❌ Task Fetch Error: {e}")
        return []


def list_running_tasks() -> List[Dict]:
    """Retrieve tasks currently marked as running."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM automation_tasks WHERE running = TRUE")
                return cur.fetchall()
    except Exception as e:
        print(f"❌ Task Fetch Error: {e}")
        return []


def get_task_counts() -> Dict:
    """Aggregate task counts by status, plus total. For admin stats."""
    counts = {"total": 0, "running": 0, "completed": 0, "stopped": 0, "error": 0}
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT status, COUNT(*) AS count
                    FROM automation_tasks
                    GROUP BY status
                ''')
                for row in cur.fetchall():
                    if row["status"] in counts:
                        counts[row["status"]] = row["count"]
                    counts["total"] += row["count"]

                cur.execute("SELECT COUNT(*) AS count FROM automation_tasks WHERE running = TRUE")
                running_result = cur.fetchone()
                counts["running"] = running_result["count"] if running_result else 0
    except Exception as e:
        print(f"❌ Task Stats Error: {e}")
    return counts


def set_task_status(task_id: str, status: str, error: Optional[str] = None) -> bool:
    """Update a task's status (and optionally its error message)."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE automation_tasks
                    SET status = %s, error = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id
                ''', (status, error, task_id))
                result = cur.fetchone()
                conn.commit()
                return result is not None
    except Exception as e:
        print(f"❌ Task Update Error: {e}")
        return False


def set_task_running(task_id: str, running: bool) -> bool:
    """Update a task's running flag."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE automation_tasks
                    SET running = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id
                ''', (running, task_id))
                result = cur.fetchone()
                conn.commit()
                return result is not None
    except Exception as e:
        print(f"❌ Task Update Error: {e}")
        return False


def get_task_stop_flag(task_id: str) -> bool:
    """Cheap single-column read of the stop flag, for the in-process stop poller."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT stop FROM automation_tasks WHERE id = %s", (task_id,))
                result = cur.fetchone()
                return bool(result["stop"]) if result else False
    except Exception as e:
        print(f"❌ Task Fetch Error: {e}")
        return False


def request_stop(task_id: str) -> bool:
    """Flag a task to stop, if it's currently running. Returns whether it hit a running task."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE automation_tasks
                    SET stop = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND running = TRUE
                    RETURNING id
                ''', (task_id,))
                result = cur.fetchone()
                conn.commit()
                return result is not None
    except Exception as e:
        print(f"❌ Task Update Error: {e}")
        return False


def request_stop_all() -> int:
    """Flag every currently-running task to stop. Returns the count flagged."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE automation_tasks
                    SET stop = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE running = TRUE
                    RETURNING id
                ''')
                result = cur.fetchall()
                conn.commit()
                return len(result)
    except Exception as e:
        print(f"❌ Task Update Error: {e}")
        return 0


def delete_task(task_id: str) -> bool:
    """Permanently delete a task."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM automation_tasks WHERE id = %s RETURNING id", (task_id,))
                result = cur.fetchone()
                conn.commit()
                return result is not None
    except Exception as e:
        print(f"❌ Task Delete Error: {e}")
        return False
