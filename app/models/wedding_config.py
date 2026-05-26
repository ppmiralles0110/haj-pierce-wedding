# =============================================================================
# app/models/wedding_config.py — Key-Value Wedding Configuration Store
# =============================================================================
"""SQLAlchemy model for storing all wedding-specific configuration."""

from datetime import datetime, timezone

from app.extensions import db


class WeddingConfig(db.Model):
    """
    Key-value store for all wedding-specific content and theme settings.

    This powers the admin panel's config editor so the couple can update
    venue details, dates, colours, and copy without touching code.

    Keys follow a snake_case convention (e.g. ``couple_name_1``,
    ``wedding_date``, ``color_primary``).  The seed script
    ``scripts/seed_db.py`` pre-populates this table with defaults.
    """

    __tablename__ = "wedding_config"

    # Integer primary key — small table, sequential IDs are fine
    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        comment="Auto-incrementing integer primary key",
    )

    # Unique configuration key (e.g. "venue_name")
    key = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        comment="Unique configuration key in snake_case",
    )

    # Value for this configuration key
    value = db.Column(
        db.Text,
        nullable=False,
        default="",
        comment="String value for this configuration entry",
    )

    # Auto-updated whenever the row changes
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp of the last update",
    )

    def __repr__(self) -> str:
        return f"<WeddingConfig {self.key}={self.value!r}>"

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """
        Retrieve a config value by key.

        Args:
            key: The configuration key to look up.
            default: Value returned if the key doesn't exist.

        Returns:
            The string value, or ``default`` if not found.
        """
        row = cls.query.filter_by(key=key).first()
        return row.value if row else default

    @classmethod
    def set(cls, key: str, value: str) -> None:
        """
        Upsert a configuration value.

        Args:
            key: The configuration key.
            value: The new string value to store.
        """
        from app.extensions import db as _db
        row = cls.query.filter_by(key=key).first()
        if row:
            row.value = value
            row.updated_at = datetime.now(timezone.utc)
        else:
            row = cls(key=key, value=value)
            _db.session.add(row)
        _db.session.commit()
