# =============================================================================
# tests/test_admin.py — Admin route tests
# =============================================================================
"""Tests for admin-only routes and access control."""


def test_admin_dashboard_requires_admin(auth_client):
    """Non-admin authenticated user should be denied admin access."""
    resp = auth_client.get("/admin/")
    assert resp.status_code == 302  # Redirect (not 200)


def test_admin_dashboard_accessible_to_admin(admin_client):
    """Admin user should be able to access the dashboard."""
    resp = admin_client.get("/admin/")
    assert resp.status_code == 200
    assert b"dashboard" in resp.data.lower() or b"admin" in resp.data.lower()


def test_admin_guests_accessible(admin_client):
    """Admin can access the guest list."""
    resp = admin_client.get("/admin/guests")
    assert resp.status_code == 200


def test_admin_export_returns_csv(admin_client):
    """Admin guest export should return a CSV file."""
    resp = admin_client.get("/admin/guests/export")
    assert resp.status_code == 200
    assert b"text/csv" in resp.content_type.encode() or "csv" in resp.content_type


def test_admin_config_accessible(admin_client):
    """Admin can access the config editor."""
    resp = admin_client.get("/admin/config")
    assert resp.status_code == 200


def test_admin_guestbook_accessible(admin_client):
    """Admin can view guestbook messages."""
    resp = admin_client.get("/admin/guestbook")
    assert resp.status_code == 200


def test_health_endpoint(client):
    """GET /health should return 200 without authentication."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert b"ok" in resp.data.lower()


# ---------------------------------------------------------------------------
# Guest list fields
# ---------------------------------------------------------------------------

def test_guest_list_shows_parking_not_meal(admin_client):
    """Guest table exposes phone/parking and no longer meal or plus-one."""
    resp = admin_client.get("/admin/guests")
    body = resp.data.decode()
    assert "<th>Parking</th>" in body
    assert "<th>Phone</th>" in body
    assert "<th>Meal</th>" not in body
    assert "<th>+1</th>" not in body


def test_guest_list_parking_filter(admin_client):
    """The Needs Parking filter renders without error."""
    resp = admin_client.get("/admin/guests?parking=1")
    assert resp.status_code == 200
    assert b"Needs Parking" in resp.data


def test_guest_export_includes_parking(admin_client):
    """CSV export header carries phone_number and parking_required."""
    resp = admin_client.get("/admin/guests/export")
    header = resp.data.decode().splitlines()[0]
    assert "parking_required" in header
    assert "phone_number" in header
    assert "meal_preference" not in header


# ---------------------------------------------------------------------------
# Admin access management
# ---------------------------------------------------------------------------

def test_admins_page_accessible(admin_client):
    """Admin can open the admin-access page."""
    resp = admin_client.get("/admin/admins")
    assert resp.status_code == 200
    assert b"Grant Admin Access" in resp.data


def test_grant_and_revoke_admin(admin_client, app):
    """Granting admin access creates a record; revoking removes it."""
    from app.extensions import db
    from app.models.admin_user import AdminUser

    admin_client.post(
        "/admin/admins/grant",
        data={"email": "Helper@Example.com", "note": "Wedding coordinator"},
        follow_redirects=True,
    )

    with app.app_context():
        entry = AdminUser.query.filter_by(email="helper@example.com").first()
        assert entry is not None
        assert entry.note == "Wedding coordinator"
        assert entry.granted_by == "admin@test.com"
        entry_id = entry.id

    admin_client.post(f"/admin/admins/{entry_id}/revoke", follow_redirects=True)

    with app.app_context():
        assert AdminUser.query.filter_by(email="helper@example.com").first() is None
        db.session.remove()


def test_grant_admin_rejects_invalid_email(admin_client, app):
    """An invalid email should not create a grant."""
    from app.models.admin_user import AdminUser

    admin_client.post(
        "/admin/admins/grant",
        data={"email": "not-an-email"},
        follow_redirects=True,
    )
    with app.app_context():
        assert AdminUser.query.filter_by(email="not-an-email").first() is None


def test_granted_admin_gains_access_without_relogin(client, app):
    """A granted email passes admin_required on its very next request."""
    from app.extensions import db
    from app.models.admin_user import AdminUser

    with app.app_context():
        db.session.add(AdminUser(email="newadmin@test.com"))
        db.session.commit()

    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["user_email"] = "newadmin@test.com"
        sess["is_admin"] = False  # stale session value

    assert client.get("/admin/").status_code == 200

    with app.app_context():
        AdminUser.query.filter_by(email="newadmin@test.com").delete()
        db.session.commit()


def test_revoked_admin_loses_access_immediately(client, app):
    """A session flagged admin is rejected once the grant is gone."""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["user_email"] = "ghost@test.com"
        sess["is_admin"] = True  # stale session value

    assert client.get("/admin/").status_code == 302


# ---------------------------------------------------------------------------
# Bulk invite import
# ---------------------------------------------------------------------------

def _clear_invites(app):
    from app.extensions import db
    from app.models.invite_code import InviteCode
    with app.app_context():
        InviteCode.query.delete()
        db.session.commit()


def test_bulk_import_from_pasted_list(admin_client, app):
    """Pasting names generates one unique active code per guest."""
    from app.models.invite_code import InviteCode
    _clear_invites(app)

    resp = admin_client.post(
        "/admin/invites/bulk",
        data={"guest_list": "Juan Dela Cruz\nMaria Santos\nThe Reyes Family"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        invites = InviteCode.query.all()
        assert len(invites) == 3
        assert {i.label for i in invites} == {
            "Juan Dela Cruz", "Maria Santos", "The Reyes Family"
        }
        assert len({i.code for i in invites}) == 3
        assert all(len(i.code) == 8 and i.is_active for i in invites)

    _clear_invites(app)


def test_bulk_import_csv_with_headers(admin_client, app):
    """A CSV upload with name/email headers captures both columns."""
    import io
    from app.models.invite_code import InviteCode
    _clear_invites(app)

    csv_bytes = b"name,email\nAna Cruz,ana@example.com\nBen Tan,\n"
    admin_client.post(
        "/admin/invites/bulk",
        data={"guest_file": (io.BytesIO(csv_bytes), "guests.csv")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    with app.app_context():
        ana = InviteCode.query.filter_by(label="Ana Cruz").first()
        ben = InviteCode.query.filter_by(label="Ben Tan").first()
        assert ana is not None and ana.email == "ana@example.com"
        assert ben is not None and ben.email is None

    _clear_invites(app)


def test_bulk_import_csv_reversed_headers(admin_client, app):
    """Column order should not matter when headers are present."""
    import io
    from app.models.invite_code import InviteCode
    _clear_invites(app)

    csv_bytes = b"email,name\ncarl@example.com,Carl Reyes\n"
    admin_client.post(
        "/admin/invites/bulk",
        data={"guest_file": (io.BytesIO(csv_bytes), "guests.csv")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    with app.app_context():
        carl = InviteCode.query.filter_by(label="Carl Reyes").first()
        assert carl is not None
        assert carl.email == "carl@example.com"

    _clear_invites(app)


def test_bulk_import_skips_duplicates(admin_client, app):
    """Existing labels are skipped when the duplicate checkbox is on."""
    from app.models.invite_code import InviteCode
    _clear_invites(app)

    admin_client.post(
        "/admin/invites/bulk",
        data={"guest_list": "Dana Lim"},
        follow_redirects=True,
    )
    admin_client.post(
        "/admin/invites/bulk",
        data={"guest_list": "Dana Lim\nEli Cruz", "skip_duplicates": "1"},
        follow_redirects=True,
    )

    with app.app_context():
        assert InviteCode.query.filter_by(label="Dana Lim").count() == 1
        assert InviteCode.query.filter_by(label="Eli Cruz").count() == 1

    _clear_invites(app)


def test_bulk_import_empty_input_creates_nothing(admin_client, app):
    """Submitting nothing should not create codes."""
    from app.models.invite_code import InviteCode
    _clear_invites(app)

    admin_client.post(
        "/admin/invites/bulk", data={"guest_list": "   "}, follow_redirects=True
    )
    with app.app_context():
        assert InviteCode.query.count() == 0


def test_invite_export_and_template(admin_client, app):
    """Invite CSV export and the blank template both download."""
    _clear_invites(app)
    admin_client.post(
        "/admin/invites/bulk",
        data={"guest_list": "Faye Ong,faye@example.com"},
        follow_redirects=True,
    )

    resp = admin_client.get("/admin/invites/export")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "invite_code" in body.splitlines()[0]
    assert "Faye Ong" in body
    assert "faye@example.com" in body

    tmpl = admin_client.get("/admin/invites/template")
    assert tmpl.status_code == 200
    assert "name,email" in tmpl.data.decode()

    _clear_invites(app)
