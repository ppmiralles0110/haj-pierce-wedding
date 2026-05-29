# =============================================================================
# app/models/otp_token.py — One-Time Password Token Model
# =============================================================================
"""SQLAlchemy model for storing hashed OTP tokens used in authentication."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class OtpToken(db.Model):
    """
    Stores a single-use, time-limited OTP for email-based authentication.

    Security design:
    - Only the SHA-256 hash of the OTP is persisted — never the plaintext.
    - Tokens expire after OTP_EXPIRY_MINUTES (default 10 minutes).
    - When a new OTP is requested for an email, all previous unused tokens
      for that email are invalidated (``used = True``) to prevent replay.
    - The ``used`` flag is set to True immediately after successful
      verification.
    """

    __tablename__ = "otp_tokens"

    # UUID primary key
    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key",
    )

    # Guest email address that requested the OTP
    email = db.Column(
        db.String(255),
        nullable=False,
        index=True,
        comment="Email address that requested the OTP",
    )

    # SHA-256 hash of the 6-digit OTP — never store plaintext
    otp_hash = db.Column(
        db.String(255),
        nullable=False,
        comment="SHA-256 hex digest of the plaintext OTP",
    )

    # Expiry timestamp — set to now + OTP_EXPIRY_MINUTES at creation
    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        comment="UTC timestamp when this OTP becomes invalid",
    )

    # Single-use flag — True once verified or explicitly invalidated
    used = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="True if this OTP has already been used or invalidated",
    )

    # Creation timestamp for audit trail
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp when this OTP was created",
    )

    # -----------------------------------------------------------------------
    # Helper properties
    # -----------------------------------------------------------------------

    @property
    def is_expired(self) -> bool:
        """
        Check whether this token has passed its expiry time.

        Returns:
            True if the current UTC time is past ``expires_at``.
        """
        expires = self.expires_at
        # SQLite (used in tests) returns naive datetimes — treat as UTC
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires

    @property
    def is_valid(self) -> bool:
        """
        Check whether this token can still be used for authentication.

        Returns:
            True if the token has not been used and has not expired.
        """
        return not self.used and not self.is_expired

    def __repr__(self) -> str:
        return f"<OtpToken email={self.email} valid={self.is_valid}>"
