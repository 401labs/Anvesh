"""
Tests for outreach database operations: email templates and outreach logs.
"""
import pytest
from app.db.outreach import (
    create_template,
    get_template,
    list_templates,
    update_template,
    delete_template,
    create_log,
    list_logs,
    count_logs,
)
from app.db import create_lead, delete_lead


def _make_lead(**overrides):
    """Create a throwaway lead for attaching outreach logs to."""
    payload = {
        "business_name": "Outreach Unit Test Business",
        "industry": "outreach-testing",
        "location": "Outreachville",
        "address": "1 Outreach Way",
    }
    payload.update(overrides)
    return create_lead(payload)


class TestEmailTemplateCRUD:
    """Tests for email template create/get/list/update/delete round-trip."""

    def test_create_and_get_template(self):
        """A created template should be fetchable by id with matching fields."""
        template = create_template("Welcome Email", "Hello {name}", "Welcome to our service!")
        assert template is not None
        assert template["name"] == "Welcome Email"

        fetched = get_template(template["id"])
        assert fetched is not None
        assert fetched["id"] == template["id"]
        assert fetched["subject"] == "Hello {name}"
        assert fetched["body"] == "Welcome to our service!"

        delete_template(template["id"])

    def test_list_templates_includes_created(self):
        """list_templates should include a freshly created template."""
        template = create_template("List Test", "Subject", "Body")

        templates = list_templates()

        assert any(t["id"] == template["id"] for t in templates)

        delete_template(template["id"])

    def test_update_template_changes_field(self):
        """Updating a field should be reflected both in the return value and a subsequent fetch."""
        template = create_template("Old Name", "Subject", "Body")

        updated = update_template(template["id"], {"name": "New Name"})
        assert updated["name"] == "New Name"
        assert updated["subject"] == "Subject"

        fetched = get_template(template["id"])
        assert fetched["name"] == "New Name"

        delete_template(template["id"])

    def test_delete_template_removes_it(self):
        """After deletion, get_template should return None for that id."""
        template = create_template("To Delete", "Subject", "Body")

        result = delete_template(template["id"])
        assert result is True
        assert get_template(template["id"]) is None

    def test_delete_already_deleted_template_returns_false(self):
        """Deleting an already-deleted template id should return False."""
        template = create_template("Double Delete", "Subject", "Body")
        delete_template(template["id"])

        result = delete_template(template["id"])
        assert result is False


class TestOutreachLogs:
    """Tests for outreach log creation and filtered listing/counting."""

    def test_create_log_and_list_by_lead_id(self):
        """A created log should appear in list_logs filtered by its lead_id."""
        lead = _make_lead(business_name="Log Test Business")

        log = create_log(lead["id"], channel="email", status="sent", subject="Hi", body="Body")
        assert log is not None
        assert log["lead_id"] == lead["id"]
        assert log["channel"] == "email"
        assert log["status"] == "sent"

        logs = list_logs(lead_id=lead["id"])
        assert any(l["id"] == log["id"] for l in logs)

        delete_lead(lead["id"])

    def test_count_logs_filtered_by_lead_id(self):
        """count_logs should only count logs belonging to the given lead."""
        lead = _make_lead(business_name="Count Log Test Business")

        create_log(lead["id"], channel="email", status="sent")
        create_log(lead["id"], channel="email", status="failed", error="SMTP not configured")

        count = count_logs(lead_id=lead["id"])
        assert count == 2

        delete_lead(lead["id"])

    def test_create_log_with_error_retains_message(self):
        """A failed log should retain its error message."""
        lead = _make_lead(business_name="Error Log Test Business")

        log = create_log(lead["id"], channel="email", status="failed", error="SMTP not configured")

        assert log["status"] == "failed"
        assert log["error"] == "SMTP not configured"

        delete_lead(lead["id"])
