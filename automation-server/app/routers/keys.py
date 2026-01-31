"""
API Key management routes.

This module provides endpoints for managing API keys:
- Admin endpoints: Create, list, revoke, and delete API keys
- User endpoints: View your own key info and usage statistics
"""
from fastapi import APIRouter, Depends, Path

from app.middleware.auth import get_api_key, require_admin
from app.models.api_key import APIKeyCreate, APIKeyData
from app.db import (
    create_api_key,
    get_api_key_by_id,
    list_api_keys,
    revoke_api_key,
    delete_api_key,
    get_usage_stats
)
from app.helpers import api_success, api_error
from app.helpers.response import APIResponse, STANDARD_RESPONSES

router = APIRouter(tags=["API Keys"])


# ============== Admin Endpoints ==============

@router.post(
    "/admin/keys",
    summary="Create a new API key",
    description="""
Create a new API key for authenticating with the Anvesh API.

**Important:** The full API key is only returned once in this response.
Store it securely - you won't be able to retrieve it again!

**Tiers:**
- `free` - 1,000 leads/month
- `pro` - 10,000 leads/month  
- `enterprise` - Unlimited
    """,
    response_description="The newly created API key (store this securely!)",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
    status_code=201,
)
async def create_key(
    request: APIKeyCreate,
    _: bool = Depends(require_admin)
):
    """Create a new API key. Admin only."""
    result = create_api_key(
        name=request.name,
        tier=request.tier,
        expires_in_days=request.expires_in_days
    )
    return api_success("API key created successfully", result, status_code=201)


@router.get(
    "/admin/keys",
    summary="List all API keys",
    description="""
Retrieve a list of all API keys in the system.

Keys are returned with masked values (showing only the prefix) for security.
    """,
    response_description="List of all API keys with masked values",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def list_keys(_: bool = Depends(require_admin)):
    """List all API keys (masked). Admin only."""
    keys = list_api_keys()
    return api_success("API keys retrieved", keys)


@router.get(
    "/admin/keys/{key_id}",
    summary="Get API key details",
    description="Retrieve the details of a specific API key by its ID.",
    response_description="API key details (value is masked)",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def get_key(
    key_id: int = Path(..., description="The unique ID of the API key"),
    _: bool = Depends(require_admin)
):
    """Get details of a specific API key. Admin only."""
    key = get_api_key_by_id(key_id)
    if not key:
        return api_error("API key not found", status_code=404)
    return api_success("API key retrieved", key)


@router.get(
    "/admin/keys/{key_id}/usage",
    summary="Get API key usage statistics",
    description="""
Retrieve usage statistics for a specific API key.

Returns:
- Total requests made
- Total leads scraped
- Monthly usage vs limit
- Remaining quota
    """,
    response_description="Usage statistics for the API key",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def get_key_usage(
    key_id: int = Path(..., description="The unique ID of the API key"),
    _: bool = Depends(require_admin)
):
    """Get usage statistics for a specific API key. Admin only."""
    key = get_api_key_by_id(key_id)
    if not key:
        return api_error("API key not found", status_code=404)
    
    stats = get_usage_stats(key_id)
    return api_success("Usage stats retrieved", stats)


@router.delete(
    "/admin/keys/{key_id}",
    summary="Delete an API key",
    description="""
Permanently delete an API key from the system.

**⚠️ Warning:** This action cannot be undone!
Any applications using this key will immediately lose access.
    """,
    response_description="Confirmation of deletion",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def delete_key(
    key_id: int = Path(..., description="The unique ID of the API key to delete"),
    _: bool = Depends(require_admin)
):
    """Permanently delete an API key. Admin only."""
    success = delete_api_key(key_id)
    if not success:
        return api_error("API key not found", status_code=404)
    return api_success(f"API key {key_id} deleted")


@router.post(
    "/admin/keys/{key_id}/revoke",
    summary="Revoke an API key",
    description="""
Revoke (deactivate) an API key without deleting it.

The key will remain in the database but will no longer authenticate.
This is useful for temporarily disabling access while preserving history.
    """,
    response_description="Confirmation of revocation",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def revoke_key(
    key_id: int = Path(..., description="The unique ID of the API key to revoke"),
    _: bool = Depends(require_admin)
):
    """Revoke (deactivate) an API key. Admin only."""
    success = revoke_api_key(key_id)
    if not success:
        return api_error("API key not found", status_code=404)
    return api_success(f"API key {key_id} revoked")


# ============== User Self-Service Endpoints ==============

@router.get(
    "/me",
    summary="Get your API key info",
    description="""
Retrieve information about your own API key.

Returns your key's name, tier, limits, and expiration date.
    """,
    response_description="Your API key information",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def get_my_info(api_key: APIKeyData = Depends(get_api_key)):
    """Get your own API key info."""
    key = get_api_key_by_id(api_key.id)
    if not key:
        return api_error("API key not found", status_code=404)
    return api_success("Your API key info", key)


@router.get(
    "/me/usage",
    summary="Get your usage statistics",
    description="""
Retrieve your own API usage statistics.

Returns:
- Total requests made
- Total leads scraped  
- Monthly usage vs your tier's limit
- Remaining quota for the month
    """,
    response_description="Your usage statistics",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
async def get_my_usage(api_key: APIKeyData = Depends(get_api_key)):
    """Get your own usage statistics."""
    stats = get_usage_stats(api_key.id)
    return api_success("Your usage stats", stats)
