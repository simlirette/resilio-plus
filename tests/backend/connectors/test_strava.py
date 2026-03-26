import json
import pytest
import respx
import httpx
from pathlib import Path
from datetime import datetime, timezone, date

from app.connectors.strava import StravaConnector
from app.schemas.connector import ConnectorCredential, StravaActivity, StravaLap

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def connector(strava_credential):
    c = StravaConnector(
        strava_credential,
        client_id="test_client_id",
        client_secret="test_client_secret",
    )
    yield c
    c.close()


def test_get_auth_url_contains_scope_and_client_id(connector):
    url = connector.get_auth_url()
    assert "activity:read_all" in url
    assert "profile:read_all" in url
    assert "test_client_id" in url
    assert "response_type=code" in url


@respx.mock
def test_exchange_code_returns_populated_credential(connector):
    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_at": 9999999999,
            "athlete": {"id": 12345},
        })
    )
    cred = connector.exchange_code("auth_code_123")
    assert cred.access_token == "new_access"
    assert cred.refresh_token == "new_refresh"
    assert cred.expires_at == 9999999999


@respx.mock
def test_fetch_activities_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "strava_activities.json").read_text())
    respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        side_effect=[
            httpx.Response(200, json=fixture),
            httpx.Response(200, json=[]),  # second page empty — stops pagination
        ]
    )
    since = datetime(2026, 3, 1, tzinfo=timezone.utc)
    until = datetime(2026, 3, 31, tzinfo=timezone.utc)
    activities = connector.fetch_activities(since, until)
    assert len(activities) == 2
    assert isinstance(activities[0], StravaActivity)
    assert activities[0].id == "strava_11111111111"
    assert activities[0].sport_type == "Run"
    assert activities[0].date == date(2026, 3, 20)
    assert activities[1].id == "strava_22222222222"
    assert activities[1].perceived_exertion is None


@respx.mock
def test_fetch_activity_laps_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "strava_laps.json").read_text())
    respx.get("https://www.strava.com/api/v3/activities/11111111111/laps").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    laps = connector.fetch_activity_laps("11111111111")
    assert len(laps) == 2
    assert isinstance(laps[0], StravaLap)
    assert laps[0].lap_index == 1
    assert laps[0].distance_meters == 1000.0
    assert laps[0].pace_per_km is not None  # computed from average_speed


@respx.mock
def test_fetch_activity_laps_returns_empty_on_404(connector):
    respx.get("https://www.strava.com/api/v3/activities/99999/laps").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    laps = connector.fetch_activity_laps("99999")
    assert laps == []
