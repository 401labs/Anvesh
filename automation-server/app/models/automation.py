"""
Automation models for lead scraping tasks.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class TaskStatus(str, Enum):
    """Possible states of an automation task."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ERROR = "error"


class LeadStatus(str, Enum):
    """Pipeline stage for a lead's outreach status."""
    NEW = "new"
    CONTACTED = "contacted"
    REPLIED = "replied"
    INTERESTED = "interested"
    WON = "won"
    LOST = "lost"


class ScrapeRequest(BaseModel):
    """Configuration for starting a lead scraping automation task."""
    
    industry: str = Field(
        ...,
        description="The industry or business type to search for",
        examples=["restaurants", "gyms", "salons", "plumbers"]
    )
    locations: List[str] = Field(
        ...,
        description="List of locations/cities to scrape leads from",
        examples=[["Mumbai", "Delhi", "Bangalore"]]
    )
    limit_per_location: int = Field(
        default=-1,
        description="Maximum number of leads to scrape per location. Use -1 for unlimited.",
        ge=-1,
        examples=[50, 100, -1]
    )
    headless: bool = Field(
        default=True,
        description="Run the browser headless. Set false to watch the scrape live in a visible browser window — only visible on the machine actually running automation-server (not in Docker).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "industry": "restaurants",
                    "locations": ["Mumbai", "Delhi"],
                    "limit_per_location": 50
                }
            ]
        }
    }


class TaskResponse(BaseModel):
    """Response model for a single automation task."""
    
    id: str = Field(description="Unique task identifier (UUID)")
    status: TaskStatus = Field(description="Current status of the task")
    config: dict = Field(description="The scraping configuration for this task")
    running: bool = Field(description="Whether the task is currently running")
    error: Optional[str] = Field(default=None, description="Error message if task failed")


class TaskStartResponse(BaseModel):
    """Response when a new automation task is started."""
    
    task_id: str = Field(description="The unique ID of the newly created task")


class TaskStopResponse(BaseModel):
    """Response when stopping automation tasks."""
    
    tasks_stopped: int = Field(description="Number of tasks that received the stop signal")


class AllTasksResponse(BaseModel):
    """Response containing all automation tasks."""

    tasks: dict = Field(description="Dictionary of all tasks keyed by task ID")


class LeadCreate(BaseModel):
    """Request model for manually creating a lead."""

    business_name: str = Field(..., examples=["Joe's Coffee"])
    industry: str = Field(..., examples=["coffee shop"])
    location: str = Field(..., examples=["Seattle"])
    address: str = Field(..., examples=["123 Main St, Seattle, WA"])
    category: Optional[str] = Field(default=None, examples=["Cafe"])
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    review_count: Optional[int] = Field(default=None, ge=0)
    is_claimed: Optional[bool] = None
    has_website: bool = False
    website_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = Field(default=None, examples=["hello@joescoffee.com"])
    status: Optional[str] = Field(default="new", examples=["new", "contacted"])
    maps_url: Optional[str] = Field(default=None, examples=["https://www.google.com/maps/place/..."])


class LeadUpdate(BaseModel):
    """Request model for updating a lead. All fields optional; only send what changes."""

    business_name: Optional[str] = None
    industry: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    review_count: Optional[int] = Field(default=None, ge=0)
    is_claimed: Optional[bool] = None
    has_website: Optional[bool] = None
    website_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    maps_url: Optional[str] = None


class LeadBulkDeleteRequest(BaseModel):
    """Request model for deleting multiple leads at once."""

    ids: List[int] = Field(..., min_length=1, description="Lead IDs to delete", examples=[[1, 2, 3]])
