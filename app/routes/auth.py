# =============================================================================
# app/routes/auth.py — Authentication Blueprint (Email OTP)
# =============================================================================
"""
Authentication routes: login (request OTP) and verify (submit OTP).

Security measures:
- Rate limited to 5 requests per 10 minutes per IP on /login
- OTP is hashed before storage (SHA-256)
- Previous unused OTPs are invalidated when a new one is requested
- Session is regenerated on successful login to prevent fixation
- Admin flag set in session based on ADMIN_EMAILS config
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Callable

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.extensions import db, limiter
from app.models.guest import Guest
from app.models.otp_token import OtpToken

logger = logging.getLogger(__name__)

# Blueprint registration
auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Decorators for protecting routes
# ---------------------------------------------------------------------------

def login_required(f: Callable) -> Callable:
    """
    Decorator: redirect unauthenticated users to /login.

    Args:
        f: The view function to protect.

    Returns:
        Wrapped function that checks session authentication.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            flash("Please log in to access this page.", "info")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f: Callable) -> Callable:
    """
    Decorator: restrict access to admin users only.

    Admin status is determined by ADMIN_EMAILS in config, set during login.

    Args:
        f: The view function to protect.

    Returns:
        Wrapped function that checks admin flag in session.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            flash("Please log in to access this page.", "info")
            return redirect(url_for("auth.login"))
        if not session.get("is_admin"):
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for("main.home"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _hash_otp(otp: str) -> str:
    """
    Hash a plaintext OTP using SHA-256.

    Args:
        otp: The 6-digit plaintext OTP string.

    Returns:
        Hex-encoded SHA-256 digest of the OTP.
    """
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _invalidate_previous_otps(email: str) -> None:
    """
    Mark all unused OTPs for this email as used.

    Called before issuing a new OTP to prevent replay attacks.

    Args:
        email: The guest's email address.
    """
    OtpToken.query.filter_by(email=email, used=False).update({"used": True})
    db.session.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per 10 minutes")
def login():
    """
    Step 1 of OTP login: collect email address and send OTP.

    GET:  Render the login form.
    POST: Validate email, generate OTP, send via SendGrid, redirect to /verify.
    """
    if session.get("authenticated"):
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email or "@" not in email:
            flash("Please enter a valid email address.", "error")
            return render_template("auth/login.html")

        # Invalidate any previous unused OTPs for this email
        _invalidate_previous_otps(email)

        # Generate a cryptographically secure 6-digit OTP
        otp_code = str(secrets.randbelow(900000) + 100000)  # 100000–999999

        # Hash and store the OTP (never log or store plaintext)
        expiry = datetime.now(timezone.utc) + timedelta(
            minutes=current_app.config.get("OTP_EXPIRY_MINUTES", 10)
        )
        token = OtpToken(
            email=email,
            otp_hash=_hash_otp(otp_code),
            expires_at=expiry,
        )
        db.session.add(token)
        db.session.commit()

        # Ensure the guest exists in the guests table
        guest = Guest.query.filter_by(email=email).first()
        if not guest:
            guest = Guest(email=email)
            db.session.add(guest)
            db.session.commit()

        # Store email in session for the verify step (not the OTP)
        session["pending_email"] = email

        # Dev mode: no SendGrid key — show OTP directly on the verify page
        if not current_app.config.get("SENDGRID_API_KEY"):
            session["dev_otp"] = otp_code  # cleared after display
            flash(
                "DEV MODE: Email sending is disabled. "
                "Your one-time code is shown below.",
                "warning",
            )
            return redirect(url_for("auth.verify"))

        # Send OTP via SendGrid
        try:
            from app.services.email_service import send_otp_email
            from app.models.wedding_config import WeddingConfig
            couple1 = WeddingConfig.get("couple_name_1", "Pierce")
            couple2 = WeddingConfig.get("couple_name_2", "")
            couple_names = f"{couple1} & {couple2}".strip(" &")
            send_otp_email(
                to_email=email,
                otp_code=otp_code,  # Plaintext to email; NEVER log
                couple_names=couple_names,
            )
            flash(
                "We've sent a 6-digit code to your email. "
                "Check your inbox (and spam folder).",
                "success",
            )
            return redirect(url_for("auth.verify"))

        except Exception as exc:
            logger.error("Failed to send OTP to %s: %s", email, exc)
            flash(
                "We couldn't send the login email. Please try again shortly.",
                "error",
            )
            # Clean up the token we just created
            db.session.delete(token)
            db.session.commit()
            session.pop("pending_email", None)
            return render_template("auth/login.html")

    return render_template("auth/login.html")


@auth_bp.route("/verify", methods=["GET", "POST"])
@limiter.limit("10 per 10 minutes")
def verify():
    """
    Step 2 of OTP login: validate the submitted code.

    GET:  Render the verification form.
    POST: Check OTP hash, mark used, create session, redirect to home.
    """
    pending_email = session.get("pending_email")
    if not pending_email:
        flash("Please enter your email address first.", "info")
        return redirect(url_for("auth.login"))

    # Dev mode: pop the OTP from session so it can be shown once
    dev_otp = session.pop("dev_otp", None)

    if request.method == "POST":
        submitted_code = request.form.get("otp", "").strip()

        if not submitted_code or len(submitted_code) != 6 or not submitted_code.isdigit():
            flash("Please enter the 6-digit code from your email.", "error")
            return render_template("auth/verify.html", email=pending_email)

        # Look up the most recent valid OTP for this email
        token = (
            OtpToken.query
            .filter_by(email=pending_email, used=False)
            .order_by(OtpToken.created_at.desc())
            .first()
        )

        if not token or not token.is_valid:
            flash(
                "This code has expired or already been used. "
                "Please request a new code.",
                "error",
            )
            session.pop("pending_email", None)
            return redirect(url_for("auth.login"))

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(token.otp_hash, _hash_otp(submitted_code)):
            flash("Invalid code. Please check your email and try again.", "error")
            return render_template("auth/verify.html", email=pending_email)

        # Mark token as used
        token.used = True
        db.session.commit()

        # Establish authenticated session
        session.clear()  # Regenerate to prevent session fixation
        admin_emails = [
            e.lower() for e in current_app.config.get("ADMIN_EMAILS", [])
        ]
        session["authenticated"] = True
        session["user_email"] = pending_email
        session["is_admin"] = pending_email.lower() in admin_emails
        session.permanent = True

        logger.info(
            "Successful login for %s (admin=%s)",
            pending_email,
            session["is_admin"],
        )

        flash("Welcome! You're now logged in.", "success")
        return redirect(url_for("main.home"))

    return render_template("auth/verify.html", email=pending_email, dev_otp=dev_otp)


@auth_bp.route("/logout")
def logout():
    """
    Clear the user's session and redirect to /login.
    """
    email = session.get("user_email", "unknown")
    session.clear()
    logger.info("User logged out: %s", email)
    flash("You've been logged out.", "info")
    return redirect(url_for("auth.login"))
