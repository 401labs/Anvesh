# Keys API

API key management endpoints for admins and users.

## Admin Endpoints

> Require `X-Admin-Secret` header

### Create API Key
`POST /admin/keys`

```bash
curl -X POST http://localhost:8000/admin/keys \
  -H "X-Admin-Secret: your-secret" \
  -H "Content-Type: application/json" \
  -d '{"name": "My App", "tier": "free", "expires_in_days": 30}'
```

**Response (201):**
```json
{
  "success": true,
  "message": "API key created successfully",
  "data": {
    "id": 1,
    "name": "My App",
    "key": "anv_abc123...",
    "tier": "free",
    "monthly_limit": 100
  }
}
```

> ⚠️ The `key` value is only shown once. Store it securely!

---

### List API Keys (paginated)
`GET /admin/keys?limit=20&offset=0`

**Response:**
```json
{
  "success": true,
  "data": {
    "keys": [{ "id": 1, "name": "My App", "tier": "free", "..." : "..." }],
    "total": 42,
    "limit": 20,
    "offset": 0
  }
}
```

---

### Get API Key Details
`GET /admin/keys/{id}`

---

### Update API Key
`PATCH /admin/keys/{id}`

Only send the fields you want to change.

```bash
curl -X PATCH http://localhost:8000/admin/keys/1 \
  -H "X-Admin-Secret: your-secret" \
  -H "Content-Type: application/json" \
  -d '{"tier": "pro"}'
```

`clear_expiry: true` removes an expiration date entirely.

---

### Get API Key Usage
`GET /admin/keys/{id}/usage`

---

### Delete API Key
`DELETE /admin/keys/{id}`

---

### Revoke API Key
`POST /admin/keys/{id}/revoke`

---

## User Endpoints

> Require `X-API-Key` header

### Get Your API Key Info
`GET /me`

---

### Get Your Usage Stats
`GET /me/usage`

**Response:**
```json
{
  "success": true,
  "data": {
    "api_key_id": 1,
    "total_requests": 150,
    "total_leads": 450,
    "monthly_leads": 75,
    "monthly_limit": 100,
    "remaining_quota": 25
  }
}
```
