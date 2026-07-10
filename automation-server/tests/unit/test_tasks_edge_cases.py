"""
Edge-case unit tests for automation task database operations: double-stop
idempotency, request_stop_all with nothing running, status-transition
freshness, stop-flag polling correctness, and pagination-vs-count consistency.
"""
import time
import uuid
from app.db.tasks import (
    create_task,
    get_task,
    list_tasks,
    count_tasks,
    list_running_tasks,
    set_task_status,
    set_task_running,
    get_task_stop_flag,
    request_stop,
    request_stop_all,
    delete_task,
)


def _task_id() -> str:
    return str(uuid.uuid4())


class TestDoubleStopIdempotency:
    """Tests that repeated stop requests on a task are safe, not errors."""

    def test_stopping_an_already_stopped_task_twice_returns_false_both_times(self):
        """Once a task is no longer running, calling request_stop on it repeatedly should keep returning False, never raise."""
        task_id = _task_id()
        create_task(task_id, {"industry": "idempotency-test", "locations": ["Pune"], "limit_per_location": 1})

        # First stop: task is running, so this flags it and returns True.
        assert request_stop(task_id) is True

        # Simulate the scraper noticing the flag and finishing (what
        # background_task_scraper's `finally` does once the loop breaks).
        set_task_running(task_id, False)

        # Second stop: task is no longer running.
        first_repeat = request_stop(task_id)
        # Third stop: repeat again — must stay False, not error or flip back to True.
        second_repeat = request_stop(task_id)

        assert first_repeat is False
        assert second_repeat is False
        # The stop flag itself doesn't get reset just because running was
        # already false — it was set True on the first call and stays there.
        assert get_task_stop_flag(task_id) is True

        delete_task(task_id)


class TestRequestStopAllWithNoRunningTasks:
    """Tests for request_stop_all when there is nothing to stop."""

    def test_request_stop_all_returns_zero_when_nothing_running(self):
        """With no running tasks in the table, request_stop_all should return 0 without error."""
        # This suite runs against a real, shared Postgres test DB (nothing is
        # mocked/rolled back), so drain any tasks left running by other tests
        # (e.g. scheduler tests whose background scrape thread never gets to
        # finish in a sandbox with no Playwright browser installed) to get a
        # clean baseline rather than assuming one.
        for stale in list_running_tasks():
            set_task_running(stale["id"], False)

        assert list_running_tasks() == []

        result = request_stop_all()

        assert result == 0


class TestTaskStatusTransitions:
    """Tests that status transitions are visible immediately after each write."""

    def test_status_transitions_are_reflected_immediately(self):
        """idle -> running -> completed should each be visible via get_task right after the corresponding set_task_status call."""
        task_id = _task_id()
        created = create_task(task_id, {"industry": "transitions-test", "locations": ["Delhi"], "limit_per_location": 1})
        assert created["status"] == "idle"
        assert get_task(task_id)["status"] == "idle"

        assert set_task_status(task_id, "running") is True
        assert get_task(task_id)["status"] == "running"

        assert set_task_status(task_id, "completed") is True
        assert get_task(task_id)["status"] == "completed"

        delete_task(task_id)

    def test_status_transition_to_error_carries_the_error_message_immediately(self):
        """A transition straight to 'error' should show both the new status and error message on the very next read."""
        task_id = _task_id()
        create_task(task_id, {"industry": "transitions-test", "locations": ["Delhi"], "limit_per_location": 1})

        set_task_status(task_id, "running")
        assert get_task(task_id)["status"] == "running"

        set_task_status(task_id, "error", error="boom: something broke")
        task = get_task(task_id)
        assert task["status"] == "error"
        assert task["error"] == "boom: something broke"

        delete_task(task_id)


class TestStopFlagPolling:
    """Tests that get_task_stop_flag reads the live DB value correctly under repeated polling."""

    def test_repeated_polls_reflect_current_value_and_are_fast(self):
        """Many back-to-back get_task_stop_flag reads (simulating make_stop_checker's throttled poller) should all reflect the true current DB value and complete quickly."""
        task_id = _task_id()
        create_task(task_id, {"industry": "poll-test", "locations": ["Goa"], "limit_per_location": 1})

        # Before any stop request, every poll should read False.
        start = time.monotonic()
        pre_stop_reads = [get_task_stop_flag(task_id) for _ in range(25)]
        elapsed_pre = time.monotonic() - start

        assert all(read is False for read in pre_stop_reads)
        assert elapsed_pre < 5.0

        request_stop(task_id)

        # After the stop request, every subsequent poll should read True —
        # proving each call re-reads the DB rather than caching a stale value.
        start = time.monotonic()
        post_stop_reads = [get_task_stop_flag(task_id) for _ in range(25)]
        elapsed_post = time.monotonic() - start

        assert all(read is True for read in post_stop_reads)
        assert elapsed_post < 5.0

        delete_task(task_id)

    def test_polling_a_nonexistent_task_consistently_returns_false(self):
        """Polling a task ID that doesn't exist should return False every time, not raise."""
        reads = [get_task_stop_flag("does-not-exist-" + str(i)) for i in range(10)]
        assert all(read is False for read in reads)


class TestPaginationBoundary:
    """Tests that count_tasks() reflects the true total regardless of the page size used for list_tasks."""

    def test_count_matches_total_regardless_of_requested_page_size(self):
        """count_tasks() should be stable and correct whether list_tasks was just called with limit=1 or limit=200."""
        created_ids = [_task_id() for _ in range(3)]
        for i, task_id in enumerate(created_ids):
            create_task(task_id, {"industry": "pagination-boundary-test", "locations": [f"City{i}"], "limit_per_location": 1})

        total = count_tasks()
        assert total >= 3

        small_page = list_tasks(limit=1, offset=0)
        large_page = list_tasks(limit=200, offset=0)

        assert len(small_page) == 1
        assert len(large_page) == min(total, 200)

        # Requesting different page sizes must never change the true total.
        assert count_tasks() == total

        for task_id in created_ids:
            delete_task(task_id)

        assert count_tasks() == total - 3
