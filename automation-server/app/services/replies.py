"""
Reply detection for outreach emails — polls the same inbox `mailer.py` sends
from over IMAP (stdlib `imaplib`, no new dependency) and matches replies back
to leads by sender address.

Matching is intentionally simple: an unseen inbound email whose From address
equals a lead's `email` is treated as that lead replying. No Message-ID/
In-Reply-To threading — good enough for a single-operator inbox, and avoids
needing to persist outgoing Message-IDs just to thread against them.

Side effect worth knowing: a matched reply is marked \\Seen via IMAP once
logged, so it isn't reprocessed on the next poll. Unmatched unseen mail is
left untouched (re-scanned harmlessly next time) — only genuine outreach
replies get their read state changed.
"""
import asyncio
import email
import imaplib
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr
from typing import Optional

from app.db import create_log, get_lead_by_email, update_lead, get_effective_email_settings

POLL_INTERVAL_SECONDS = 120


def decode_header_value(value: Optional[str]) -> str:
    """Decode a raw (possibly RFC 2047 encoded-word) email header into plain text."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for text, charset in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(text)
    return "".join(decoded)


def extract_plain_body(msg: Message) -> str:
    """Pull the text/plain part out of a (possibly multipart) email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        return ""

    payload = msg.get_payload(decode=True)
    if not payload:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def check_for_replies() -> int:
    """
    Check the configured inbox for unseen replies from known leads. Returns
    the number matched and logged. Returns 0 (no error) if IMAP isn't
    configured, same graceful-degradation posture as mailer.send_email.
    """
    cfg = get_effective_email_settings()
    if not cfg["smtp_user"] or not cfg["smtp_app_password"]:
        return 0

    matched = 0
    conn = None
    try:
        conn = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"])
        conn.login(cfg["smtp_user"], cfg["smtp_app_password"])
        conn.select("INBOX")

        status, data = conn.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return 0

        for msg_num in data[0].split():
            fetch_status, msg_data = conn.fetch(msg_num, "(RFC822)")
            if fetch_status != "OK" or not msg_data or not msg_data[0]:
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            from_addr = parseaddr(msg.get("From", ""))[1].lower()
            if not from_addr:
                continue

            lead = get_lead_by_email(from_addr)
            if not lead:
                continue

            subject = decode_header_value(msg.get("Subject"))
            body = extract_plain_body(msg)
            create_log(lead_id=lead["id"], channel="email", status="replied", subject=subject, body=body)

            if lead.get("status") in ("new", "contacted"):
                update_lead(lead["id"], {"status": "replied"})

            conn.store(msg_num, "+FLAGS", "\\Seen")
            matched += 1
            print(f"📬 Reply matched: lead {lead['id']} ({from_addr}) — \"{subject}\"")
    except Exception as e:
        print(f"❌ Reply Check Error: {e}")
    finally:
        if conn is not None:
            try:
                conn.logout()
            except Exception:
                pass
    return matched


async def reply_checker_loop():
    """Infinite polling loop — started once at app startup, never awaited on elsewhere."""
    while True:
        try:
            check_for_replies()
        except Exception as e:
            print(f"❌ Reply Checker Loop Error: {e}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
