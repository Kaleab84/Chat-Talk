"""
Supabase GoTrue provider for magic links and access token verification.

This module talks directly to Supabase GoTrue endpoints using the public anon key.
For local development, ensure SUPABASE_URL and SUPABASE_ANON_KEY are set.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, Optional


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")


class SupabaseAuthError(RuntimeError):
    pass


def _require_env():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise SupabaseAuthError("Supabase auth not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.")


def _headers(include_bearer: Optional[str] = None) -> Dict[str, str]:
    headers = {
        "apikey": SUPABASE_ANON_KEY or "",
        "Content-Type": "application/json",
    }
    if include_bearer:
        headers["Authorization"] = f"Bearer {include_bearer}"
    else:
        headers["Authorization"] = f"Bearer {SUPABASE_ANON_KEY}"
    return headers


def request_magic_link(email: str, redirect_to: Optional[str] = None) -> Dict[str, Any]:
    """Request a magic link to be emailed to the given address.

    Uses GoTrue endpoint: POST /auth/v1/otp
    Body: { email, type: 'magiclink', create_user: false, (optional) redirect_to }
    """
    _require_env()
    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/otp"
    payload: Dict[str, Any] = {
        "email": email,
        "type": "magiclink",
        "create_user": False,
    }
    if redirect_to:
        payload["redirect_to"] = redirect_to

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return {"ok": True, "status": resp.status, "body": body or None}
    except Exception as exc:
        raise SupabaseAuthError(f"Failed to request magic link: {exc}")


def verify_access_token(access_token: str) -> Dict[str, Any]:
    """Verify a Supabase access token and return user info.

    Calls GoTrue endpoint: GET /auth/v1/user with Authorization: Bearer <access_token>
    """
    _require_env()
    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/user"
    req = urllib.request.Request(url, headers=_headers(include_bearer=access_token), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body) if body else {}
            if not isinstance(data, dict) or not data.get("id"):
                raise SupabaseAuthError("Invalid user response from Supabase.")
            # Normalize shape
            user = {
                "id": data.get("id"),
                "email": (data.get("email") or (data.get("user_metadata") or {}).get("email")),
                "raw": data,
            }
            return user
    except Exception as exc:
        raise SupabaseAuthError(f"Failed to verify access token: {exc}")

