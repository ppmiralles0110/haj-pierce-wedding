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
    current_app,
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
from app.models.admin_user import AdminUser
from app.models.ai_chat_log import AiChatLog
from app.models.guest import Guest
from app.models.invite_code import InviteCode, generate_unique_code
from app.models.guestbook_message import GuestbookMessage
from app.models.login_log import LoginLog
from app.models.photo import Photo
from app.models.wedding_config import (
    WeddingConfig,
    DRESS_CODE_PHOTO_KEYS,
    LEGACY_DRESS_CODE_PHOTO_KEYS,
)
from app.routes.auth import admin_required, is_owner_email

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
        "parking_needed": Guest.query.filter_by(rsvp_status="attending", parking_required=True).count(),
        "total_photos": Photo.query.count(),
        "guestbook_count": GuestbookMessage.query.count(),
        "chat_logs": AiChatLog.query.count(),
    }

    return render_template("admin/dashboard.html", stats=stats)


@admin_bp.route("/guests")
@admin_required
def guests():
    """
    Guest list with optional status / parking filters.
    Query params: ?status=attending|not_attending|pending  &  ?parking=1
    """
    status_filter = request.args.get("status")
    parking_filter = request.args.get("parking") == "1"
    query = Guest.query.order_by(Guest.name.asc())
    if status_filter in ("attending", "not_attending", "pending"):
        query = query.filter_by(rsvp_status=status_filter)
    if parking_filter:
        query = query.filter_by(rsvp_status="attending", parking_required=True)
    all_guests = query.all()
    return render_template(
        "admin/guests.html",
        guests=all_guests,
        status_filter=status_filter,
        parking_filter=parking_filter,
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
            "name", "email", "rsvp_status", "phone_number",
            "parking_required", "table_number", "rsvp_submitted_at",
        ],
    )
    writer.writeheader()
    for g in guests_list:
        writer.writerow({
            "name": g.name or "",
            "email": g.email,
            "rsvp_status": g.rsvp_status,
            "phone_number": g.phone_number or "",
            "parking_required": "Yes" if g.parking_required else "No",
            "table_number": g.table_number or "",
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
        # "clear_*" checkboxes are UI-only controls, not config keys
        for key, value in request.form.items():
            if not key.startswith("clear_"):
                WeddingConfig.set(key, value)

        # Handle image file uploads for config image fields
        image_fields = {"hero_image_file": "hero_image_url"}
        for group_keys in DRESS_CODE_PHOTO_KEYS.values():
            for config_key in group_keys:
                image_fields[f"{config_key}_file"] = config_key

        uploaded_keys: set[str] = set()
        for file_field, config_key in image_fields.items():
            f = request.files.get(file_field)
            if f and f.filename:
                try:
                    if current_app.config.get("BLOB_STORAGE_URL"):
                        from app.services.storage_service import upload_photo
                        url = upload_photo(
                            file_data=f.read(),
                            original_filename=f.filename,
                            uploaded_by=session["user_email"],
                        )
                    else:
                        import os
                        import time
                        from werkzeug.utils import secure_filename
                        uploads_dir = os.path.join(current_app.root_path, "static", "uploads")
                        os.makedirs(uploads_dir, exist_ok=True)
                        safe_name = secure_filename(f.filename)
                        unique_name = f"{int(time.time())}_{safe_name}"
                        f.save(os.path.join(uploads_dir, unique_name))
                        url = f"/static/uploads/{unique_name}"
                    WeddingConfig.set(config_key, url)
                    uploaded_keys.add(config_key)
                except Exception as exc:
                    logger.error("Config image upload failed for %s: %s", config_key, exc)
                    flash(f"Image upload failed: {exc}", "error")

        # Apply "remove photo" checkboxes — a new upload in the same slot wins
        for group_keys in DRESS_CODE_PHOTO_KEYS.values():
            for config_key in group_keys:
                if config_key in uploaded_keys:
                    continue
                if request.form.get(f"clear_{config_key}") == "1":
                    WeddingConfig.set(config_key, "")
                    legacy_key = LEGACY_DRESS_CODE_PHOTO_KEYS.get(
                        "men" if "_men_" in config_key else "women", ""
                    )
                    # Slot 1 mirrors the legacy key — clear it too, or it reappears
                    if config_key.endswith("_1") and legacy_key:
                        WeddingConfig.set(legacy_key, "")

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
            if current_app.config.get("BLOB_STORAGE_URL"):
                # Production path — Azure Blob Storage
                from app.services.storage_service import upload_photo
                blob_url = upload_photo(
                    file_data=file.read(),
                    original_filename=file.filename,
                    uploaded_by=session["user_email"],
                )
            else:
                # Local development path — save to static/uploads/
                import os
                import time
                from werkzeug.utils import secure_filename
                uploads_dir = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(uploads_dir, exist_ok=True)
                safe_name = secure_filename(file.filename)
                unique_name = f"{int(time.time())}_{safe_name}"
                file.save(os.path.join(uploads_dir, unique_name))
                blob_url = f"/static/uploads/{unique_name}"
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


@admin_bp.route("/login-logs")
@admin_required
def login_logs():
    """
    View recent login logs with location data.
    """
    logs = LoginLog.query.order_by(LoginLog.logged_at.desc()).limit(200).all()
    return render_template("admin/login_logs.html", logs=logs)


# ---------------------------------------------------------------------------
# Admin Access
# ---------------------------------------------------------------------------

@admin_bp.route("/admins")
@admin_required
def admins():
    """List owner admins (from config) and portal-granted admins."""
    owner_emails = sorted(
        {e.strip().lower() for e in current_app.config.get("ADMIN_EMAILS", []) if e.strip()}
    )
    granted = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    return render_template(
        "admin/admins.html",
        owner_emails=owner_emails,
        granted=granted,
        current_email=(session.get("user_email") or "").lower(),
    )


@admin_bp.route("/admins/grant", methods=["POST"])
@admin_required
def grant_admin():
    """Grant admin access to an email address."""
    email = request.form.get("email", "").strip().lower()
    note = request.form.get("note", "").strip() or None

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("admin.admins"))

    if is_owner_email(email):
        flash(f"{email} already has permanent admin access via ADMIN_EMAILS.", "info")
        return redirect(url_for("admin.admins"))

    if AdminUser.query.filter_by(email=email).first():
        flash(f"{email} is already an admin.", "info")
        return redirect(url_for("admin.admins"))

    db.session.add(
        AdminUser(email=email, note=note, granted_by=session.get("user_email"))
    )
    db.session.commit()
    logger.info("Admin access granted to %s by %s", email, session.get("user_email"))
    flash(
        f"Admin access granted to {email}. "
        "They'll see the admin panel the next time they load a page.",
        "success",
    )
    return redirect(url_for("admin.admins"))


@admin_bp.route("/admins/<int:admin_id>/revoke", methods=["POST"])
@admin_required
def revoke_admin(admin_id):
    """Revoke a portal-granted admin access entry."""
    entry = AdminUser.query.get_or_404(admin_id)

    if entry.email == (session.get("user_email") or "").lower():
        flash("You cannot revoke your own admin access.", "error")
        return redirect(url_for("admin.admins"))

    # Never leave the site without an admin who can restore access
    if AdminUser.query.count() <= 1 and not current_app.config.get("ADMIN_EMAILS"):
        flash(
            "Cannot revoke the last remaining admin. "
            "Grant access to someone else first.",
            "error",
        )
        return redirect(url_for("admin.admins"))

    email = entry.email
    db.session.delete(entry)
    db.session.commit()
    logger.info("Admin access revoked for %s by %s", email, session.get("user_email"))
    flash(f"Admin access revoked for {email}.", "success")
    return redirect(url_for("admin.admins"))


# ---------------------------------------------------------------------------
# Invite Codes
# ---------------------------------------------------------------------------

@admin_bp.route("/invites")
@admin_required
def invites():
    """
    List all invite codes.

    Codes generated by the most recent bulk import are highlighted so the
    admin can copy a freshly generated batch without hunting for it.
    """
    all_invites = InviteCode.query.order_by(InviteCode.created_at.desc()).all()
    batch_ids = session.pop("last_invite_batch", None) or []
    return render_template(
        "admin/invites.html",
        invites=all_invites,
        batch_ids=batch_ids,
        max_bulk_invites=MAX_BULK_INVITES,
    )


@admin_bp.route("/invites/create", methods=["POST"])
@admin_required
def create_invite():
    """Generate a new invite code for a guest label."""
    label = request.form.get("label", "").strip()
    email = request.form.get("email", "").strip().lower() or None
    if not label:
        flash("Please enter a name or label for the invite.", "error")
        return redirect(url_for("admin.invites"))

    try:
        code = generate_unique_code()
    except RuntimeError:
        flash("Could not generate a unique invite code. Please try again.", "error")
        return redirect(url_for("admin.invites"))

    invite = InviteCode(code=code, label=label, email=email)
    db.session.add(invite)
    db.session.commit()

    flash(f"Invite code generated for \"{label}\": {code}", "invite_created")
    return redirect(url_for("admin.invites"))


# ---------------------------------------------------------------------------
# Bulk invite import
# ---------------------------------------------------------------------------

# Column headers accepted for each field in an uploaded guest list.
_NAME_HEADERS = {"name", "guest", "guest name", "full name", "label", "guests"}
_EMAIL_HEADERS = {"email", "e-mail", "email address", "mail"}

MAX_BULK_INVITES = 1000


def _parse_guest_list(text: str) -> tuple[list[tuple[str, str | None]], list[str]]:
    """
    Parse a pasted or uploaded guest list into ``(name, email)`` pairs.

    Accepts CSV with a header row (``name``/``email`` columns in any order),
    headerless CSV (first column name, optional second column email), or a
    plain list with one guest per line.

    Args:
        text: Raw guest-list text.

    Returns:
        Tuple of (rows, warnings) where rows are ``(name, email_or_None)``.
    """
    rows: list[tuple[str, str | None]] = []
    warnings: list[str] = []

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return rows, warnings

    reader = list(csv.reader(lines))
    if not reader:
        return rows, warnings

    header = [c.strip().lower() for c in reader[0]]
    name_idx: int | None = None
    email_idx: int | None = None
    if any(h in _NAME_HEADERS for h in header) or any(h in _EMAIL_HEADERS for h in header):
        for i, col in enumerate(header):
            if name_idx is None and col in _NAME_HEADERS:
                name_idx = i
            elif email_idx is None and col in _EMAIL_HEADERS:
                email_idx = i
        data_rows = reader[1:]
    else:
        # Headerless — assume column 0 is the name, column 1 (if any) the email
        name_idx, email_idx = 0, 1 if len(header) > 1 else None
        data_rows = reader

    if name_idx is None:
        warnings.append(
            "No name column found. Add a 'name' column header, or put names in the first column."
        )
        return rows, warnings

    for line_no, cols in enumerate(data_rows, start=2):
        if not any(c.strip() for c in cols):
            continue
        name = cols[name_idx].strip() if name_idx < len(cols) else ""
        email = ""
        if email_idx is not None and email_idx < len(cols):
            email = cols[email_idx].strip().lower()

        if not name:
            warnings.append(f"Row {line_no}: skipped — no name.")
            continue
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            warnings.append(f"Row {line_no} ({name}): ignored invalid email '{email}'.")
            email = ""

        rows.append((name[:200], email[:255] or None))

    return rows, warnings


@admin_bp.route("/invites/bulk", methods=["POST"])
@admin_required
def bulk_create_invites():
    """
    Generate one invite code per guest from an uploaded CSV or pasted list.
    """
    text = ""
    upload = request.files.get("guest_file")
    if upload and upload.filename:
        try:
            text = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            flash(
                "Could not read that file. Please save it as CSV (UTF-8) and try again.",
                "error",
            )
            return redirect(url_for("admin.invites"))
    else:
        text = request.form.get("guest_list", "")

    if not text.strip():
        flash("Upload a CSV file or paste a guest list first.", "error")
        return redirect(url_for("admin.invites"))

    rows, warnings = _parse_guest_list(text)
    if not rows:
        for warning in warnings[:5]:
            flash(warning, "error")
        if not warnings:
            flash("No guests found in that list.", "error")
        return redirect(url_for("admin.invites"))

    if len(rows) > MAX_BULK_INVITES:
        flash(
            f"That list has {len(rows)} guests — the limit is {MAX_BULK_INVITES} per import.",
            "error",
        )
        return redirect(url_for("admin.invites"))

    skip_duplicates = request.form.get("skip_duplicates") == "1"
    existing_labels = {
        (inv.label or "").strip().lower() for inv in InviteCode.query.all()
    }

    created: list[InviteCode] = []
    skipped = 0
    reserved: set[str] = set()
    seen_in_batch: set[str] = set()

    try:
        for name, email in rows:
            key = name.strip().lower()
            if key in seen_in_batch:
                skipped += 1
                continue
            if skip_duplicates and key in existing_labels:
                skipped += 1
                continue
            seen_in_batch.add(key)

            invite = InviteCode(
                code=generate_unique_code(reserved),
                label=name,
                email=email,
            )
            db.session.add(invite)
            created.append(invite)

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Bulk invite import failed: %s", exc)
        flash(f"Import failed, no codes were created: {exc}", "error")
        return redirect(url_for("admin.invites"))

    # Remember the batch so the table can highlight the new rows
    session["last_invite_batch"] = [inv.id for inv in created]

    logger.info(
        "Bulk invite import by %s — %d created, %d skipped",
        session.get("user_email"),
        len(created),
        skipped,
    )

    summary = f"Generated {len(created)} invite code(s)."
    if skipped:
        summary += f" Skipped {skipped} duplicate name(s)."
    flash(summary, "success")
    for warning in warnings[:5]:
        flash(warning, "info")
    if len(warnings) > 5:
        flash(f"…and {len(warnings) - 5} more row warning(s).", "info")

    return redirect(url_for("admin.invites"))


@admin_bp.route("/invites/export")
@admin_required
def export_invites():
    """Download every invite code as CSV (name, email, code, status)."""
    all_invites = InviteCode.query.order_by(InviteCode.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "email", "invite_code", "status", "uses", "created_at"])
    for inv in all_invites:
        writer.writerow([
            inv.label,
            inv.email or "",
            inv.code,
            "active" if inv.is_active else "inactive",
            inv.use_count,
            inv.created_at.isoformat(),
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=invite_codes.csv"},
    )


@admin_bp.route("/invites/template")
@admin_required
def invite_template():
    """Download a blank CSV template for the bulk guest-list upload."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "email"])
    writer.writerow(["Juan Dela Cruz", "juan@example.com"])
    writer.writerow(["Maria Santos", ""])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=guest_list_template.csv"},
    )


@admin_bp.route("/invites/<int:invite_id>/toggle", methods=["POST"])
@admin_required
def toggle_invite(invite_id):
    """Activate or deactivate an invite code."""
    invite = InviteCode.query.get_or_404(invite_id)
    invite.is_active = not invite.is_active
    db.session.commit()
    status = "activated" if invite.is_active else "deactivated"
    flash(f"Invite code {invite.code} ({invite.label}) {status}.", "success")
    return redirect(url_for("admin.invites"))


@admin_bp.route("/invites/<int:invite_id>/delete", methods=["POST"])
@admin_required
def delete_invite(invite_id):
    """Permanently delete an invite code."""
    invite = InviteCode.query.get_or_404(invite_id)
    db.session.delete(invite)
    db.session.commit()
    flash(f"Invite code {invite.code} ({invite.label}) deleted.", "success")
    return redirect(url_for("admin.invites"))


# ---------------------------------------------------------------------------
# One-time admin bootstrap (self-disables once any invite code exists)
# ---------------------------------------------------------------------------

@admin_bp.route("/bootstrap-first-code")
def bootstrap_first_code():
    """
    Creates the very first admin invite code so the admin can log in.
    SELF-DISABLING: returns 404 once any invite code exists in the database.
    Safe to leave deployed — it cannot be used to create codes after initial setup.
    """
    if InviteCode.query.count() > 0:
        from flask import abort
        abort(404)

    code = generate_unique_code()
    invite = InviteCode(code=code, label="Admin")
    db.session.add(invite)
    db.session.commit()

    from flask import make_response
    html = f"""<!doctype html>
<html><head><title>Admin Bootstrap</title>
<style>body{{font-family:monospace;padding:2rem;background:#111;color:#eee;}}
.code{{font-size:2rem;letter-spacing:.3em;background:#222;padding:1rem 2rem;border-radius:4px;display:inline-block;margin:1rem 0;}}
</style></head><body>
<h2>Admin Invite Code Created</h2>
<p>Use this code to log in for the first time:</p>
<div class="code">{code}</div>
<p style="opacity:.6;font-size:.85rem;">This page will return 404 on all future visits.</p>
<p><a href="/login" style="color:#adf;">Go to Login &rarr;</a></p>
</body></html>"""
    return make_response(html, 200)
