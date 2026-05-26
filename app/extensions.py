# =============================================================================
# app/extensions.py — Flask Extension Singletons
# Instantiated here (without an app) then wired up in create_app()
# =============================================================================
"""
Shared extension instances.

All extensions are created *without* an app object so they can be
imported anywhere without triggering circular imports.  They are
connected to the actual Flask app inside ``create_app()`` using the
``init_app()`` pattern.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# SQLAlchemy ORM — the single shared db session for the entire app
db = SQLAlchemy()

# Flask-Migrate — Alembic wrapper for schema migrations
migrate = Migrate()

# Flask-Limiter — IP-based rate limiting (storage configured via Config)
limiter = Limiter(
    key_func=get_remote_address,    # Rate-limit by client IP address
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",        # Overridden by RATELIMIT_STORAGE_URI in config
)
