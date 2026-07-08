# API Overview

## Authentication

Most endpoints require an API key via the `X-API-Key` header. A valid `X-Admin-Secret` header may be sent instead of `X-API-Key` on any of these endpoints — it bypasses per-key quota entirely.

Admin-only endpoints (`/admin/*`) require `X-Admin-Secret`.

## Response Format

All responses follow a standardized structure:

```json
{
  "success": true,
  "message": "Human readable message",
  "data": { ... },
  "error": false
}
```

## Tier Limits

| Tier | Monthly Leads | Rate Limit |
|------|---------------|------------|
| Free | 100 | 10/min |
| Pro | 5,000 | 60/min |
| Enterprise | Unlimited | 300/min |

## API Sections

- [Keys API](keys.md) - API key management (admin & user)
- [Automation API](automation.md) - Scraping and lead generation
