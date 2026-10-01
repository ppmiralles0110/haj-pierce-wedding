# =============================================================================
# tests/test_rsvp.py — RSVP route tests
# =============================================================================
"""Tests for RSVP form submission and validation."""

from unittest.mock import patch


def test_rsvp_page_renders(auth_client):
    """GET /rsvp should render for authenticated users."""
    resp = auth_client.get("/rsvp")
    assert resp.status_code == 200
    assert b"rsvp" in resp.data.lower()


def test_rsvp_submit_attending(auth_client, app):
    """POST /rsvp with valid attending data should save and redirect to success."""
    with patch("app.services.ai_service.generate_rsvp_confirmation", return_value="Welcome!"):
        resp = auth_client.post(
            "/rsvp",
            data={
                "name": "Test Guest",
                "rsvp_status": "attending",
                "parking_required": "yes",
            },
            follow_redirects=True,
        )
    assert resp.status_code == 200
    # Success page should be rendered
    assert b"confirmed" in resp.data.lower() or b"success" in resp.data.lower() or b"rsvp" in resp.data.lower()


def test_rsvp_submit_not_attending(auth_client):
    """POST /rsvp declining attendance should be saved."""
    with patch("app.services.ai_service.generate_rsvp_confirmation", return_value="Thanks"):
        resp = auth_client.post(
            "/rsvp",
            data={
                "name": "Declining Guest",
                "rsvp_status": "not_attending",
            },
            follow_redirects=True,
        )
    assert resp.status_code == 200


def test_rsvp_submit_missing_name(auth_client):
    """POST /rsvp without a name should fail validation."""
    resp = auth_client.post(
        "/rsvp",
        data={
            "name": "",
            "rsvp_status": "attending",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"name" in resp.data.lower()


def test_rsvp_submit_invalid_phone(auth_client):
    """POST /rsvp with a non-Philippine mobile number should fail validation."""
    resp = auth_client.post(
        "/rsvp",
        data={
            "name": "Wrong Number",
            "rsvp_status": "attending",
            "phone_number": "12345",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"philippine" in resp.data.lower()


def test_rsvp_parking_saved_when_attending(auth_client, app):
    """Parking preference should persist for attending guests."""
    with patch("app.services.ai_service.generate_rsvp_confirmation", return_value="Welcome!"):
        auth_client.post(
            "/rsvp",
            data={
                "name": "Parking Guest",
                "rsvp_status": "attending",
                "parking_required": "yes",
            },
            follow_redirects=True,
        )

    from app.models.guest import Guest
    with app.app_context():
        guest = Guest.query.filter_by(email="guest@test.com").first()
        assert guest is not None
        assert guest.parking_required is True


def test_rsvp_parking_cleared_when_declining(auth_client, app):
    """Parking should be forced off when a guest declines."""
    with patch("app.services.ai_service.generate_rsvp_confirmation", return_value="Thanks"):
        auth_client.post(
            "/rsvp",
            data={
                "name": "Declining Guest",
                "rsvp_status": "not_attending",
                "parking_required": "yes",
            },
            follow_redirects=True,
        )

    from app.models.guest import Guest
    with app.app_context():
        guest = Guest.query.filter_by(email="guest@test.com").first()
        assert guest is not None
        assert guest.parking_required is False
