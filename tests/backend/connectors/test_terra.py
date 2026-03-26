import json
import pytest
import respx
import httpx
from pathlib import Path
from datetime import date

from app.connectors.terra import TerraConnector
from app.schemas.connector import TerraHealthData

FIXTURES_DIR = Path(__file__).parent / "fixtures"

TERRA_DAILY_URL = "https://api.tryterra.co/v2/daily"


@pytest.fixture
def connector(terra_credential):
    c = TerraConnector(
        terra_credential,
        client_id="test_terra_key",
        client_secret="test_dev_id",
    )
    yield c
    c.close()


@respx.mock
def test_fetch_daily_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "terra_daily.json").read_text())
    respx.get(TERRA_DAILY_URL).mock(return_value=httpx.Response(200, json=fixture))
    result = connector.fetch_daily(date(2026, 3, 20))
    assert isinstance(result, TerraHealthData)
    assert result.hrv_rmssd == pytest.approx(45.2)
    assert result.sleep_duration_hours == pytest.approx(7.5)
    assert result.steps == 8500
    assert result.active_energy_kcal == pytest.approx(450.0)
    assert result.sleep_score == pytest.approx(78.0)


@respx.mock
def test_fetch_daily_missing_hrv_returns_none(connector):
    no_hrv = {
        "status": "ok",
        "data": [{
            "user": {"user_id": "test_terra_user_123"},
            "metadata": {"start_time": "2026-03-20T00:00:00+00:00"},
            "heart_rate_data": {"summary": {}},
            "sleep_durations_data": {"total_sleep_time": 25200},
            "daily_movement": {"steps": 5000, "active_energy_burned_cal": 300.0},
        }]
    }
    respx.get(TERRA_DAILY_URL).mock(return_value=httpx.Response(200, json=no_hrv))
    result = connector.fetch_daily(date(2026, 3, 20))
    assert result.hrv_rmssd is None
    assert result.steps == 5000


@respx.mock
def test_fetch_daily_empty_data_returns_all_none(connector):
    respx.get(TERRA_DAILY_URL).mock(
        return_value=httpx.Response(200, json={"status": "ok", "data": []})
    )
    result = connector.fetch_daily(date(2026, 3, 20))
    assert result.hrv_rmssd is None
    assert result.sleep_duration_hours is None
    assert result.steps is None
    assert result.date == date(2026, 3, 20)
