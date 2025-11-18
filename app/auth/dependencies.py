from __future__ import annotations
from fastapi import Depends, HTTPException, Request, status


HTTP_401 = 401
HTTP_403 = 403


def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=HTTP_401, detail="Authentication required.")
    return user


def require_user(user=Depends(get_current_user)):
    return user


def require_admin(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "admin":
        raise HTTPException(status_code=HTTP_403, detail="Admin access required.")
    return user
