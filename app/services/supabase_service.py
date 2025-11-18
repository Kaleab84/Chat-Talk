from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger(__name__)
_client: Optional[Client] = None


def _get_client() -> Client:
    global _client
    if _client is None:
        if not settings.SUPABASE_URL:
            raise RuntimeError("SUPABASE_URL is not configured.")
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        if not key:
            raise RuntimeError("Supabase key is not configured.")
        _client = create_client(settings.SUPABASE_URL, key)
    return _client


def get_allowed_user(email: str) -> Optional[Dict[str, Any]]:
    try:
        response = (
            _get_client()
            .table("allowed_users")
            .select("*")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None
    except Exception as exc:
        logger.error("Failed to fetch allowed_user for %s: %s", email, exc)
        return None


def upsert_user(user_id: str, email: str, role: str) -> Optional[Dict[str, Any]]:
    payload = {"id": user_id, "email": email, "role": role}
    try:
        response = (
            _get_client()
            .table("users")
            .upsert(payload, on_conflict="email")
            .select("*")
            .execute()
        )
        data = response.data or []
        return data[0] if data else payload
    except Exception as exc:
        logger.error("Failed to upsert user %s: %s", email, exc)
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        response = (
            _get_client()
            .table("users")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None
    except Exception as exc:
        logger.error("Failed to load user %s: %s", user_id, exc)
        return None


def create_session(
    user_id: str,
    expires_at: datetime,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "expires_at": expires_at.isoformat(),
    }
    if session_id:
        payload["id"] = session_id
    if ip:
        payload["ip_address"] = ip
    if user_agent:
        payload["user_agent"] = user_agent[:255]
    try:
        response = (
            _get_client()
            .table("sessions")
            .insert(payload)
            .select("*")
            .execute()
        )
        data = response.data or []
        return data[0] if data else payload
    except Exception as exc:
        logger.error("Failed to create session for %s: %s", user_id, exc)
        return None


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        response = (
            _get_client()
            .table("sessions")
            .select("*")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )
        data = response.data or []
        return data[0] if data else None
    except Exception as exc:
        logger.error("Failed to load session %s: %s", session_id, exc)
        return None


def revoke_session(session_id: str) -> bool:
    try:
        (
            _get_client()
            .table("sessions")
            .update({"revoked_at": datetime.utcnow().isoformat()})
            .eq("id", session_id)
            .execute()
        )
        return True
    except Exception as exc:
        logger.error("Failed to revoke session %s: %s", session_id, exc)
        return False
