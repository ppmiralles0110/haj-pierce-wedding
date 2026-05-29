# =============================================================================
# app/routes/auth.py — Authentication Blueprint (Invite Code)
# =============================================================================
"""
Authentication routes: login with email + first/last name + 8-character invite code.

Security measures:
- Rate limited to 50 requests per 10 minutes per IP on /login
- Invite codes validated against the invite_codes table (must be active)
- Session regenerated on successful login to prevent session fixation
- Admin flag set in session based on ADMIN_EMAILS config
"""

import logging
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
from app.models.invite_code import InviteCode

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Decorators for protecting routes
# ---------------------------------------------------------------------------

def login_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            flash("Please log in to access this page.", "info")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f: Callable) -> Callable:
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
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("50 per 10 minutes")
def login():
    if session.get("authenticated"):
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email      = request.form.get("email", "").strip().lower()
        first_name = request.form.get("first_name", "").strip()
        last_name  = request.form.get("last_name", "").strip()
        code       = request.form.get("invite_code", "").strip().upper()

        # --- Input validation ---
        if not email or "@" not in email:
            flash("Please enter a valid email address.", "error")
            return render_template("auth/login.html")

        if not first_name:
            flash("Please enter your first name.", "error")
            return render_template("auth/login.html")

        if not last_name:
            flash("Please enter your last name.", "error")
            return render_template("auth/login.html")

        if not code or len(code) != 8:
            flash("Please enter the 8-character invite code from your invitation.", "error")
            return render_template("auth/login.html")

        # --- Validate invite code ---
        invite = InviteCode.query.filter_by(code=code, is_active=True).first()
        if not invite:
            flash(
                "Invalid or inactive invite code. "
                "Please double-check the code provided in your invitation.",
                "error",
            )
            return render_template("auth/login.html")

        # --- Upsert guest record ---
        full_name = f"{first_name} {last_name}"
        guest = Guest.query.filter_by(email=email).first()
        if not guest:
            guest = Guest(email=email, name=full_name)
            db.session.add(guest)
        elif not guest.name:
            guest.name = full_name

        # Track usage
        invite.use_count += 1
        db.session.commit()

        # --- Build session (clear first to prevent fixation) ---
        session.clear()
        admin_emails = [e.lower() for e in current_app.config.get("ADMIN_EMAILS", [])]
        session["authenticated"]    = True
        session["user_email"]       = email
        session["user_first_name"]  = first_name
        session["user_last_name"]   = last_name
        session["user_full_name"]   = full_name
        session["is_admin"]         = email.lower() in admin_emails
        session.permanent = True

        # --- Log the login ---
        try:
            from app.models.login_log import LoginLog
            log = LoginLog(
                email=email,
                guest_name=full_name,
                invite_code=code,
                invite_label=invite.label,
                ip_address=request.remote_addr,
            )
            db.session.add(log)
            db.session.commit()
        except Exception as exc:
            logger.warning("Could not save login log: %s", exc)

        logger.info(
            "Successful login for %s (admin=%s) from %s using code %s",
            email,
            session["is_admin"],
            request.remote_addr,
            code,
        )

        flash(f"Welcome, {first_name}! You're now logged in.", "success")
        return redirect(url_for("main.home"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    email = session.get("user_email", "unknown")
    session.clear()
    logger.info("User logged out: %s", email)
    flash("You've been logged out.", "info")
    return redirect(url_for("auth.login"))
