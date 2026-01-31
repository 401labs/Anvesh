"""
Tests for authentication middleware.
"""
import pytest


class TestAPIKeyMiddleware:
    """Tests for API key authentication middleware."""
    
    def test_missing_api_key_header(self, client):
        """Request without X-API-Key should return 422 (missing required header)."""
        response = client.get("/automation/tasks")
        
        # FastAPI returns 422 for missing required headers
        assert response.status_code == 422
    
    def test_invalid_api_key(self, client):
        """Request with invalid API key should return 401."""
        response = client.get(
            "/automation/tasks",
            headers={"X-API-Key": "anv_invalid_key"}
        )
        
        assert response.status_code == 401
        assert "Invalid or expired" in response.json()["detail"]
    
    def test_valid_api_key_passes(self, client, user_headers):
        """Request with valid API key should succeed."""
        response = client.get("/automation/tasks", headers=user_headers)
        
        assert response.status_code == 200


class TestAdminMiddleware:
    """Tests for admin authentication middleware."""
    
    def test_missing_admin_secret(self, client):
        """Request without X-Admin-Secret should return 422 (missing required header)."""
        response = client.get("/admin/keys")
        
        # FastAPI returns 422 for missing required headers
        assert response.status_code == 422
    
    def test_invalid_admin_secret(self, client):
        """Request with invalid admin secret should return 403."""
        response = client.get(
            "/admin/keys",
            headers={"X-Admin-Secret": "wrong-secret"}
        )
        
        assert response.status_code == 403
        assert "Invalid admin secret" in response.json()["detail"]
    
    def test_valid_admin_secret(self, client, admin_headers):
        """Request with valid admin secret should succeed."""
        response = client.get("/admin/keys", headers=admin_headers)
        
        assert response.status_code == 200
