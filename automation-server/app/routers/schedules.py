"""
Scheduled (recurring) scrape API routes.
"""
from fastapi import APIRouter, Depends, Path
from app.models.schedule import ScheduleCreate, ScheduleUpdate
from app.models.api_key import APIKeyData
from app.db import (
    create_schedule,
    get_schedule,
    list_schedules,
    update_schedule,
    delete_schedule,
)
from app.services.scheduler import fire_schedule
from app.middleware.auth import get_api_key
from app.helpers import api_success, api_error
from app.helpers.response import APIResponse, STANDARD_RESPONSES

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.post(
    "",
    summary="Create a recurring scrape schedule",
    description="""
Save a scrape configuration (industry + locations + limit) to re-run
automatically every `interval_hours` hours — e.g. `24` for daily, `168` for
weekly. The first run happens on the next scheduler tick (within about a
minute of creation), then repeats on the interval.
    """,
    response_description="The created schedule",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
    status_code=201,
)
def create_schedule_endpoint(request: ScheduleCreate, api_key: APIKeyData = Depends(get_api_key)):
    """Create a recurring scrape schedule."""
    schedule = create_schedule(request.name, request.industry, request.locations, request.limit_per_location, request.interval_hours)
    if not schedule:
        return api_error("Failed to create schedule", status_code=500)
    return api_success("Schedule created", schedule, status_code=201)


@router.get(
    "",
    summary="List scrape schedules",
    description="List all recurring scrape schedules.",
    response_description="All schedules",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def list_schedules_endpoint(api_key: APIKeyData = Depends(get_api_key)):
    """List all recurring scrape schedules."""
    return api_success("Schedules retrieved", {"schedules": list_schedules()})


@router.patch(
    "/{schedule_id}",
    summary="Update a scrape schedule",
    description="Update a schedule's fields (including `enabled`, to pause/resume it). Only the fields you send are changed.",
    response_description="The updated schedule",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def update_schedule_endpoint(
    request: ScheduleUpdate,
    schedule_id: int = Path(..., description="The schedule ID"),
    api_key: APIKeyData = Depends(get_api_key),
):
    """Update a scrape schedule."""
    if not get_schedule(schedule_id):
        return api_error("Schedule not found", status_code=404)
    updated = update_schedule(schedule_id, request.model_dump(exclude_unset=True))
    if not updated:
        return api_error("Schedule not found", status_code=404)
    return api_success("Schedule updated", updated)


@router.delete(
    "/{schedule_id}",
    summary="Delete a scrape schedule",
    description="Permanently delete a recurring scrape schedule. Doesn't affect tasks it already started.",
    response_description="Confirmation of deletion",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def delete_schedule_endpoint(
    schedule_id: int = Path(..., description="The schedule ID"),
    api_key: APIKeyData = Depends(get_api_key),
):
    """Delete a scrape schedule."""
    if not delete_schedule(schedule_id):
        return api_error("Schedule not found", status_code=404)
    return api_success(f"Schedule {schedule_id} deleted")


@router.post(
    "/{schedule_id}/run-now",
    summary="Run a schedule immediately",
    description="Fire a schedule's scrape right now instead of waiting for its next scheduled tick, and reset its interval from this run.",
    response_description="The newly started task's id",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def run_schedule_now_endpoint(
    schedule_id: int = Path(..., description="The schedule ID"),
    api_key: APIKeyData = Depends(get_api_key),
):
    """Fire a schedule immediately, regardless of its next_run_at."""
    schedule = get_schedule(schedule_id)
    if not schedule:
        return api_error("Schedule not found", status_code=404)
    task_id = fire_schedule(schedule)
    return api_success("Schedule triggered", {"task_id": task_id})
