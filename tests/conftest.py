# =============================================================================
# tests/conftest.py — pytest fixtures and test app setup
# =============================================================================
"""Shared test fixtures for the entire test suite."""

import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """
    Create a Flask application instance configured for testing.

    Uses TestConfig which sets TESTING=True and uses SQLite in-memory DB.
    Session-scoped so the app is created only once per test session.
    """
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """
    Provide a Flask test client.

    Function-scoped so each test gets a fresh client (but shares the DB).
    """
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """
    Provide the database with per-test rollback for isolation.
    """
    connection = _db.engine.connect()
    transaction = connection.begin()

    yield _db

    transaction.rollback()
    connection.close()


@pytest.fixture
def auth_client(client, app):
    """
    A test client pre-loaded with an authenticated session.
    """
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["user_email"] = "guest@test.com"
        sess["is_admin"] = False
    return client


@pytest.fixture
def admin_client(client, app):
    """
    A test client pre-loaded with an admin session.
    """
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["user_email"] = "admin@test.com"
        sess["is_admin"] = True
    return client
