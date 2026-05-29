# =============================================================================
# app/routes/main.py — Main / Public Pages Blueprint
# =============================================================================
"""
Main public-facing routes: home, details, gallery, guestbook, health check.
All routes except /health require authentication via @login_required.
"""

import logging
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response

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


@main_bp.route("/details/calendar.ics")
@login_required
def download_ics():
    """Generate and serve an .ics calendar file for the wedding event."""
    from app.models.wedding_config import WeddingConfig
    c1      = WeddingConfig.get("couple_name_1", "Pierce")
    c2      = WeddingConfig.get("couple_name_2", "Haj")
    w_date  = WeddingConfig.get("wedding_date", "")
    w_time  = WeddingConfig.get("wedding_time", "15:00")
    v_name  = WeddingConfig.get("venue_name", "")
    v_addr  = WeddingConfig.get("venue_address", "")

    # Build datetime strings (YYYYMMDDTHHMMSS)
    try:
        dt_start = datetime.strptime(f"{w_date} {w_time}", "%Y-%m-%d %H:%M")
        dt_end   = dt_start.replace(hour=(dt_start.hour + 5) % 24)
        dtstart  = dt_start.strftime("%Y%m%dT%H%M%S")
        dtend    = dt_end.strftime("%Y%m%dT%H%M%S")
    except (ValueError, AttributeError):
        dtstart  = dtend = "20261218T150000"

    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    location  = f"{v_name}, {v_addr}".strip(", ")
    title     = f"{c1} & {c2} Wedding"

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Pierce & Haj Wedding//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"DTSTART:{dtstart}\r\n"
        f"DTEND:{dtend}\r\n"
        f"DTSTAMP:{now_stamp}\r\n"
        f"SUMMARY:{title}\r\n"
        f"LOCATION:{location}\r\n"
        "DESCRIPTION:Join us for our wedding celebration!\r\n"
        "STATUS:CONFIRMED\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    return Response(
        ics,
        mimetype="text/calendar",
        headers={"Content-Disposition": "attachment; filename=pierce-haj-wedding.ics"},
    )


@main_bp.route("/photo/<uuid:photo_id>")
@login_required
def serve_photo(photo_id):
    """Stream a private blob photo via managed identity — requires login."""
    import re
    from flask import abort
    photo = Photo.query.get(str(photo_id))
    if not photo:
        abort(404)
    try:
        from azure.storage.blob import BlobServiceClient
        from azure.identity import DefaultAzureCredential
        match = re.match(
            r'https://([^.]+)\.blob\.core\.windows\.net/([^/]+)/(.+)',
            photo.blob_url
        )
        if not match:
            abort(404)
        account_name, container_name, blob_name = match.groups()
        client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )
        blob = client.get_blob_client(container=container_name, blob=blob_name)
        stream = blob.download_blob()
        content_type = stream.properties.get("content_settings", {}).get("content_type") or "image/jpeg"
        return Response(stream.readall(), content_type=content_type)
    except Exception:
        abort(404)


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
