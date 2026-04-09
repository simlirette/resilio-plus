"""Tests for core/security.py — JWT + password hashing."""
import uuid

import pytest
from fastapi import HTTPException

from core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    """hash_password → verify_password round-trip returns True."""
    plain = "MySecretP@ssw0rd"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_wrong_password():
    """verify_password with wrong plain text returns False."""
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_access_token():
    """create_access_token → decode_access_token round-trip returns same UUID."""
    athlete_id = uuid.uuid4()
    token = create_access_token(athlete_id)
    decoded = decode_access_token(token)
    assert decoded == athlete_id


def test_decode_invalid_token_raises_401():
    """decode_access_token with garbage token raises HTTPException 401."""
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("garbage.token.value")
    assert exc_info.value.status_code == 401
