"""
API Key and Usage Log database operations.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from app.db.database import get_connection
from config import settings, get_tier_limit


def create_tables():
    """Create api_keys and usage_logs tables if they don't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # API Keys table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    key_hash VARCHAR(64) NOT NULL UNIQUE,
                    key_prefix VARCHAR(12) NOT NULL,
                    tier VARCHAR(50) DEFAULT 'free',
                    monthly_limit INT DEFAULT 100,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')
            
            # Usage logs table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id SERIAL PRIMARY KEY,
                    api_key_id INT REFERENCES api_keys(id) ON DELETE CASCADE,
                    endpoint VARCHAR(255),
                    leads_scraped INT DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    print("✅ API Keys and Usage Logs tables initialized.")


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.
    Returns: (full_key, key_hash, key_prefix)
    """
    # Generate 32 random bytes -> 64 hex characters
    random_part = secrets.token_hex(32)
    full_key = f"{settings.api_key_prefix}{random_part}"
    
    # Hash for storage (never store the actual key)
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    
    # Prefix for display (first 12 chars including anv_)
    key_prefix = full_key[:12]
    
    return full_key, key_hash, key_prefix


def create_api_key(
    name: str,
    tier: str = "free",
    expires_in_days: Optional[int] = None
) -> Dict:
    """
    Create a new API key and store it in the database.
    Returns the key info including the UNHASHED key (only shown once).
    """
    full_key, key_hash, key_prefix = generate_api_key()
    monthly_limit = get_tier_limit(tier)
    
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now() + timedelta(days=expires_in_days)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO api_keys (name, key_hash, key_prefix, tier, monthly_limit, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            ''', (name, key_hash, key_prefix, tier, monthly_limit, expires_at))
            
            result = cur.fetchone()
            conn.commit()
            
            return {
                "id": result["id"],
                "name": name,
                "key": full_key,  # Only returned once!
                "key_prefix": key_prefix,
                "tier": tier,
                "monthly_limit": monthly_limit,
                "created_at": result["created_at"],
                "expires_at": expires_at
            }


def validate_api_key(api_key: str) -> Optional[Dict]:
    """
    Validate an API key and return its info if valid.
    Returns None if invalid, expired, or inactive.
    """
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, name, key_prefix, tier, monthly_limit, is_active, expires_at
                FROM api_keys
                WHERE key_hash = %s
            ''', (key_hash,))
            
            result = cur.fetchone()
            
            if not result:
                return None
            
            # Check if active
            if not result["is_active"]:
                return None
            
            # Check if expired
            if result["expires_at"] and result["expires_at"] < datetime.now():
                return None
            
            return dict(result)


def get_api_key_by_id(key_id: int) -> Optional[Dict]:
    """Get API key info by ID (for admin operations)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, name, key_prefix, tier, monthly_limit, is_active, created_at, expires_at
                FROM api_keys
                WHERE id = %s
            ''', (key_id,))
            result = cur.fetchone()
            return dict(result) if result else None


def list_api_keys(limit: int = 20, offset: int = 0) -> List[Dict]:
    """List a page of API keys (masked) for admin, most recently created first."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT id, name, key_prefix, tier, monthly_limit, is_active, created_at, expires_at
                FROM api_keys
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            ''', (limit, offset))
            return [dict(row) for row in cur.fetchall()]


def count_api_keys() -> int:
    """Count the total number of API keys."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) AS count FROM api_keys')
            result = cur.fetchone()
            return result["count"] if result else 0


def update_api_key(
    key_id: int,
    name: Optional[str] = None,
    tier: Optional[str] = None,
    expires_in_days: Optional[int] = None,
    clear_expiry: bool = False,
) -> Optional[Dict]:
    """
    Update an API key's name/tier/expiry. Only fields explicitly passed are changed.
    Setting `tier` also recomputes `monthly_limit` from the new tier.
    Returns the updated key info, or None if the key doesn't exist.
    """
    fields = []
    values = []

    if name is not None:
        fields.append("name = %s")
        values.append(name)

    if tier is not None:
        fields.append("tier = %s")
        values.append(tier)
        fields.append("monthly_limit = %s")
        values.append(get_tier_limit(tier))

    if clear_expiry:
        fields.append("expires_at = NULL")
    elif expires_in_days is not None:
        fields.append("expires_at = %s")
        values.append(datetime.now() + timedelta(days=expires_in_days))

    if not fields:
        return get_api_key_by_id(key_id)

    values.append(key_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f'''
                UPDATE api_keys SET {", ".join(fields)}
                WHERE id = %s
                RETURNING id
            ''', values)
            result = cur.fetchone()
            conn.commit()

            if not result:
                return None

    return get_api_key_by_id(key_id)


def revoke_api_key(key_id: int) -> bool:
    """Revoke (deactivate) an API key."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                UPDATE api_keys SET is_active = FALSE WHERE id = %s RETURNING id
            ''', (key_id,))
            result = cur.fetchone()
            conn.commit()
            return result is not None


def delete_api_key(key_id: int) -> bool:
    """Permanently delete an API key."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM api_keys WHERE id = %s RETURNING id', (key_id,))
            result = cur.fetchone()
            conn.commit()
            return result is not None


# ============== Usage Logging ==============

def log_usage(api_key_id: int, endpoint: str, leads_scraped: int = 0):
    """Log an API usage event."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO usage_logs (api_key_id, endpoint, leads_scraped)
                VALUES (%s, %s, %s)
            ''', (api_key_id, endpoint, leads_scraped))
            conn.commit()


def get_usage_stats(api_key_id: int) -> Dict:
    """Get usage statistics for an API key."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Total usage
            cur.execute('''
                SELECT 
                    COUNT(*) as total_requests,
                    COALESCE(SUM(leads_scraped), 0) as total_leads
                FROM usage_logs
                WHERE api_key_id = %s
            ''', (api_key_id,))
            totals = cur.fetchone()
            
            # This month's usage
            cur.execute('''
                SELECT COALESCE(SUM(leads_scraped), 0) as monthly_leads
                FROM usage_logs
                WHERE api_key_id = %s
                AND timestamp >= date_trunc('month', CURRENT_TIMESTAMP)
            ''', (api_key_id,))
            monthly = cur.fetchone()
            
            # Get the key's limit
            cur.execute('SELECT monthly_limit FROM api_keys WHERE id = %s', (api_key_id,))
            key_info = cur.fetchone()
            monthly_limit = key_info["monthly_limit"] if key_info else 100
            
            monthly_leads = monthly["monthly_leads"] if monthly else 0
            remaining = monthly_limit - monthly_leads if monthly_limit > 0 else -1  # -1 = unlimited
            
            return {
                "api_key_id": api_key_id,
                "total_requests": totals["total_requests"],
                "total_leads": totals["total_leads"],
                "monthly_leads": monthly_leads,
                "monthly_limit": monthly_limit,
                "remaining_quota": remaining if remaining >= 0 else "unlimited"
            }


def check_quota(api_key_id: int, monthly_limit: int) -> bool:
    """
    Check if the API key has remaining quota.
    Returns True if quota is available, False if exceeded.
    monthly_limit of -1 means unlimited.
    """
    if monthly_limit == -1:
        return True  # Unlimited
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT COALESCE(SUM(leads_scraped), 0) as monthly_leads
                FROM usage_logs
                WHERE api_key_id = %s
                AND timestamp >= date_trunc('month', CURRENT_TIMESTAMP)
            ''', (api_key_id,))
            result = cur.fetchone()
            monthly_leads = result["monthly_leads"] if result else 0
            
            return monthly_leads < monthly_limit
