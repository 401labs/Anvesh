"""
Automation API routes for lead scraping tasks.

This module provides endpoints to start, stop, and monitor
lead scraping automation tasks.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query
from fastapi.responses import FileResponse
from app.models.automation import (
    ScrapeRequest,
    TaskResponse,
    TaskStartResponse,
    TaskStopResponse,
    TaskStatus,
    LeadCreate,
    LeadUpdate,
    LeadBulkDeleteRequest,
)
from app.models.api_key import APIKeyData
from app.services.scraper import scrape_google_maps
from app.db import (
    get_all_leads,
    get_leads,
    count_leads,
    get_lead,
    create_lead,
    update_lead,
    delete_lead,
    bulk_delete_leads,
    get_lead_filter_options,
    log_usage,
    LeadInsertError,
    create_task,
    get_task,
    list_tasks,
    count_tasks,
    set_task_status,
    set_task_running,
    get_task_stop_flag,
    request_stop,
    request_stop_all,
    delete_task as delete_task_row,
)
from app.middleware.auth import get_api_key
from app.helpers import api_success, api_error
from app.helpers.response import APIResponse, STANDARD_RESPONSES
from typing import Optional
import csv
import os
import time
import uuid

router = APIRouter(prefix="/automation", tags=["Automation"])

# Hard ceiling on how long a single task may run, regardless of how many
# locations or how "unlimited" the per-location cap is. Without this, a scrape
# stuck in a selector-wait loop (Google Maps markup changed, network stall,
# etc.) stays "running" forever — observed in practice as a task still marked
# running=true 30+ minutes after its scrape thread stopped making progress,
# with no way for an operator to distinguish "still working" from "wedged".
MAX_TASK_DURATION_SECONDS = 3600  # 1 hour


def make_stop_checker(task_id: str, poll_interval: float = 2.0, max_duration_seconds: Optional[float] = None):
    """
    Returns a callable that reports whether `task_id` has been flagged to stop,
    backed by the `automation_tasks.stop` column so a stop request handled by a
    different worker (or process) is still observed. Throttled to one DB read per
    `poll_interval` seconds regardless of how often the scraper calls it.

    Also self-terminates once `max_duration_seconds` has elapsed since the
    checker was created — a task can never run forever, even if nothing ever
    flips its `stop` column. Callers can distinguish the two via `.timed_out()`.
    `max_duration_seconds` defaults to the module-level `MAX_TASK_DURATION_SECONDS`,
    looked up at call time (not bound as a literal default) so tests can
    monkeypatch the module constant and have it actually take effect.
    """
    if max_duration_seconds is None:
        max_duration_seconds = MAX_TASK_DURATION_SECONDS

    state = {"last_check": 0.0, "stop": False, "timed_out": False}
    start = time.monotonic()

    def check() -> bool:
        if not state["stop"] and time.monotonic() - start > max_duration_seconds:
            state["stop"] = True
            state["timed_out"] = True
            return True

        now = time.monotonic()
        if now - state["last_check"] >= poll_interval:
            state["last_check"] = now
            if get_task_stop_flag(task_id):
                state["stop"] = True
        return state["stop"]

    check.timed_out = lambda: state["timed_out"]
    return check


def background_task_scraper(task_id: str, request: ScrapeRequest):
    """
    Runs the scraper in the background for a specific task ID.
    """
    print(f"▶️ Automation Started: {request.industry} (ID: {task_id})")
    set_task_status(task_id, TaskStatus.RUNNING)
    should_stop = make_stop_checker(task_id)

    def finish_as_stopped_or_timed_out():
        if should_stop.timed_out():
            minutes = MAX_TASK_DURATION_SECONDS // 60
            set_task_status(task_id, TaskStatus.ERROR, error=f"Scrape timed out after {minutes} minutes")
            print(f"⏱️ Automation {task_id} timed out after {minutes} minutes.")
        else:
            set_task_status(task_id, TaskStatus.STOPPED)
            print(f"🛑 Automation {task_id} stopped by user.")

    try:
        total_locations = len(request.locations)
        for i, loc in enumerate(request.locations):
            if should_stop():
                finish_as_stopped_or_timed_out()
                break

            print(f"📍 [{i+1}/{total_locations}] Processing location: {loc} (ID: {task_id})")

            scrape_google_maps(
                industry=request.industry,
                location=loc,
                total=request.limit_per_location,
                stop_signal=should_stop,
                headless=request.headless
            )

            if should_stop():
                finish_as_stopped_or_timed_out()
                break

            print(f"✅ Finished location: {loc}. Checking next...")
        else:
            # Loop ran to completion without ever `break`-ing out via a stop/timeout.
            set_task_status(task_id, TaskStatus.COMPLETED)

    except Exception as e:
        set_task_status(task_id, TaskStatus.ERROR, error=str(e))
        print(f"❌ Automation {task_id} Error: {e}")
    finally:
        set_task_running(task_id, False)
        finished_task = get_task(task_id)
        print(f"🏁 Automation {task_id} Finished. Status: {finished_task['status'] if finished_task else 'unknown'}")


@router.post(
    "/start",
    summary="Start a new automation task",
    description="""
Start a new lead scraping automation task. The task runs in the background
and scrapes Google Maps for businesses matching your criteria.

**How it works:**
1. Provide an industry keyword (e.g., "restaurants", "gyms")
2. Specify one or more locations to search
3. Optionally set a limit per location

The task will run asynchronously and you can monitor its progress
using the `/automation/tasks/{task_id}` endpoint.
    """,
    response_description="Returns the unique task ID for tracking",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
    status_code=201,
)
def start_automation(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    api_key: APIKeyData = Depends(get_api_key)
):
    """Start a new lead scraping automation task."""
    if api_key.id is not None:
        log_usage(api_key.id, "/automation/start", 0)
    
    task_id = str(uuid.uuid4())
    create_task(task_id, request.model_dump())

    background_tasks.add_task(background_task_scraper, task_id, request)
    return api_success("Automation task started", {"task_id": task_id}, status_code=201)


@router.post(
    "/stop",
    summary="Stop all running tasks",
    description="""
Send a stop signal to all currently running automation tasks.

Tasks will gracefully stop after completing their current operation.
This is useful when you want to halt all scraping activity at once.
    """,
    response_description="Returns the count of tasks that received the stop signal",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def stop_all_automation(api_key: APIKeyData = Depends(get_api_key)):
    """Stop all currently running automation tasks."""
    if api_key.id is not None:
        log_usage(api_key.id, "/automation/stop", 0)
    
    count_stopped = request_stop_all()

    if count_stopped == 0:
        return api_success("No running automation found", {"tasks_stopped": 0})
        
    return api_success(f"Stop signal sent to {count_stopped} tasks", {"tasks_stopped": count_stopped})


@router.post(
    "/tasks/{task_id}/stop",
    summary="Stop a specific task",
    description="Send a stop signal to a specific automation task by its ID.",
    response_description="Confirmation that the stop signal was sent",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def stop_task(
    task_id: str = Path(..., description="The unique task ID to stop"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """Stop a specific automation task by ID."""
    task = get_task(task_id)
    if not task:
        return api_error("Task not found", status_code=404)

    if not task["running"]:
        return api_success("Task is not running", {"task_id": task_id, "status": task["status"]})

    request_stop(task_id)
    return api_success("Stop signal sent", {"task_id": task_id})


@router.get(
    "/tasks/{task_id}",
    summary="Get task status",
    description="""
Retrieve the current status and details of a specific automation task.

**Possible statuses:**
- `idle` - Task is queued but not yet started
- `running` - Task is currently scraping
- `completed` - Task finished successfully
- `stopped` - Task was stopped by user
- `error` - Task encountered an error
    """,
    response_description="Task details including status, config, and any errors",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def get_task_status(
    task_id: str = Path(..., description="The unique task ID"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """Get the status of a specific automation task."""
    task = get_task(task_id)
    if not task:
        return api_error("Task not found", status_code=404)
    return api_success("Task status retrieved", task)


@router.get(
    "/tasks",
    summary="List tasks (paginated)",
    description="""
Retrieve a page of automation tasks (running and completed), most recently
started first. Use `limit` and `offset` to paginate.

This returns the full task history, persisted in Postgres.
    """,
    response_description="A page of tasks plus the total task count",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def get_all_tasks(
    limit: int = Query(20, ge=1, le=200, description="Max number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """List automation tasks, paginated."""
    page = list_tasks(limit=limit, offset=offset)
    total = count_tasks()
    return api_success("Tasks retrieved", {"tasks": page, "total": total, "limit": limit, "offset": offset})


@router.delete(
    "/tasks/{task_id}",
    summary="Delete a task",
    description="""
Remove a finished task from the task list. Only tasks that are not currently
running can be deleted — stop the task first if it's still running.
    """,
    response_description="Confirmation of deletion",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def delete_task_endpoint(
    task_id: str = Path(..., description="The unique task ID to delete"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """Delete a finished task."""
    task = get_task(task_id)
    if not task:
        return api_error("Task not found", status_code=404)

    if task["running"]:
        return api_error("Cannot delete a running task — stop it first", status_code=400)

    delete_task_row(task_id)
    return api_success(f"Task {task_id} deleted")


def _lead_filters_from_query(
    industry: Optional[str],
    location: Optional[str],
    category: Optional[str],
    has_website: Optional[bool],
    has_email: Optional[bool],
    is_claimed: Optional[bool],
    min_rating: Optional[float],
    search: Optional[str],
    status: Optional[str],
    min_score: Optional[int],
) -> dict:
    return {
        "industry": industry,
        "location": location,
        "category": category,
        "has_website": has_website,
        "has_email": has_email,
        "is_claimed": is_claimed,
        "min_rating": min_rating,
        "search": search,
        "status": status,
        "min_score": min_score,
    }


@router.get(
    "/leads/filter-options",
    summary="Get available lead filter values",
    description="Distinct industries, locations, and categories currently present in the leads table, for populating filter dropdowns.",
    response_description="Distinct filter values",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def get_leads_filter_options(api_key: APIKeyData = Depends(get_api_key)):
    """Get distinct industry/location/category values for lead filters."""
    return api_success("Filter options retrieved", get_lead_filter_options())


@router.get(
    "/leads",
    summary="List leads (paginated, filterable, sortable)",
    description="""
Retrieve a page of scraped leads from the database.

Use `limit`/`offset` to paginate, any of the filter params to narrow results,
and `sort_by`/`sort_dir` to order them. `/automation/export` accepts the same
filter params and downloads a CSV of exactly what matches (or everything, if
no filters are given).

Each lead includes a computed `score` (0-100): higher rating, more reviews, no
website, and an unclaimed listing all push it up — a rough "how worth pitching
is this business" ranking. Sort by it with `sort_by=score`, or narrow to the
best prospects with `min_score`.
    """,
    response_description="A page of leads plus the total matching count",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def list_leads(
    limit: int = Query(20, ge=1, le=200, description="Max number of leads to return"),
    offset: int = Query(0, ge=0, description="Number of leads to skip"),
    industry: Optional[str] = Query(None, description="Exact industry match (case-insensitive)"),
    location: Optional[str] = Query(None, description="Exact location match (case-insensitive)"),
    category: Optional[str] = Query(None, description="Exact category match (case-insensitive)"),
    has_website: Optional[bool] = Query(None, description="Filter to leads with/without a website"),
    has_email: Optional[bool] = Query(None, description="Filter to leads with/without an email"),
    is_claimed: Optional[bool] = Query(None, description="Filter to claimed/unclaimed Google Business listings"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating (inclusive)"),
    search: Optional[str] = Query(None, description="Free-text search across business name, address, and phone"),
    status: Optional[str] = Query(None, description="Filter to leads at a specific outreach status (new/contacted/replied/interested/won/lost)"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum opportunity score (inclusive) — see 'score' in the response"),
    sort_by: str = Query("created_at", pattern="^(created_at|rating|review_count|business_name|score)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """List leads from the database, paginated, filtered, and sorted."""
    filters = _lead_filters_from_query(industry, location, category, has_website, has_email, is_claimed, min_rating, search, status, min_score)
    leads = get_leads(limit=limit, offset=offset, filters=filters, sort_by=sort_by, sort_dir=sort_dir)
    total = count_leads(filters=filters)
    return api_success("Leads retrieved", {"leads": leads, "total": total, "limit": limit, "offset": offset})


@router.post(
    "/leads",
    summary="Create a lead manually",
    description="Manually add a lead, e.g. one found outside of Google Maps scraping.",
    response_description="The created lead",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
    status_code=201,
)
def create_lead_endpoint(
    request: LeadCreate,
    api_key: APIKeyData = Depends(get_api_key)
):
    """Manually create a lead."""
    try:
        lead = create_lead(request.model_dump())
    except LeadInsertError as e:
        return api_error(f"Could not create lead: {e}", status_code=422)

    if not lead:
        return api_error(
            "A lead with this business name and address already exists",
            status_code=409
        )
    return api_success("Lead created", lead, status_code=201)


@router.post(
    "/leads/bulk-delete",
    summary="Delete multiple leads",
    description="Permanently delete multiple leads at once by ID.",
    response_description="The number of leads deleted",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def bulk_delete_leads_endpoint(
    request: LeadBulkDeleteRequest,
    api_key: APIKeyData = Depends(get_api_key)
):
    """Delete multiple leads by ID."""
    deleted = bulk_delete_leads(request.ids)
    return api_success(f"{deleted} lead(s) deleted", {"deleted": deleted})


@router.patch(
    "/leads/{lead_id}",
    summary="Update a lead",
    description="Update a lead's fields. Only the fields you send are changed.",
    response_description="The updated lead",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def update_lead_endpoint(
    request: LeadUpdate,
    lead_id: int = Path(..., description="The unique ID of the lead to update"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """Update a lead."""
    if not get_lead(lead_id):
        return api_error("Lead not found", status_code=404)

    updated = update_lead(lead_id, request.model_dump(exclude_unset=True))
    if not updated:
        return api_error("Lead not found", status_code=404)
    return api_success("Lead updated", updated)


@router.delete(
    "/leads/{lead_id}",
    summary="Delete a lead",
    description="Permanently delete a single lead.",
    response_description="Confirmation of deletion",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def delete_lead_endpoint(
    lead_id: int = Path(..., description="The unique ID of the lead to delete"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """Delete a lead."""
    if not delete_lead(lead_id):
        return api_error("Lead not found", status_code=404)
    return api_success(f"Lead {lead_id} deleted")


@router.get(
    "/export",
    summary="Export leads to CSV",
    description="""
Export scraped leads to a downloadable CSV file.

Accepts the same filter params as `GET /automation/leads` — if any are given,
only matching leads are exported; with no filters, every lead is exported.

The CSV includes all lead data: business name, address, phone, website, email, etc.
    """,
    response_description="A CSV file download containing the matching leads",
    response_class=FileResponse,
)
def export_leads(
    industry: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    has_website: Optional[bool] = Query(None),
    has_email: Optional[bool] = Query(None),
    is_claimed: Optional[bool] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="Filter to leads at a specific outreach status (new/contacted/replied/interested/won/lost)"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum opportunity score (inclusive)"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """Export leads matching the given filters (or all leads) to a CSV file."""
    if api_key.id is not None:
        log_usage(api_key.id, "/automation/export", 0)

    filters = _lead_filters_from_query(industry, location, category, has_website, has_email, is_claimed, min_rating, search, status, min_score)
    leads = get_all_leads(filters=filters)
    if not leads:
        return api_success("No data found", {"count": 0})
    
    os.makedirs("data", exist_ok=True)
    filename = "data/all_leads_export.csv"
    
    keys = leads[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(leads)
        
    return FileResponse(filename, filename="leads_export.csv", media_type="text/csv")