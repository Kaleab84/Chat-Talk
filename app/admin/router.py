from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import require_admin
from services.supabase_service import SupabaseService


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/allowed-users", dependencies=[Depends(require_admin)])
def list_allowed_users():
    db = SupabaseService()
    return {"items": db.list_allowed_users()}


@router.post("/allowed-users", dependencies=[Depends(require_admin)])
def add_allowed_user(email: str, role: str = "user"):
    if role not in ("user", "admin"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role must be 'user' or 'admin'")
    db = SupabaseService()
    db.add_allowed_user(email, role)
    return {"ok": True}


@router.delete("/allowed-users/{email}", dependencies=[Depends(require_admin)])
def remove_allowed_user(email: str):
    db = SupabaseService()
    db.remove_allowed_user(email)
    return {"ok": True}


@router.get("/users", dependencies=[Depends(require_admin)])
def list_users():
    db = SupabaseService()
    return {"items": db.list_users()}


@router.get("/sessions", dependencies=[Depends(require_admin)])
def list_sessions(active_only: bool = False):
    db = SupabaseService()
    items = db.list_sessions(active_only=active_only)
    return {"items": items}


@router.post("/sessions/{session_id}/revoke", dependencies=[Depends(require_admin)])
def revoke_session(session_id: str):
    db = SupabaseService()
    db.revoke_session(session_id)
    return {"ok": True}


@router.get("/metrics/usage", dependencies=[Depends(require_admin)])
def usage_metrics(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    db = SupabaseService()
    try:
        df = dt.datetime.fromisoformat(date_from) if date_from else None
        dt_to = dt.datetime.fromisoformat(date_to) if date_to else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ISO date format")
    return db.usage_metrics(df, dt_to)

