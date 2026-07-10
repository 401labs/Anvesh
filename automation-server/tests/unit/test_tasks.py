"""
Tests for automation task database operations.
"""
import uuid
import pytest
from app.db.tasks import (
    create_task,
    get_task,
    list_tasks,
    count_tasks,
    list_all_tasks,
    list_running_tasks,
    get_task_counts,
    set_task_status,
    set_task_running,
    get_task_stop_flag,
    request_stop,
    request_stop_all,
    delete_task,
)


def _task_id() -> str:
    return str(uuid.uuid4())


class TestTaskCreateAndGet:
    """Tests for creating and retrieving tasks."""

    def test_create_task_round_trips_config(self):
        """A created task should be retrievable with the same config it was given."""
        task_id = _task_id()
        config = {"industry": "bakeries", "locations": ["Pune"], "limit_per_location": 5}
        created = create_task(task_id, config)

        assert created["id"] == task_id
        assert created["status"] == "idle"
        assert created["running"] is True
        assert created["stop"] is False
        assert created["config"] == config

        fetched = get_task(task_id)
        assert fetched["config"] == config

        delete_task(task_id)

    def test_get_task_not_found(self):
        """A non-existent task ID should return None."""
        assert get_task("non-existent-task-id") is None


class TestTaskListingAndPagination:
    """Tests for listing/counting tasks."""

    def test_list_and_count_tasks(self):
        """A newly created task should show up in list_tasks and count_tasks."""
        task_id = _task_id()
        create_task(task_id, {"industry": "gyms", "locations": ["Delhi"], "limit_per_location": 1})

        total_before = count_tasks()
        page = list_tasks(limit=total_before + 5, offset=0)

        assert total_before >= 1
        assert any(t["id"] == task_id for t in page)

        delete_task(task_id)

    def test_list_all_tasks_includes_created(self):
        """list_all_tasks (admin, unbounded) should include a freshly created task."""
        task_id = _task_id()
        create_task(task_id, {"industry": "salons", "locations": ["Pune"], "limit_per_location": 1})

        all_tasks = list_all_tasks()
        assert any(t["id"] == task_id for t in all_tasks)

        delete_task(task_id)


class TestTaskStatusAndRunning:
    """Tests for status/running transitions."""

    def test_set_task_status_updates_status_and_error(self):
        """set_task_status should update both status and error fields."""
        task_id = _task_id()
        create_task(task_id, {"industry": "cafes", "locations": ["Chennai"], "limit_per_location": 1})

        set_task_status(task_id, "error", error="boom")
        task = get_task(task_id)

        assert task["status"] == "error"
        assert task["error"] == "boom"

        delete_task(task_id)

    def test_set_task_running_updates_flag(self):
        """set_task_running should flip the running flag."""
        task_id = _task_id()
        create_task(task_id, {"industry": "spas", "locations": ["Goa"], "limit_per_location": 1})

        set_task_running(task_id, False)
        task = get_task(task_id)

        assert task["running"] is False
        assert task_id not in [t["id"] for t in list_running_tasks()]

        delete_task(task_id)


class TestTaskStop:
    """Tests for stop-flag behavior."""

    def test_request_stop_flags_running_task(self):
        """request_stop should flip the stop flag on a running task and return True."""
        task_id = _task_id()
        create_task(task_id, {"industry": "hotels", "locations": ["Jaipur"], "limit_per_location": 1})

        result = request_stop(task_id)

        assert result is True
        assert get_task_stop_flag(task_id) is True

        delete_task(task_id)

    def test_request_stop_returns_false_for_finished_task(self):
        """request_stop should return False for a task that's no longer running."""
        task_id = _task_id()
        create_task(task_id, {"industry": "clinics", "locations": ["Nagpur"], "limit_per_location": 1})
        set_task_running(task_id, False)

        result = request_stop(task_id)

        assert result is False
        assert get_task_stop_flag(task_id) is False

        delete_task(task_id)

    def test_request_stop_all_only_affects_running_tasks(self):
        """request_stop_all should flag running tasks and skip already-finished ones."""
        running_id = _task_id()
        finished_id = _task_id()
        create_task(running_id, {"industry": "bars", "locations": ["Kochi"], "limit_per_location": 1})
        create_task(finished_id, {"industry": "bars", "locations": ["Kochi"], "limit_per_location": 1})
        set_task_running(finished_id, False)

        count_stopped = request_stop_all()

        assert count_stopped >= 1
        assert get_task_stop_flag(running_id) is True
        assert get_task_stop_flag(finished_id) is False

        delete_task(running_id)
        delete_task(finished_id)


class TestTaskCounts:
    """Tests for aggregate task counts."""

    def test_get_task_counts_reflects_status(self):
        """get_task_counts should reflect a task's current status and running flag."""
        task_id = _task_id()
        create_task(task_id, {"industry": "resorts", "locations": ["Shimla"], "limit_per_location": 1})
        set_task_status(task_id, "completed")
        set_task_running(task_id, False)

        counts = get_task_counts()

        assert counts["total"] >= 1
        assert counts["completed"] >= 1

        delete_task(task_id)


class TestTaskDeletion:
    """Tests for deleting tasks."""

    def test_delete_task_removes_it(self):
        """A deleted task should no longer be retrievable."""
        task_id = _task_id()
        create_task(task_id, {"industry": "pubs", "locations": ["Mumbai"], "limit_per_location": 1})

        result = delete_task(task_id)

        assert result is True
        assert get_task(task_id) is None

    def test_delete_task_not_found(self):
        """Deleting a non-existent task should return False."""
        assert delete_task("non-existent-task-id") is False
