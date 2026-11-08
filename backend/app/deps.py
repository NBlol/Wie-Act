"""Shared request dependencies."""
from __future__ import annotations

from app.compat import Depends, HTTPException, Request, status
from app.db import Connection, get_db
from app.security import decode_access_token
from app.services.users import serialize_user, touch_activity

__all__ = ["get_db", "get_current_user", "require_teacher", "Connection"]


def _bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    return auth.split(" ", 1)[1].strip() or None


def get_current_user(request: Request, db: Connection = Depends(get_db)) -> dict:
    token = _bearer_token(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.fetchone("SELECT * FROM users WHERE id = ?", (payload["sub"],))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    touch_activity(db, user)
    return user


def require_teacher(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "teacher":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Teacher role required")
    return user


def public_user(user: dict) -> dict:
    return serialize_user(user)
