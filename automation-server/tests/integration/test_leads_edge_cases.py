"""
Additional enterprise-grade edge case tests for the Leads feature.

This file is additive to tests/integration/test_automation.py — it does not
duplicate the happy-path CRUD/filter/sort/score coverage already there, and
instead focuses on boundary validation, pagination edges, uniqueness-pair
semantics, unicode/SQL-injection-shaped input, column-length limits, cascade
deletes, score-formula boundaries, and bulk-delete edge cases.
"""
import pytest

from app.db import create_log, list_logs


class TestLeadsValidationBoundaries:
    """Tests for query-param boundary validation on GET /automation/leads."""

    def test_limit_zero_rejected(self, client, user_headers):
        """limit=0 should 422 (limit has ge=1)."""
        response = client.get("/automation/leads?limit=0", headers=user_headers)

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"] is True

    def test_limit_above_max_rejected(self, client, user_headers):
        """limit=201 should 422 (limit has le=200)."""
        response = client.get("/automation/leads?limit=201", headers=user_headers)

        assert response.status_code == 422

    def test_limit_at_max_accepted(self, client, user_headers):
        """limit=200 (the upper bound) should be accepted."""
        response = client.get("/automation/leads?limit=200", headers=user_headers)

        assert response.status_code == 200

    def test_offset_negative_rejected(self, client, user_headers):
        """offset=-1 should 422 (offset has ge=0)."""
        response = client.get("/automation/leads?offset=-1", headers=user_headers)

        assert response.status_code == 422

    def test_min_rating_above_max_rejected(self, client, user_headers):
        """min_rating=5.1 should 422 (min_rating has le=5)."""
        response = client.get("/automation/leads?min_rating=5.1", headers=user_headers)

        assert response.status_code == 422

    def test_min_rating_below_min_rejected(self, client, user_headers):
        """min_rating=-0.1 should 422 (min_rating has ge=0)."""
        response = client.get("/automation/leads?min_rating=-0.1", headers=user_headers)

        assert response.status_code == 422

    def test_min_score_above_max_rejected(self, client, user_headers):
        """min_score=101 should 422 (min_score has le=100)."""
        response = client.get("/automation/leads?min_score=101", headers=user_headers)

        assert response.status_code == 422

    def test_min_score_below_min_rejected(self, client, user_headers):
        """min_score=-1 should 422 (min_score has ge=0)."""
        response = client.get("/automation/leads?min_score=-1", headers=user_headers)

        assert response.status_code == 422

    def test_invalid_sort_by_rejected(self, client, user_headers):
        """sort_by must match the regex-constrained set of known columns."""
        response = client.get("/automation/leads?sort_by=nonexistent_column", headers=user_headers)

        assert response.status_code == 422

    def test_invalid_sort_dir_rejected(self, client, user_headers):
        """sort_dir must be either 'asc' or 'desc'."""
        response = client.get("/automation/leads?sort_dir=sideways", headers=user_headers)

        assert response.status_code == 422


class TestLeadsPaginationEdgeCases:
    """Tests for pagination behavior at and beyond the edges of the result set."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "Pagination Edge Business",
            "industry": "pagination-edge-industry",
            "location": "Paginationville",
            "address": "1 Pagination Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_offset_beyond_total_returns_empty_not_error(self, client, user_headers):
        """An offset far beyond the total row count returns an empty list, not an error."""
        response = client.get(
            "/automation/leads?offset=999999999&limit=10",
            headers=user_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["leads"] == []

    def test_limit_one_returns_exactly_one_row(self, client, user_headers):
        """limit=1 returns exactly one row when at least one matching lead exists."""
        create_response = self._create_lead(client, user_headers, business_name="Limit One Business")
        lead_id = create_response.json()["data"]["id"]

        response = client.get(
            "/automation/leads?industry=pagination-edge-industry&limit=1",
            headers=user_headers
        )

        assert response.status_code == 200
        leads = response.json()["data"]["leads"]
        assert len(leads) == 1

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)


class TestLeadsUniquenessIsPairNotField:
    """Tests proving the (business_name, address) UNIQUE constraint applies to the pair, not either field alone."""

    def test_same_business_name_different_address_both_succeed(self, client, user_headers):
        """Two leads sharing a business_name but with different addresses should both be creatable."""
        first = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": "Shared Name Business",
                "industry": "uniqueness-test-industry",
                "location": "Uniqueville",
                "address": "1 First Address",
            }
        )
        second = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": "Shared Name Business",
                "industry": "uniqueness-test-industry",
                "location": "Uniqueville",
                "address": "2 Second Address",
            }
        )

        assert first.status_code == 201
        assert second.status_code == 201

        first_id = first.json()["data"]["id"]
        second_id = second.json()["data"]["id"]
        assert first_id != second_id

        client.delete(f"/automation/leads/{first_id}", headers=user_headers)
        client.delete(f"/automation/leads/{second_id}", headers=user_headers)

    def test_same_address_different_business_name_both_succeed(self, client, user_headers):
        """Two leads sharing an address but with different business_names should both be creatable."""
        first = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": "First Shared Address Business",
                "industry": "uniqueness-test-industry",
                "location": "Uniqueville",
                "address": "1 Shared Address",
            }
        )
        second = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": "Second Shared Address Business",
                "industry": "uniqueness-test-industry",
                "location": "Uniqueville",
                "address": "1 Shared Address",
            }
        )

        assert first.status_code == 201
        assert second.status_code == 201

        first_id = first.json()["data"]["id"]
        second_id = second.json()["data"]["id"]
        assert first_id != second_id

        client.delete(f"/automation/leads/{first_id}", headers=user_headers)
        client.delete(f"/automation/leads/{second_id}", headers=user_headers)


class TestLeadsUnicodeAndSpecialCharacters:
    """Tests proving lead fields round-trip unicode and SQL-metacharacter content byte-for-byte (parameterized queries, not string interpolation)."""

    def test_unicode_business_name_and_sql_metacharacter_address_roundtrip(self, client, user_headers):
        """A unicode business name and an address containing quotes/ampersands/SQL metacharacters should be stored and retrieved exactly."""
        business_name = "Café Münster 咖啡"
        address = "12 O'Brien & Sons St; DROP TABLE leads; -- \"quoted\""

        create_response = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": business_name,
                "industry": "unicode-test-industry",
                "location": "Unicodeville",
                "address": address,
            }
        )

        assert create_response.status_code == 201
        created = create_response.json()["data"]
        assert created["business_name"] == business_name
        assert created["address"] == address
        lead_id = created["id"]

        # Verify the leads table itself survived (proving this wasn't executed as SQL).
        list_response = client.get(
            "/automation/leads?industry=unicode-test-industry&limit=50",
            headers=user_headers
        )
        assert list_response.status_code == 200
        leads = list_response.json()["data"]["leads"]
        match = next(l for l in leads if l["id"] == lead_id)
        assert match["business_name"] == business_name
        assert match["address"] == address

        # Sanity check the leads table wasn't dropped: a follow-up query still works.
        sanity = client.get("/automation/leads?limit=1", headers=user_headers)
        assert sanity.status_code == 200

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)


class TestLeadsVeryLongStrings:
    """Tests for business_name lengths at/over the VARCHAR(255) column limit."""

    def test_business_name_over_255_chars_fails_cleanly_not_500(self, client, user_headers):
        """A business_name longer than the VARCHAR(255) column should fail cleanly (not crash with a 500)."""
        long_name = "A" * 300

        response = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": long_name,
                "industry": "long-string-test-industry",
                "location": "Longville",
                "address": "1 Long Business Address",
            }
        )

        # The DB layer's insert catches the "value too long for type character
        # varying(255)" error and raises LeadInsertError, which the endpoint
        # surfaces as a 422 (distinct from the 409 used for a genuine
        # (business_name, address) duplicate) — never an unhandled 500.
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"] is True

        # No row should have been created — nothing to clean up. Confirm via a
        # search that would have matched had it slipped through.
        list_response = client.get(
            "/automation/leads?industry=long-string-test-industry&limit=10",
            headers=user_headers
        )
        assert list_response.status_code == 200
        assert list_response.json()["data"]["leads"] == []

    def test_business_name_at_255_chars_succeeds(self, client, user_headers):
        """A business_name at exactly the VARCHAR(255) limit should be accepted."""
        name_255 = "B" * 255

        response = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": name_255,
                "industry": "long-string-test-industry",
                "location": "Longville",
                "address": "1 Exact Limit Business Address",
            }
        )

        assert response.status_code == 201
        created = response.json()["data"]
        assert created["business_name"] == name_255

        client.delete(f"/automation/leads/{created['id']}", headers=user_headers)


class TestLeadsCascadeDelete:
    """Tests proving ON DELETE CASCADE actually removes dependent outreach_logs rows, not just declares it in SQL."""

    def test_deleting_lead_cascades_to_outreach_logs(self, client, user_headers):
        """Deleting a lead should also remove any outreach_logs rows referencing it."""
        create_response = client.post(
            "/automation/leads",
            headers=user_headers,
            json={
                "business_name": "Cascade Delete Business",
                "industry": "cascade-test-industry",
                "location": "Cascadeville",
                "address": "1 Cascade Way",
            }
        )
        assert create_response.status_code == 201
        lead_id = create_response.json()["data"]["id"]

        log = create_log(lead_id, channel="email", status="sent", subject="Hi", body="Hello there")
        assert log is not None
        assert log["lead_id"] == lead_id

        # Confirm the log row is visible before deletion.
        logs_before = list_logs(lead_id=lead_id)
        assert any(l["id"] == log["id"] for l in logs_before)

        delete_response = client.delete(f"/automation/leads/{lead_id}", headers=user_headers)
        assert delete_response.status_code == 200

        logs_after = list_logs(lead_id=lead_id)
        assert logs_after == []


class TestLeadScoreFormulaBoundaries:
    """Tests for the LEAD_SCORE_SQL formula at its numeric extremes."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "Score Boundary Business",
            "industry": "score-boundary-industry",
            "location": "Scoreville",
            "address": "1 Score Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_minimum_possible_score_is_zero(self, client, user_headers):
        """rating=0, review_count=0, has_website=True, is_claimed=True should score exactly 0."""
        create_response = self._create_lead(
            client, user_headers, business_name="Zero Score Business",
            rating=0, review_count=0, has_website=True, is_claimed=True
        )
        assert create_response.status_code == 201
        lead_id = create_response.json()["data"]["id"]

        response = client.get(
            "/automation/leads?industry=score-boundary-industry&limit=50",
            headers=user_headers
        )
        leads = response.json()["data"]["leads"]
        target = next(l for l in leads if l["id"] == lead_id)
        assert target["score"] == 0

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_review_count_cap_is_enforced_far_over_the_cap(self, client, user_headers):
        """rating=5, review_count=1,000,000 (way over the 500 cap), no website, unclaimed should score exactly 100."""
        create_response = self._create_lead(
            client, user_headers, business_name="Capped Score Business",
            rating=5, review_count=1_000_000, has_website=False, is_claimed=False
        )
        assert create_response.status_code == 201
        lead_id = create_response.json()["data"]["id"]

        response = client.get(
            "/automation/leads?industry=score-boundary-industry&limit=50",
            headers=user_headers
        )
        leads = response.json()["data"]["leads"]
        target = next(l for l in leads if l["id"] == lead_id)
        assert target["score"] == 100

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)


class TestLeadsBulkDeleteEdgeCases:
    """Tests for edge cases in the bulk-delete endpoint."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "Bulk Edge Business",
            "industry": "bulk-edge-industry",
            "location": "Bulkville",
            "address": "1 Bulk Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_bulk_delete_empty_ids_rejected(self, client, user_headers):
        """An empty ids array should 422 (ids has min_length=1)."""
        response = client.post(
            "/automation/leads/bulk-delete",
            headers=user_headers,
            json={"ids": []}
        )

        assert response.status_code == 422

    def test_bulk_delete_mix_of_valid_and_nonexistent_ids(self, client, user_headers):
        """Bulk-deleting a mix of valid and already-gone/nonexistent ids should succeed, counting only the valid ones actually removed."""
        create_response = self._create_lead(client, user_headers, business_name="Bulk Valid Business")
        valid_id = create_response.json()["data"]["id"]
        nonexistent_id = 999999999

        response = client.post(
            "/automation/leads/bulk-delete",
            headers=user_headers,
            json={"ids": [valid_id, nonexistent_id]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] == 1

        # The valid lead is really gone now.
        second_delete = client.delete(f"/automation/leads/{valid_id}", headers=user_headers)
        assert second_delete.status_code == 404

    def test_bulk_delete_all_nonexistent_ids_still_succeeds_with_zero_deleted(self, client, user_headers):
        """Bulk-deleting only nonexistent ids should succeed (not error) with deleted=0."""
        response = client.post(
            "/automation/leads/bulk-delete",
            headers=user_headers,
            json={"ids": [999999998, 999999999]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] == 0
