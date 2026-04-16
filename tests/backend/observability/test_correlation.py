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
