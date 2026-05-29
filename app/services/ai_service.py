# =============================================================================
# app/services/ai_service.py — Azure OpenAI (gpt-4o-mini) Service
# =============================================================================
"""
Service layer for all Azure OpenAI interactions.

Uses the ``openai`` SDK configured with the Azure endpoint.  All public
methods are typed and raise ``AIServiceError`` on failure so callers
can handle errors gracefully.
"""

import json
import logging
from typing import Generator, Optional

from flask import current_app
from openai import AzureOpenAI, OpenAIError

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when the AI service encounters an unrecoverable error."""


def _get_client() -> AzureOpenAI:
    """
    Build and return a configured AzureOpenAI client.

    Reads credentials from Flask's current app config so the client is
    always fresh (important for token rotation in production).

    Returns:
        Configured AzureOpenAI client instance.

    Raises:
        AIServiceError: If the endpoint or API key is not configured.
    """
    endpoint = current_app.config.get("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        raise AIServiceError("AZURE_OPENAI_ENDPOINT must be set.")

    api_key = current_app.config.get("AZURE_OPENAI_API_KEY")
    api_version = current_app.config.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    if api_key:
        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    # No API key — use Managed Identity (Cognitive Services OpenAI User role assigned)
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=api_version,
    )


def _get_deployment() -> str:
    """
    Return the Azure OpenAI deployment name from config.

    Returns:
        Deployment name string (default: ``gpt-4o-mini``).
    """
    return current_app.config.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")


def _build_system_prompt(wedding_config: dict) -> str:
    """
    Build a dynamic system prompt for the AI concierge chatbot.

    The prompt is constructed from the live ``wedding_config`` table so
    the admin can update it without touching code.

    Args:
        wedding_config: Dict of key-value pairs from the wedding_config DB table.

    Returns:
        Multi-line system prompt string for the AI model.
    """
    couple1 = wedding_config.get("couple_name_1", "the couple")
    couple2 = wedding_config.get("couple_name_2", "their partner")
    date = wedding_config.get("wedding_date", "TBD")
    time = wedding_config.get("wedding_time", "TBD")
    venue = wedding_config.get("venue_name", "TBD")
    address = wedding_config.get("venue_address", "TBD")
    dress_code = wedding_config.get("dress_code", "TBD")
    theme = wedding_config.get("theme_description", "TBD")
    rsvp_deadline = wedding_config.get("rsvp_deadline", "TBD")
    hashtag = wedding_config.get("wedding_hashtag", "")

    return f"""You are the warm, witty, and helpful AI wedding concierge for {couple1} and {couple2}'s wedding.

WEDDING DETAILS:
- Date: {date} at {time}
- Venue: {venue}
- Address: {address}
- Dress Code: {dress_code}
- Theme: {theme}
- RSVP Deadline: {rsvp_deadline}
- Wedding Hashtag: {hashtag}

YOUR ROLE:
You help guests with questions about the wedding — logistics, dress code, venue directions,
parking, accommodation nearby, the program, and general celebration questions.

GUIDELINES:
- Be warm, gracious, and celebratory in tone.
- If you don't know something, say so honestly and suggest the guest contact the couple directly.
- Never invent details not provided above.
- Keep answers concise but complete.
- Use the wedding hashtag naturally in relevant answers.
- If asked about the RSVP, remind them of the deadline and direct them to the RSVP page."""


def chat_completion(
    messages: list[dict],
    wedding_config: dict,
) -> str:
    """
    Get a non-streaming chat completion from gpt-4o-mini.

    Args:
        messages: List of prior conversation messages in OpenAI format
                  (``[{"role": "user"|"assistant", "content": "..."}]``).
        wedding_config: Dict from the ``wedding_config`` DB table to
                        build the system prompt.

    Returns:
        The AI's response as a plain string.

    Raises:
        AIServiceError: On OpenAI API failure.
    """
    try:
        client = _get_client()
        deployment = _get_deployment()

        system_prompt = _build_system_prompt(wedding_config)

        all_messages = [
            {"role": "system", "content": system_prompt},
            *messages[-10:],  # Keep last 10 messages to stay within token budget
        ]

        response = client.chat.completions.create(
            model=deployment,
            messages=all_messages,
            max_completion_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content or ""

    except OpenAIError as exc:
        logger.error("OpenAI API error in chat_completion: %s", exc)
        raise AIServiceError(f"AI service unavailable: {exc}") from exc


def chat_stream(
    messages: list[dict],
    wedding_config: dict,
) -> Generator[str, None, None]:
    """
    Stream a chat completion via Server-Sent Events.

    Yields incremental response chunks as they arrive from the API,
    formatted as SSE ``data: ...`` lines for the browser's EventSource.

    Args:
        messages: Conversation history in OpenAI message format.
        wedding_config: Dict from the ``wedding_config`` table.

    Yields:
        SSE-formatted strings (``"data: <json>\\n\\n"``).
    """
    try:
        client = _get_client()
        deployment = _get_deployment()

        system_prompt = _build_system_prompt(wedding_config)
        all_messages = [
            {"role": "system", "content": system_prompt},
            *messages[-10:],
        ]

        stream = client.chat.completions.create(
            model=deployment,
            messages=all_messages,
            max_completion_tokens=500,
            temperature=0.7,
            stream=True,
        )

        full_response = []
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                token = delta.content
                full_response.append(token)
                # Yield each token as a JSON-encoded SSE event
                yield f"data: {json.dumps({'token': token})}\n\n"

        # Signal stream completion
        yield f"data: {json.dumps({'done': True, 'full': ''.join(full_response)})}\n\n"

    except OpenAIError as exc:
        logger.error("OpenAI API error in chat_stream: %s", exc)
        yield f"data: {json.dumps({'error': 'AI service unavailable'})}\n\n"


def enhance_message(original: str) -> str:
    """
    Rewrite a guestbook message in a poetic, heartfelt tone.

    Args:
        original: The guest's original message text.

    Returns:
        The AI-enhanced message as a string.

    Raises:
        AIServiceError: On OpenAI API failure.
    """
    try:
        client = _get_client()
        deployment = _get_deployment()

        prompt = (
            "You are a poetic wedding speechwriter. Rewrite the following short "
            "guestbook message to be more heartfelt, poetic, and emotionally resonant "
            "while keeping the core sentiment. Keep it under 100 words. "
            "Return only the rewritten message — no explanation, no quotes.\n\n"
            f"Original: {original}"
        )

        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=200,
            temperature=0.85,
        )
        return response.choices[0].message.content or original

    except OpenAIError as exc:
        logger.error("OpenAI API error in enhance_message: %s", exc)
        raise AIServiceError(f"AI service unavailable: {exc}") from exc


def generate_rsvp_confirmation(
    guest_name: str,
    attending: bool,
    wedding_config: dict,
) -> str:
    """
    Generate a personalised RSVP confirmation message.

    Args:
        guest_name: The guest's full name.
        attending: True if the guest is attending.
        wedding_config: Dict from the ``wedding_config`` table.

    Returns:
        A warm personalised confirmation message string.

    Raises:
        AIServiceError: On OpenAI API failure.
    """
    try:
        client = _get_client()
        deployment = _get_deployment()

        couple1 = wedding_config.get("couple_name_1", "the couple")
        couple2 = wedding_config.get("couple_name_2", "their partner")
        date = wedding_config.get("wedding_date", "the big day")

        attendance_context = (
            f"confirming they WILL attend" if attending
            else "letting us know they cannot attend"
        )

        prompt = (
            f"Write a warm, personalised 2-3 sentence RSVP confirmation message for "
            f"{guest_name}, who is {attendance_context} the wedding of {couple1} and "
            f"{couple2} on {date}. Be gracious, celebratory, and specific to their "
            f"attendance decision. Return only the message."
        )

        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content or ""

    except OpenAIError as exc:
        logger.error("OpenAI API error in generate_rsvp_confirmation: %s", exc)
        raise AIServiceError(f"AI service unavailable: {exc}") from exc


def generate_photo_caption(photo_description: str) -> str:
    """
    Generate a romantic caption for a photo based on its description.

    Args:
        photo_description: Short description of the photo content.

    Returns:
        A one-line romantic caption string.

    Raises:
        AIServiceError: On OpenAI API failure.
    """
    try:
        client = _get_client()
        deployment = _get_deployment()

        prompt = (
            "Write a short, romantic, one-line caption for a wedding photo described as: "
            f'"{photo_description}". Return only the caption text, no quotes.'
        )

        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=60,
            temperature=0.8,
        )
        return response.choices[0].message.content or ""

    except OpenAIError as exc:
        logger.error("OpenAI API error in generate_photo_caption: %s", exc)
        raise AIServiceError(f"AI service unavailable: {exc}") from exc
