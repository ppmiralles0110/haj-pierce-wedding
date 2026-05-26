# =============================================================================
# app/models/login_log.py — Login Location Log
# =============================================================================
from datetime import datetime, timezone
from app.extensions import db


class LoginLog(db.Model):
    """Records each successful login with IP address and optional geolocation."""

    __tablename__ = "login_logs"

    id           = db.Column(db.Integer, primary_key=True)
    email        = db.Column(db.String(255), nullable=False, index=True)
    ip_address   = db.Column(db.String(45))          # IPv4 or IPv6
    location_name = db.Column(db.String(500))        # Human-readable (reverse geocode)
    latitude     = db.Column(db.Float)
    longitude    = db.Column(db.Float)
    logged_at    = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
