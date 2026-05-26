# =============================================================================
# app/models/guestbook_message.py — Guestbook Message Model
# =============================================================================
"""SQLAlchemy model for guestbook messages left by wedding guests."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class GuestbookMessage(db.Model):
    """
    Stores a message left by a guest in the wedding guestbook.

    Guests can optionally use the AI message enhancer to rewrite their
    message in a more poetic tone.  The ``ai_enhanced`` flag indicates
    whether the stored message is the AI-rewritten version.
    """

    __tablename__ = "guestbook_messages"

    # UUID primary key
    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key",
    )

    # Email of the authenticated guest who posted the message
    guest_email = db.Column(
        db.String(255),
        nullable=False,
        comment="Email of the guest who wrote this message",
    )

    # Display name shown next to the message in the guestbook
    guest_name = db.Column(
        db.String(255),
        nullable=False,
        comment="Display name for this guestbook entry",
    )

    # The message text (original or AI-enhanced)
    message = db.Column(
        db.Text,
        nullable=False,
        comment="Guestbook message content",
    )

    # True when the guest accepted the AI-enhanced version
    ai_enhanced = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="True if guest accepted the AI-enhanced version of their message",
    )

    # Creation timestamp
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp when this message was posted",
    )

    def __repr__(self) -> str:
        return f"<GuestbookMessage {self.guest_email!r} | ai={self.ai_enhanced}>"
