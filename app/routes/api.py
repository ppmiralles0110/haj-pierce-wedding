# =============================================================================
# app/routes/api.py — AI API Blueprint (SSE Chat + Message Enhancer)
# =============================================================================
"""
JSON/SSE API routes consumed by the frontend JavaScript.

Routes:
  POST /api/chat           — Streaming AI chat response (SSE)
  POST /api/enhance-message — AI guestbook message enhancer
  POST /api/photo-caption  — AI photo caption generator (admin)
"""

import json
import logging

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
    session,
    stream_with_context,
)

from app.extensions import db, limiter
from app.models.ai_chat_log import AiChatLog
from app.models.wedding_config import WeddingConfig
from app.routes.auth import login_required, admin_required

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


@api_bp.route("/chat", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def chat():
    """
    Streaming AI chat endpoint using Server-Sent Events.

    Expects JSON body: ``{"message": "...", "history": [...]}``

    Streams tokens back to the client as SSE events:
      ``data: {"token": "..."}``
    Then sends a final event:
      ``data: {"done": true, "full": "..."}``

    Also logs the full exchange to ``ai_chat_logs``.

    Returns:
        SSE stream (Content-Type: text/event-stream).
    """
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    email = session["user_email"]

    # Build conversation history in OpenAI format
    messages = []
    for turn in history[-9:]:   # Last 9 turns = 9 messages (stay under token limit)
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    # Load wedding config for system prompt
    config_rows = WeddingConfig.query.all()
    wedding_config = {row.key: row.value for row in config_rows}

    def generate():
        """Inner generator that yields SSE events and logs the exchange."""
        from app.services.ai_service import chat_stream, AIServiceError
        try:
            full_response_parts = []
            for event in chat_stream(messages=messages, wedding_config=wedding_config):
                # Parse "done" event to capture full response for logging
                if event.startswith("data: "):
                    try:
                        payload = json.loads(event[6:].strip())
                        if payload.get("done"):
                            full_response_parts.append(payload.get("full", ""))
                    except json.JSONDecodeError:
                        pass
                yield event

            # Log the full exchange (uses app context from stream_with_context)
            full_response = "".join(full_response_parts)
            if full_response:
                log_entry = AiChatLog(
                    guest_email=email,
                    user_message=user_message,
                    ai_response=full_response,
                )
                db.session.add(log_entry)
                db.session.commit()

        except Exception as exc:
            logger.error("Chat stream error for %s: %s", email, exc)
            yield f"data: {json.dumps({'error': 'AI service unavailable'})}\n\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


@api_bp.route("/enhance-message", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def enhance_message():
    """
    Enhance a guestbook message with AI.

    Expects JSON body: ``{"message": "..."}``

    Returns:
        JSON: ``{"enhanced": "..."}`` or ``{"error": "..."}``
    """
    data = request.get_json(silent=True) or {}
    original = (data.get("message") or "").strip()

    if not original:
        return jsonify({"error": "message is required"}), 400

    if len(original) > 1000:
        return jsonify({"error": "Message is too long (max 1000 characters)."}), 400

    try:
        from app.services.ai_service import enhance_message as ai_enhance
        enhanced = ai_enhance(original)
        return jsonify({"enhanced": enhanced})

    except Exception as exc:
        logger.error("enhance_message error: %s", exc)
        return jsonify({"error": "AI service unavailable"}), 503


@api_bp.route("/photo-caption", methods=["POST"])
@admin_required
@limiter.limit("20 per minute")
def photo_caption():
    """
    Generate an AI caption for a photo (admin only).

    Expects JSON body: ``{"photo_id": "...", "description": "..."}``
    Saves the caption to the photo record.

    Returns:
        JSON: ``{"caption": "..."}`` or ``{"error": "..."}``
    """
    data = request.get_json(silent=True) or {}
    photo_id = data.get("photo_id", "").strip()
    description = (data.get("description") or "wedding photo").strip()

    if not photo_id:
        return jsonify({"error": "photo_id is required"}), 400

    from app.models.photo import Photo
    photo = Photo.query.get(photo_id)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    try:
        from app.services.ai_service import generate_photo_caption
        caption = generate_photo_caption(description)
        photo.caption = caption
        db.session.commit()
        return jsonify({"caption": caption})

    except Exception as exc:
        logger.error("photo_caption error: %s", exc)
        return jsonify({"error": "AI service unavailable"}), 503
