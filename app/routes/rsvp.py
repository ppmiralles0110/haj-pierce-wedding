# =============================================================================
# app/routes/rsvp.py — RSVP Blueprint
# =============================================================================
"""
RSVP routes: display the form and process submissions.
"""

import logging
import re
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
    prefill_name = session.get("user_full_name", "") or (guest.name if guest else "")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", email).strip().lower()
        rsvp_status = request.form.get("rsvp_status", "").strip()
        phone_number = request.form.get("phone_number", "").strip() or None
        parking_required = request.form.get("parking_required") == "yes"

        # Basic validation
        if not name:
            flash("Please enter your full name.", "error")
            return render_template("rsvp.html", guest=guest, prefill_name=prefill_name)

        if not email or "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address.", "error")
            return render_template("rsvp.html", guest=guest, prefill_name=prefill_name)

        if phone_number and not re.match(r'^(09|\+639)[0-9]{9}$', phone_number):
            flash("Please enter a valid Philippine mobile number (09XXXXXXXXX or +639XXXXXXXXX).", "error")
            return render_template("rsvp.html", guest=guest, prefill_name=prefill_name)

        if rsvp_status not in ("attending", "not_attending"):
            flash("Please select whether you will attend.", "error")
            return render_template("rsvp.html", guest=guest, prefill_name=prefill_name)

        # Upsert the guest record
        if not guest:
            guest = Guest(email=email)
            db.session.add(guest)

        guest.name = name
        guest.rsvp_status = rsvp_status
        guest.phone_number = phone_number
        guest.parking_required = parking_required if rsvp_status == "attending" else False
        guest.rsvp_submitted_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info(
            "RSVP submitted: %s — status=%s parking=%s",
            email,
            rsvp_status,
            parking_required,
        )

        # Generate a personalised AI confirmation message
        ai_message = None
        try:
            from app.services.ai_service import generate_rsvp_confirmation
            config_rows = WeddingConfig.query.all()
            wedding_config_data = {row.key: row.value for row in config_rows}
            ai_message = generate_rsvp_confirmation(
                guest_name=name,
                attending=(rsvp_status == "attending"),
                wedding_config=wedding_config_data,
            )
        except Exception as exc:
            logger.warning("Could not generate AI RSVP message: %s", exc)

        return render_template(
            "rsvp_success.html",
            guest=guest,
            ai_message=ai_message,
        )

    return render_template("rsvp.html", guest=guest, prefill_name=prefill_name)
