import hashlib
import hmac
import time
from uuid import UUID

from app.core.config import settings

# Broker login flows redirect the user's raw browser back to our callback
# endpoint, which can't carry an Authorization header -- so those endpoints
# can't use get_current_user_id() like the rest of the app (documented
# exception in docs/project-context.md's Architecture Rules). This signed,
# short-lived token replaces trusting a bare user_id query param: it's
# generated at login-url time and verified at callback time, so a callback
# can't be replayed against a different user or after the login window closes.
_STATE_TTL_SECONDS = 600  # 10 minutes -- enough to complete a broker login


def sign_state(user_id: UUID) -> str:
    expires_at = int(time.time()) + _STATE_TTL_SECONDS
    payload = f"{user_id}:{expires_at}"
    signature = hmac.new(
        settings.OAUTH_STATE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def verify_state(state: str) -> UUID:
    """Raises ValueError if the token is malformed, tampered with, or expired."""
    parts = state.split(":")
    if len(parts) != 3:
        raise ValueError("Malformed state parameter.")
    user_id_str, expires_at_str, signature = parts

    payload = f"{user_id_str}:{expires_at_str}"
    expected_signature = hmac.new(
        settings.OAUTH_STATE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid state parameter signature.")

    try:
        expires_at = int(expires_at_str)
    except ValueError:
        raise ValueError("Malformed state parameter.")
    if expires_at < int(time.time()):
        raise ValueError("State parameter has expired. Please reconnect.")

    try:
        return UUID(user_id_str)
    except ValueError:
        raise ValueError("Malformed state parameter.")
