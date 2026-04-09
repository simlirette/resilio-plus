"""
SECURITY — Resilio+
JWT access tokens (PyJWT) + password hashing (pwdlib argon2).
"""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from core.config import settings

_pwd_hash = PasswordHash([Argon2Hasher()])


def hash_password(plain: str) -> str:
    """Hash a plaintext password using argon2."""
    return _pwd_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an argon2 hash."""
    return _pwd_hash.verify(plain, hashed)


def create_access_token(athlete_id: uuid.UUID) -> str:
    """Create a JWT access token with athlete_id as subject."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(athlete_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> uuid.UUID:
    """Decode JWT and return athlete_id. Raises HTTP 401 on any error."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return uuid.UUID(payload["sub"])
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
