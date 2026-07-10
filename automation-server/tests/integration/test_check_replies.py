"""
Tests for POST /outreach/check-replies.
"""
import pytest


class TestCheckReplies:
    """Tests for the manual reply-check trigger."""

    def test_check_replies_requires_auth(self, client):
        """Checking for replies should require an API key or admin secret."""
        response = client.post("/outreach/check-replies")
        assert response.status_code == 401

    def test_check_replies_returns_zero_when_unconfigured(self, client, user_headers):
        """With IMAP unconfigured in the test env, this should succeed with matched=0, not error."""
        response = client.post("/outreach/check-replies", headers=user_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["matched"] == 0
