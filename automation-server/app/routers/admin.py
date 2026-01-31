"""
Admin-only automation management routes.

This module provides admin endpoints for system-wide
automation monitoring and control. All endpoints require
X-Admin-Secret header for authentication.
"""
from fastapi import APIRouter, Depends
from datetime import datetime

from app.middleware.auth import require_admin
from app.routers.automation import TASKS
from app.models.automation import TaskStatus
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
    task_summary = {
        "total": len(TASKS),
        "running": sum(1 for t in TASKS.values() if t["running"]),
        "completed": sum(1 for t in TASKS.values() if t["status"] == TaskStatus.COMPLETED),
        "stopped": sum(1 for t in TASKS.values() if t["status"] == TaskStatus.STOPPED),
        "error": sum(1 for t in TASKS.values() if t["status"] == TaskStatus.ERROR),
    }
    
    return api_success("All tasks retrieved", {
        "summary": task_summary,
        "tasks": TASKS
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
    count_stopped = 0
    for tid, task in TASKS.items():
        if task["running"]:
            task["stop"] = True
            count_stopped += 1
    
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
    running_count = sum(1 for t in TASKS.values() if t["running"])
    completed_count = sum(1 for t in TASKS.values() if t["status"] == TaskStatus.COMPLETED)
    stopped_count = sum(1 for t in TASKS.values() if t["status"] == TaskStatus.STOPPED)
    error_count = sum(1 for t in TASKS.values() if t["status"] == TaskStatus.ERROR)
    
    # Calculate locations and industries being scraped
    active_industries = set()
    active_locations = set()
    for task in TASKS.values():
        if task["running"]:
            config = task.get("config", {})
            active_industries.add(config.get("industry", "unknown"))
            for loc in config.get("locations", []):
                active_locations.add(loc)
    
    stats = {
        "timestamp": datetime.now().isoformat(),
        "tasks": {
            "total": len(TASKS),
            "running": running_count,
            "completed": completed_count,
            "stopped": stopped_count,
            "error": error_count,
        },
        "active_scraping": {
            "industries": list(active_industries),
            "locations": list(active_locations),
        },
        "success_rate": f"{(completed_count / len(TASKS) * 100):.1f}%" if TASKS else "N/A",
    }
    
    return api_success("System statistics retrieved", stats)
