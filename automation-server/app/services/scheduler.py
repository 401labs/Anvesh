"""
Recurring scrape scheduler.

No new dependency (no APScheduler/Celery) — same philosophy as the rest of
this project: a plain polling loop over a Postgres table, matching how task
stop-signals are already polled (see app/routers/automation.py's
make_stop_checker). `run_due_schedules_once()` is the testable unit; the
infinite loop around it is just a thin wrapper started once at app startup.
"""
import asyncio
import threading
import uuid
from typing import Dict

from app.db import create_task, get_due_schedules, mark_schedule_ran
from app.models.automation import ScrapeRequest

POLL_INTERVAL_SECONDS = 60


def fire_schedule(schedule: Dict) -> str:
    """
    Start a scrape task for one schedule (same task machinery `/automation/start`
    uses), advance its next_run_at, and return the new task's id.
    """
    from app.routers.automation import background_task_scraper  # local import: avoids a circular import at module load

    request = ScrapeRequest(
        industry=schedule["industry"],
        locations=schedule["locations"],
        limit_per_location=schedule["limit_per_location"],
    )
    task_id = str(uuid.uuid4())
    create_task(task_id, request.model_dump())

    # Same "run the sync scraper off the request thread" pattern FastAPI's
    # BackgroundTasks uses under the hood — a plain thread rather than asyncio's
    # executor keeps this callable from both sync and async contexts.
    threading.Thread(target=background_task_scraper, args=(task_id, request), daemon=True).start()

    mark_schedule_ran(schedule["id"], schedule["interval_hours"])
    print(f"⏰ Scheduled scrape '{schedule['name']}' fired -> task {task_id}; next run in {schedule['interval_hours']}h")
    return task_id


def run_due_schedules_once() -> int:
    """Fire every currently-due schedule once. Returns how many fired."""
    due = get_due_schedules()
    for schedule in due:
        fire_schedule(schedule)
    return len(due)


async def scheduler_loop():
    """Infinite polling loop — started once at app startup, never awaited on elsewhere."""
    while True:
        try:
            run_due_schedules_once()
        except Exception as e:
            print(f"❌ Scheduler Loop Error: {e}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
