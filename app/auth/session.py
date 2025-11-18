from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from app.config import settings


def create_session(user_id: str, ttl_days: int) -> Tuple[str, datetime]:
    """Generate a new opaque session identifier and expiry timestamp."""
    _ = user_id  # reserved for future linkage logic
    session_id = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
    return session_id, expires_at


def _get_secret() -> bytes:
    if not settings.SESSION_SECRET:
        raise RuntimeError("SESSION_SECRET is required for signing session cookies.")
    return settings.SESSION_SECRET.encode("utf-8")


def sign_session_cookie(session_id: str) -> str:
    """Produce a cookie payload `session_id:issued_at:signature` with HMAC SHA256."""
    issued_at = int(datetime.now(timezone.utc).timestamp())
    payload = f"{session_id}:{issued_at}"
    signature = hmac.new(_get_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_session_cookie(cookie_value: Optional[str]) -> Optional[str]:
    """Return the session_id when signature is valid; otherwise None."""
    if not cookie_value:
        return None
    parts = cookie_value.split(":")
    if len(parts) != 3:
        return None
    session_id, issued_at, signature = parts
    payload = f"{session_id}:{issued_at}"
    expected = hmac.new(_get_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    return session_id
