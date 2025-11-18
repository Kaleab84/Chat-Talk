from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.auth.session import verify_session_cookie
from app.config import settings
from app.services import supabase_service


@dataclass
class AuthenticatedUser:
    id: str
    email: str
    role: str


class AuthMiddleware(BaseHTTPMiddleware):
    """Attach request.state.user when a valid session cookie is present."""

    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        request.state.session_id = None

        cookie_value = request.cookies.get(settings.SESSION_COOKIE_NAME)
        session_id = verify_session_cookie(cookie_value)

        if session_id:
            session_row = supabase_service.get_session(session_id)
            if self._is_session_active(session_row):
                user = supabase_service.get_user_by_id(session_row["user_id"])
                if user:
                    request.state.user = AuthenticatedUser(
                        id=str(user.get("id")),
                        email=user.get("email"),
                        role=user.get("role", "user"),
                    )
                    request.state.session_id = session_id

        response = await call_next(request)
        return response

    def _is_session_active(self, session_row: Optional[dict]) -> bool:
        if not session_row:
            return False
        if session_row.get("revoked_at"):
            return False
        expires_at = _parse_datetime(session_row.get("expires_at"))
        if not expires_at:
            return False
        return expires_at > datetime.now(timezone.utc)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None
