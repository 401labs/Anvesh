"""
Tests for automation routes with authentication.
"""
import pytest


class TestAutomationAuth:
    """Tests for automation routes requiring authentication."""
    
    def test_start_requires_auth(self, client):
        """Start automation endpoint should require an API key or admin secret (401 when neither is given)."""
        response = client.post(
            "/automation/start",
            json={"industry": "restaurants", "locations": ["Mumbai"]}
        )

        assert response.status_code == 401
    
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
        """Tasks endpoint should require an API key or admin secret (401 when neither is given)."""
        response = client.get("/automation/tasks")

        assert response.status_code == 401
    
    def test_tasks_with_auth(self, client, user_headers):
        """Tasks endpoint should work with valid API key."""
        response = client.get("/automation/tasks", headers=user_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_export_requires_auth(self, client):
        """Export endpoint should require an API key or admin secret (401 when neither is given)."""
        response = client.get("/automation/export")

        assert response.status_code == 401
    
    def test_export_with_auth(self, client, user_headers):
        """Export endpoint should work with valid API key."""
        response = client.get("/automation/export", headers=user_headers)
        
        # Should return 200 (either file or success message)
        assert response.status_code == 200


class TestLeadsEndpoint:
    """Tests for the paginated leads listing endpoint."""

    def test_leads_requires_auth(self, client):
        """Leads endpoint should require an API key or admin secret (401 when neither is given)."""
        response = client.get("/automation/leads")

        assert response.status_code == 401

    def test_leads_with_admin_secret(self, client, admin_headers):
        """Leads endpoint should also accept the admin secret in place of an API key."""
        response = client.get("/automation/leads", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    def test_leads_with_auth(self, client, user_headers):
        """Leads endpoint should work with valid API key and return pagination fields."""
        response = client.get("/automation/leads", headers=user_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "leads" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["leads"], list)

    def test_leads_respects_limit_and_offset(self, client, user_headers):
        """Leads endpoint should echo back the requested limit/offset."""
        response = client.get(
            "/automation/leads?limit=5&offset=0",
            headers=user_headers
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["leads"]) <= 5

    def test_leads_rejects_invalid_limit(self, client, user_headers):
        """Leads endpoint should reject an out-of-range limit."""
        response = client.get(
            "/automation/leads?limit=0",
            headers=user_headers
        )

        assert response.status_code == 422


class TestLeadsFiltersSortAndExport:
    """Tests for lead filtering, sorting, filter-options, and filtered CSV export."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "Filter Test Business",
            "industry": "filter-test-industry",
            "location": "Filtertown",
            "address": "1 Filter Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_filter_options(self, client, user_headers):
        """filter-options should include a freshly created lead's industry."""
        create_response = self._create_lead(client, user_headers, business_name="Filter Options Business")
        lead_id = create_response.json()["data"]["id"]

        response = client.get("/automation/leads/filter-options", headers=user_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert "filter-test-industry" in data["industries"]
        assert "Filtertown" in data["locations"]

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_filter_by_industry(self, client, user_headers):
        """Filtering by industry should only return matching leads."""
        create_response = self._create_lead(client, user_headers, business_name="Industry Filter Business")
        lead_id = create_response.json()["data"]["id"]

        response = client.get(
            "/automation/leads?industry=filter-test-industry",
            headers=user_headers
        )

        assert response.status_code == 200
        leads = response.json()["data"]["leads"]
        assert all(l["industry"] == "filter-test-industry" for l in leads)
        assert any(l["id"] == lead_id for l in leads)

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_filter_by_has_email(self, client, user_headers):
        """has_email=true should only return leads with a non-empty email."""
        with_email = self._create_lead(
            client, user_headers, business_name="Has Email Business", email="test@example.com"
        )
        without_email = self._create_lead(client, user_headers, business_name="No Email Business")
        with_id = with_email.json()["data"]["id"]
        without_id = without_email.json()["data"]["id"]

        response = client.get("/automation/leads?has_email=true&limit=200", headers=user_headers)

        assert response.status_code == 200
        leads = response.json()["data"]["leads"]
        ids = [l["id"] for l in leads]
        assert with_id in ids
        assert without_id not in ids

        client.delete(f"/automation/leads/{with_id}", headers=user_headers)
        client.delete(f"/automation/leads/{without_id}", headers=user_headers)

    def test_sort_by_rating(self, client, user_headers):
        """sort_by=rating&sort_dir=desc should order leads by rating descending."""
        low = self._create_lead(client, user_headers, business_name="Low Rating Business", rating=2.0)
        high = self._create_lead(client, user_headers, business_name="High Rating Business", rating=4.9)
        low_id = low.json()["data"]["id"]
        high_id = high.json()["data"]["id"]

        response = client.get(
            "/automation/leads?industry=filter-test-industry&sort_by=rating&sort_dir=desc",
            headers=user_headers
        )

        assert response.status_code == 200
        leads = response.json()["data"]["leads"]
        rated_ids = [l["id"] for l in leads if l["id"] in (low_id, high_id)]
        assert rated_ids == [high_id, low_id]

        client.delete(f"/automation/leads/{low_id}", headers=user_headers)
        client.delete(f"/automation/leads/{high_id}", headers=user_headers)

    def test_export_respects_filters(self, client, user_headers):
        """CSV export should only include leads matching the given filters."""
        matching = self._create_lead(client, user_headers, business_name="Export Match Business")
        other = self._create_lead(
            client, user_headers, business_name="Export No Match Business", industry="something-else"
        )
        matching_id = matching.json()["data"]["id"]
        other_id = other.json()["data"]["id"]

        response = client.get(
            "/automation/export?industry=filter-test-industry",
            headers=user_headers
        )

        assert response.status_code == 200
        csv_body = response.text
        assert "Export Match Business" in csv_body
        assert "Export No Match Business" not in csv_body

        client.delete(f"/automation/leads/{matching_id}", headers=user_headers)
        client.delete(f"/automation/leads/{other_id}", headers=user_headers)


class TestLeadsCRUD:
    """Tests for creating, updating, and deleting leads."""

    def _create_lead(self, client, user_headers, **overrides):
        payload = {
            "business_name": "CRUD Test Business",
            "industry": "testing",
            "location": "Testville",
            "address": "1 Test Way",
        }
        payload.update(overrides)
        return client.post("/automation/leads", headers=user_headers, json=payload)

    def test_create_lead(self, client, user_headers):
        """A new lead should be creatable via the API."""
        response = self._create_lead(client, user_headers, business_name="Create Test Business")

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["business_name"] == "Create Test Business"
        lead_id = data["id"]

        # Cleanup
        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_create_duplicate_lead_conflicts(self, client, user_headers):
        """Creating a lead with the same business_name+address twice should 409."""
        first = self._create_lead(client, user_headers, business_name="Duplicate Test Business")
        lead_id = first.json()["data"]["id"]

        second = self._create_lead(client, user_headers, business_name="Duplicate Test Business")
        assert second.status_code == 409

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_update_lead(self, client, user_headers):
        """A lead's fields should be updatable."""
        create_response = self._create_lead(client, user_headers, business_name="Update Test Business")
        lead_id = create_response.json()["data"]["id"]

        response = client.patch(
            f"/automation/leads/{lead_id}",
            headers=user_headers,
            json={"phone": "+1 555-0100"}
        )

        assert response.status_code == 200
        assert response.json()["data"]["phone"] == "+1 555-0100"

        client.delete(f"/automation/leads/{lead_id}", headers=user_headers)

    def test_update_lead_not_found(self, client, user_headers):
        """Updating a non-existent lead should 404."""
        response = client.patch(
            "/automation/leads/999999999",
            headers=user_headers,
            json={"phone": "+1 555-0100"}
        )

        assert response.status_code == 404

    def test_delete_lead(self, client, user_headers):
        """A lead should be deletable, and gone afterward."""
        create_response = self._create_lead(client, user_headers, business_name="Delete Test Business")
        lead_id = create_response.json()["data"]["id"]

        response = client.delete(f"/automation/leads/{lead_id}", headers=user_headers)
        assert response.status_code == 200

        second_delete = client.delete(f"/automation/leads/{lead_id}", headers=user_headers)
        assert second_delete.status_code == 404

    def test_bulk_delete_leads(self, client, user_headers):
        """Multiple leads should be deletable in one call."""
        ids = []
        for i in range(3):
            resp = self._create_lead(client, user_headers, business_name=f"Bulk Test Business {i}")
            ids.append(resp.json()["data"]["id"])

        response = client.post(
            "/automation/leads/bulk-delete",
            headers=user_headers,
            json={"ids": ids}
        )

        assert response.status_code == 200
        assert response.json()["data"]["deleted"] == 3


class TestTasksPagination:
    """Tests for paginated task listing."""

    def test_tasks_pagination_shape(self, client, user_headers):
        """Tasks list should include pagination fields."""
        response = client.get("/automation/tasks", headers=user_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data["tasks"], list)
        assert "total" in data
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_tasks_respects_limit(self, client, user_headers):
        """Tasks list should respect a custom limit."""
        response = client.get("/automation/tasks?limit=1&offset=0", headers=user_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["limit"] == 1
        assert len(data["tasks"]) <= 1


class TestTaskDeletion:
    """Tests for deleting finished tasks."""

    def test_delete_task_after_stopped(self, client, user_headers):
        """A task can be deleted once it's no longer running (stopped/completed)."""
        start_response = client.post(
            "/automation/start",
            headers=user_headers,
            json={"industry": "test-industry", "locations": ["Test City"], "limit_per_location": 1}
        )
        task_id = start_response.json()["data"]["task_id"]
        client.post(f"/automation/tasks/{task_id}/stop", headers=user_headers)

        # Poll until it's actually finished (background scraper needs a moment to notice the stop signal)
        import time
        for _ in range(30):
            status = client.get(f"/automation/tasks/{task_id}", headers=user_headers).json()["data"]
            if not status["running"]:
                break
            time.sleep(1)

        response = client.delete(f"/automation/tasks/{task_id}", headers=user_headers)
        assert response.status_code == 200

        get_response = client.get(f"/automation/tasks/{task_id}", headers=user_headers)
        assert get_response.status_code == 404

    def test_delete_task_not_found(self, client, user_headers):
        """Deleting a non-existent task should 404."""
        response = client.delete("/automation/tasks/non-existent-task-id", headers=user_headers)
        assert response.status_code == 404


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
