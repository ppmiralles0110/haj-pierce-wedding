# =============================================================================
# app/models/photo.py — Photo Gallery Model
# =============================================================================
"""SQLAlchemy model for photos stored in Azure Blob Storage."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class Photo(db.Model):
    """
    Represents a single photo in the wedding gallery.

    The binary image data is stored in Azure Blob Storage; this model
    only tracks the metadata and the URL needed to render the image.
    Admins upload photos via ``/admin/photos``.  Optional AI-generated
    captions are written back to the ``caption`` field.
    """

    __tablename__ = "photos"

    # UUID primary key
    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="UUID primary key",
    )

    # Full public or SAS-token URL of the blob in Azure Blob Storage
    blob_url = db.Column(
        db.String(500),
        nullable=False,
        comment="Full Azure Blob Storage URL for this photo",
    )

    # Optional caption — may be AI-generated or manually entered
    caption = db.Column(
        db.Text,
        nullable=True,
        comment="Photo caption (may be AI-generated)",
    )

    # Email of the person who uploaded this photo
    uploaded_by = db.Column(
        db.String(255),
        nullable=False,
        comment="Email of the admin or guest who uploaded this photo",
    )

    # Controls the order photos appear in the gallery (ascending)
    display_order = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        comment="Display order in gallery (lower = earlier)",
    )

    # Creation timestamp
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp when this photo was uploaded",
    )

    def __repr__(self) -> str:
        return f"<Photo {self.id} | order={self.display_order}>"

    def to_dict(self) -> dict:
        """
        Serialise the photo record to a dict for JSON API responses.

        Returns:
            Dict with all photo fields as JSON-serialisable values.
        """
        return {
            "id": str(self.id),
            "blob_url": self.blob_url,
            "caption": self.caption,
            "uploaded_by": self.uploaded_by,
            "display_order": self.display_order,
            "created_at": self.created_at.isoformat(),
        }
