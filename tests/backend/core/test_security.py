import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


def test_hash_password_returns_different_string():
    hashed = hash_password("mysecret")
    assert hashed != "mysecret"
    assert len(hashed) > 20


def test_verify_password_correct():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("mysecret")
    assert verify_password("wrongpass", hashed) is False


def test_create_and_decode_token_round_trip():
    token = create_access_token(athlete_id="athlete-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "athlete-123"


def test_decode_invalid_token_returns_none():
    result = decode_access_token("not.a.valid.token")
    assert result is None


def test_decode_tampered_token_returns_none():
    token = create_access_token(athlete_id="athlete-123")
    tampered = token[:-5] + "XXXXX"
    result = decode_access_token(tampered)
    assert result is None
