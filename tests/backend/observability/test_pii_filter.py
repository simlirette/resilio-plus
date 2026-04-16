from app.observability.pii_filter import scrub_value

BLOCKLIST_FIELDS = [
    "password", "passwd", "token", "access_token", "refresh_token",
    "authorization", "auth", "api_key", "apikey", "secret",
    "fernet_key", "encryption_key", "smtp_password", "jwt", "bearer",
    "client_secret", "cookie",
]


def test_scrubs_flat_blocklisted_field():
    payload = {"password": "hunter2", "username": "alice"}
    result = scrub_value(payload)
    assert result["password"] == "***"
    assert result["username"] == "alice"


def test_scrubs_case_insensitive():
    payload = {"Password": "hunter2", "API_KEY": "abc", "Authorization": "xyz"}
    result = scrub_value(payload)
    assert result["Password"] == "***"
    assert result["API_KEY"] == "***"
    assert result["Authorization"] == "***"


def test_scrubs_nested_dict():
    payload = {"user": {"email": "a@b.com", "token": "secret"}}
    result = scrub_value(payload)
    assert result["user"]["token"] == "***"


def test_scrubs_list_of_dicts():
    payload = {"items": [{"password": "a"}, {"password": "b"}]}
    result = scrub_value(payload)
    assert result["items"][0]["password"] == "***"
    assert result["items"][1]["password"] == "***"


def test_preserves_legitimate_fields():
    payload = {"username": "alice", "athlete_id": "uuid-1", "path": "/api"}
    result = scrub_value(payload)
    assert result == payload


def test_all_blocklist_fields_scrubbed():
    for field in BLOCKLIST_FIELDS:
        payload = {field: "leak"}
        assert scrub_value(payload)[field] == "***", f"{field} not scrubbed"


from app.observability.pii_filter import scrub_string


def test_scrubs_jwt_in_string():
    s = "token is eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NSJ9.SflKxwRJSMeKKF2QT4"
    assert "eyJ" not in scrub_string(s)
    assert "***" in scrub_string(s)


def test_scrubs_bearer_token():
    s = "Authorization: Bearer abc123def456"
    assert "abc123def456" not in scrub_string(s)
    assert "***" in scrub_string(s)


def test_scrubs_email():
    s = "failed login for user alice@example.com"
    out = scrub_string(s)
    assert "alice@example.com" not in out
    assert "***" in out


def test_scrubs_long_hex_string():
    s = "fernet key: " + "a" * 32
    out = scrub_string(s)
    assert "a" * 32 not in out
    assert "***" in out


def test_preserves_short_hex():
    # short hex like "abc123" should NOT match
    s = "version abc123 deployed"
    assert scrub_string(s) == s


def test_scrub_value_applies_regex_to_string_values():
    payload = {"msg": "user a@b.com logged in"}
    result = scrub_value(payload)
    assert "a@b.com" not in result["msg"]


def test_scrub_idempotent():
    s = "user a@b.com token eyJabc.def.ghi"
    once = scrub_string(s)
    twice = scrub_string(once)
    assert once == twice


import logging
from app.observability.pii_filter import PIIFilter


def _make_record(msg: str, extra: dict | None = None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=None,
        exc_info=None,
    )
    if extra:
        for k, v in extra.items():
            setattr(record, k, v)
    return record


def test_pii_filter_scrubs_msg():
    f = PIIFilter()
    record = _make_record("user a@b.com logged in")
    assert f.filter(record) is True
    assert "a@b.com" not in record.getMessage()


def test_pii_filter_scrubs_extra_dict():
    f = PIIFilter()
    record = _make_record("event", extra={"user": {"password": "secret"}})
    f.filter(record)
    assert record.user["password"] == "***"


def test_pii_filter_returns_true_always():
    f = PIIFilter()
    record = _make_record("hello")
    assert f.filter(record) is True
