"""
Edge-case unit tests for reply detection: extract_plain_body corner cases,
decode_header_value corner cases, get_lead_by_email case/whitespace/NULL
sensitivity, and repeated calls to check_for_replies when unconfigured.
"""
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.services.replies import decode_header_value, extract_plain_body, check_for_replies
from app.db import create_lead, delete_lead, get_lead_by_email


class TestExtractPlainBodyEdgeCases:
    """Tests for extract_plain_body's real behavior on non-simple message shapes."""

    def test_html_only_multipart_returns_empty_string(self):
        """A multipart message with only an HTML part (no text/plain alternative) returns '' — the function only ever walks for text/plain."""
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText("<p>HTML only, no plain part</p>", "html"))

        assert extract_plain_body(msg) == ""

    def test_empty_multipart_message_returns_empty_string(self):
        """A multipart container with zero sub-parts attached should return '' rather than erroring."""
        msg = MIMEMultipart()

        assert msg.is_multipart() is True
        assert extract_plain_body(msg) == ""

    def test_plain_part_with_no_charset_falls_back_to_default(self):
        """A non-multipart text/plain message with no charset parameter should decode using the utf-8 fallback, not crash."""
        msg = Message()
        msg.set_type("text/plain")
        msg.set_payload("Hello without an explicit charset")

        assert msg.get_content_charset() is None
        assert extract_plain_body(msg) == "Hello without an explicit charset"

    def test_non_multipart_with_no_payload_returns_empty_string(self):
        """A non-multipart message with no payload at all should return '' rather than raising."""
        msg = Message()
        msg.set_type("text/plain")

        assert extract_plain_body(msg) == ""


class TestDecodeHeaderValueEdgeCases:
    """Tests for decode_header_value's real behavior on mixed, plain, and malformed headers."""

    def test_mixed_encoded_word_and_plain_text(self):
        """An encoded-word segment followed by plain text should decode and concatenate correctly."""
        # "=?utf-8?b?SGVsbG8=?=" decodes to "Hello", followed by literal " World".
        header = "=?utf-8?b?SGVsbG8=?= World"

        assert decode_header_value(header) == "Hello World"

    def test_plain_utf8_header_without_rfc2047_passes_through(self):
        """A header that's already plain UTF-8 (no RFC 2047 encoded-word syntax) should pass through unchanged."""
        header = "Café standalone reply"

        assert decode_header_value(header) == "Café standalone reply"

    def test_malformed_encoding_tag_degrades_to_raw_string(self):
        """An encoded-word with an invalid charset/encoding tag (not B or Q) is not recognized as an encoded word at all, so it comes back as the original raw string rather than raising."""
        header = "=?utf-8?X?broken?="

        result = decode_header_value(header)

        assert result == header

    def test_malformed_base64_payload_does_not_raise(self):
        """An encoded-word with a corrupt base64 payload should degrade gracefully (no exception), even if the output is not meaningful text."""
        header = "=?utf-8?b?not-valid-base64??="

        result = decode_header_value(header)

        assert isinstance(result, str)


class TestGetLeadByEmailSensitivity:
    """Tests for get_lead_by_email's case-insensitivity and NULL-safety."""

    def test_matches_regardless_of_stored_case(self):
        """A lead stored with mixed-case email should be found when searching with a different case entirely."""
        lead = create_lead({
            "business_name": "Case Sensitivity Business",
            "industry": "testing",
            "location": "Caseville",
            "address": "1 Case Way",
            "email": "MixedCase@Example.COM",
        })

        found_lower = get_lead_by_email("mixedcase@example.com")
        found_upper = get_lead_by_email("MIXEDCASE@EXAMPLE.COM")

        assert found_lower is not None
        assert found_lower["id"] == lead["id"]
        assert found_upper is not None
        assert found_upper["id"] == lead["id"]

        delete_lead(lead["id"])

    def test_null_email_lead_never_matched_by_empty_string_search(self):
        """A lead with no email on file (NULL) should never match an empty-string search, since NULL comparisons never equal ''."""
        lead = create_lead({
            "business_name": "No Email Sensitivity Business",
            "industry": "testing",
            "location": "Nullville",
            "address": "1 Null Way",
        })
        assert lead.get("email") is None

        found = get_lead_by_email("")

        assert found is None or found["id"] != lead["id"]

        delete_lead(lead["id"])


class TestCheckForRepliesRepeatedCalls:
    """Tests that check_for_replies is safe to call repeatedly when IMAP is unconfigured."""

    def test_repeated_calls_are_idempotent_and_do_not_raise(self):
        """Calling check_for_replies() several times in a row should consistently return 0 with no leaked state or errors."""
        results = [check_for_replies() for _ in range(3)]

        assert results == [0, 0, 0]
