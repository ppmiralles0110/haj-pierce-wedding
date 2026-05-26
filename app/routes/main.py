# =============================================================================
# app/routes/main.py — Main / Public Pages Blueprint
# =============================================================================
"""
Main public-facing routes: home, details, gallery, guestbook, health check.
All routes except /health require authentication via @login_required.
"""

import logging

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from app.routes.auth import login_required
from app.models.photo import Photo
from app.models.guestbook_message import GuestbookMessage
from app.extensions import db

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


@main_bp.route("/health")
def health():
    """
    Health check endpoint for Azure Front Door probe.

    Returns a 200 OK so Front Door knows the origin is healthy.
    No authentication required — probes don't have sessions.
    """
    return {"status": "ok"}, 200


@main_bp.route("/")
@login_required
def home():
    """
    Homepage — hero, countdown, feature strip, gallery preview, CTA section.
    """
    # Fetch a limited set of photos for the homepage preview (4 max)
    preview_photos = (
        Photo.query
        .order_by(Photo.display_order.asc(), Photo.created_at.desc())
        .limit(4)
        .all()
    )
    return render_template("home.html", preview_photos=preview_photos)


@main_bp.route("/details")
@login_required
def details():
    """
    Wedding details page — venue, date, time, dress code, program.
    All content is driven by the wedding_config table.
    """
    return render_template("details.html")


@main_bp.route("/gallery")
@login_required
def gallery():
    """
    Full photo gallery — loads all photos from Azure Blob Storage metadata.
    """
    photos = (
        Photo.query
        .order_by(Photo.display_order.asc(), Photo.created_at.desc())
        .all()
    )
    return render_template("gallery.html", photos=photos)


@main_bp.route("/guestbook", methods=["GET", "POST"])
@login_required
def guestbook():
    """
    Guestbook — view messages and submit a new one.

    GET:  List all approved messages.
    POST: Save a new message (original or AI-enhanced).
    """
    if request.method == "POST":
        message_text = request.form.get("message", "").strip()
        guest_name = request.form.get("name", "").strip()
        ai_enhanced_flag = request.form.get("ai_enhanced", "false") == "true"

        if not message_text or not guest_name:
            flash("Please fill in your name and message.", "error")
        else:
            msg = GuestbookMessage(
                guest_email=session["user_email"],
                guest_name=guest_name,
                message=message_text,
                ai_enhanced=ai_enhanced_flag,
            )
            db.session.add(msg)
            db.session.commit()
            flash("Your message has been added to the guestbook!", "success")
            return redirect(url_for("main.guestbook"))

    messages = (
        GuestbookMessage.query
        .order_by(GuestbookMessage.created_at.desc())
        .all()
    )
    return render_template("guestbook.html", messages=messages)


@main_bp.route("/chat")
@login_required
def chat():
    """
    AI Wedding Concierge chatbot page.
    The actual streaming API is at /api/chat.
    """
    return render_template("chat.html")
