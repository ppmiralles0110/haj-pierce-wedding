# =============================================================================
# app/config.py — Application Configuration
# Reads secrets from Azure Key Vault (production) or .env (local dev)
# =============================================================================
"""
Configuration classes for different environments.

All secrets are loaded via environment variables.  In production, the
Azure App Service is configured with Key Vault references so the env
vars are automatically populated from Key Vault secrets — the app code
never calls Key Vault directly at startup.

For local development, copy ``.env.example`` to ``.env`` and fill in
your values.  ``python-dotenv`` will load them automatically.
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv

# Load .env for local development (no-op in production where env vars
# are already set by App Service / Key Vault references)
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """
    Base configuration.  All settings read from environment variables.
    """

    # ------------------------------------------------------------------
    # Flask core
    # ------------------------------------------------------------------
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    TESTING: bool = False

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://wedding_user:wedding_pass@localhost:5432/wedding_db",
    )
    # Disable modification tracking to save memory
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    # Connection pool settings suitable for Basic B2 App Service
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,       # Test connections before use
        "pool_recycle": 300,         # Recycle connections every 5 min
    }

    # ------------------------------------------------------------------
    # Azure OpenAI (via Azure AI Foundry — Sweden Central)
    # ------------------------------------------------------------------
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.environ.get("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY: Optional[str] = os.environ.get("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_DEPLOYMENT: str = os.environ.get(
        "AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"
    )
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"

    # ------------------------------------------------------------------
    # Azure Blob Storage
    # ------------------------------------------------------------------
    BLOB_STORAGE_URL: Optional[str] = os.environ.get("BLOB_STORAGE_URL")
    BLOB_PHOTOS_CONTAINER: str = "photos"

    # ------------------------------------------------------------------
    # Gmail SMTP Email
    # ------------------------------------------------------------------
    GMAIL_USER: str = os.environ.get("GMAIL_USER", "")
    GMAIL_APP_PASSWORD: Optional[str] = os.environ.get("GMAIL_APP_PASSWORD")
    MAIL_FROM_NAME: str = os.environ.get("MAIL_FROM_NAME", "Our Wedding")

    # ------------------------------------------------------------------
    # Azure Application Insights
    # ------------------------------------------------------------------
    APPINSIGHTS_INSTRUMENTATIONKEY: Optional[str] = os.environ.get(
        "APPINSIGHTS_INSTRUMENTATIONKEY"
    )

    # ------------------------------------------------------------------
    # Admin access
    # ADMIN_EMAILS is a comma-separated list of email addresses that
    # have admin privileges (e.g. "alice@example.com,bob@example.com")
    # ------------------------------------------------------------------
    ADMIN_EMAILS: list[str] = [
        e.strip().lower()
        for e in os.environ.get("ADMIN_EMAILS", "").split(",")
        if e.strip()
    ]

    # ------------------------------------------------------------------
    # OTP settings
    # ------------------------------------------------------------------
    OTP_EXPIRY_MINUTES: int = 10    # OTP expires after 10 minutes
    OTP_MAX_ATTEMPTS: int = 5       # Max failed verify attempts

    # ------------------------------------------------------------------
    # Flask-Limiter (rate limiting)
    # ------------------------------------------------------------------
    RATELIMIT_STORAGE_URI: str = os.environ.get(
        "RATELIMIT_STORAGE_URI", "memory://"
    )
    RATELIMIT_DEFAULT: str = "2000 per day;500 per hour"
    RATELIMIT_ENABLED: bool = os.environ.get("RATELIMIT_ENABLED", "true").lower() != "false"


class TestConfig(Config):
    """
    Configuration for pytest test suite.

    Uses an in-memory SQLite database so tests run without a real
    PostgreSQL server.  Disables CSRF-equivalent protections for easier
    form testing.
    """

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # SQLite doesn't support PostgreSQL pool options — clear them for tests
    SQLALCHEMY_ENGINE_OPTIONS: dict = {}
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False         # Disable rate limiting in tests
    GMAIL_APP_PASSWORD = "test-key"   # Prevent real email sends
    AZURE_OPENAI_API_KEY = "test-key"
    ADMIN_EMAILS = ["admin@test.com"]
    SECRET_KEY = "test-secret-key-32-chars-minimum!!"
