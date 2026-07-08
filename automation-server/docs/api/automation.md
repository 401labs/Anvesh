# Automation API

Lead generation, scraping, and lead management endpoints.

> All endpoints accept `X-API-Key`, or `X-Admin-Secret` in its place.

## Tasks

### Start a Scrape

`POST /automation/start`

```bash
curl -X POST http://localhost:8000/automation/start \
  -H "X-API-Key: anv_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "dentist",
    "locations": ["New York, NY", "Los Angeles, CA"],
    "limit_per_location": 50
  }'
```

**Response (201):**
```json
{
  "success": true,
  "message": "Automation task started",
  "data": { "task_id": "abc-123-def-456" }
}
```

---

### Stop All Running Tasks
`POST /automation/stop`

```bash
curl -X POST http://localhost:8000/automation/stop -H "X-API-Key: anv_your_key"
```

---

### Stop a Specific Task
`POST /automation/tasks/{task_id}/stop`

---

### Get a Task's Status
`GET /automation/tasks/{task_id}`

---

### List Tasks (paginated)
`GET /automation/tasks?limit=20&offset=0`

Most recently started first.

**Response:**
```json
{
  "success": true,
  "data": {
    "tasks": [{ "id": "abc-123", "status": "completed", "..." : "..." }],
    "total": 12,
    "limit": 20,
    "offset": 0
  }
}
```

---

### Delete a Task
`DELETE /automation/tasks/{task_id}`

Removes a finished task from the list. Returns `400` if the task is still running — stop it first.

---

## Leads

### List Leads (paginated, filterable, sortable)
`GET /automation/leads?limit=20&offset=0`

Most recently scraped first by default. All filter params are optional and combine with AND.

| Param | Type | Notes |
|---|---|---|
| `industry` | string | Exact match, case-insensitive |
| `location` | string | Exact match, case-insensitive |
| `category` | string | Exact match, case-insensitive |
| `has_website` | bool | |
| `has_email` | bool | |
| `is_claimed` | bool | |
| `min_rating` | float 0–5 | Inclusive |
| `search` | string | Substring match across business name, address, phone |
| `sort_by` | `created_at` \| `rating` \| `review_count` \| `business_name` | Default `created_at` |
| `sort_dir` | `asc` \| `desc` | Default `desc` |

```bash
curl "http://localhost:8000/automation/leads?industry=coffee%20shop&has_email=true&sort_by=rating&sort_dir=desc" \
  -H "X-API-Key: anv_your_key"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "leads": [{ "id": 1, "business_name": "Joe's Coffee", "..." : "..." }],
    "total": 340,
    "limit": 20,
    "offset": 0
  }
}
```

---

### Get Available Filter Values
`GET /automation/leads/filter-options`

Distinct industries/locations/categories currently in the database, for populating filter dropdowns.

**Response:**
```json
{
  "success": true,
  "data": {
    "industries": ["coffee shop", "restaurants"],
    "locations": ["Mumbai", "Seattle"],
    "categories": ["Cafe", "Pizza restaurant"]
  }
}
```

---

### Create a Lead
`POST /automation/leads`

Manually add a lead (e.g. one found outside of scraping).

```bash
curl -X POST http://localhost:8000/automation/leads \
  -H "X-API-Key: anv_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Joe'\''s Coffee",
    "industry": "coffee shop",
    "location": "Seattle",
    "address": "123 Main St, Seattle, WA"
  }'
```

Returns `409` if a lead with the same business name and address already exists.

---

### Update a Lead
`PATCH /automation/leads/{lead_id}`

Only send the fields you want to change.

```bash
curl -X PATCH http://localhost:8000/automation/leads/1 \
  -H "X-API-Key: anv_your_key" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1 555-0100"}'
```

---

### Delete a Lead
`DELETE /automation/leads/{lead_id}`

---

### Delete Multiple Leads
`POST /automation/leads/bulk-delete`

```bash
curl -X POST http://localhost:8000/automation/leads/bulk-delete \
  -H "X-API-Key: anv_your_key" \
  -H "Content-Type: application/json" \
  -d '{"ids": [1, 2, 3]}'
```

---

### Export Leads to CSV
`GET /automation/export`

Downloads scraped leads (unpaginated) as a CSV file. Accepts the same filter
params as `GET /automation/leads` (`industry`, `location`, `category`,
`has_website`, `has_email`, `is_claimed`, `min_rating`, `search`) — with no
filters, every lead is exported; with filters, only matching leads are.

```bash
# Export everything
curl http://localhost:8000/automation/export \
  -H "X-API-Key: anv_your_key" \
  -o leads.csv

# Export only unclaimed coffee shops
curl "http://localhost:8000/automation/export?industry=coffee%20shop&is_claimed=false" \
  -H "X-API-Key: anv_your_key" \
  -o leads.csv
```
