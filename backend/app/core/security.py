from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt  # type: ignore[import-untyped]
from passlib.context import CryptContext  # type: ignore[import-untyped]

_SECRET = os.getenv("JWT_SECRET", "resilio-dev-secret")
_ALGORITHM = "HS256"
_ACCESS_TTL_MINUTES = int(os.getenv("JWT_ACCESS_TTL_MINUTES", "15"))
_REFRESH_TTL_DAYS = int(os.getenv("JWT_REFRESH_TTL_DAYS", "30"))

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return str(_pwd_context.hash(plain))


def verify_password(plain: str, hashed: str) -> bool:
    return bool(_pwd_context.verify(plain, hashed))


def create_access_token(athlete_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_TTL_MINUTES)
    payload = {"sub": athlete_id, "exp": expire, "jti": secrets.token_hex(8)}
    return str(jwt.encode(payload, _SECRET, algorithm=_ALGORITHM))


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        result: dict[str, Any] = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return result
    except JWTError:
        return None


def generate_token() -> str:
    """Generate a cryptographically secure URL-safe token (32 bytes)."""
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """Hash a raw token with SHA-256 for DB storage. Deterministic — suitable for lookup."""
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_token(raw: str, hashed: str) -> bool:
    """Constant-time comparison of raw token against stored hash."""
    return hmac.compare_digest(hashlib.sha256(raw.encode()).hexdigest(), hashed)
