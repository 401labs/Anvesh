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
)
from app.middleware.auth import get_api_key
from app.helpers import api_success, api_error
from app.helpers.response import APIResponse, STANDARD_RESPONSES
from typing import Optional
import csv
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/automation", tags=["Automation"])

# In-Memory Storage for Tasks
TASKS = {}


def background_task_scraper(task_id: str, request: ScrapeRequest):
    """
    Runs the scraper in the background for a specific task ID.
    """
    print(f"▶️ Automation Started: {request.industry} (ID: {task_id})")
    TASKS[task_id]["status"] = TaskStatus.RUNNING
    
    try:
        total_locations = len(request.locations)
        for i, loc in enumerate(request.locations):
            if TASKS[task_id]["stop"]:
                TASKS[task_id]["status"] = TaskStatus.STOPPED
                print(f"🛑 Automation {task_id} stopped by user.")
                break
                
            print(f"📍 [{i+1}/{total_locations}] Processing location: {loc} (ID: {task_id})")
            
            should_stop = lambda: TASKS[task_id]["stop"]
            
            scrape_google_maps(
                industry=request.industry, 
                location=loc, 
                total=request.limit_per_location,
                stop_signal=should_stop
            )
            
            if not TASKS[task_id]["stop"]:
                print(f"✅ Finished location: {loc}. Checking next...")
        
        # If we finished the loop and weren't stopped
        if not TASKS[task_id]["stop"]:
             TASKS[task_id]["status"] = TaskStatus.COMPLETED

    except Exception as e:
        TASKS[task_id]["status"] = TaskStatus.ERROR
        TASKS[task_id]["error"] = str(e)
        print(f"❌ Automation {task_id} Error: {e}")
    finally:
        TASKS[task_id]["running"] = False
        print(f"🏁 Automation {task_id} Finished. Status: {TASKS[task_id]['status']}")


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
    TASKS[task_id] = {
        "id": task_id,
        "config": request.model_dump(),
        "running": True,
        "stop": False,
        "status": TaskStatus.IDLE,
        "error": None,
        "created_at": datetime.now().isoformat(),
    }
    
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
    
    count_stopped = 0
    for tid, task in TASKS.items():
        if task["running"]:
            task["stop"] = True
            count_stopped += 1
    
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
    task = TASKS.get(task_id)
    if not task:
        return api_error("Task not found", status_code=404)
    
    if not task["running"]:
        return api_success("Task is not running", {"task_id": task_id, "status": task["status"]})
    
    task["stop"] = True
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
    task = TASKS.get(task_id)
    if not task:
        return api_error("Task not found", status_code=404)
    return api_success("Task status retrieved", task)


@router.get(
    "/tasks",
    summary="List tasks (paginated)",
    description="""
Retrieve a page of automation tasks (running and completed), most recently
started first. Use `limit` and `offset` to paginate.

This returns the task history for the current session.
Note: Tasks are stored in memory and will be cleared on server restart.
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
    all_tasks = sorted(TASKS.values(), key=lambda t: t.get("created_at", ""), reverse=True)
    page = all_tasks[offset:offset + limit]
    return api_success("Tasks retrieved", {"tasks": page, "total": len(all_tasks), "limit": limit, "offset": offset})


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
def delete_task(
    task_id: str = Path(..., description="The unique task ID to delete"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """Delete a finished task."""
    task = TASKS.get(task_id)
    if not task:
        return api_error("Task not found", status_code=404)

    if task["running"]:
        return api_error("Cannot delete a running task — stop it first", status_code=400)

    del TASKS[task_id]
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
    sort_by: str = Query("created_at", pattern="^(created_at|rating|review_count|business_name)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    api_key: APIKeyData = Depends(get_api_key)
):
    """List leads from the database, paginated, filtered, and sorted."""
    filters = _lead_filters_from_query(industry, location, category, has_website, has_email, is_claimed, min_rating, search)
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
    lead = create_lead(request.model_dump())
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
    api_key: APIKeyData = Depends(get_api_key)
):
    """Export leads matching the given filters (or all leads) to a CSV file."""
    if api_key.id is not None:
        log_usage(api_key.id, "/automation/export", 0)

    filters = _lead_filters_from_query(industry, location, category, has_website, has_email, is_claimed, min_rating, search)
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