from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth.dependencies import get_current_user, require_user
from app.auth.schemas import ExchangeTokenRequest, RequestMagicLinkRequest, UserOut
from app.auth.session import create_session as generate_session
from app.auth.session import sign_session_cookie
from app.config import settings
from app.services import supabase_service

router = APIRouter()


@router.post("/request-link", status_code=status.HTTP_202_ACCEPTED)
async def request_magic_link(payload: RequestMagicLinkRequest):
    allowed = supabase_service.get_allowed_user(payload.email)
    if not allowed or allowed.get("status") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email is not allowed to access this app.")

    supabase_url, supabase_key = _get_supabase_credentials()
    body = {
        "email": payload.email,
        "create_user": False,
        "redirect_to": f"{settings.FRONTEND_BASE_URL.rstrip('/')}/auth/callback",
    }
    headers = {
        "apikey": supabase_key,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{supabase_url}/auth/v1/magiclink", headers=headers, json=body)
    if resp.status_code >= 400:
        detail = resp.json().get("error_description") if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to request magic link: {detail}")
    return {"message": "Magic link sent."}


@router.post("/exchange", response_model=UserOut)
async def exchange_token(payload: ExchangeTokenRequest, request: Request, response: Response):
    supabase_url, supabase_key = _get_supabase_credentials()
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {payload.access_token}",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{supabase_url}/auth/v1/user", headers=headers)
    if resp.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired Supabase token.")
    user_data = resp.json()
    email = user_data.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supabase user payload missing email.")

    allowed = supabase_service.get_allowed_user(email)
    if not allowed or allowed.get("status") != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email is not authorized.")

    role = allowed.get("role") or user_data.get("role") or "user"
    user_row = supabase_service.upsert_user(user_data.get("id"), email, role)
    if not user_row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to persist user.")

    session_id, expires_at = generate_session(str(user_row.get("id")), settings.SESSION_TTL_DAYS)
    supabase_service.create_session(
        user_id=str(user_row.get("id")),
        expires_at=expires_at,
        ip=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        session_id=session_id,
    )
    cookie_value = sign_session_cookie(session_id)
    max_age = settings.SESSION_TTL_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=cookie_value,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=max_age,
        expires=expires_at,
        path="/",
    )
    return UserOut(id=str(user_row.get("id")), email=email, role=role)


@router.get("/me", response_model=UserOut)
async def auth_me(user=Depends(require_user)):
    return UserOut(id=str(user.id), email=user.email, role=user.role)


@router.post("/logout")
async def logout(request: Request, response: Response, user=Depends(get_current_user)):
    _ = user
    session_id = getattr(request.state, "session_id", None)
    if session_id:
        supabase_service.revoke_session(session_id)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value="",
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=0,
        expires=0,
    )
    return {"message": "Logged out"}


def _get_supabase_credentials() -> tuple[str, str]:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase is not configured.")
    return settings.SUPABASE_URL.rstrip("/"), settings.SUPABASE_ANON_KEY


def _get_client_ip(request: Request) -> str:
    client = request.client
    return client.host if client else "unknown"
