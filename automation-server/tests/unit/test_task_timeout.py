"""
Tests for the task max-duration safety net (app/routers/automation.py's
make_stop_checker / background_task_scraper) — a task must never stay
`running` forever, even if nothing ever flips its `stop` column.
"""
import time
import pytest
from app.routers.automation import make_stop_checker, background_task_scraper
from app.models.automation import ScrapeRequest, TaskStatus
from app.db import create_task, get_task, request_stop, delete_task


def _task_id_for(config: dict) -> str:
    import uuid
    task_id = str(uuid.uuid4())
    create_task(task_id, config)
    return task_id


class TestMakeStopCheckerTimeout:
    """Tests for make_stop_checker's self-terminating timeout behavior."""

    def test_does_not_stop_before_timeout(self):
        """A fresh checker with a generous timeout should report stop=False immediately."""
        task_id = _task_id_for({"industry": "x", "locations": ["y"], "limit_per_location": 1})
        should_stop = make_stop_checker(task_id, poll_interval=0.05, max_duration_seconds=5)

        assert should_stop() is False
        assert should_stop.timed_out() is False

        delete_task(task_id)

    def test_times_out_after_max_duration(self):
        """Once max_duration_seconds elapses, the checker should report stop=True and timed_out=True."""
        task_id = _task_id_for({"industry": "x", "locations": ["y"], "limit_per_location": 1})
        should_stop = make_stop_checker(task_id, poll_interval=0.05, max_duration_seconds=0.2)

        assert should_stop() is False

        time.sleep(0.3)

        assert should_stop() is True
        assert should_stop.timed_out() is True

        delete_task(task_id)

    def test_real_stop_flag_is_not_reported_as_timeout(self):
        """A user-initiated stop (DB flag) that fires before the timeout should not be misreported as a timeout."""
        task_id = _task_id_for({"industry": "x", "locations": ["y"], "limit_per_location": 1})
        should_stop = make_stop_checker(task_id, poll_interval=0.01, max_duration_seconds=30)

        request_stop(task_id)
        # Force the running flag true first since request_stop only affects running=true rows
        # (create_task already sets running=true by default, so this should have taken effect).
        time.sleep(0.05)

        assert should_stop() is True
        assert should_stop.timed_out() is False

        delete_task(task_id)

    def test_timeout_flag_stays_true_once_set(self):
        """Once timed_out is latched True, it should stay True on subsequent calls, not flap."""
        task_id = _task_id_for({"industry": "x", "locations": ["y"], "limit_per_location": 1})
        should_stop = make_stop_checker(task_id, poll_interval=0.01, max_duration_seconds=0.1)

        time.sleep(0.2)
        assert should_stop() is True
        assert should_stop.timed_out() is True
        # Call again — should remain latched, not re-derived from elapsed time each call.
        assert should_stop() is True
        assert should_stop.timed_out() is True

        delete_task(task_id)


class TestBackgroundTaskScraperTimeoutIntegration:
    """Tests that a timed-out task is marked ERROR (not STOPPED) with a clear message."""

    def test_task_marked_error_on_timeout(self, monkeypatch):
        """When the scrape loop's stop checker times out, the task should end as ERROR with a timeout message, not STOPPED."""
        # Negative: guarantees the very first should_stop() check (before
        # scrape_google_maps is ever invoked) already reports "timed out" —
        # keeps this test fast and independent of whether Playwright/Chromium
        # is actually installed in the environment running it.
        monkeypatch.setattr("app.routers.automation.MAX_TASK_DURATION_SECONDS", -1)

        import uuid
        task_id = str(uuid.uuid4())
        create_task(task_id, {"industry": "timeout-test", "locations": ["Timeout City"], "limit_per_location": 1})

        request = ScrapeRequest(industry="timeout-test", locations=["Timeout City"], limit_per_location=1)

        # Run synchronously (not via BackgroundTasks/threading) so the assertion
        # below observes the final state deterministically.
        background_task_scraper(task_id, request)

        task = get_task(task_id)
        assert task["status"] == TaskStatus.ERROR.value
        assert "timed out" in (task["error"] or "").lower()
        assert task["running"] is False

        delete_task(task_id)
