"""
Outreach models: email templates and sending.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class EmailTemplateCreate(BaseModel):
    """Request model for creating a reusable email template."""

    name: str = Field(..., examples=["Cold intro"])
    subject: str = Field(..., examples=["Quick question about {{business_name}}'s website"])
    body: str = Field(..., examples=["Hi {{business_name}} team, I noticed you don't have a website yet..."])


class EmailTemplateUpdate(BaseModel):
    """Request model for updating a template. All fields optional; only send what changes."""

    name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class SendEmailRequest(BaseModel):
    """Request model for sending an outreach email to one or more leads."""

    lead_ids: List[int] = Field(..., min_length=1, description="Leads to send to.", examples=[[1, 2, 3]])
    template_id: Optional[int] = Field(
        default=None, description="Use a saved template. Mutually exclusive with subject/body."
    )
    subject: Optional[str] = Field(
        default=None, description="One-off subject (supports {{business_name}} etc placeholders). Mutually exclusive with template_id."
    )
    body: Optional[str] = Field(
        default=None, description="One-off body (supports {{business_name}} etc placeholders). Mutually exclusive with template_id."
    )
