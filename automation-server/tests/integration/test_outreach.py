"""
Integration tests for outreach routes: email templates, sending, and logs.
"""
import pytest


class TestEmailTemplates:
    """Tests for the template CRUD endpoints."""

    def _create_template(self, client, user_headers, **overrides):
        payload = {
            "name": "Outreach Template",
            "subject": "Hello {business_name}",
            "body": "We noticed your business could use a website.",
        }
        payload.update(overrides)
        return client.post("/outreach/templates", headers=user_headers, json=payload)

    def test_templates_require_auth(self, client):
        """Templates endpoint should require an API key or admin secret (401 when neither is given)."""
        response = client.get("/outreach/templates")

        assert response.status_code == 401

    def test_create_template(self, client, user_headers):
        """A new template should be creatable via the API."""
        response = self._create_template(client, user_headers, name="Create Test Template")

        assert response.status_code == 201
        data = response.json()
        assert data["success"] == True
        assert data["data"]["name"] == "Create Test Template"
        template_id = data["data"]["id"]

        client.delete(f"/outreach/templates/{template_id}", headers=user_headers)

    def test_list_templates_includes_created(self, client, user_headers):
        """Listing templates should include a freshly created template."""
        create_response = self._create_template(client, user_headers, name="List Test Template")
        template_id = create_response.json()["data"]["id"]

        response = client.get("/outreach/templates", headers=user_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert any(t["id"] == template_id for t in data["templates"])

        client.delete(f"/outreach/templates/{template_id}", headers=user_headers)

    def test_update_template(self, client, user_headers):
        """A template's fields should be partially updatable."""
        create_response = self._create_template(client, user_headers, name="Update Test Template")
        template_id = create_response.json()["data"]["id"]

        response = client.patch(
            f"/outreach/templates/{template_id}",
            headers=user_headers,
            json={"name": "Updated Name"}
        )

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated Name"

        client.delete(f"/outreach/templates/{template_id}", headers=user_headers)

    def test_update_template_not_found(self, client, user_headers):
        """Updating a non-existent template should 404."""
        response = client.patch(
            "/outreach/templates/999999999",
            headers=user_headers,
            json={"name": "Nope"}
        )

        assert response.status_code == 404

    def test_delete_template(self, client, user_headers):
        """A template should be deletable, and gone afterward (second delete 404s)."""
        create_response = self._create_template(client, user_headers, name="Delete Test Template")
        template_id = create_response.json()["data"]["id"]

        response = client.delete(f"/outreach/templates/{template_id}", headers=user_headers)
        assert response.status_code == 200

        second_delete = client.delete(f"/outreach/templates/{template_id}", headers=user_headers)
        assert second_delete.status_code == 404

    def test_delete_nonexistent_template(self, client, user_headers):
        """Deleting a non-existent template should 404."""
        response = client.delete("/outreach/templates/999999999", headers=user_headers)
        assert response.status_code == 404


class TestSendEmail:
    """Tests for the templated email sending endpoint."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "Outreach Send Test Business",
            "industry": "outreach-testing",
            "location": "Sendville",
            "address": "1 Send Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_send_requires_auth(self, client):
        """Send endpoint should require an API key or admin secret (401 when neither is given)."""
        response = client.post(
            "/outreach/email/send",
            json={"lead_ids": [1], "subject": "Hi", "body": "Body"}
        )

        assert response.status_code == 401

    def test_send_requires_template_xor_subject_body(self, client, user_headers):
        """Providing neither template_id nor subject+body should 400."""
        lead_response = self._create_lead(
            client, user_headers, business_name="Neither Provided Business", email="neither@example.com"
        )
        lead_id = lead_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_id]}
        )

        assert response.status_code == 400

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_send_rejects_both_template_and_subject_body(self, client, user_headers):
        """Providing both template_id and subject+body should 400."""
        lead_response = self._create_lead(
            client, user_headers, business_name="Both Provided Business", email="both@example.com"
        )
        lead_id = lead_response.json()["data"]["id"]

        template_response = client.post(
            "/outreach/templates",
            headers=user_headers,
            json={"name": "Both Test Template", "subject": "Subj", "body": "Body"}
        )
        template_id = template_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={
                "lead_ids": [lead_id],
                "template_id": template_id,
                "subject": "Override Subject",
                "body": "Override Body",
            }
        )

        assert response.status_code == 400

        client.delete(f"/outreach/templates/{template_id}", headers=user_headers)
        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_send_to_lead_without_email_is_skipped(self, client, user_headers):
        """A lead with no email on file should be reported in skipped_no_email rather than erroring."""
        lead_response = self._create_lead(client, user_headers, business_name="No Email Send Business")
        lead_id = lead_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_id], "subject": "Hi", "body": "Body"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert lead_id in data["skipped_no_email"]

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_send_to_nonexistent_lead_is_skipped(self, client, user_headers):
        """A nonexistent lead id should be reported in skipped_no_lead rather than erroring."""
        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [999999999], "subject": "Hi", "body": "Body"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert 999999999 in data["skipped_no_lead"]

    def test_send_to_single_valid_recipient_sends_synchronously(self, client, user_headers):
        """A single valid recipient sends synchronously; with SMTP unconfigured, sent is False and error mentions SMTP."""
        lead_response = self._create_lead(
            client, user_headers, business_name="Single Send Business", email="single@example.com"
        )
        lead_id = lead_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_id], "subject": "Hi", "body": "Body"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert "result" in data
        result = data["result"]
        assert result["lead_id"] == lead_id
        assert result["sent"] is False
        assert "smtp" in result["error"].lower()

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_send_to_multiple_valid_recipients_is_queued(self, client, user_headers):
        """Multiple valid recipients should be queued via a background task instead of sent synchronously."""
        first = self._create_lead(client, user_headers, business_name="Queued Business One", email="one@example.com")
        second = self._create_lead(client, user_headers, business_name="Queued Business Two", email="two@example.com")
        first_id = first.json()["data"]["id"]
        second_id = second.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [first_id, second_id], "subject": "Hi", "body": "Body"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data["queued"], int)
        assert data["queued"] == 2

        client.delete(f"/automation/leads/{first_id}", headers=user_headers)
        client.delete(f"/automation/leads/{second_id}", headers=user_headers)

    def test_send_with_template_id(self, client, user_headers):
        """Sending with a template_id (instead of subject+body) should be accepted and attempt a send."""
        lead_response = self._create_lead(
            client, user_headers, business_name="Template Send Business", email="template@example.com"
        )
        lead_id = lead_response.json()["data"]["id"]

        template_response = client.post(
            "/outreach/templates",
            headers=user_headers,
            json={"name": "Send Test Template", "subject": "Template Subject", "body": "Template Body"}
        )
        template_id = template_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_id], "template_id": template_id}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["result"]["lead_id"] == lead_id
        assert data["result"]["sent"] is False

        client.delete(f"/outreach/templates/{template_id}", headers=user_headers)
        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)


class TestOutreachLogs:
    """Tests for the outreach logs listing endpoint."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "Outreach Logs Test Business",
            "industry": "outreach-testing",
            "location": "Logsville",
            "address": "1 Logs Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_logs_requires_auth(self, client):
        """Logs endpoint should require an API key or admin secret (401 when neither is given)."""
        response = client.get("/outreach/logs")

        assert response.status_code == 401

    def test_logs_shape(self, client, user_headers):
        """Logs endpoint should return the expected pagination envelope."""
        response = client.get("/outreach/logs", headers=user_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data["logs"], list)
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    def test_send_creates_matching_log_entry(self, client, user_headers):
        """A failed send should still be logged, with channel=email and status=failed, visible in that lead's logs."""
        lead_response = self._create_lead(
            client, user_headers, business_name="Logged Send Business", email="logged@example.com"
        )
        lead_id = lead_response.json()["data"]["id"]

        client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_id], "subject": "Hi", "body": "Body"}
        )

        response = client.get(f"/outreach/logs?lead_id={lead_id}", headers=user_headers)

        assert response.status_code == 200
        logs = response.json()["data"]["logs"]
        assert len(logs) >= 1
        assert any(l["channel"] == "email" and l["status"] == "failed" for l in logs)

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)
