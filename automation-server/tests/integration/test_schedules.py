"""
Tests for the scheduled (recurring) scrape API routes.
"""
import pytest


class TestScheduleCRUD:
    """Tests for creating, listing, updating, and deleting schedules via the API."""

    def _create(self, client, user_headers, **overrides):
        payload = {
            "name": "API Test Schedule",
            "industry": "schedule-test-industry",
            "locations": ["Schedule Test City"],
            "limit_per_location": 5,
            "interval_hours": 24,
        }
        payload.update(overrides)
        return client.post("/schedules", headers=user_headers, json=payload)

    def test_create_requires_auth(self, client):
        """Creating a schedule should require an API key or admin secret."""
        response = client.post("/schedules", json={
            "name": "No Auth", "industry": "x", "locations": ["y"], "interval_hours": 24
        })
        assert response.status_code == 401

    def test_create_schedule(self, client, user_headers):
        """A new schedule should be creatable via the API."""
        response = self._create(client, user_headers)

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "API Test Schedule"
        assert data["enabled"] is True

        client.delete(f"/schedules/{data['id']}", headers=user_headers)

    def test_create_requires_positive_interval(self, client, user_headers):
        """interval_hours must be at least 1."""
        response = self._create(client, user_headers, interval_hours=0)
        assert response.status_code == 422

    def test_list_schedules_includes_created(self, client, user_headers):
        """A created schedule should appear in the list."""
        create_response = self._create(client, user_headers)
        schedule_id = create_response.json()["data"]["id"]

        response = client.get("/schedules", headers=user_headers)

        assert response.status_code == 200
        schedules = response.json()["data"]["schedules"]
        assert any(s["id"] == schedule_id for s in schedules)

        client.delete(f"/schedules/{schedule_id}", headers=user_headers)

    def test_update_schedule(self, client, user_headers):
        """A schedule's fields should be updatable, including pausing via enabled=false."""
        create_response = self._create(client, user_headers)
        schedule_id = create_response.json()["data"]["id"]

        response = client.patch(
            f"/schedules/{schedule_id}", headers=user_headers, json={"enabled": False}
        )

        assert response.status_code == 200
        assert response.json()["data"]["enabled"] is False

        client.delete(f"/schedules/{schedule_id}", headers=user_headers)

    def test_update_nonexistent_schedule(self, client, user_headers):
        """Updating a nonexistent schedule should 404."""
        response = client.patch("/schedules/999999999", headers=user_headers, json={"enabled": False})
        assert response.status_code == 404

    def test_delete_schedule(self, client, user_headers):
        """A schedule should be deletable, and gone afterward."""
        create_response = self._create(client, user_headers)
        schedule_id = create_response.json()["data"]["id"]

        response = client.delete(f"/schedules/{schedule_id}", headers=user_headers)
        assert response.status_code == 200

        second_delete = client.delete(f"/schedules/{schedule_id}", headers=user_headers)
        assert second_delete.status_code == 404


class TestRunScheduleNow:
    """Tests for the manual run-now trigger."""

    def _create(self, client, user_headers, **overrides):
        payload = {
            "name": "Run Now Test Schedule",
            "industry": "run-now-test-industry",
            "locations": ["Run Now Test City"],
            "limit_per_location": 1,
            "interval_hours": 24,
        }
        payload.update(overrides)
        return client.post("/schedules", headers=user_headers, json=payload)

    def test_run_now_starts_a_task(self, client, user_headers):
        """POST /schedules/{id}/run-now should immediately start a task."""
        create_response = self._create(client, user_headers)
        schedule_id = create_response.json()["data"]["id"]

        response = client.post(f"/schedules/{schedule_id}/run-now", headers=user_headers)

        assert response.status_code == 200
        task_id = response.json()["data"]["task_id"]
        assert task_id

        task_response = client.get(f"/automation/tasks/{task_id}", headers=user_headers)
        assert task_response.status_code == 200

        client.delete(f"/schedules/{schedule_id}", headers=user_headers)

    def test_run_now_nonexistent_schedule(self, client, user_headers):
        """run-now on a nonexistent schedule should 404."""
        response = client.post("/schedules/999999999/run-now", headers=user_headers)
        assert response.status_code == 404
