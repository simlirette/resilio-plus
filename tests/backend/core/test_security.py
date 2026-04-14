import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token, generate_token, hash_token, verify_token


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


def test_generate_token_is_urlsafe_string():
    token = generate_token()
    assert isinstance(token, str)
    assert len(token) >= 40  # base64url of 32 bytes = 43 chars


def test_generate_token_is_unique():
    assert generate_token() != generate_token()


def test_hash_token_is_deterministic():
    raw = generate_token()
    assert hash_token(raw) == hash_token(raw)


def test_hash_token_differs_from_raw():
    raw = generate_token()
    assert hash_token(raw) != raw


def test_verify_token_correct():
    raw = generate_token()
    hashed = hash_token(raw)
    assert verify_token(raw, hashed) is True


def test_verify_token_wrong():
    raw = generate_token()
    hashed = hash_token(raw)
    assert verify_token("wrong-token", hashed) is False
