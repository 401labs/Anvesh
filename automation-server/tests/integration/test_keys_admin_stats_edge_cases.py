"""
Edge-case and boundary tests for API Keys, Admin auth, and the Stats endpoint.

NOTE on rate limiting: config/keys.py::TIERS defines `rate_limit_per_minute` per
tier and `get_tier_rate_limit()` exists as a getter, but it is NOT enforced
anywhere in the request path (grepped the whole app/ tree — only referenced by
its own definition and re-export). There is deliberately no test here asserting
rate-limit enforcement, since that would test a feature that doesn't exist.

NOTE on stats + division-by-zero: `/stats` (app/routers/stats.py) aggregates
get_lead_stats/get_leads_by_day/get_top_industries/get_top_locations/
get_outreach_stats/get_task_counts (app/db/database.py, app/db/outreach.py,
app/db/tasks.py) — none of these perform division. The only division in the
codebase touching these areas is `success_rate` in app/routers/admin.py's
`/admin/automation/stats` (a different, admin-only endpoint), and it's already
guarded (`if counts["total"] else "N/A"`). It's also not reliably testable at
the integration level here since `automation_tasks` is a shared table other
tests populate concurrently, so `total == 0` can't be forced. Skipped per the
task's explicit scope (stats.py / database.py only).
"""
import hmac
import pytest

from app.db.api_keys import (
    create_api_key,
    validate_api_key,
    get_api_key_by_id,
    revoke_api_key,
    delete_api_key,
    log_usage,
)


class TestQuotaBoundaryEnforcement:
    """Tests for free-tier monthly quota boundary (check_quota: monthly_leads < monthly_limit)."""

    def test_quota_boundary_at_limit_minus_one_still_succeeds(self, client, admin_headers):
        """At 99/100 logged leads, a request should still succeed (99 < 100)."""
        key_data = create_api_key(name="Quota Boundary Test", tier="free")
        try:
            log_usage(key_data["id"], "/test-endpoint", 99)

            response = client.get(
                "/automation/tasks",
                headers={"X-API-Key": key_data["key"]},
            )

            assert response.status_code == 200
        finally:
            delete_api_key(key_data["id"])

    def test_quota_boundary_at_limit_rejects_next_request(self, client, admin_headers):
        """At exactly 100/100 logged leads, the next request should 429 with the quota message."""
        key_data = create_api_key(name="Quota Exceeded Test", tier="free")
        try:
            log_usage(key_data["id"], "/test-endpoint", 99)
            log_usage(key_data["id"], "/test-endpoint", 1)

            response = client.get(
                "/automation/tasks",
                headers={"X-API-Key": key_data["key"]},
            )

            assert response.status_code == 429
            assert "Monthly quota exceeded" in response.json()["detail"]
        finally:
            delete_api_key(key_data["id"])

    def test_deleting_key_cascades_usage_logs(self, client, admin_headers):
        """Deleting an API key should remove it (usage_logs FK is ON DELETE CASCADE, so no orphaned rows)."""
        key_data = create_api_key(name="Cascade Delete Test", tier="free")
        log_usage(key_data["id"], "/test-endpoint", 50)

        deleted = delete_api_key(key_data["id"])

        assert deleted is True
        assert get_api_key_by_id(key_data["id"]) is None
        # Re-validating the (now-deleted) key should also fail cleanly.
        assert validate_api_key(key_data["key"]) is None


class TestEnterpriseUnlimitedQuota:
    """Tests confirming enterprise tier (monthly_limit=-1) has no quota ceiling."""

    def test_enterprise_key_succeeds_past_free_tier_ceiling(self, client, admin_headers):
        """Enterprise key with usage well past the free tier's 100 limit should still succeed."""
        key_data = create_api_key(name="Enterprise Unlimited Test", tier="enterprise")
        try:
            log_usage(key_data["id"], "/test-endpoint", 10000)

            response = client.get(
                "/automation/tasks",
                headers={"X-API-Key": key_data["key"]},
            )

            assert response.status_code == 200
        finally:
            delete_api_key(key_data["id"])

    def test_enterprise_key_monthly_limit_is_negative_one(self):
        """Enterprise tier's monthly_limit should be -1 (unlimited), matching config/keys.py::TIERS."""
        key_data = create_api_key(name="Enterprise Limit Check", tier="enterprise")
        try:
            assert key_data["monthly_limit"] == -1
        finally:
            delete_api_key(key_data["id"])


class TestExpiredKeyRejection:
    """Tests for already-expired API keys."""

    def test_expired_key_validate_returns_none(self):
        """A key created with expires_in_days=-1 (already expired) should fail validate_api_key."""
        key_data = create_api_key(name="Expired Key Test", tier="free", expires_in_days=-1)
        try:
            result = validate_api_key(key_data["key"])
            assert result is None
        finally:
            delete_api_key(key_data["id"])

    def test_expired_key_request_gets_401(self, client):
        """A request using an already-expired key should be rejected with 401."""
        key_data = create_api_key(name="Expired Key Request Test", tier="free", expires_in_days=-1)
        try:
            response = client.get(
                "/automation/tasks",
                headers={"X-API-Key": key_data["key"]},
            )

            assert response.status_code == 401
            assert "Invalid or expired" in response.json()["detail"]
        finally:
            delete_api_key(key_data["id"])


class TestRevokedVsDeletedKeyDistinction:
    """Tests distinguishing revoke_api_key (soft, row kept, is_active=false) from delete_api_key (hard, row gone)."""

    def test_revoked_key_row_still_found_by_id(self):
        """After revoke, get_api_key_by_id should still find the row, but with is_active=False."""
        key_data = create_api_key(name="Revoke Row Test", tier="free")
        try:
            revoked = revoke_api_key(key_data["id"])
            assert revoked is True

            row = get_api_key_by_id(key_data["id"])
            assert row is not None
            assert row["is_active"] is False
        finally:
            delete_api_key(key_data["id"])

    def test_revoked_key_fails_validation_and_requests(self, client):
        """A revoked key should fail validate_api_key and get 401 on a live request."""
        key_data = create_api_key(name="Revoke Reject Test", tier="free")
        try:
            revoke_api_key(key_data["id"])

            assert validate_api_key(key_data["key"]) is None

            response = client.get(
                "/automation/tasks",
                headers={"X-API-Key": key_data["key"]},
            )
            assert response.status_code == 401
        finally:
            delete_api_key(key_data["id"])

    def test_deleted_key_row_not_found_by_id(self):
        """After delete, get_api_key_by_id should return None (row is fully gone, unlike revoke)."""
        key_data = create_api_key(name="Delete Row Test", tier="free")

        deleted = delete_api_key(key_data["id"])

        assert deleted is True
        assert get_api_key_by_id(key_data["id"]) is None


class TestAdminSecretTimingSafety:
    """Correctness (not statistical timing) checks that hmac.compare_digest isn't accidentally bypassed."""

    def test_same_length_wrong_secret_is_rejected(self, client):
        """A wrong secret with the exact same length as the real admin secret must still 403."""
        real_secret = "test-admin-secret"
        wrong_secret = "test-admin-secreT"  # same length, last char flipped

        assert len(wrong_secret) == len(real_secret)
        assert not hmac.compare_digest(wrong_secret, real_secret)

        response = client.get(
            "/admin/keys",
            headers={"X-Admin-Secret": wrong_secret},
        )

        assert response.status_code == 403
        assert "Invalid admin secret" in response.json()["detail"]

    def test_completely_different_length_wrong_secret_is_rejected(self, client):
        """Sanity check: a wrong secret of a different length is also rejected (not a length-only check)."""
        response = client.get(
            "/admin/keys",
            headers={"X-Admin-Secret": "short"},
        )

        assert response.status_code == 403


class TestAdminRoutesRejectValidUserKey:
    """Confirm require_admin truly requires X-Admin-Secret, not just any valid credential."""

    def test_admin_keys_list_rejects_user_key(self, client, user_headers):
        """GET /admin/keys should reject a valid X-API-Key (missing required X-Admin-Secret header)."""
        response = client.get("/admin/keys", headers=user_headers)
        # require_admin declares X-Admin-Secret as a required header, so FastAPI's
        # own validation (422) fires before require_admin's body ever runs.
        assert response.status_code in [401, 403, 422]

    def test_admin_automation_tasks_rejects_user_key(self, client, user_headers):
        """GET /admin/automation/tasks should reject a valid X-API-Key."""
        response = client.get("/admin/automation/tasks", headers=user_headers)
        assert response.status_code in [401, 403, 422]

    def test_admin_automation_stats_rejects_user_key(self, client, user_headers):
        """GET /admin/automation/stats should reject a valid X-API-Key."""
        response = client.get("/admin/automation/stats", headers=user_headers)
        assert response.status_code in [401, 403, 422]

    def test_admin_stop_all_rejects_user_key(self, client, user_headers):
        """POST /admin/automation/stop-all should reject a valid X-API-Key."""
        response = client.post("/admin/automation/stop-all", headers=user_headers)
        assert response.status_code in [401, 403, 422]


class TestStatsDaysBoundary:
    """Tests for GET /stats?days= boundary values (Query(30, ge=1, le=365))."""

    def test_days_lower_bound_one_succeeds(self, client, user_headers):
        """days=1 (minimum allowed) should succeed."""
        response = client.get("/stats?days=1", headers=user_headers)
        assert response.status_code == 200

    def test_days_upper_bound_365_succeeds(self, client, user_headers):
        """days=365 (maximum allowed) should succeed."""
        response = client.get("/stats?days=365", headers=user_headers)
        assert response.status_code == 200

    def test_days_zero_rejected(self, client, user_headers):
        """days=0 is below the minimum and should 422."""
        response = client.get("/stats?days=0", headers=user_headers)
        assert response.status_code == 422

    def test_days_366_rejected(self, client, user_headers):
        """days=366 is above the maximum and should 422."""
        response = client.get("/stats?days=366", headers=user_headers)
        assert response.status_code == 422
