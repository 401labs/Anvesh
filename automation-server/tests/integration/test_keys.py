"""
Tests for API key management routes.
"""
import pytest


class TestAdminKeyRoutes:
    """Tests for admin API key management endpoints."""
    
    def test_create_api_key(self, client, admin_headers):
        """Admin should be able to create API keys."""
        response = client.post(
            "/admin/keys",
            headers=admin_headers,
            json={"name": "Test Key", "tier": "free"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] == True
        assert data["error"] == False
        assert "data" in data
        assert data["data"]["name"] == "Test Key"
        assert data["data"]["key"].startswith("anv_")
        
        # Cleanup
        client.delete(f"/admin/keys/{data['data']['id']}", headers=admin_headers)
    
    def test_create_api_key_with_tier(self, client, admin_headers):
        """Admin should be able to create keys with different tiers."""
        response = client.post(
            "/admin/keys",
            headers=admin_headers,
            json={"name": "Pro Key", "tier": "pro"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["tier"] == "pro"
        assert data["data"]["monthly_limit"] == 5000
        
        # Cleanup
        client.delete(f"/admin/keys/{data['data']['id']}", headers=admin_headers)
    
    def test_list_api_keys(self, client, admin_headers, test_api_key):
        """Admin should be able to list API keys, paginated."""
        response = client.get("/admin/keys", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        page = data["data"]
        assert isinstance(page["keys"], list)
        assert "total" in page
        assert page["limit"] == 20
        assert page["offset"] == 0

        # Our test key should be in the list (it's on the first page since it was just created)
        key_ids = [k["id"] for k in page["keys"]]
        assert test_api_key["id"] in key_ids

    def test_list_api_keys_respects_limit_and_offset(self, client, admin_headers, test_api_key):
        """List endpoint should echo back the requested limit/offset."""
        response = client.get("/admin/keys?limit=1&offset=0", headers=admin_headers)

        assert response.status_code == 200
        page = response.json()["data"]
        assert page["limit"] == 1
        assert len(page["keys"]) <= 1

    def test_update_api_key_name_and_tier(self, client, admin_headers, test_api_key):
        """Admin should be able to update a key's name and tier."""
        response = client.patch(
            f"/admin/keys/{test_api_key['id']}",
            headers=admin_headers,
            json={"name": "Renamed Key", "tier": "pro"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Renamed Key"
        assert data["tier"] == "pro"
        assert data["monthly_limit"] == 5000

    def test_update_api_key_not_found(self, client, admin_headers):
        """Updating a non-existent key should 404."""
        response = client.patch(
            "/admin/keys/999999",
            headers=admin_headers,
            json={"name": "Nope"}
        )

        assert response.status_code == 404


    def test_get_api_key_by_id(self, client, admin_headers, test_api_key):
        """Admin should be able to get a specific key."""
        response = client.get(
            f"/admin/keys/{test_api_key['id']}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["id"] == test_api_key["id"]
        assert data["data"]["name"] == test_api_key["name"]
    
    def test_get_key_usage(self, client, admin_headers, test_api_key):
        """Admin should be able to view key usage."""
        response = client.get(
            f"/admin/keys/{test_api_key['id']}/usage",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["api_key_id"] == test_api_key["id"]
        assert "total_requests" in data["data"]
        assert "monthly_leads" in data["data"]
    
    def test_delete_api_key(self, client, admin_headers):
        """Admin should be able to delete API keys."""
        # Create a key to delete
        create_response = client.post(
            "/admin/keys",
            headers=admin_headers,
            json={"name": "To Delete", "tier": "free"}
        )
        key_id = create_response.json()["data"]["id"]
        
        # Delete it
        response = client.delete(
            f"/admin/keys/{key_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify it's gone
        get_response = client.get(
            f"/admin/keys/{key_id}",
            headers=admin_headers
        )
        assert get_response.json()["error"] == True


class TestUserSelfServiceRoutes:
    """Tests for user self-service endpoints."""
    
    def test_get_my_info(self, client, user_headers, test_api_key):
        """User should be able to view their own key info."""
        response = client.get("/me", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["id"] == test_api_key["id"]
        assert data["data"]["name"] == test_api_key["name"]
    
    def test_get_my_usage(self, client, user_headers, test_api_key):
        """User should be able to view their own usage."""
        response = client.get("/me/usage", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["api_key_id"] == test_api_key["id"]
        assert "remaining_quota" in data["data"]
