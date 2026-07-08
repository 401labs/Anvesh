"""
API Key authentication models.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class APIKeyCreate(BaseModel):
    """Request model for creating a new API key."""
    name: str = Field(
        ...,
        description="A descriptive name for this API key",
        examples=["Production Key", "Development Key", "Client XYZ"]
    )
    tier: str = Field(
        default="free",
        description="Pricing tier for rate limiting. Options: free, pro, enterprise",
        examples=["free", "pro", "enterprise"]
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        description="Number of days until the key expires. Leave empty for no expiration.",
        ge=1,
        examples=[30, 90, 365]
    )



class APIKeyUpdate(BaseModel):
    """Request model for updating an existing API key. All fields optional; only send what changes."""
    name: Optional[str] = Field(
        default=None,
        description="New name for this API key",
        examples=["Renamed Key"]
    )
    tier: Optional[str] = Field(
        default=None,
        description="New pricing tier. Recomputes monthly_limit. Options: free, pro, enterprise",
        examples=["pro"]
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        description="Set expiry to N days from now.",
        ge=1,
        examples=[30]
    )
    clear_expiry: bool = Field(
        default=False,
        description="If true, removes any expiration date (takes precedence over expires_in_days)."
    )


class APIKeyResponse(BaseModel):
    """Response model for API key creation (includes the actual key - shown once)."""
    id: int
    name: str
    key: str  # Only shown once on creation!
    key_prefix: str
    tier: str
    monthly_limit: int
    created_at: datetime
    expires_at: Optional[datetime] = None


class APIKeyInfo(BaseModel):
    """Response model for API key info (without the actual key)."""
    id: int
    name: str
    key_prefix: str
    tier: str
    monthly_limit: int
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None


class APIKeyData(BaseModel):
    """Data passed to route handlers after auth validation."""
    id: Optional[int] = None
    name: str
    tier: str
    monthly_limit: int


class UsageStats(BaseModel):
    """Response model for usage statistics."""
    api_key_id: int
    total_requests: int
    total_leads: int
    monthly_leads: int
    monthly_limit: int
    remaining_quota: str | int  # "unlimited" or number
