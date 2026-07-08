"""
API Key authentication middleware for FastAPI.
"""
import hmac
from fastapi import Header, HTTPException, Depends
from typing import Optional
from app.db import validate_api_key, check_quota
from config import settings
from app.models.api_key import APIKeyData


async def get_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_admin_secret: Optional[str] = Header(None, alias="X-Admin-Secret"),
) -> APIKeyData:
    """
    FastAPI dependency that validates either an API key (X-API-Key) or the
    admin secret (X-Admin-Secret) — a valid admin secret bypasses per-key
    quota entirely, since it's already full system access via /admin/*.
    Returns APIKeyData if valid, raises HTTPException otherwise.
    """
    if x_admin_secret and hmac.compare_digest(x_admin_secret, settings.admin_secret):
        return APIKeyData(id=None, name="admin", tier="enterprise", monthly_limit=-1)

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header."
        )

    # Validate the key
    key_data = validate_api_key(x_api_key)
    
    if not key_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key."
        )
    
    # Check quota
    if not check_quota(key_data["id"], key_data["monthly_limit"]):
        raise HTTPException(
            status_code=429,
            detail="Monthly quota exceeded. Please upgrade your plan."
        )
    
    return APIKeyData(
        id=key_data["id"],
        name=key_data["name"],
        tier=key_data["tier"],
        monthly_limit=key_data["monthly_limit"]
    )


async def get_optional_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[APIKeyData]:
    """
    Optional API key dependency - returns None if no key provided.
    Useful for endpoints that can work with or without auth.
    """
    if not x_api_key:
        return None
    
    key_data = validate_api_key(x_api_key)
    if not key_data:
        return None
    
    return APIKeyData(
        id=key_data["id"],
        name=key_data["name"],
        tier=key_data["tier"],
        monthly_limit=key_data["monthly_limit"]
    )


async def require_admin(x_admin_secret: str = Header(..., alias="X-Admin-Secret")):
    """
    FastAPI dependency that validates the admin secret.
    Used for admin-only endpoints like key management.
    """
    if not x_admin_secret:
        raise HTTPException(
            status_code=401,
            detail="Missing admin secret. Provide X-Admin-Secret header."
        )

    if not hmac.compare_digest(x_admin_secret, settings.admin_secret):
        raise HTTPException(
            status_code=403,
            detail="Invalid admin secret."
        )

    return True
