"""
Tests for scheduled (recurring) scrape database operations and the scheduler.
"""
from datetime import timedelta
from app.db.schedules import (
    create_schedule,
    get_schedule,
    list_schedules,
    update_schedule,
    delete_schedule,
    get_due_schedules,
    mark_schedule_ran,
)
from app.services.scheduler import fire_schedule
from app.db import get_task


class TestScheduleCRUD:
    """Tests for creating, reading, updating, and deleting schedules."""

    def test_create_and_get_schedule(self):
        """A created schedule should round-trip through get_schedule."""
        schedule = create_schedule("Test Schedule", "bakeries", ["Pune"], -1, 24)

        assert schedule["name"] == "Test Schedule"
        assert schedule["industry"] == "bakeries"
        assert schedule["locations"] == ["Pune"]
        assert schedule["interval_hours"] == 24
        assert schedule["enabled"] is True

        fetched = get_schedule(schedule["id"])
        assert fetched["locations"] == ["Pune"]

        delete_schedule(schedule["id"])

    def test_list_schedules_includes_created(self):
        """A newly created schedule should show up in list_schedules."""
        schedule = create_schedule("List Test Schedule", "cafes", ["Goa"], 10, 48)

        all_schedules = list_schedules()
        assert any(s["id"] == schedule["id"] for s in all_schedules)

        delete_schedule(schedule["id"])

    def test_update_schedule_changes_field(self):
        """update_schedule should change only the fields passed."""
        schedule = create_schedule("Update Test Schedule", "gyms", ["Delhi"], -1, 24)

        updated = update_schedule(schedule["id"], {"enabled": False, "interval_hours": 12})

        assert updated["enabled"] is False
        assert updated["interval_hours"] == 12
        assert updated["industry"] == "gyms"  # untouched field preserved

        delete_schedule(schedule["id"])

    def test_delete_schedule_removes_it(self):
        """A deleted schedule should no longer be retrievable."""
        schedule = create_schedule("Delete Test Schedule", "salons", ["Chennai"], -1, 24)

        result = delete_schedule(schedule["id"])

        assert result is True
        assert get_schedule(schedule["id"]) is None

    def test_delete_nonexistent_schedule_returns_false(self):
        """Deleting a schedule that doesn't exist should return False."""
        assert delete_schedule(999999999) is False


class TestDueSchedules:
    """Tests for the due-schedule polling query."""

    def test_get_due_schedules_includes_past_due(self):
        """A schedule with next_run_at in the past should be considered due."""
        schedule = create_schedule("Due Test Schedule", "spas", ["Jaipur"], -1, 24)
        update_schedule(schedule["id"], {})  # no-op, just confirming update path works with empty fields
        # Force it due with a negative interval (computed in SQL, relative to
        # Postgres's own clock — see mark_schedule_ran's docstring for why).
        mark_schedule_ran(schedule["id"], -1)

        due = get_due_schedules()
        assert any(s["id"] == schedule["id"] for s in due)

        delete_schedule(schedule["id"])

    def test_get_due_schedules_excludes_future(self):
        """A schedule with next_run_at in the future should not be considered due."""
        schedule = create_schedule("Future Test Schedule", "spas", ["Jaipur"], -1, 24)
        mark_schedule_ran(schedule["id"], 5)

        due = get_due_schedules()
        assert not any(s["id"] == schedule["id"] for s in due)

        delete_schedule(schedule["id"])

    def test_get_due_schedules_excludes_disabled(self):
        """A disabled schedule should not be considered due even if next_run_at is past."""
        schedule = create_schedule("Disabled Test Schedule", "spas", ["Jaipur"], -1, 24)
        mark_schedule_ran(schedule["id"], -1)
        update_schedule(schedule["id"], {"enabled": False})

        due = get_due_schedules()
        assert not any(s["id"] == schedule["id"] for s in due)

        delete_schedule(schedule["id"])


class TestFireSchedule:
    """Tests for firing a schedule (starting a task and advancing next_run_at)."""

    def test_fire_schedule_creates_task_and_advances_next_run(self):
        """fire_schedule should create a task row and push next_run_at forward by interval_hours."""
        schedule = create_schedule("Fire Test Schedule", "fire-test-industry", ["Fire Test City"], 1, 6)

        task_id = fire_schedule(schedule)

        task = get_task(task_id)
        assert task is not None
        assert task["config"]["industry"] == "fire-test-industry"

        after = get_schedule(schedule["id"])
        assert after["last_run_at"] is not None
        # Compare the two Postgres-returned timestamps against each other, not
        # against Python's local clock (see mark_schedule_ran's docstring).
        assert after["next_run_at"] - after["last_run_at"] >= timedelta(hours=5, minutes=55)

        delete_schedule(schedule["id"])
