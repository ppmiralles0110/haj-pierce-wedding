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
