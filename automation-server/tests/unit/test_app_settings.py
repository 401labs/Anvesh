"""
Tests for the runtime app_settings key-value store and the email-settings merge.
"""
from app.db.app_settings import (
    get_setting,
    get_settings,
    set_setting,
    get_effective_email_settings,
)


class TestSettingCRUD:
    """Tests for the basic key-value get/set operations."""

    def test_set_and_get_setting(self):
        """A set value should round-trip through get_setting."""
        set_setting("test_key_basic", "hello")
        assert get_setting("test_key_basic") == "hello"
        set_setting("test_key_basic", None)

    def test_get_missing_setting_returns_none(self):
        """A key that was never set should return None, not raise."""
        assert get_setting("test_key_never_set") is None

    def test_set_none_clears_the_key(self):
        """Setting a key to None should delete it, not store the literal string 'None'."""
        set_setting("test_key_clear", "value")
        assert get_setting("test_key_clear") == "value"

        set_setting("test_key_clear", None)
        assert get_setting("test_key_clear") is None

    def test_set_setting_upserts(self):
        """Setting an existing key again should overwrite, not duplicate/error."""
        set_setting("test_key_upsert", "first")
        set_setting("test_key_upsert", "second")
        assert get_setting("test_key_upsert") == "second"
        set_setting("test_key_upsert", None)

    def test_get_settings_batch(self):
        """get_settings should fetch multiple keys at once, omitting unset ones."""
        set_setting("test_key_batch_a", "a")
        set_setting("test_key_batch_b", "b")

        result = get_settings(["test_key_batch_a", "test_key_batch_b", "test_key_batch_missing"])

        assert result["test_key_batch_a"] == "a"
        assert result["test_key_batch_b"] == "b"
        assert "test_key_batch_missing" not in result

        set_setting("test_key_batch_a", None)
        set_setting("test_key_batch_b", None)


class TestEffectiveEmailSettings:
    """Tests for merging DB overrides with env-var defaults."""

    def test_falls_back_to_env_defaults_when_nothing_overridden(self):
        """With no DB overrides, all fields should come from config.settings."""
        from config import settings as env_settings

        cfg = get_effective_email_settings()

        assert cfg["smtp_host"] == env_settings.smtp_host
        assert cfg["imap_host"] == env_settings.imap_host

    def test_db_override_takes_priority_over_env(self):
        """A DB-set value should win over the env-var default."""
        set_setting("smtp_host", "smtp.override-test.example.com")
        try:
            cfg = get_effective_email_settings()
            assert cfg["smtp_host"] == "smtp.override-test.example.com"
        finally:
            set_setting("smtp_host", None)

    def test_port_fields_are_coerced_to_int(self):
        """smtp_port/imap_port should come back as real ints even though they're stored as TEXT."""
        set_setting("smtp_port", "2525")
        try:
            cfg = get_effective_email_settings()
            assert cfg["smtp_port"] == 2525
            assert isinstance(cfg["smtp_port"], int)
        finally:
            set_setting("smtp_port", None)

    def test_clearing_override_reverts_to_env_default(self):
        """Setting a value then clearing it should return to the original env default."""
        from config import settings as env_settings

        set_setting("smtp_host", "smtp.temp.example.com")
        assert get_effective_email_settings()["smtp_host"] == "smtp.temp.example.com"

        set_setting("smtp_host", None)
        assert get_effective_email_settings()["smtp_host"] == env_settings.smtp_host
