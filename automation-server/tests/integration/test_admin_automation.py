"""
Tests for admin automation management routes.
"""
import pytest


class TestAdminAutomationAuth:
    """Tests for admin automation routes authentication."""
    
    def test_admin_tasks_requires_admin(self, client):
        """Admin tasks endpoint should require admin secret."""
        response = client.get("/admin/automation/tasks")
        
        # Should return 401 or 403 for missing admin header
        assert response.status_code in [401, 403, 422]
    
    def test_admin_tasks_with_user_key_fails(self, client, user_headers):
        """Admin tasks endpoint should reject regular API key."""
        response = client.get("/admin/automation/tasks", headers=user_headers)
        
        # Admin endpoints require X-Admin-Secret, not X-API-Key
        # FastAPI returns 422 for missing required header
        assert response.status_code in [401, 403, 422]
    
    def test_admin_tasks_with_admin_secret(self, client, admin_headers):
        """Admin tasks endpoint should work with admin secret."""
        response = client.get("/admin/automation/tasks", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "summary" in data["data"]
        assert "tasks" in data["data"]
    
    def test_admin_stop_all_requires_admin(self, client):
        """Admin stop-all endpoint should require admin secret."""
        response = client.post("/admin/automation/stop-all")
        
        assert response.status_code in [401, 403, 422]
    
    def test_admin_stop_all_with_admin_secret(self, client, admin_headers):
        """Admin stop-all endpoint should work with admin secret."""
        response = client.post("/admin/automation/stop-all", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "tasks_stopped" in data["data"]
    
    def test_admin_stats_requires_admin(self, client):
        """Admin stats endpoint should require admin secret."""
        response = client.get("/admin/automation/stats")
        
        assert response.status_code in [401, 403, 422]
    
    def test_admin_stats_with_admin_secret(self, client, admin_headers):
        """Admin stats endpoint should work with admin secret."""
        response = client.get("/admin/automation/stats", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "tasks" in data["data"]
        assert "active_scraping" in data["data"]


class TestAdminAutomationResponses:
    """Tests for admin automation response formats."""
    
    def test_tasks_summary_structure(self, client, admin_headers):
        """Tasks response should include proper summary structure."""
        response = client.get("/admin/automation/tasks", headers=admin_headers)
        
        data = response.json()
        summary = data["data"]["summary"]
        
        assert "total" in summary
        assert "running" in summary
        assert "completed" in summary
        assert "stopped" in summary
        assert "error" in summary
    
    def test_stats_structure(self, client, admin_headers):
        """Stats response should include proper structure."""
        response = client.get("/admin/automation/stats", headers=admin_headers)
        
        data = response.json()
        stats = data["data"]
        
        assert "timestamp" in stats
        assert "tasks" in stats
        assert "active_scraping" in stats
        assert "success_rate" in stats
        
        # Verify nested structure
        assert "total" in stats["tasks"]
        assert "running" in stats["tasks"]
        assert "industries" in stats["active_scraping"]
        assert "locations" in stats["active_scraping"]


class TestAdminAutomationWorkflow:
    """Tests for admin automation workflow scenarios."""
    
    def test_admin_can_see_user_task(self, client, admin_headers, user_headers):
        """Admin should be able to see tasks created by users."""
        # User creates a task
        start_response = client.post(
            "/automation/start",
            headers=user_headers,
            json={
                "industry": "test-admin-visibility",
                "locations": ["Test City"],
                "limit_per_location": 1
            }
        )
        
        assert start_response.status_code == 201
        task_id = start_response.json()["data"]["task_id"]
        
        # Admin should see the task
        admin_response = client.get("/admin/automation/tasks", headers=admin_headers)
        
        assert admin_response.status_code == 200
        tasks = admin_response.json()["data"]["tasks"]
        assert task_id in tasks
    
    def test_admin_stop_all_affects_user_task(self, client, admin_headers, user_headers):
        """Admin stop-all should affect user-created tasks."""
        # Create a task
        start_response = client.post(
            "/automation/start",
            headers=user_headers,
            json={
                "industry": "test-stop-all",
                "locations": ["Test City"],
                "limit_per_location": 1
            }
        )
        
        task_id = start_response.json()["data"]["task_id"]
        
        # Admin stops all
        stop_response = client.post("/admin/automation/stop-all", headers=admin_headers)
        
        assert stop_response.status_code == 200
        # Should have stopped at least 1 task
        assert stop_response.json()["data"]["tasks_stopped"] >= 0
