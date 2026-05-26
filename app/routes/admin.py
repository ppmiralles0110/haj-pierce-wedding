# =============================================================================
# app/routes/admin.py — Admin Blueprint
# =============================================================================
"""
Admin-only routes for managing guests, content, photos, and config.
All routes protected by @admin_required decorator.
"""

import csv
import io
import logging

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    Response,
    session,
    url_for,
)

from app.extensions import db
from app.models.ai_chat_log import AiChatLog
from app.models.guest import Guest
from app.models.guestbook_message import GuestbookMessage
from app.models.photo import Photo
from app.models.wedding_config import WeddingConfig
from app.routes.auth import admin_required

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@admin_required
def dashboard():
    """
    Admin dashboard — overview statistics.
    """
    stats = {
        "total_guests": Guest.query.count(),
        "attending": Guest.query.filter_by(rsvp_status="attending").count(),
        "not_attending": Guest.query.filter_by(rsvp_status="not_attending").count(),
        "pending": Guest.query.filter_by(rsvp_status="pending").count(),
        "plus_ones": Guest.query.filter_by(plus_one=True).count(),
        "total_photos": Photo.query.count(),
        "guestbook_count": GuestbookMessage.query.count(),
        "chat_logs": AiChatLog.query.count(),
    }
    # Meal breakdown
    for meal in ("chicken", "fish", "vegetarian", "vegan"):
        stats[f"meal_{meal}"] = Guest.query.filter_by(
            rsvp_status="attending", meal_preference=meal
        ).count()

    return render_template("admin/dashboard.html", stats=stats)


@admin_bp.route("/guests")
@admin_required
def guests():
    """
    Guest list with optional status filter.
    Query param: ?status=attending|not_attending|pending
    """
    status_filter = request.args.get("status")
    query = Guest.query.order_by(Guest.name.asc())
    if status_filter in ("attending", "not_attending", "pending"):
        query = query.filter_by(rsvp_status=status_filter)
    all_guests = query.all()
    return render_template(
        "admin/guests.html",
        guests=all_guests,
        status_filter=status_filter,
    )


@admin_bp.route("/guests/export")
@admin_required
def export_guests():
    """
    Export all RSVPs as a downloadable CSV file.
    """
    guests_list = Guest.query.order_by(Guest.name.asc()).all()

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "name", "email", "rsvp_status", "meal_preference",
            "plus_one", "plus_one_name", "table_number",
            "special_requests", "rsvp_submitted_at",
        ],
    )
    writer.writeheader()
    for g in guests_list:
        writer.writerow({
            "name": g.name or "",
            "email": g.email,
            "rsvp_status": g.rsvp_status,
            "meal_preference": g.meal_preference or "",
            "plus_one": "Yes" if g.plus_one else "No",
            "plus_one_name": g.plus_one_name or "",
            "table_number": g.table_number or "",
            "special_requests": g.special_requests or "",
            "rsvp_submitted_at": (
                g.rsvp_submitted_at.isoformat() if g.rsvp_submitted_at else ""
            ),
        })

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=rsvp_export.csv"},
    )


@admin_bp.route("/config", methods=["GET", "POST"])
@admin_required
def config():
    """
    Edit wedding configuration key-value pairs.

    GET:  Display all config rows in an editable form.
    POST: Save updated values back to the DB.
    """
    if request.method == "POST":
        for key, value in request.form.items():
            WeddingConfig.set(key, value)
        flash("Configuration updated successfully.", "success")
        return redirect(url_for("admin.config"))

    config_rows = WeddingConfig.query.order_by(WeddingConfig.key.asc()).all()
    return render_template("admin/config.html", config_rows=config_rows)


@admin_bp.route("/photos", methods=["GET", "POST"])
@admin_required
def photos():
    """
    Photo gallery management.

    GET:  List all photos with delete/caption controls.
    POST: Upload a new photo to Azure Blob Storage.
    """
    if request.method == "POST":
        if "photo" not in request.files:
            flash("No file selected.", "error")
            return redirect(url_for("admin.photos"))

        file = request.files["photo"]
        if not file.filename:
            flash("No file selected.", "error")
            return redirect(url_for("admin.photos"))

        try:
            from app.services.storage_service import upload_photo
            blob_url = upload_photo(
                file_data=file.read(),
                original_filename=file.filename,
                uploaded_by=session["user_email"],
            )
            photo = Photo(
                blob_url=blob_url,
                uploaded_by=session["user_email"],
            )
            db.session.add(photo)
            db.session.commit()
            flash("Photo uploaded successfully.", "success")
        except Exception as exc:
            logger.error("Photo upload failed: %s", exc)
            flash(f"Upload failed: {exc}", "error")

        return redirect(url_for("admin.photos"))

    all_photos = Photo.query.order_by(Photo.display_order.asc()).all()
    return render_template("admin/photos.html", photos=all_photos)


@admin_bp.route("/photos/<photo_id>/delete", methods=["POST"])
@admin_required
def delete_photo(photo_id: str):
    """
    Delete a photo from both Azure Blob Storage and the database.

    Args:
        photo_id: UUID of the photo to delete.
    """
    photo = Photo.query.get_or_404(photo_id)
    try:
        from app.services.storage_service import delete_photo as blob_delete
        blob_delete(photo.blob_url)
    except Exception as exc:
        logger.warning("Blob deletion failed (continuing with DB delete): %s", exc)

    db.session.delete(photo)
    db.session.commit()
    flash("Photo deleted.", "success")
    return redirect(url_for("admin.photos"))


@admin_bp.route("/guestbook")
@admin_required
def guestbook():
    """
    View all guestbook messages (admin read-only view).
    """
    messages = GuestbookMessage.query.order_by(
        GuestbookMessage.created_at.desc()
    ).all()
    return render_template("admin/guestbook.html", messages=messages)
