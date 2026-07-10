"""
Tests for reply detection: header/body parsing helpers and the
graceful-degradation path when IMAP isn't configured.
"""
from email.message import EmailMessage
from app.services.replies import decode_header_value, extract_plain_body, check_for_replies
from app.db import create_lead, delete_lead, get_lead_by_email


class TestDecodeHeaderValue:
    """Tests for decoding raw email headers."""

    def test_plain_ascii_header(self):
        """A plain ASCII header should pass through unchanged."""
        assert decode_header_value("Re: Quick question") == "Re: Quick question"

    def test_empty_header(self):
        """A missing/empty header should decode to an empty string."""
        assert decode_header_value(None) == ""
        assert decode_header_value("") == ""

    def test_encoded_word_header(self):
        """An RFC 2047 encoded-word header should decode to readable text."""
        # "Café" encoded as UTF-8 base64 encoded-word
        encoded = "=?utf-8?b?Q2Fmw6k=?="
        assert decode_header_value(encoded) == "Café"


class TestExtractPlainBody:
    """Tests for pulling the text/plain part out of an email message."""

    def test_simple_plain_text_message(self):
        """A non-multipart plain text message should return its body directly."""
        msg = EmailMessage()
        msg.set_content("Hello, this is a reply.")

        assert extract_plain_body(msg).strip() == "Hello, this is a reply."

    def test_multipart_message_picks_plain_part(self):
        """A multipart alternative message should return the text/plain part, not HTML."""
        msg = EmailMessage()
        msg.set_content("Plain text version")
        msg.add_alternative("<p>HTML version</p>", subtype="html")

        assert "Plain text version" in extract_plain_body(msg)
        assert "HTML version" not in extract_plain_body(msg)


class TestCheckForRepliesUnconfigured:
    """Tests for the graceful-degradation path when IMAP isn't configured."""

    def test_check_for_replies_returns_zero_when_unconfigured(self):
        """With no SMTP_USER/SMTP_APP_PASSWORD set (as in the test env), check_for_replies should return 0, not raise."""
        assert check_for_replies() == 0


class TestGetLeadByEmail:
    """Tests for the lead-by-email lookup used to match replies."""

    def test_get_lead_by_email_finds_match(self):
        """A lead with a matching email should be found, case-insensitively."""
        lead = create_lead({
            "business_name": "Reply Match Business",
            "industry": "testing",
            "location": "Testville",
            "address": "1 Reply Way",
            "email": "ReplyTest@Example.com",
        })

        found = get_lead_by_email("replytest@example.com")

        assert found is not None
        assert found["id"] == lead["id"]

        delete_lead(lead["id"])

    def test_get_lead_by_email_no_match(self):
        """A non-existent email should return None."""
        assert get_lead_by_email("no-such-lead@example.com") is None
