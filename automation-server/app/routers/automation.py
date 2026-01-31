"""
Automation API routes for lead scraping tasks.

This module provides endpoints to start, stop, and monitor
lead scraping automation tasks.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Path
from fastapi.responses import FileResponse
from app.models.automation import (
    ScrapeRequest,
    TaskResponse,
    TaskStartResponse,
    TaskStopResponse,
    TaskStatus,
)
from app.models.api_key import APIKeyData
from app.services.scraper import scrape_google_maps
from app.db import get_all_leads, log_usage
from app.middleware.auth import get_api_key
from app.helpers import api_success, api_error
from app.helpers.response import APIResponse, STANDARD_RESPONSES
import csv
import os
import uuid

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
    log_usage(api_key.id, "/automation/start", 0)
    
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "id": task_id,
        "config": request.model_dump(),
        "running": True,
        "stop": False,
        "status": TaskStatus.IDLE,
        "error": None
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
    summary="List all tasks",
    description="""
Retrieve a list of all automation tasks (running and completed).

This returns the full task history for the current session.
Note: Tasks are stored in memory and will be cleared on server restart.
    """,
    response_description="Dictionary of all tasks keyed by task ID",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def get_all_tasks(api_key: APIKeyData = Depends(get_api_key)):
    """List all automation tasks."""
    return api_success("All tasks retrieved", {"tasks": TASKS, "count": len(TASKS)})


@router.get(
    "/export",
    summary="Export leads to CSV",
    description="""
Export all scraped leads from the database to a downloadable CSV file.

The CSV includes all lead data: business name, address, phone, website, etc.
    """,
    response_description="A CSV file download containing all leads",
    response_class=FileResponse,
)
def export_leads(api_key: APIKeyData = Depends(get_api_key)):
    """Export all leads from the database to a CSV file."""
    log_usage(api_key.id, "/automation/export", 0)
    
    leads = get_all_leads()
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