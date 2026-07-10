"""
Edge-case tests for scheduled (recurring) scrapes: create-time validation
boundaries, enabled/disabled toggling against the due-check, run-now bypassing
the due-check entirely, firing multiple due schedules in one poll tick, and
confirming a deleted schedule doesn't linger in either query.

Background scrape threads started by fire_schedule/run-now will fail (or, per
an earlier probe of this sandbox, sometimes hang indefinitely) because no
Playwright browser is installed here — that's expected and irrelevant to these
tests. Every assertion below is about schedule/task *state* (rows, timestamps,
counts), never about a scrape actually completing.
"""
from datetime import timedelta
from app.db import get_due_schedules
from app.db.schedules import (
    create_schedule,
    get_schedule,
    list_schedules,
    delete_schedule,
    mark_schedule_ran,
)
from app.services.scheduler import run_due_schedules_once


class TestScheduleValidationBoundaries:
    """Tests for ScheduleCreate's field validation boundaries via the API."""

    def _payload(self, **overrides):
        payload = {
            "name": "Validation Boundary Schedule",
            "industry": "validation-test",
            "locations": ["Validation City"],
            "limit_per_location": 5,
            "interval_hours": 24,
        }
        payload.update(overrides)
        return payload

    def test_interval_hours_zero_is_rejected(self, client, user_headers):
        """interval_hours has ge=1 — 0 must 422, not be silently accepted as 'run constantly'."""
        response = client.post("/schedules", headers=user_headers, json=self._payload(interval_hours=0))
        assert response.status_code == 422

    def test_interval_hours_negative_is_rejected(self, client, user_headers):
        """A negative interval_hours must also 422 at create time."""
        response = client.post("/schedules", headers=user_headers, json=self._payload(interval_hours=-5))
        assert response.status_code == 422

    def test_missing_locations_field_is_rejected(self, client, user_headers):
        """locations is a required field — omitting it entirely must 422 (an empty list, by contrast, is a valid — if useless — value, since there's no min_length constraint)."""
        payload = self._payload()
        del payload["locations"]
        response = client.post("/schedules", headers=user_headers, json=payload)
        assert response.status_code == 422

    def test_limit_per_location_below_negative_one_is_rejected(self, client, user_headers):
        """limit_per_location has ge=-1 (-1 means unlimited) — anything lower like -2 must 422."""
        response = client.post("/schedules", headers=user_headers, json=self._payload(limit_per_location=-2))
        assert response.status_code == 422

    def test_missing_industry_field_is_rejected(self, client, user_headers):
        """industry is also a required field — omitting it must 422."""
        payload = self._payload()
        del payload["industry"]
        response = client.post("/schedules", headers=user_headers, json=payload)
        assert response.status_code == 422


class TestToggleEnabledAgainstDueCheck:
    """Tests that disabling/re-enabling a schedule is honored by get_due_schedules, independent of next_run_at."""

    def test_disabling_excludes_from_due_even_when_forced_past_due(self, client, user_headers):
        """A schedule paused via PATCH enabled=false must be excluded from get_due_schedules even with next_run_at forced into the past — then reappear once re-enabled."""
        create_response = client.post(
            "/schedules",
            headers=user_headers,
            json={
                "name": "Toggle Enabled Schedule",
                "industry": "toggle-test",
                "locations": ["Toggle City"],
                "limit_per_location": 1,
                "interval_hours": 24,
            },
        )
        schedule_id = create_response.json()["data"]["id"]

        # Force it into the past — would be due if enabled.
        mark_schedule_ran(schedule_id, -1)
        assert any(s["id"] == schedule_id for s in get_due_schedules())

        disable_response = client.patch(f"/schedules/{schedule_id}", headers=user_headers, json={"enabled": False})
        assert disable_response.status_code == 200
        assert disable_response.json()["data"]["enabled"] is False

        due_while_disabled = get_due_schedules()
        assert not any(s["id"] == schedule_id for s in due_while_disabled)

        enable_response = client.patch(f"/schedules/{schedule_id}", headers=user_headers, json={"enabled": True})
        assert enable_response.status_code == 200
        assert enable_response.json()["data"]["enabled"] is True

        due_after_reenable = get_due_schedules()
        assert any(s["id"] == schedule_id for s in due_after_reenable)

        client.delete(f"/schedules/{schedule_id}", headers=user_headers)


class TestRunNowBypassesDueCheck:
    """Tests that run-now fires regardless of next_run_at, and correctly resets it."""

    def test_run_now_fires_a_far_future_schedule_and_resets_next_run_at(self, client, user_headers):
        """A schedule with next_run_at pushed far into the future should still fire on run-now, and next_run_at should end up relative to interval_hours, not left at the far-future value."""
        create_response = client.post(
            "/schedules",
            headers=user_headers,
            json={
                "name": "Run Now Bypass Schedule",
                "industry": "run-now-bypass-test",
                "locations": ["Bypass City"],
                "limit_per_location": 1,
                "interval_hours": 6,
            },
        )
        schedule_id = create_response.json()["data"]["id"]

        # Push it absurdly far into the future — many years away.
        mark_schedule_ran(schedule_id, 999999)
        far_future_schedule = get_schedule(schedule_id)
        assert not any(s["id"] == schedule_id for s in get_due_schedules())

        response = client.post(f"/schedules/{schedule_id}/run-now", headers=user_headers)

        assert response.status_code == 200
        task_id = response.json()["data"]["task_id"]
        assert task_id

        after = get_schedule(schedule_id)
        assert after["last_run_at"] is not None
        # next_run_at must have moved back drastically from the far-future value...
        assert after["next_run_at"] < far_future_schedule["next_run_at"]
        # ...and now sit close to interval_hours (6h) after last_run_at, not
        # some arbitrary value — same Postgres-vs-Postgres timestamp
        # comparison pattern as test_fire_schedule_creates_task_and_advances_next_run,
        # to avoid comparing against Python's local clock.
        assert after["next_run_at"] - after["last_run_at"] >= timedelta(hours=5, minutes=55)
        assert after["next_run_at"] - after["last_run_at"] < timedelta(hours=6, minutes=5)

        client.delete(f"/schedules/{schedule_id}", headers=user_headers)


class TestMultipleSchedulesDueAtOnce:
    """Tests that a single poll tick processes the whole due-set, not just one schedule."""

    def test_run_due_schedules_once_fires_every_due_schedule_in_one_tick(self, user_headers, client):
        """Force 3 schedules due at once and confirm run_due_schedules_once's returned count covers all of them, not just the first."""
        created_ids = []
        for i in range(3):
            schedule = create_schedule(
                f"Multi Due Schedule {i}",
                "multi-due-test",
                [f"Multi Due City {i}"],
                1,
                24,
            )
            created_ids.append(schedule["id"])
            mark_schedule_ran(schedule["id"], -1)  # force into the past -> due

        due_before = get_due_schedules()
        assert all(any(s["id"] == cid for s in due_before) for cid in created_ids)

        fired_count = run_due_schedules_once()

        assert fired_count >= len(created_ids)

        # Firing must have advanced next_run_at into the future for each of
        # ours, so none of them should still show up as due right after.
        due_after = get_due_schedules()
        assert not any(s["id"] in created_ids for s in due_after)

        for schedule_id in created_ids:
            delete_schedule(schedule_id)


class TestDeletedScheduleLeavesNoTrace:
    """Tests that deleting a schedule removes it from both due and list queries, even with a far-future next_run_at."""

    def test_delete_removes_from_due_and_list_queries(self, user_headers, client):
        """A deleted schedule (even one with a far-future next_run_at) must not appear in get_due_schedules() or list_schedules() afterward."""
        schedule = create_schedule(
            "Deletion Trace Schedule",
            "deletion-trace-test",
            ["Deletion Trace City"],
            1,
            24,
        )
        schedule_id = schedule["id"]
        mark_schedule_ran(schedule_id, 999999)  # far future, deliberately not due

        assert any(s["id"] == schedule_id for s in list_schedules())
        assert not any(s["id"] == schedule_id for s in get_due_schedules())

        result = delete_schedule(schedule_id)
        assert result is True

        assert not any(s["id"] == schedule_id for s in list_schedules())
        assert not any(s["id"] == schedule_id for s in get_due_schedules())
        assert get_schedule(schedule_id) is None
