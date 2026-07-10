"""
Runtime-configurable settings, stored as key-value pairs in Postgres.

These override the env-var defaults in `config/settings.py` at read time
(see `get_effective_email_settings()`) — letting an operator configure SMTP/IMAP
credentials from the web portal instead of editing `.env.local` and restarting
the server. Env vars remain the fallback when a key has no DB override, so
existing Docker/`.env.local` setups keep working unchanged.
"""
from typing import Dict, Optional
from app.db.database import get_connection

# The only keys this table is currently used for. Kept as an allowlist so
# arbitrary keys can't be written through the API by mistake.
EMAIL_SETTING_KEYS = (
    "smtp_host", "smtp_port", "smtp_user", "smtp_app_password", "smtp_from_name",
    "imap_host", "imap_port",
)


def create_tables():
    """Create the app_settings table if it doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS app_settings (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    print("✅ PostgreSQL Table 'app_settings' initialized.")


def get_setting(key: str) -> Optional[str]:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM app_settings WHERE key = %s", (key,))
                result = cur.fetchone()
                return result["value"] if result else None
    except Exception as e:
        print(f"❌ Setting Fetch Error: {e}")
        return None


def get_settings(keys) -> Dict[str, Optional[str]]:
    """Fetch multiple keys at once. Missing keys are simply absent from the DB (not an error)."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT key, value FROM app_settings WHERE key = ANY(%s)", (list(keys),))
                return {row["key"]: row["value"] for row in cur.fetchall()}
    except Exception as e:
        print(f"❌ Settings Fetch Error: {e}")
        return {}


def set_setting(key: str, value: Optional[str]) -> bool:
    """Upsert a setting. Passing value=None clears it (falls back to the env var default)."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if value is None:
                    cur.execute("DELETE FROM app_settings WHERE key = %s", (key,))
                else:
                    cur.execute('''
                        INSERT INTO app_settings (key, value, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                    ''', (key, value))
                conn.commit()
                return True
    except Exception as e:
        print(f"❌ Setting Update Error: {e}")
        return False


def get_effective_email_settings() -> Dict:
    """
    SMTP/IMAP config actually in effect right now: DB overrides (set via the
    portal's Settings page) take priority, falling back to the env-var defaults
    in `config.settings` for anything never overridden. `mailer.py`/`replies.py`
    call this instead of reading `config.settings` directly, so a credential
    change in the portal takes effect immediately, no restart needed.
    """
    from config import settings as env_settings

    db_values = get_settings(EMAIL_SETTING_KEYS)

    def pick(key: str, env_value):
        value = db_values.get(key)
        return value if value not in (None, "") else env_value

    return {
        "smtp_host": pick("smtp_host", env_settings.smtp_host),
        "smtp_port": int(pick("smtp_port", env_settings.smtp_port)),
        "smtp_user": pick("smtp_user", env_settings.smtp_user),
        "smtp_app_password": pick("smtp_app_password", env_settings.smtp_app_password),
        "smtp_from_name": pick("smtp_from_name", env_settings.smtp_from_name),
        "imap_host": pick("imap_host", env_settings.imap_host),
        "imap_port": int(pick("imap_port", env_settings.imap_port)),
    }
