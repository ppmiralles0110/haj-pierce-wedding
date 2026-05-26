# =============================================================================
# app/models/ai_chat_log.py — AI Chatbot Conversation Log
# =============================================================================
"""SQLAlchemy model for logging AI concierge chatbot interactions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class AiChatLog(db.Model):
    """
    Stores every interaction a guest has with the AI wedding concierge.

    Used for monitoring conversation quality, detecting misuse, and
    providing conversation history context to the AI model.  Logs are
    visible to admins via the dashboard.
    """

    __tablename__ = "ai_chat_logs"

    # UUID primary key
    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key",
    )

    # Email of the authenticated guest who sent the message
    guest_email = db.Column(
        db.String(255),
        nullable=False,
        comment="Email of the authenticated guest",
    )

    # The verbatim message sent by the guest
    user_message = db.Column(
        db.Text,
        nullable=False,
        comment="Verbatim message from the guest",
    )

    # The full response returned by the AI model
    ai_response = db.Column(
        db.Text,
        nullable=False,
        comment="Full response returned by gpt-4o-mini",
    )

    # When this exchange was logged
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp of this chat interaction",
    )

    def __repr__(self) -> str:
        return f"<AiChatLog {self.guest_email!r} @ {self.created_at}>"
