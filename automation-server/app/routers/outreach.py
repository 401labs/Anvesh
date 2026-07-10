"""
Outreach API routes: email templates and sending templated/one-off emails to leads.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query
from app.models.outreach import EmailTemplateCreate, EmailTemplateUpdate, SendEmailRequest
from app.models.api_key import APIKeyData
from app.services.mailer import render_template, send_email
from app.db import (
    create_template,
    get_template,
    list_templates,
    update_template,
    delete_template,
    create_log,
    list_logs,
    count_logs,
    get_lead,
    update_lead,
)
from app.middleware.auth import get_api_key
from app.helpers import api_success, api_error
from app.helpers.response import APIResponse, STANDARD_RESPONSES

router = APIRouter(prefix="/outreach", tags=["Outreach"])


def _advance_status_if_new(lead_id: int):
    lead = get_lead(lead_id)
    if lead and lead.get("status") == "new":
        update_lead(lead_id, {"status": "contacted"})


def _send_to_lead(lead_id: int, subject_template: str, body_template: str) -> dict:
    lead = get_lead(lead_id)
    if not lead:
        return {"lead_id": lead_id, "sent": False, "error": "Lead not found"}
    if not lead.get("email"):
        return {"lead_id": lead_id, "sent": False, "error": "Lead has no email on file"}

    subject = render_template(subject_template, lead)
    body = render_template(body_template, lead)
    success, error = send_email(lead["email"], subject, body)

    create_log(
        lead_id=lead_id,
        channel="email",
        status="sent" if success else "failed",
        subject=subject,
        body=body,
        error=error,
    )
    if success:
        _advance_status_if_new(lead_id)

    return {"lead_id": lead_id, "sent": success, "error": error}


def _bulk_send(lead_ids, subject_template: str, body_template: str):
    for lead_id in lead_ids:
        _send_to_lead(lead_id, subject_template, body_template)


@router.post(
    "/templates",
    summary="Create an email template",
    description="""
Create a reusable email template for outreach. Use placeholders like
`{{business_name}}`, `{{industry}}`, `{{location}}`, `{{address}}`,
`{{category}}` in the subject or body — they're filled in per-lead when you
send.
    """,
    response_description="The created template",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
    status_code=201,
)
def create_template_endpoint(request: EmailTemplateCreate, api_key: APIKeyData = Depends(get_api_key)):
    """Create a reusable email template."""
    template = create_template(request.name, request.subject, request.body)
    if not template:
        return api_error("Failed to create template", status_code=500)
    return api_success("Template created", template, status_code=201)


@router.get(
    "/templates",
    summary="List email templates",
    description="List all saved email templates.",
    response_description="All email templates",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def list_templates_endpoint(api_key: APIKeyData = Depends(get_api_key)):
    """List all saved email templates."""
    return api_success("Templates retrieved", {"templates": list_templates()})


@router.patch(
    "/templates/{template_id}",
    summary="Update an email template",
    description="Update a template's fields. Only the fields you send are changed.",
    response_description="The updated template",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def update_template_endpoint(
    request: EmailTemplateUpdate,
    template_id: int = Path(..., description="The template ID"),
    api_key: APIKeyData = Depends(get_api_key),
):
    """Update an email template."""
    if not get_template(template_id):
        return api_error("Template not found", status_code=404)
    updated = update_template(template_id, request.model_dump(exclude_unset=True))
    if not updated:
        return api_error("Template not found", status_code=404)
    return api_success("Template updated", updated)


@router.delete(
    "/templates/{template_id}",
    summary="Delete an email template",
    description="Permanently delete an email template.",
    response_description="Confirmation of deletion",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def delete_template_endpoint(
    template_id: int = Path(..., description="The template ID"),
    api_key: APIKeyData = Depends(get_api_key),
):
    """Delete an email template."""
    if not delete_template(template_id):
        return api_error("Template not found", status_code=404)
    return api_success(f"Template {template_id} deleted")


@router.post(
    "/email/send",
    summary="Send an outreach email to one or more leads",
    description="""
Send an email to one or more leads, either from a saved template
(`template_id`) or a one-off `subject`/`body` — provide exactly one of the
two, not both.

Placeholders like `{{business_name}}` are filled in per-lead. Leads with no
email on file are skipped and reported back rather than causing an error.

Sending to a single lead happens synchronously and the result is returned
immediately. Sending to more than one lead is queued as a background job —
check `GET /outreach/logs?lead_id=` to see results land as they complete.
    """,
    response_description="Send result (single) or queue confirmation (bulk), plus any skipped leads",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def send_email_endpoint(
    request: SendEmailRequest,
    background_tasks: BackgroundTasks,
    api_key: APIKeyData = Depends(get_api_key),
):
    """Send an outreach email to one or more leads."""
    using_template = request.template_id is not None
    using_raw = request.subject is not None or request.body is not None

    if using_template and using_raw:
        return api_error("Provide either template_id or subject/body, not both", status_code=400)
    if not using_template and not using_raw:
        return api_error("Provide either template_id or subject and body", status_code=400)

    if using_template:
        template = get_template(request.template_id)
        if not template:
            return api_error("Template not found", status_code=404)
        subject_template, body_template = template["subject"], template["body"]
    else:
        if not request.subject or not request.body:
            return api_error("Both subject and body are required when not using a template", status_code=400)
        subject_template, body_template = request.subject, request.body

    valid_ids = []
    skipped_no_lead = []
    skipped_no_email = []
    for lead_id in request.lead_ids:
        lead = get_lead(lead_id)
        if not lead:
            skipped_no_lead.append(lead_id)
        elif not lead.get("email"):
            skipped_no_email.append(lead_id)
        else:
            valid_ids.append(lead_id)

    if len(valid_ids) == 1:
        result = _send_to_lead(valid_ids[0], subject_template, body_template)
        return api_success("Email sent", {
            "result": result,
            "skipped_no_lead": skipped_no_lead,
            "skipped_no_email": skipped_no_email,
        })

    if not valid_ids:
        return api_success("No valid recipients", {
            "queued": 0,
            "skipped_no_lead": skipped_no_lead,
            "skipped_no_email": skipped_no_email,
        })

    background_tasks.add_task(_bulk_send, valid_ids, subject_template, body_template)
    return api_success(f"{len(valid_ids)} email(s) queued", {
        "queued": len(valid_ids),
        "skipped_no_lead": skipped_no_lead,
        "skipped_no_email": skipped_no_email,
    })


@router.get(
    "/logs",
    summary="List outreach logs",
    description="Retrieve outreach history (email sends), optionally filtered to a single lead. Paginated.",
    response_description="A page of outreach logs plus the total matching count",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def list_logs_endpoint(
    lead_id: int = Query(None, description="Filter to a single lead's outreach history"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    api_key: APIKeyData = Depends(get_api_key),
):
    """List outreach logs, optionally filtered to one lead, paginated."""
    logs = list_logs(lead_id=lead_id, limit=limit, offset=offset)
    total = count_logs(lead_id=lead_id)
    return api_success("Logs retrieved", {"logs": logs, "total": total, "limit": limit, "offset": offset})


@router.post(
    "/check-replies",
    summary="Check for reply emails now",
    description="""
Poll the configured inbox (see `SMTP_USER`/`SMTP_APP_PASSWORD` — IMAP reuses
those same credentials) for unseen emails from known lead addresses, right
now instead of waiting for the next background poll (every 2 minutes).

Matched replies get logged (`channel=email`, `status=replied`) and the
lead's status advances to `replied` if it was `new`/`contacted`. Returns 0
with no error if IMAP isn't configured.
    """,
    response_description="Number of replies matched and logged",
    response_model=APIResponse,
    responses=STANDARD_RESPONSES,
)
def check_replies_endpoint(api_key: APIKeyData = Depends(get_api_key)):
    """Check the inbox for replies right now."""
    from app.services.replies import check_for_replies
    matched = check_for_replies()
    return api_success(f"{matched} repl{'y' if matched == 1 else 'ies'} matched", {"matched": matched})
