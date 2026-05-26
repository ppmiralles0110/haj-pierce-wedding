# =============================================================================
# tests/test_auth.py — Authentication route tests
# =============================================================================
"""Tests for OTP-based login and session management."""

from unittest.mock import patch


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
    resp = client.post("/login", data={"email": "not-an-email"}, follow_redirects=True)
    assert resp.status_code == 200
    # Should stay on login page
    assert b"valid email" in resp.data.lower()


def test_login_post_empty_email(client):
    """POST /login with empty email should show an error."""
    resp = client.post("/login", data={"email": ""}, follow_redirects=True)
    assert resp.status_code == 200


def test_login_post_valid_email_sends_otp(client, app):
    """POST /login with valid email should send OTP and redirect to /verify."""
    with patch("app.routes.auth.send_otp_email", return_value=True):
        resp = client.post(
            "/login",
            data={"email": "guest@example.com"},
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert "/verify" in resp.headers["Location"]


def test_verify_page_requires_pending_email(client):
    """GET /verify without a pending email in session should redirect to /login."""
    resp = client.get("/verify")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_verify_invalid_code(client, app):
    """POST /verify with wrong code should show error."""
    from app.models.otp_token import OtpToken
    from app.routes.auth import _hash_otp
    from datetime import datetime, timedelta, timezone
    from app.extensions import db

    with app.app_context():
        token = OtpToken(
            email="test@example.com",
            otp_hash=_hash_otp("123456"),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.session.add(token)
        db.session.commit()

    with client.session_transaction() as sess:
        sess["pending_email"] = "test@example.com"

    resp = client.post("/verify", data={"otp": "999999"}, follow_redirects=True)
    assert resp.status_code == 200
    # Should remain on verify/login with error
    assert b"invalid" in resp.data.lower() or b"error" in resp.data.lower()


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
