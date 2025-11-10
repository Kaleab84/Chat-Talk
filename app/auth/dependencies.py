from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status


def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_user(user=Depends(get_current_user)):
    return user


def require_admin(user=Depends(get_current_user)):
    role = (user or {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

