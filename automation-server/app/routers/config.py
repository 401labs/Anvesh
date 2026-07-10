"""
Runtime configuration API routes — lets an operator set SMTP/IMAP credentials
from the web portal instead of editing .env.local and restarting the server.
Admin-only: these are account credentials for the whole instance, not
per-API-key scoped data.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.db import get_effective_email_settings, set_setting
from app.middleware.auth import require_admin
from app.helpers import api_success
from app.helpers.response import APIResponse, STANDARD_RESPONSES

router = APIRouter(prefix="/config", tags=["Config"])


class EmailConfigUpdate(BaseModel):
    """
    Request model for updating SMTP/IMAP settings. All fields optional; only
    send what changes. Send an empty string for a field to clear its override
    and revert to the env-var default.
    """
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = Field(default=None, ge=1, le=65535)
    smtp_user: Optional[str] = None
    smtp_app_password: Optional[str] = None
    smtp_from_name: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = Field(default=None, ge=1, le=65535)


@router.get(
    "/email",
    summary="Get the current SMTP/IMAP configuration",
    description="""
Returns the SMTP/IMAP settings actually in effect right now — a DB override
(set via `PUT /config/email`) if one exists, otherwise the server's env-var
default. The app password itself is never returned, only whether one is set.
    """,
    response_description="Effective email configuration",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def get_email_config(_: bool = Depends(require_admin)):
    """Get the current effective SMTP/IMAP configuration (admin only)."""
    cfg = get_effective_email_settings()
    return api_success("Email configuration retrieved", {
        "smtp_host": cfg["smtp_host"],
        "smtp_port": cfg["smtp_port"],
        "smtp_user": cfg["smtp_user"],
        "smtp_from_name": cfg["smtp_from_name"],
        "imap_host": cfg["imap_host"],
        "imap_port": cfg["imap_port"],
        "smtp_app_password_set": bool(cfg["smtp_app_password"]),
    })


@router.put(
    "/email",
    summary="Update SMTP/IMAP configuration",
    description="""
Update SMTP/IMAP settings — takes effect on the very next email send or
reply check, no restart needed. Only the fields you send are changed; send
an empty string for a field to clear its override and fall back to the
server's env-var default.
    """,
    response_description="The updated (effective) email configuration",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def update_email_config(request: EmailConfigUpdate, _: bool = Depends(require_admin)):
    """Update SMTP/IMAP configuration (admin only)."""
    fields = request.model_dump(exclude_unset=True)
    for key, value in fields.items():
        set_setting(key, str(value) if value not in (None, "") else None)

    cfg = get_effective_email_settings()
    return api_success("Email configuration updated", {
        "smtp_host": cfg["smtp_host"],
        "smtp_port": cfg["smtp_port"],
        "smtp_user": cfg["smtp_user"],
        "smtp_from_name": cfg["smtp_from_name"],
        "imap_host": cfg["imap_host"],
        "imap_port": cfg["imap_port"],
        "smtp_app_password_set": bool(cfg["smtp_app_password"]),
    })
