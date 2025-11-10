from __future__ import annotations

from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.session import COOKIE_NAME, SessionCookie
from app.services.supabase_service import SupabaseService


PUBLIC_PATH_PREFIXES = (
    "/auth/",  # auth routes
    "/docs", 
    "/openapi.json",
    "/",  # allow root (adjust if you need)
)


def _is_public_path(path: str) -> bool:
    if path == "/":
        return True
    return any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.db = SupabaseService()

    async def dispatch(self, request: Request, call_next):
        # Default: unauthenticated
        request.state.user = None

        path = request.url.path
        if _is_public_path(path):
            return await call_next(request)

        cookie_val: Optional[str] = request.cookies.get(COOKIE_NAME)
        if not cookie_val:
            return await call_next(request)

        parsed = SessionCookie.parse_and_verify(cookie_val)
        if not parsed:
            return await call_next(request)

        # Load session from DB and validate
        session = self.db.get_session_by_id(parsed.session_id)
        if not session or session.get("revoked"):
            return await call_next(request)

        # Expiration check (server-side)
        expires_at = session.get("expires_at")
        # If expires_at exists and is in the past, treat as invalid
        try:
            import datetime as _dt
            if expires_at and _dt.datetime.fromisoformat(str(expires_at).replace("Z", "+00:00")) < _dt.datetime.now(_dt.timezone.utc):
                return await call_next(request)
        except Exception:
            pass

        user = self.db.get_user_by_id(session.get("user_id")) if session else None
        if user:
            request.state.user = {
                "id": user.get("id"),
                "email": user.get("email"),
                "role": user.get("role", "user"),
            }

            # async best-effort update last_seen
            try:
                self.db.touch_session(parsed.session_id)
            except Exception:
                pass

        response = await call_next(request)
        return response
