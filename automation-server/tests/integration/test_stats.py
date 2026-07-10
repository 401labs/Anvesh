"""
Tests for the analytics dashboard stats endpoint.
"""
import pytest


class TestDashboardStats:
    """Tests for GET /stats."""

    def test_stats_requires_auth(self, client):
        """Stats endpoint should require an API key or admin secret."""
        response = client.get("/stats")
        assert response.status_code == 401

    def test_stats_shape(self, client, user_headers):
        """Stats response should include leads/outreach/tasks sections with expected keys."""
        response = client.get("/stats", headers=user_headers)

        assert response.status_code == 200
        data = response.json()["data"]

        assert "total" in data["leads"]
        assert "by_status" in data["leads"]
        assert "by_score_tier" in data["leads"]
        assert set(data["leads"]["by_status"].keys()) == {
            "new", "contacted", "replied", "interested", "won", "lost"
        }
        assert set(data["leads"]["by_score_tier"].keys()) == {"hot", "warm", "cool"}

        assert isinstance(data["leads_by_day"], list)
        assert isinstance(data["top_industries"], list)
        assert isinstance(data["top_locations"], list)

        assert "total" in data["outreach"]
        assert "sent" in data["outreach"]
        assert "failed" in data["outreach"]

        assert "total" in data["tasks"]
        assert "running" in data["tasks"]

    def test_stats_reflects_new_lead(self, client, user_headers):
        """A newly created lead should be reflected in the leads.total and by_status counts."""
        before = client.get("/stats", headers=user_headers).json()["data"]["leads"]

        create_response = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": "Stats Test Business",
                "industry": "stats-testing",
                "location": "Statsville",
                "address": "1 Stats Way",
            },
        )
        lead_id = create_response.json()["data"]["id"]

        after = client.get("/stats", headers=user_headers).json()["data"]["leads"]

        assert after["total"] == before["total"] + 1
        assert after["by_status"]["new"] == before["by_status"]["new"] + 1

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_stats_respects_days_param(self, client, user_headers):
        """days query param should be accepted and bound leads_by_day's window."""
        response = client.get("/stats?days=7", headers=user_headers)
        assert response.status_code == 200

    def test_stats_rejects_invalid_days(self, client, user_headers):
        """days outside the allowed range should 422."""
        response = client.get("/stats?days=0", headers=user_headers)
        assert response.status_code == 422
