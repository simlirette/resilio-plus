import time
import pytest
import respx
import httpx
from tenacity import wait_none

from app.schemas.connector import ConnectorCredential
from app.connectors.base import (
    BaseConnector,
    ConnectorAPIError,
    ConnectorAuthError,
    ConnectorRateLimitError,
)


class FakeConnector(BaseConnector):
    """Test subclass: no-op refresh, instant retry (no sleep)."""
    provider = "fake"
    _retry_wait = wait_none()

    def _do_refresh_token(self) -> ConnectorCredential:
        return self.credential.model_copy(update={
            "access_token": "refreshed_token",
            "expires_at": int(time.time()) + 3600,
        })


@pytest.fixture
def cred():
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="fake",
        access_token="test_token",
        expires_at=int(time.time()) + 3600,
    )


@pytest.fixture
def connector(cred):
    c = FakeConnector(cred, client_id="cid", client_secret="csecret")
    yield c
    c.close()


TEST_URL = "https://api.fake.test/endpoint"


@respx.mock
def test_retry_succeeds_on_third_attempt(connector):
    route = respx.get(TEST_URL).mock(
        side_effect=[
            httpx.Response(500, json={"error": "server error"}),
            httpx.Response(500, json={"error": "server error"}),
            httpx.Response(200, json={"data": "ok"}),
        ]
    )
    result = connector._request("GET", TEST_URL)
    assert result == {"data": "ok"}
    assert route.call_count == 3


@respx.mock
def test_exhausted_retries_raises_connector_api_error(connector):
    respx.get(TEST_URL).mock(return_value=httpx.Response(500, json={"error": "fail"}))
    with pytest.raises(ConnectorAPIError):
        connector._request("GET", TEST_URL)


@respx.mock
def test_429_raises_rate_limit_immediately(connector):
    route = respx.get(TEST_URL).mock(
        return_value=httpx.Response(429, headers={"Retry-After": "30"}, json={})
    )
    with pytest.raises(ConnectorRateLimitError) as exc_info:
        connector._request("GET", TEST_URL)
    assert exc_info.value.retry_after == 30
    assert route.call_count == 1  # not retried


@respx.mock
def test_429_missing_retry_after_defaults_to_60(connector):
    respx.get(TEST_URL).mock(
        return_value=httpx.Response(429, json={})  # no Retry-After header
    )
    with pytest.raises(ConnectorRateLimitError) as exc_info:
        connector._request("GET", TEST_URL)
    assert exc_info.value.retry_after == 60


@respx.mock
def test_401_raises_auth_error(connector):
    respx.get(TEST_URL).mock(return_value=httpx.Response(401, json={"error": "unauthorized"}))
    with pytest.raises(ConnectorAuthError):
        connector._request("GET", TEST_URL)


def test_get_valid_token_no_refresh_when_valid(connector):
    original_token = connector.credential.access_token
    token = connector.get_valid_token()
    assert token == original_token


def test_get_valid_token_refreshes_when_expired(cred):
    expired_cred = cred.model_copy(update={"expires_at": int(time.time()) - 100})
    c = FakeConnector(expired_cred, client_id="cid", client_secret="csecret")
    token = c.get_valid_token()
    assert token == "refreshed_token"
    c.close()


def test_context_manager_closes_client(cred):
    with FakeConnector(cred, client_id="cid", client_secret="csecret") as c:
        client = c._client
    assert client.is_closed
