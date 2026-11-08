"""Password hashing and JWT helpers.

Passwords are hashed with `hashlib.scrypt` (memory-hard KDF from the Python
standard library, per-user random salt). No third-party dependency is
required; `bcrypt` would be an equivalent choice.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import typing as t
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    return "scrypt$%d$%d$%d$%s$%s" % (
        _SCRYPT_N,
        _SCRYPT_R,
        _SCRYPT_P,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, role: str, minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes or settings.access_token_minutes)
    payload: dict[str, t.Any] = {"sub": user_id, "role": role, "exp": expire, "iat": datetime.now(timezone.utc), "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access" or not payload.get("sub"):
        return None
    return payload
