"""
Tests for automation routes with authentication.
"""
import pytest


class TestAutomationAuth:
    """Tests for automation routes requiring authentication."""
    
    def test_start_requires_auth(self, client):
        """Start automation endpoint should require API key (422 for missing header)."""
        response = client.post(
            "/automation/start",
            json={"industry": "restaurants", "locations": ["Mumbai"]}
        )
        
        # FastAPI returns 422 for missing required headers
        assert response.status_code == 422
    
    def test_start_with_auth(self, client, user_headers):
        """Start automation endpoint should work with valid API key."""
        response = client.post(
            "/automation/start",
            headers=user_headers,
            json={
                "industry": "test-industry",
                "locations": ["Test City"],
                "limit_per_location": 1
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] == True
        assert "task_id" in data["data"]
    
    def test_stop_with_auth(self, client, user_headers):
        """Stop automation endpoint should work with valid API key."""
        response = client.post(
            "/automation/stop",
            headers=user_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_tasks_requires_auth(self, client):
        """Tasks endpoint should require API key (422 for missing header)."""
        response = client.get("/automation/tasks")
        
        assert response.status_code == 422
    
    def test_tasks_with_auth(self, client, user_headers):
        """Tasks endpoint should work with valid API key."""
        response = client.get("/automation/tasks", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_export_requires_auth(self, client):
        """Export endpoint should require API key (422 for missing header)."""
        response = client.get("/automation/export")
        
        assert response.status_code == 422
    
    def test_export_with_auth(self, client, user_headers):
        """Export endpoint should work with valid API key."""
        response = client.get("/automation/export", headers=user_headers)
        
        # Should return 200 (either file or success message)
        assert response.status_code == 200


class TestAutomationResponses:
    """Tests for standardized automation responses."""
    
    def test_start_requires_industry(self, client, user_headers):
        """Starting automation without industry should return validation error."""
        response = client.post(
            "/automation/start",
            headers=user_headers,
            json={"locations": ["Mumbai"]}
        )
        
        # Pydantic validation error
        assert response.status_code == 422
    
    def test_start_requires_locations(self, client, user_headers):
        """Starting automation without locations should return validation error."""
        response = client.post(
            "/automation/start",
            headers=user_headers,
            json={"industry": "restaurants"}
        )
        
        # Pydantic validation error
        assert response.status_code == 422
    
    def test_task_not_found(self, client, user_headers):
        """Non-existent task should return error."""
        response = client.get("/automation/tasks/non-existent-task-id", headers=user_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] == False
        assert data["error"] == True
    
    def test_stop_specific_task_not_found(self, client, user_headers):
        """Stopping non-existent task should return error."""
        response = client.post("/automation/tasks/non-existent-task-id/stop", headers=user_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] == False
        assert data["error"] == True


class TestAutomationWorkflow:
    """Tests for complete automation workflow."""
    
    def test_start_and_check_status(self, client, user_headers):
        """Start a task and verify it appears in task list."""
        # Start a task
        start_response = client.post(
            "/automation/start",
            headers=user_headers,
            json={
                "industry": "test-industry",
                "locations": ["Test City"],
                "limit_per_location": 1
            }
        )
        
        assert start_response.status_code == 201
        task_id = start_response.json()["data"]["task_id"]
        
        # Check task status
        status_response = client.get(
            f"/automation/tasks/{task_id}",
            headers=user_headers
        )
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["success"] == True
        assert data["data"]["id"] == task_id
