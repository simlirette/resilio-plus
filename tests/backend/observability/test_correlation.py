from app.observability.correlation import (
    correlation_id_ctx,
    athlete_id_ctx,
    get_correlation_id,
    get_athlete_id,
)


def test_correlation_id_default():
    assert get_correlation_id() == "-"


def test_correlation_id_set_and_get():
    token = correlation_id_ctx.set("abc-123")
    try:
        assert get_correlation_id() == "abc-123"
    finally:
        correlation_id_ctx.reset(token)
    assert get_correlation_id() == "-"


def test_athlete_id_default_none():
    assert get_athlete_id() is None


def test_athlete_id_set_and_get():
    token = athlete_id_ctx.set("uuid-xyz")
    try:
        assert get_athlete_id() == "uuid-xyz"
    finally:
        athlete_id_ctx.reset(token)
    assert get_athlete_id() is None


import re
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.observability.correlation import (
    CorrelationIdMiddleware,
    correlation_id_ctx,
)


def _make_app():
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"cid": correlation_id_ctx.get()}

    return app


def test_middleware_generates_uuid_when_header_missing():
    client = TestClient(_make_app())
    response = client.get("/ping")
    cid = response.headers["X-Request-ID"]
    # UUID4 is 36 chars with hyphens
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", cid)
    assert response.json()["cid"] == cid


def test_middleware_echoes_valid_header():
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-ID": "my-trace-id-42"})
    assert response.headers["X-Request-ID"] == "my-trace-id-42"
    assert response.json()["cid"] == "my-trace-id-42"


def test_middleware_regenerates_invalid_header():
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-ID": "bad id with spaces!@#"})
    cid = response.headers["X-Request-ID"]
    assert cid != "bad id with spaces!@#"
    assert re.match(r"^[0-9a-f-]+$", cid)


def test_middleware_regenerates_oversized_header():
    client = TestClient(_make_app())
    response = client.get("/ping", headers={"X-Request-ID": "x" * 200})
    cid = response.headers["X-Request-ID"]
    assert cid != "x" * 200


def test_middleware_resets_contextvar_between_requests():
    client = TestClient(_make_app())
    r1 = client.get("/ping", headers={"X-Request-ID": "first"})
    r2 = client.get("/ping")
    assert r1.headers["X-Request-ID"] == "first"
    assert r2.headers["X-Request-ID"] != "first"
