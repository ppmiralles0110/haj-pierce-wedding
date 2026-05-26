# =============================================================================
# tests/test_ai.py — AI service and API route tests
# =============================================================================
"""Tests for AI service functions and API endpoints."""

import json
from unittest.mock import MagicMock, patch


def test_enhance_message_api_requires_auth(client):
    """POST /api/enhance-message should require authentication."""
    resp = client.post(
        "/api/enhance-message",
        json={"message": "Hello"},
    )
    assert resp.status_code == 302  # Redirect to login


def test_enhance_message_api_authenticated(auth_client):
    """POST /api/enhance-message should call AI and return enhanced text."""
    with patch("app.routes.api.ai_enhance", return_value="A beautifully poetic wish."):
        resp = auth_client.post(
            "/api/enhance-message",
            json={"message": "Congrats!"},
            content_type="application/json",
        )
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "enhanced" in data


def test_enhance_message_api_empty_message(auth_client):
    """POST /api/enhance-message with empty message should return 400."""
    resp = auth_client.post(
        "/api/enhance-message",
        json={"message": ""},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_enhance_message_api_too_long(auth_client):
    """POST /api/enhance-message with >1000 chars should return 400."""
    resp = auth_client.post(
        "/api/enhance-message",
        json={"message": "x" * 1001},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_chat_api_requires_auth(client):
    """POST /api/chat should require authentication."""
    resp = client.post("/api/chat", json={"message": "Hello"})
    assert resp.status_code == 302


def test_chat_api_empty_message(auth_client):
    """POST /api/chat with empty message should return 400."""
    resp = auth_client.post(
        "/api/chat",
        json={"message": ""},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_ai_service_enhance_message():
    """Unit test: enhance_message calls the OpenAI client correctly."""
    from app.services.ai_service import enhance_message, AIServiceError

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Enhanced poetic message"

    with patch("app.services.ai_service._get_client") as mock_client_fn, \
         patch("app.services.ai_service._get_deployment", return_value="gpt-4o-mini"):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        # Need app context for config access
        from app import create_app
        from app.config import TestConfig
        app = create_app(TestConfig)
        with app.app_context():
            result = enhance_message("Simple wish")

    assert result == "Enhanced poetic message"
