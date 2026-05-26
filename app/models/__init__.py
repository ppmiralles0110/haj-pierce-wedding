# models package — import all models so Flask-Migrate auto-detects them
from app.models.guest import Guest
from app.models.otp_token import OtpToken
from app.models.wedding_config import WeddingConfig
from app.models.photo import Photo
from app.models.guestbook_message import GuestbookMessage
from app.models.ai_chat_log import AiChatLog

__all__ = [
    "Guest",
    "OtpToken",
    "WeddingConfig",
    "Photo",
    "GuestbookMessage",
    "AiChatLog",
]
