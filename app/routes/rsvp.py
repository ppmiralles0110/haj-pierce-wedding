# =============================================================================
# app/routes/rsvp.py — RSVP Blueprint
# =============================================================================
"""
RSVP routes: display the form and process submissions.
"""

import logging
from datetime import datetime, timezone

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.extensions import db
from app.models.guest import Guest
from app.models.wedding_config import WeddingConfig
from app.routes.auth import login_required

logger = logging.getLogger(__name__)

rsvp_bp = Blueprint("rsvp", __name__)


@rsvp_bp.route("/rsvp", methods=["GET", "POST"])
@login_required
def rsvp():
    """
    RSVP form — collect attendance, meal preference, and +1 details.

    GET:  Render the form, pre-populated if the guest has RSVPed before.
    POST: Validate and save the RSVP, then redirect to success page.
    """
    # Check if RSVP window is open
    rsvp_open = WeddingConfig.get("rsvp_open", "true").lower() == "true"
    if not rsvp_open:
        return render_template("rsvp_closed.html")

    email = session["user_email"]
    guest = Guest.query.filter_by(email=email).first()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        rsvp_status = request.form.get("rsvp_status", "").strip()
        meal_preference = request.form.get("meal_preference", "").strip() or None
        plus_one = request.form.get("plus_one") == "yes"
        plus_one_name = request.form.get("plus_one_name", "").strip() or None
        special_requests = request.form.get("special_requests", "").strip() or None

        # Basic validation
        if not name:
            flash("Please enter your full name.", "error")
            return render_template("rsvp.html", guest=guest)

        if rsvp_status not in ("attending", "not_attending"):
            flash("Please select whether you will attend.", "error")
            return render_template("rsvp.html", guest=guest)

        if rsvp_status == "attending" and not meal_preference:
            flash("Please select your meal preference.", "error")
            return render_template("rsvp.html", guest=guest)

        # Upsert the guest record
        if not guest:
            guest = Guest(email=email)
            db.session.add(guest)

        guest.name = name
        guest.rsvp_status = rsvp_status
        guest.meal_preference = meal_preference if rsvp_status == "attending" else None
        guest.plus_one = plus_one and rsvp_status == "attending"
        guest.plus_one_name = plus_one_name if guest.plus_one else None
        guest.special_requests = special_requests
        guest.rsvp_submitted_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(
            "RSVP submitted: %s — status=%s meal=%s +1=%s",
            email,
            rsvp_status,
            meal_preference,
            plus_one,
        )

        # Generate a personalised AI confirmation message
        ai_message = None
        try:
            from app.services.ai_service import generate_rsvp_confirmation
            from app.models.wedding_config import WeddingConfig
            config_rows = WeddingConfig.query.all()
            wedding_config = {row.key: row.value for row in config_rows}
            ai_message = generate_rsvp_confirmation(
                guest_name=name,
                attending=(rsvp_status == "attending"),
                wedding_config=wedding_config,
            )
        except Exception as exc:
            logger.warning("Could not generate AI RSVP message: %s", exc)

        return render_template(
            "rsvp_success.html",
            guest=guest,
            ai_message=ai_message,
        )

    return render_template("rsvp.html", guest=guest)
