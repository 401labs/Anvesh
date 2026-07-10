"""
Integration tests for outreach edge cases: template field validation, the
send_email_endpoint validation matrix, bulk-send accounting, placeholder
rendering with missing fields, logs pagination/filtering, and template
update field independence.
"""
import pytest


class TestTemplateFieldValidation:
    """Tests for EmailTemplateCreate's actual (not assumed) validation behavior."""

    def test_create_template_with_empty_strings_is_accepted(self, client, user_headers):
        """EmailTemplateCreate has no min_length constraint, so empty name/subject/body are accepted, not rejected with 422."""
        response = client.post(
            "/outreach/templates",
            headers=user_headers,
            json={"name": "", "subject": "", "body": ""}
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == ""
        assert data["subject"] == ""
        assert data["body"] == ""

        client.delete(f"/outreach/templates/{data['id']}", headers=user_headers)

    def test_create_template_missing_required_field_is_422(self, client, user_headers):
        """Omitting a required field entirely (as opposed to sending it empty) should 422, since pydantic still requires the key be present."""
        response = client.post(
            "/outreach/templates",
            headers=user_headers,
            json={"name": "Missing Subject And Body"}
        )

        assert response.status_code == 422


class TestSendEmailValidationMatrix:
    """Tests for every branch of send_email_endpoint's template_id-XOR-subject/body validation."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "Validation Matrix Business",
            "industry": "outreach-testing",
            "location": "Matrixville",
            "address": "1 Matrix Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_neither_template_nor_subject_body_is_400(self, client, user_headers):
        """Sending with neither template_id nor subject/body should 400."""
        lead_response = self._create_lead(client, user_headers, email="matrix-neither@example.com")
        lead_id = lead_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_id]}
        )

        assert response.status_code == 400

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_both_template_and_subject_body_is_400(self, client, user_headers):
        """Sending with both template_id and subject/body should 400."""
        lead_response = self._create_lead(client, user_headers, email="matrix-both@example.com")
        lead_id = lead_response.json()["data"]["id"]
        template_response = client.post(
            "/outreach/templates",
            headers=user_headers,
            json={"name": "Matrix Both Template", "subject": "Subj", "body": "Body"}
        )
        template_id = template_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={
                "lead_ids": [lead_id],
                "template_id": template_id,
                "subject": "Override",
                "body": "Override Body",
            }
        )

        assert response.status_code == 400

        client.delete(f"/outreach/templates/{template_id}", headers=user_headers)
        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_nonexistent_template_id_is_404(self, client, user_headers):
        """Sending with a template_id that doesn't exist should 404."""
        lead_response = self._create_lead(client, user_headers, email="matrix-notemplate@example.com")
        lead_id = lead_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_id], "template_id": 999999999}
        )

        assert response.status_code == 404

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_subject_without_body_is_400(self, client, user_headers):
        """Sending subject without body (and no template_id) should 400 — both are required when not using a template."""
        lead_response = self._create_lead(client, user_headers, email="matrix-subjectonly@example.com")
        lead_id = lead_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_id], "subject": "Only A Subject"}
        )

        assert response.status_code == 400

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_body_without_subject_is_400(self, client, user_headers):
        """Sending body without subject (and no template_id) should 400 — both are required when not using a template."""
        lead_response = self._create_lead(client, user_headers, email="matrix-bodyonly@example.com")
        lead_id = lead_response.json()["data"]["id"]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_id], "body": "Only A Body"}
        )

        assert response.status_code == 400

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)


class TestBulkSendAccounting:
    """Tests that skipped_no_email / skipped_no_lead / queued|result accounting adds up for mixed batches."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "Bulk Accounting Business",
            "industry": "outreach-testing",
            "location": "Bulkville",
            "address": "1 Bulk Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_mixed_batch_with_multiple_valid_recipients_is_queued(self, client, user_headers):
        """3 valid + 2 no-email + 2 nonexistent: skipped lists are exact, and 3 valid (>1) means queued == 3."""
        valid_leads = [
            self._create_lead(client, user_headers, business_name=f"Bulk Valid {i}", email=f"bulk-valid-{i}@example.com")
            for i in range(3)
        ]
        valid_ids = [r.json()["data"]["id"] for r in valid_leads]

        no_email_leads = [
            self._create_lead(client, user_headers, business_name=f"Bulk NoEmail {i}")
            for i in range(2)
        ]
        no_email_ids = [r.json()["data"]["id"] for r in no_email_leads]

        nonexistent_ids = [888888801, 888888802]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={
                "lead_ids": valid_ids + no_email_ids + nonexistent_ids,
                "subject": "Bulk Hi",
                "body": "Bulk Body",
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert sorted(data["skipped_no_email"]) == sorted(no_email_ids)
        assert sorted(data["skipped_no_lead"]) == sorted(nonexistent_ids)
        assert data["queued"] == 3

        for lead_id in valid_ids + no_email_ids:
            client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_mixed_batch_with_single_valid_recipient_sends_synchronously(self, client, user_headers):
        """1 valid + 2 no-email + 2 nonexistent: skipped lists are exact, and 1 valid means a synchronous result, not queued."""
        valid_lead = self._create_lead(client, user_headers, email="bulk-single-valid@example.com")
        valid_id = valid_lead.json()["data"]["id"]

        no_email_leads = [
            self._create_lead(client, user_headers, business_name=f"Bulk Single NoEmail {i}")
            for i in range(2)
        ]
        no_email_ids = [r.json()["data"]["id"] for r in no_email_leads]

        nonexistent_ids = [888888901, 888888902]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={
                "lead_ids": [valid_id] + no_email_ids + nonexistent_ids,
                "subject": "Single Hi",
                "body": "Single Body",
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert sorted(data["skipped_no_email"]) == sorted(no_email_ids)
        assert sorted(data["skipped_no_lead"]) == sorted(nonexistent_ids)
        assert "queued" not in data
        assert data["result"]["lead_id"] == valid_id
        assert data["result"]["sent"] is False

        for lead_id in [valid_id] + no_email_ids:
            client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_batch_with_zero_valid_recipients_reports_queued_zero(self, client, user_headers):
        """All-skipped batch (no valid recipients at all) should report queued == 0, not attempt a send."""
        no_email_lead = self._create_lead(client, user_headers)
        no_email_id = no_email_lead.json()["data"]["id"]
        nonexistent_ids = [888889001]

        response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={
                "lead_ids": [no_email_id] + nonexistent_ids,
                "subject": "Nobody Hi",
                "body": "Nobody Body",
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["queued"] == 0
        assert data["skipped_no_email"] == [no_email_id]
        assert data["skipped_no_lead"] == nonexistent_ids

        client.delete(f"/automation/leads/{no_email_id}", headers=user_headers)


class TestPlaceholderRenderingMissingField:
    """Tests that rendering a placeholder for an unset lead field degrades to empty string, not a crash or literal placeholder text."""

    def test_missing_field_placeholder_renders_as_empty_string(self, client, user_headers):
        """{{category}} on a lead with category unset should render as empty string in the logged subject/body."""
        lead_response = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": "Placeholder Test Business",
                "industry": "outreach-testing",
                "location": "Placeholderville",
                "address": "1 Placeholder Way",
                "email": "placeholder-test@example.com",
                # category intentionally omitted -> None
            }
        )
        lead_id = lead_response.json()["data"]["id"]

        send_response = client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={
                "lead_ids": [lead_id],
                "subject": "Update for {{business_name}}",
                "body": "Category: [{{category}}] end.",
            }
        )
        assert send_response.status_code == 200

        logs_response = client.get(f"/outreach/logs?lead_id={lead_id}", headers=user_headers)
        assert logs_response.status_code == 200
        logs = logs_response.json()["data"]["logs"]
        assert len(logs) >= 1
        log = logs[0]

        assert log["subject"] == "Update for Placeholder Test Business"
        assert log["body"] == "Category: [] end."
        assert "{{category}}" not in log["body"]

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)


class TestLogsPaginationAndFiltering:
    """Tests that GET /outreach/logs filters strictly by lead_id and totals are correct in each case."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "Logs Filter Business",
            "industry": "outreach-testing",
            "location": "Filterville",
            "address": "1 Filter Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_lead_id_filter_excludes_other_leads_logs(self, client, user_headers):
        """Logs filtered to lead A should not include lead B's logs, and each filtered total should match exactly."""
        lead_a = self._create_lead(client, user_headers, business_name="Logs Filter Lead A", email="logs-filter-a@example.com")
        lead_b = self._create_lead(client, user_headers, business_name="Logs Filter Lead B", email="logs-filter-b@example.com")
        lead_a_id = lead_a.json()["data"]["id"]
        lead_b_id = lead_b.json()["data"]["id"]

        client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_a_id], "subject": "A Subject", "body": "A Body"}
        )
        client.post(
            "/outreach/email/send",
            headers=user_headers,
            json={"lead_ids": [lead_b_id], "subject": "B Subject", "body": "B Body"}
        )

        response_a = client.get(f"/outreach/logs?lead_id={lead_a_id}", headers=user_headers)
        data_a = response_a.json()["data"]
        assert data_a["total"] == 1
        assert len(data_a["logs"]) == 1
        assert all(l["lead_id"] == lead_a_id for l in data_a["logs"])

        response_b = client.get(f"/outreach/logs?lead_id={lead_b_id}", headers=user_headers)
        data_b = response_b.json()["data"]
        assert data_b["total"] == 1
        assert len(data_b["logs"]) == 1
        assert all(l["lead_id"] == lead_b_id for l in data_b["logs"])

        response_all = client.get("/outreach/logs?limit=200", headers=user_headers)
        data_all = response_all.json()["data"]
        all_lead_ids = {l["lead_id"] for l in data_all["logs"]}
        assert lead_a_id in all_lead_ids
        assert lead_b_id in all_lead_ids
        assert data_all["total"] >= 2

        client.delete(f"/automation/leads/{lead_a_id}", headers=user_headers)
        client.delete(f"/automation/leads/{lead_b_id}", headers=user_headers)


class TestTemplateUpdateFieldIndependence:
    """Tests that a PATCH to a template only touches the fields it sends, verified across two separate PATCH calls."""

    def _create_template(self, client, user_headers, **overrides):
        payload = {
            "name": "Independence Template",
            "subject": "Original Subject",
            "body": "Original Body",
        }
        payload.update(overrides)
        return client.post("/outreach/templates", headers=user_headers, json=payload)

    def test_independent_subject_then_body_updates_leave_other_fields_untouched(self, client, user_headers):
        """Updating subject alone, then body alone, should each leave the untouched fields exactly as they were."""
        create_response = self._create_template(client, user_headers)
        template_id = create_response.json()["data"]["id"]

        subject_update = client.patch(
            f"/outreach/templates/{template_id}",
            headers=user_headers,
            json={"subject": "New Subject"}
        )
        assert subject_update.status_code == 200
        data = subject_update.json()["data"]
        assert data["subject"] == "New Subject"
        assert data["name"] == "Independence Template"
        assert data["body"] == "Original Body"

        body_update = client.patch(
            f"/outreach/templates/{template_id}",
            headers=user_headers,
            json={"body": "New Body"}
        )
        assert body_update.status_code == 200
        data2 = body_update.json()["data"]
        assert data2["body"] == "New Body"
        assert data2["subject"] == "New Subject"
        assert data2["name"] == "Independence Template"

        client.delete(f"/outreach/templates/{template_id}", headers=user_headers)
