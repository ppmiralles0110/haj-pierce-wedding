# =============================================================================
# tests/test_auth.py — Authentication route tests
# =============================================================================
"""Tests for invite-code login and session management."""

import pytest

from app.extensions import db
from app.models.invite_code import InviteCode


@pytest.fixture
def invite(app):
    """Create an active invite code for the duration of one test."""
    with app.app_context():
        code = InviteCode(code="TESTCODE", label="Test Guest")
        db.session.add(code)
        db.session.commit()
    yield "TESTCODE"
    with app.app_context():
        InviteCode.query.filter_by(code="TESTCODE").delete()
        db.session.commit()


def _login_form(**overrides):
    data = {
        "email": "guest@example.com",
        "first_name": "Test",
        "last_name": "Guest",
        "invite_code": "TESTCODE",
    }
    data.update(overrides)
    return data


def test_login_page_renders(client):
    """GET /login should return 200."""
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"login" in resp.data.lower()


def test_login_redirects_when_authenticated(auth_client):
    """Authenticated users visiting /login should be redirected."""
    resp = auth_client.get("/login")
    assert resp.status_code == 302


def test_login_post_invalid_email(client):
    """POST /login with invalid email should show an error."""
    resp = client.post(
        "/login", data=_login_form(email="not-an-email"), follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"valid email" in resp.data.lower()


def test_login_post_empty_email(client):
    """POST /login with empty email should show an error."""
    resp = client.post("/login", data=_login_form(email=""), follow_redirects=True)
    assert resp.status_code == 200


def test_login_valid_invite_code_authenticates(client, app, invite):
    """A valid invite code should log the guest in and create their record."""
    from app.models.guest import Guest

    resp = client.post("/login", data=_login_form(), follow_redirects=False)
    assert resp.status_code == 302

    with client.session_transaction() as sess:
        assert sess["authenticated"] is True
        assert sess["user_email"] == "guest@example.com"
        assert sess["user_full_name"] == "Test Guest"

    with app.app_context():
        guest = Guest.query.filter_by(email="guest@example.com").first()
        assert guest is not None
        assert guest.name == "Test Guest"
        assert InviteCode.query.filter_by(code="TESTCODE").first().use_count == 1
        Guest.query.filter_by(email="guest@example.com").delete()
        db.session.commit()


def test_login_rejects_unknown_invite_code(client):
    """An invite code that does not exist should be refused."""
    resp = client.post(
        "/login", data=_login_form(invite_code="NOPECODE"), follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"invalid or inactive invite code" in resp.data.lower()

    with client.session_transaction() as sess:
        assert not sess.get("authenticated")


def test_login_rejects_inactive_invite_code(client, app, invite):
    """A deactivated invite code should be refused."""
    with app.app_context():
        row = InviteCode.query.filter_by(code="TESTCODE").first()
        row.is_active = False
        db.session.commit()

    resp = client.post("/login", data=_login_form(), follow_redirects=True)
    assert resp.status_code == 200
    assert b"invalid or inactive invite code" in resp.data.lower()

    with client.session_transaction() as sess:
        assert not sess.get("authenticated")


def test_login_requires_name_fields(client, invite):
    """Both first and last name are required."""
    resp = client.post(
        "/login", data=_login_form(first_name=""), follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"first name" in resp.data.lower()

    resp = client.post("/login", data=_login_form(last_name=""), follow_redirects=True)
    assert resp.status_code == 200
    assert b"last name" in resp.data.lower()


def test_login_requires_eight_character_code(client):
    """Codes that are not 8 characters are rejected before any DB lookup."""
    resp = client.post(
        "/login", data=_login_form(invite_code="SHORT"), follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"8-character invite code" in resp.data.lower()


def test_logout_clears_session(auth_client):
    """GET /logout should clear session and redirect to /login."""
    resp = auth_client.get("/logout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_protected_route_requires_login(client):
    """/rsvp should redirect unauthenticated users to /login."""
    resp = client.get("/rsvp")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

