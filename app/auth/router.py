from __future__ import annotations

import os
import uuid
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from app.auth.schemas import (
    RequestLinkPayload,
    ExchangePayload,
    AuthMeResponse,
    AuthUser,
    MessageResponse,
)
from app.auth.providers import supabase as sb_auth
from app.auth.session import SessionCookie, build_cookie_header, build_clear_cookie_header
from app.auth.dependencies import require_user
from app.services.supabase_service import SupabaseService


router = APIRouter(prefix="/auth", tags=["auth"])


FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")


@router.post("/request-link", response_model=MessageResponse)
def request_link(payload: RequestLinkPayload):
    email = payload.email
    redirect_to = payload.redirect_to or f"{FRONTEND_BASE_URL.rstrip('/')}/auth/callback"

    db = SupabaseService()
    allowed = db.is_email_allowed(email)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email is not allowlisted")

    try:
        sb_auth.request_magic_link(email=email, redirect_to=redirect_to)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to send magic link: {exc}")

    return MessageResponse(ok=True, message="Magic link sent if email is registered.")


@router.post("/exchange", response_model=AuthUser)
def exchange_token(response: Response, payload: ExchangePayload, request: Request):
    access_token = payload.access_token
    db = SupabaseService()

    try:
        user_info = sb_auth.verify_access_token(access_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}")

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token lacks email")

    if not db.is_email_allowed(email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email is not allowlisted")

    # Upsert local user mirror
    user = db.upsert_user(user_id=user_info.get("id"), email=email)

    # Create a new session (rotate)
    now = dt.datetime.now(dt.timezone.utc)
    ttl_days = int(os.getenv("SESSION_TTL_DAYS", "7"))
    expires_at = now + dt.timedelta(days=ttl_days)
    session_id = str(uuid.uuid4())
    db.create_session(
        session_id=session_id,
        user_id=user["id"],
        expires_at=expires_at,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    cookie_value = SessionCookie.create(session_id=session_id)
    header_name, header_val = build_cookie_header(cookie_value)
    response.headers.append(header_name, header_val)

    return AuthUser(id=user["id"], email=user["email"], role=user.get("role", "user"))


@router.get("/me", response_model=AuthMeResponse)
def me(user=Depends(require_user)):
    return AuthMeResponse(authenticated=True, user=AuthUser(**user))


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response, user=Depends(require_user), request: Request = None):
    # Revoke current session if present
    db = SupabaseService()
    cookie_val = request.cookies.get(os.getenv("SESSION_COOKIE_NAME", "CFC_SESSION")) if request else None
    if cookie_val:
        parsed = SessionCookie.parse_and_verify(cookie_val)
        if parsed:
            try:
                db.revoke_session(parsed.session_id)
            except Exception:
                pass
    header_name, header_val = build_clear_cookie_header()
    response.headers.append(header_name, header_val)
    return MessageResponse(ok=True, message="Logged out")
