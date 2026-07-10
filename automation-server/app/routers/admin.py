"""
Admin-only automation management routes.

This module provides admin endpoints for system-wide
automation monitoring and control. All endpoints require
X-Admin-Secret header for authentication.
"""
from fastapi import APIRouter, Depends
from datetime import datetime

from app.middleware.auth import require_admin
from app.db import list_all_tasks, list_running_tasks, get_task_counts, request_stop_all
from app.helpers import api_success
from app.helpers.response import APIResponse, STANDARD_RESPONSES

router = APIRouter(prefix="/admin/automation", tags=["Admin - Automation"])


@router.get(
    "/tasks",
    summary="List all automation tasks (Admin)",
    description="""
View all automation tasks across the entire system.

Unlike the user endpoint, this shows ALL tasks regardless of who created them.
Useful for monitoring system-wide scraping activity.
    """,
    response_description="All automation tasks with their current status",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def admin_get_all_tasks(_: bool = Depends(require_admin)):
    """Get all automation tasks system-wide. Admin only."""
    task_summary = get_task_counts()

    return api_success("All tasks retrieved", {
        "summary": task_summary,
        "tasks": {t["id"]: t for t in list_all_tasks()}
    })


@router.post(
    "/stop-all",
    summary="Force stop all running tasks (Admin)",
    description="""
Send a stop signal to ALL running automation tasks across the entire system.

This is a system-wide emergency stop that affects all users' tasks.
Use with caution!
    """,
    response_description="Count of tasks that received the stop signal",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def admin_stop_all_tasks(_: bool = Depends(require_admin)):
    """Force stop all running tasks system-wide. Admin only."""
    count_stopped = request_stop_all()

    return api_success(
        f"Stop signal sent to {count_stopped} tasks",
        {"tasks_stopped": count_stopped}
    )


@router.get(
    "/stats",
    summary="Get system-wide automation statistics (Admin)",
    description="""
Retrieve system-wide automation statistics.

Returns aggregate data about:
- Total tasks created
- Currently running tasks
- Task completion rates
- Error counts
    """,
    response_description="System-wide automation statistics",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def admin_get_stats(_: bool = Depends(require_admin)):
    """Get system-wide automation statistics. Admin only."""
    counts = get_task_counts()
    running_tasks = list_running_tasks()

    # Calculate locations and industries being scraped
    active_industries = set()
    active_locations = set()
    for task in running_tasks:
        config = task.get("config", {})
        active_industries.add(config.get("industry", "unknown"))
        for loc in config.get("locations", []):
            active_locations.add(loc)

    stats = {
        "timestamp": datetime.now().isoformat(),
        "tasks": counts,
        "active_scraping": {
            "industries": list(active_industries),
            "locations": list(active_locations),
        },
        "success_rate": f"{(counts['completed'] / counts['total'] * 100):.1f}%" if counts["total"] else "N/A",
    }

    return api_success("System statistics retrieved", stats)
