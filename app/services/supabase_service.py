from __future__ import annotations

import datetime as dt
import os
from typing import Any, Dict, List, Optional

try:
    from supabase import create_client, Client  # type: ignore
except Exception:  # pragma: no cover
    create_client = None  # type: ignore
    Client = None  # type: ignore


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class SupabaseService:
    """Thin wrapper over Supabase for app-local tables.

    Requires tables: allowed_users, users, sessions, interactions.
    For local development, configure RLS appropriately or use a service role key.
    """

    def __init__(self) -> None:
        if not SUPABASE_URL or not (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY):
            self.client = None
        else:
            key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY  # prefer service role for write access
            assert create_client is not None
            self.client: Optional[Client] = create_client(SUPABASE_URL, key)

    # ---------- Allowed Users ----------
    def is_email_allowed(self, email: str) -> bool:
        if not self.client:
            # Local dev fallback: allow everything if no Supabase configured
            return True
        res = self.client.table("allowed_users").select("email,status").eq("email", email.lower()).maybe_single().execute()
        item = (res.data or {}) if isinstance(res.data, dict) else (res.data[0] if res.data else None)
        if not item:
            return False
        return (item.get("status") or "active") == "active"

    def add_allowed_user(self, email: str, role: str = "user") -> None:
        if not self.client:
            return
        email = email.lower()
        # upsert based on email
        self.client.table("allowed_users").upsert({"email": email, "role": role, "status": "active"}, on_conflict="email").execute()

    def remove_allowed_user(self, email: str) -> None:
        if not self.client:
            return
        self.client.table("allowed_users").delete().eq("email", email.lower()).execute()

    def list_allowed_users(self) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        res = self.client.table("allowed_users").select("email,role,status,created_at").order("created_at", desc=True).execute()
        return res.data or []

    # ---------- Users ----------
    def upsert_user(self, user_id: str, email: str) -> Dict[str, Any]:
        if not self.client:
            return {"id": user_id, "email": email, "role": "user"}
        email_l = email.lower()
        # Determine role from allowed_users if present
        role = "user"
        try:
            allowed = self.client.table("allowed_users").select("email,role").eq("email", email_l).maybe_single().execute()
            item = (allowed.data or {}) if isinstance(allowed.data, dict) else (allowed.data[0] if allowed.data else None)
            if item and item.get("role") in ("user", "admin"):
                role = item.get("role")
        except Exception:
            pass

        self.client.table("users").upsert({"id": user_id, "email": email_l, "role": role}, on_conflict="id").execute()
        return {"id": user_id, "email": email_l, "role": role}

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return {"id": user_id, "email": "local@example.com", "role": "user"}
        res = self.client.table("users").select("id,email,role").eq("id", user_id).maybe_single().execute()
        data = res.data
        if isinstance(data, list):
            data = data[0] if data else None
        return data

    def list_users(self) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        res = self.client.table("users").select("id,email,role,created_at").order("created_at", desc=True).execute()
        return res.data or []

    # ---------- Sessions ----------
    def create_session(self, session_id: str, user_id: str, expires_at: dt.datetime, ip: Optional[str], user_agent: Optional[str]) -> None:
        if not self.client:
            return
        self.client.table("sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "expires_at": expires_at.isoformat(),
            "ip": ip,
            "user_agent": user_agent,
            "revoked": False,
        }).execute()

    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        res = self.client.table("sessions").select("id,user_id,expires_at,revoked").eq("id", session_id).maybe_single().execute()
        data = res.data
        if isinstance(data, list):
            data = data[0] if data else None
        return data

    def touch_session(self, session_id: str) -> None:
        if not self.client:
            return
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        self.client.table("sessions").update({"last_seen": now}).eq("id", session_id).execute()

    def revoke_session(self, session_id: str) -> None:
        if not self.client:
            return
        self.client.table("sessions").update({"revoked": True}).eq("id", session_id).execute()

    def list_sessions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        q = self.client.table("sessions").select("id,user_id,created_at,expires_at,last_seen,revoked,ip,user_agent").order("created_at", desc=True)
        if active_only:
            q = q.eq("revoked", False)
        return q.execute().data or []

    # ---------- Interactions ----------
    def record_interaction(self, user_id: Optional[str], route: str, status: str, duration_ms: Optional[int] = None, tokens_used: Optional[int] = None, meta: Optional[dict] = None) -> None:
        if not self.client:
            return
        payload = {
            "user_id": user_id,
            "route": route,
            "status": status,
            "duration_ms": duration_ms,
            "tokens_used": tokens_used,
            "meta": meta or {},
        }
        self.client.table("interactions").insert(payload).execute()

    def usage_metrics(self, date_from: Optional[dt.datetime], date_to: Optional[dt.datetime]) -> Dict[str, Any]:
        if not self.client:
            return {"total": 0, "by_route": []}
        data = self.client.table("interactions").select("id,route,created_at").execute().data or []
        if date_from or date_to:
            def _in_range(ts: str) -> bool:
                try:
                    t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    return True
                if date_from and t < date_from:
                    return False
                if date_to and t > date_to:
                    return False
                return True
            data = [row for row in data if _in_range(str(row.get("created_at")))]
        by_route: Dict[str, int] = {}
        for row in data:
            r = row.get("route") or "unknown"
            by_route[r] = by_route.get(r, 0) + 1
        items = [{"route": k, "count": v} for k, v in sorted(by_route.items(), key=lambda x: x[1], reverse=True)]
        return {"total": len(data), "by_route": items}

