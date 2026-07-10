"""
Email sending for outreach — plain SMTP (e.g. Gmail with an app password),
no external email service dependency.
"""
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, Tuple

PLACEHOLDER_PATTERN = re.compile(r'\{\{(\w+)\}\}')


def render_template(text: str, lead: Dict) -> str:
    """Replace {{field}} placeholders (e.g. {{business_name}}) with values from a lead dict."""
    return PLACEHOLDER_PATTERN.sub(lambda m: str(lead.get(m.group(1)) or ''), text)


def send_email(to: str, subject: str, body: str) -> Tuple[bool, Optional[str]]:
    """Send a plain-text email via SMTP. Returns (success, error_message)."""
    from app.db import get_effective_email_settings  # local import: avoids a circular import at module load
    cfg = get_effective_email_settings()

    if not cfg["smtp_user"] or not cfg["smtp_app_password"]:
        return False, "SMTP is not configured (set it on the Settings page, or SMTP_USER/SMTP_APP_PASSWORD env vars)"

    try:
        msg = MIMEMultipart()
        from_header = f"{cfg['smtp_from_name']} <{cfg['smtp_user']}>" if cfg["smtp_from_name"] else cfg["smtp_user"]
        msg["From"] = from_header
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=15) as server:
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_app_password"])
            server.sendmail(cfg["smtp_user"], [to], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)
