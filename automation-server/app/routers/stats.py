"""
Analytics dashboard API routes: aggregate stats across leads, outreach, and tasks.
"""
from fastapi import APIRouter, Depends, Query
from app.models.api_key import APIKeyData
from app.db import (
    get_lead_stats,
    get_leads_by_day,
    get_top_industries,
    get_top_locations,
    get_outreach_stats,
    get_task_counts,
)
from app.middleware.auth import get_api_key
from app.helpers import api_success
from app.helpers.response import APIResponse, STANDARD_RESPONSES

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get(
    "",
    summary="Get the analytics dashboard",
    description="""
Aggregate stats across leads, outreach, and scrape tasks — everything a
dashboard view needs in one call:

- Lead counts by outreach status and by opportunity-score tier (hot ≥70 / warm ≥40 / cool)
- Leads scraped per day over the requested window
- Top industries and locations scraped
- Outreach email send/failure counts
- Scrape task counts by status
    """,
    response_description="Dashboard stats",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def get_dashboard_stats(
    days: int = Query(30, ge=1, le=365, description="Window for the leads-per-day trend"),
    api_key: APIKeyData = Depends(get_api_key),
):
    """Aggregate stats for the analytics dashboard."""
    return api_success("Stats retrieved", {
        "leads": get_lead_stats(),
        "leads_by_day": get_leads_by_day(days=days),
        "top_industries": get_top_industries(),
        "top_locations": get_top_locations(),
        "outreach": get_outreach_stats(),
        "tasks": get_task_counts(),
    })
