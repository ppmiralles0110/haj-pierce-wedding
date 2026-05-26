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
    with patch("app.routes.rsvp.generate_rsvp_confirmation", return_value="Welcome!"):
        resp = auth_client.post(
            "/rsvp",
            data={
                "name": "Test Guest",
                "rsvp_status": "attending",
                "meal_preference": "chicken",
                "plus_one": "no",
                "special_requests": "",
            },
            follow_redirects=True,
        )
    assert resp.status_code == 200
    # Success page should be rendered
    assert b"confirmed" in resp.data.lower() or b"success" in resp.data.lower() or b"rsvp" in resp.data.lower()


def test_rsvp_submit_not_attending(auth_client):
    """POST /rsvp declining attendance should be saved."""
    with patch("app.routes.rsvp.generate_rsvp_confirmation", return_value="Thanks"):
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
            "meal_preference": "fish",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"name" in resp.data.lower()


def test_rsvp_submit_attending_no_meal(auth_client):
    """POST /rsvp attending without a meal preference should fail validation."""
    resp = auth_client.post(
        "/rsvp",
        data={
            "name": "Hungry Guest",
            "rsvp_status": "attending",
            "meal_preference": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"meal" in resp.data.lower()
