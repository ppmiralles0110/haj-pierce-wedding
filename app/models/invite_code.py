# =============================================================================
# app/models/invite_code.py — Guest Invite Code
# =============================================================================
import secrets
from datetime import datetime, timezone

from app.extensions import db


def generate_invite_code() -> str:
    """
    Generate a random 8-character uppercase alphanumeric code.
    Excludes visually ambiguous characters: 0, O, I, 1.
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


class InviteCode(db.Model):
    """
    A single-use or reusable invite code issued by the admin to a named guest.
    Guests present this code at login instead of an OTP.
    """

    __tablename__ = "invite_codes"

    id         = db.Column(db.Integer, primary_key=True)
    code       = db.Column(db.String(8), unique=True, nullable=False, index=True)
    label      = db.Column(db.String(200), nullable=False)   # admin-given name/label
    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    use_count  = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<InviteCode {self.code!r} label={self.label!r} active={self.is_active}>"
