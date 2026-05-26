# =============================================================================
# app/models/guest.py — Guest & RSVP Model
# =============================================================================
"""SQLAlchemy model representing an invited wedding guest."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class Guest(db.Model):
    """
    Represents an invited guest who may RSVP via the website.

    The ``email`` field is the primary identifier — it must match the
    email the guest uses to log in via OTP.  Admin can pre-populate
    this table with expected guests; if a guest logs in with an email
    not in this table, a new row is created automatically.
    """

    __tablename__ = "guests"

    # UUID primary key — avoids sequential ID enumeration
    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key",
    )

    # Guest's full name (provided at login or RSVP)
    name = db.Column(
        db.String(255),
        nullable=True,
        comment="Guest's full name",
    )

    # Email address — unique, used as login identifier
    email = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Guest email — unique login identifier",
    )

    # RSVP status — default pending until they respond
    rsvp_status = db.Column(
        db.Enum("pending", "attending", "not_attending", name="rsvp_status_enum"),
        nullable=False,
        default="pending",
        comment="RSVP status: pending | attending | not_attending",
    )

    # Meal preference — only relevant if attending
    meal_preference = db.Column(
        db.Enum("chicken", "fish", "vegetarian", "vegan", name="meal_pref_enum"),
        nullable=True,
        comment="Meal preference: chicken | fish | vegetarian | vegan",
    )

    # Whether the guest is bringing a +1
    plus_one = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="True if guest is bringing a plus-one",
    )

    # Name of the +1 (optional)
    plus_one_name = db.Column(
        db.String(255),
        nullable=True,
        comment="Full name of the plus-one guest",
    )

    # Table assignment — set by admin after RSVP closes
    table_number = db.Column(
        db.Integer,
        nullable=True,
        comment="Seating table number assigned by admin",
    )

    # Free-text dietary or accessibility notes
    special_requests = db.Column(
        db.Text,
        nullable=True,
        comment="Dietary restrictions, accessibility needs, etc.",
    )

    # Timestamp when the guest submitted their RSVP
    rsvp_submitted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp of RSVP submission",
    )

    # Auto-managed timestamps
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Record creation timestamp (UTC)",
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Record last-updated timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return f"<Guest {self.email} | {self.rsvp_status}>"

    def to_dict(self) -> dict:
        """
        Serialize the guest record to a plain dict for CSV export or
        JSON API responses.

        Returns:
            Dict with all guest fields as JSON-serialisable values.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "rsvp_status": self.rsvp_status,
            "meal_preference": self.meal_preference,
            "plus_one": self.plus_one,
            "plus_one_name": self.plus_one_name,
            "table_number": self.table_number,
            "special_requests": self.special_requests,
            "rsvp_submitted_at": (
                self.rsvp_submitted_at.isoformat() if self.rsvp_submitted_at else None
            ),
            "created_at": self.created_at.isoformat(),
        }
