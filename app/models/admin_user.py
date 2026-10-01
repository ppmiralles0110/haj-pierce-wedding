# =============================================================================
# app/models/admin_user.py — Admin Access Grants
# =============================================================================
"""
Database-backed admin access list.

Admin privileges come from two sources:

* ``ADMIN_EMAILS`` — the environment/Key Vault list. These are *owner*
  accounts: they are always admins and cannot be revoked from the UI.
* ``admin_users`` — grants created from the admin portal. These can be
  added and revoked at any time by any existing admin.
"""

from datetime import datetime, timezone

from app.extensions import db


class AdminUser(db.Model):
    """An email address granted admin access from the admin portal."""

    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Email address granted admin access (lowercase)",
    )

    granted_by = db.Column(
        db.String(255),
        nullable=True,
        comment="Email of the admin who granted this access",
    )

    note = db.Column(
        db.String(255),
        nullable=True,
        comment="Optional label, e.g. the person's name or role",
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp the grant was created",
    )

    def __repr__(self) -> str:
        return f"<AdminUser {self.email!r}>"
