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
