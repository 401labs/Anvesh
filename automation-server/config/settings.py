"""
Application settings with .env file priority and hardcoded fallbacks.
"""
import os
from dotenv import load_dotenv

# Load .env file if it exists (priority over defaults)
load_dotenv(".env.local")
load_dotenv(".env")


class Settings:
    """
    Centralized configuration for the Anvesh API.
    Loads from environment variables with hardcoded fallbacks.
    """
    
    # Database
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "password")
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: str = os.getenv("DB_PORT", "5432")
    db_name: str = os.getenv("DB_NAME", "lead_scraper")
    
    # Admin Authentication
    admin_secret: str = os.getenv("ADMIN_SECRET", "change-me-in-production")
    
    # API Key Settings
    api_key_prefix: str = os.getenv("API_KEY_PREFIX", "anv_")

    # Outreach: SMTP (e.g. Gmail with an app password — https://myaccount.google.com/apppasswords)
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_app_password: str = os.getenv("SMTP_APP_PASSWORD", "")
    smtp_from_name: str = os.getenv("SMTP_FROM_NAME", "")

    # Outreach: IMAP, for detecting replies. Reuses smtp_user/smtp_app_password
    # (Gmail's app password authenticates both SMTP and IMAP) — only the host/port
    # differ, and only need overriding for a non-Gmail provider.
    imap_host: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    imap_port: int = int(os.getenv("IMAP_PORT", "993"))

    @property
    def db_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


# Singleton instance
settings = Settings()
