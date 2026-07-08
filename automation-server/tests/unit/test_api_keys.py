"""
Tests for API key database operations.
"""
import pytest
from app.db.api_keys import (
    generate_api_key,
    create_api_key,
    validate_api_key,
    get_api_key_by_id,
    list_api_keys,
    count_api_keys,
    update_api_key,
    delete_api_key,
    log_usage,
    get_usage_stats
)
from config import settings


class TestAPIKeyGeneration:
    """Tests for API key generation and hashing."""
    
    def test_generate_api_key_format(self):
        """Generated key should have the correct prefix."""
        full_key, key_hash, key_prefix = generate_api_key()
        
        assert full_key.startswith(settings.api_key_prefix)
        assert len(key_hash) == 64  # SHA256 hex
        assert key_prefix == full_key[:12]
    
    def test_generate_api_key_uniqueness(self):
        """Each generated key should be unique."""
        keys = [generate_api_key()[0] for _ in range(5)]
        assert len(set(keys)) == 5


class TestAPIKeyValidation:
    """Tests for API key validation."""
    
    def test_validate_api_key_success(self):
        """Valid key should return key data."""
        key_data = create_api_key(name="Validation Test", tier="free")
        
        result = validate_api_key(key_data["key"])
        
        assert result is not None
        assert result["id"] == key_data["id"]
        assert result["name"] == "Validation Test"
        assert result["tier"] == "free"
        
        # Cleanup
        delete_api_key(key_data["id"])
    
    def test_validate_api_key_invalid(self):
        """Invalid key should return None."""
        result = validate_api_key("anv_invalid_key_that_does_not_exist")
        assert result is None
    
    def test_validate_api_key_empty(self):
        """Empty key should return None."""
        result = validate_api_key("")
        assert result is None


class TestAPIKeyPaginationAndUpdate:
    """Tests for listing/counting/updating API keys."""

    def test_list_and_count(self):
        """list_api_keys and count_api_keys should agree on presence of a new key."""
        key_data = create_api_key(name="Pagination Test", tier="free")

        before = count_api_keys()
        page = list_api_keys(limit=before + 10, offset=0)

        assert any(k["id"] == key_data["id"] for k in page)

        delete_api_key(key_data["id"])

    def test_update_tier_recomputes_limit(self):
        """Changing tier should recompute monthly_limit."""
        key_data = create_api_key(name="Update Test", tier="free")

        updated = update_api_key(key_data["id"], tier="enterprise")

        assert updated["tier"] == "enterprise"
        assert updated["monthly_limit"] == -1

        delete_api_key(key_data["id"])

    def test_update_nonexistent_key(self):
        """Updating a key that doesn't exist should return None."""
        result = update_api_key(999999999, name="Nope")
        assert result is None

    def test_clear_expiry(self):
        """clear_expiry should remove expires_at."""
        key_data = create_api_key(name="Expiry Test", tier="free", expires_in_days=30)
        assert key_data["expires_at"] is not None

        updated = update_api_key(key_data["id"], clear_expiry=True)
        assert updated["expires_at"] is None

        delete_api_key(key_data["id"])


class TestUsageLogging:
    """Tests for usage logging and statistics."""
    
    def test_log_usage(self):
        """Usage should be logged correctly."""
        key_data = create_api_key(name="Usage Test", tier="free")
        
        log_usage(key_data["id"], "/test-endpoint", 5)
        log_usage(key_data["id"], "/test-endpoint", 3)
        
        stats = get_usage_stats(key_data["id"])
        
        assert stats["total_requests"] >= 2
        assert stats["total_leads"] >= 8
        
        # Cleanup
        delete_api_key(key_data["id"])
    
    def test_get_usage_stats_empty(self):
        """New key should have zero usage."""
        key_data = create_api_key(name="Empty Stats Test", tier="pro")
        
        stats = get_usage_stats(key_data["id"])
        
        assert stats["total_requests"] == 0
        assert stats["total_leads"] == 0
        assert stats["monthly_leads"] == 0
        
        # Cleanup
        delete_api_key(key_data["id"])
