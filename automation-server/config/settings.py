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
    
    @property
    def db_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


# Singleton instance
settings = Settings()
