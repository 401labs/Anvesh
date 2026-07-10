"""
Scheduled (recurring) scrape models.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class ScheduleCreate(BaseModel):
    """Request model for creating a recurring scrape schedule."""

    name: str = Field(..., examples=["Weekly Mumbai restaurants"])
    industry: str = Field(..., examples=["restaurants"])
    locations: List[str] = Field(..., examples=[["Mumbai", "Pune"]])
    limit_per_location: int = Field(default=-1, ge=-1, description="Max leads per location per run. -1 for unlimited.")
    interval_hours: int = Field(..., ge=1, description="How often to re-run, in hours (24 = daily, 168 = weekly).")


class ScheduleUpdate(BaseModel):
    """Request model for updating a schedule. All fields optional; only send what changes."""

    name: Optional[str] = None
    industry: Optional[str] = None
    locations: Optional[List[str]] = None
    limit_per_location: Optional[int] = Field(default=None, ge=-1)
    interval_hours: Optional[int] = Field(default=None, ge=1)
    enabled: Optional[bool] = None
