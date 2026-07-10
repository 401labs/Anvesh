"""
Tests for the runtime email configuration API (SMTP/IMAP settings).
"""
import pytest
from app.db import set_setting


class TestEmailConfig:
    """Tests for GET/PUT /config/email."""

    def test_get_requires_admin(self, client, user_headers):
        """A regular API key should not be able to read email config — admin only."""
        response = client.get("/config/email", headers=user_headers)
        assert response.status_code in (401, 403, 422)

    def test_update_requires_admin(self, client, user_headers):
        """A regular API key should not be able to update email config — admin only."""
        response = client.put("/config/email", headers=user_headers, json={"smtp_host": "smtp.example.com"})
        assert response.status_code in (401, 403, 422)

    def test_get_returns_effective_config_shape(self, client, admin_headers):
        """GET should return the expected fields, never the raw app password."""
        response = client.get("/config/email", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert "smtp_host" in data
        assert "smtp_port" in data
        assert "smtp_user" in data
        assert "smtp_from_name" in data
        assert "imap_host" in data
        assert "imap_port" in data
        assert "smtp_app_password_set" in data
        assert "smtp_app_password" not in data

    def test_update_overrides_and_persists(self, client, admin_headers):
        """Updating a field should be reflected on the next GET."""
        try:
            response = client.put(
                "/config/email", headers=admin_headers,
                json={"smtp_host": "smtp.config-test.example.com", "smtp_port": 2525}
            )
            assert response.status_code == 200
            assert response.json()["data"]["smtp_host"] == "smtp.config-test.example.com"
            assert response.json()["data"]["smtp_port"] == 2525

            get_response = client.get("/config/email", headers=admin_headers)
            assert get_response.json()["data"]["smtp_host"] == "smtp.config-test.example.com"
            assert get_response.json()["data"]["smtp_port"] == 2525
        finally:
            set_setting("smtp_host", None)
            set_setting("smtp_port", None)

    def test_app_password_set_flag_reflects_state(self, client, admin_headers):
        """smtp_app_password_set should become true after setting a password, false after clearing it."""
        try:
            client.put("/config/email", headers=admin_headers, json={"smtp_app_password": "test-app-password"})
            response = client.get("/config/email", headers=admin_headers)
            assert response.json()["data"]["smtp_app_password_set"] is True

            client.put("/config/email", headers=admin_headers, json={"smtp_app_password": ""})
            response = client.get("/config/email", headers=admin_headers)
            assert response.json()["data"]["smtp_app_password_set"] is False
        finally:
            set_setting("smtp_app_password", None)

    def test_empty_string_clears_override(self, client, admin_headers):
        """Sending an empty string for a field should clear the DB override, reverting to the env default."""
        try:
            client.put("/config/email", headers=admin_headers, json={"smtp_host": "smtp.temp-override.example.com"})
            assert client.get("/config/email", headers=admin_headers).json()["data"]["smtp_host"] == "smtp.temp-override.example.com"

            client.put("/config/email", headers=admin_headers, json={"smtp_host": ""})
            reverted = client.get("/config/email", headers=admin_headers).json()["data"]["smtp_host"]
            assert reverted != "smtp.temp-override.example.com"
        finally:
            set_setting("smtp_host", None)

    def test_partial_update_leaves_other_fields_untouched(self, client, admin_headers):
        """Updating one field should not affect other previously-set fields."""
        try:
            client.put("/config/email", headers=admin_headers, json={"smtp_host": "smtp.partial-a.example.com"})
            client.put("/config/email", headers=admin_headers, json={"smtp_from_name": "Partial Test"})

            response = client.get("/config/email", headers=admin_headers)
            data = response.json()["data"]
            assert data["smtp_host"] == "smtp.partial-a.example.com"
            assert data["smtp_from_name"] == "Partial Test"
        finally:
            set_setting("smtp_host", None)
            set_setting("smtp_from_name", None)
