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
