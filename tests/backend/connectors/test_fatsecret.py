import json
import pytest
import respx
import httpx
from pathlib import Path
from datetime import date

from app.connectors.fatsecret import FatSecretConnector
from app.schemas.connector import FatSecretDay

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FATSECRET_API_URL = "https://platform.fatsecret.com/rest/server.api"
FATSECRET_TOKEN_URL = "https://oauth.fatsecret.com/connect/token"


@pytest.fixture
def connector(fatsecret_credential):
    c = FatSecretConnector(
        fatsecret_credential,
        client_id="test_fs_id",
        client_secret="test_fs_secret",
    )
    yield c
    c.close()


@respx.mock
def test_do_refresh_token_fetches_new_bearer(fatsecret_credential):
    respx.post(FATSECRET_TOKEN_URL).mock(
        return_value=httpx.Response(200, json={
            "access_token": "new_bearer_token",
            "expires_in": 86400,
            "token_type": "Bearer",
        })
    )
    c = FatSecretConnector(fatsecret_credential, client_id="cid", client_secret="csecret")
    updated_cred = c._do_refresh_token()
    assert updated_cred.access_token == "new_bearer_token"
    c.close()


@respx.mock
def test_fetch_food_entries_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "fatsecret_day.json").read_text())
    respx.get(FATSECRET_API_URL).mock(return_value=httpx.Response(200, json=fixture))
    result = connector.fetch_food_entries(date(2026, 3, 20))
    assert isinstance(result, FatSecretDay)
    assert result.date == date(2026, 3, 20)
    assert result.calories_total == pytest.approx(1180.0)  # 350 + 280 + 550
    assert result.protein_g == pytest.approx(105.0)  # 10 + 55 + 40
    assert result.carbs_g == pytest.approx(125.0)   # 65 + 0 + 60
    assert len(result.meals) == 3
    assert result.meals[0].name == "Breakfast"


@respx.mock
def test_fetch_food_entries_missing_meals_does_not_raise(connector):
    partial_fixture = {
        "food_entries": {
            "food_entry": [
                {
                    "food_entry_id": "1", "food_entry_name": "Oatmeal",
                    "meal": "breakfast", "calories": "300",
                    "carbohydrate": "50", "protein": "10", "fat": "5",
                }
            ]
        }
    }
    respx.get(FATSECRET_API_URL).mock(return_value=httpx.Response(200, json=partial_fixture))
    result = connector.fetch_food_entries(date(2026, 3, 20))
    assert result.calories_total == pytest.approx(300.0)
    assert len(result.meals) == 1


@respx.mock
def test_fetch_food_entries_single_entry_as_dict(connector):
    # FatSecret returns food_entry as a dict (not list) when only one entry exists
    single_entry_fixture = {
        "food_entries": {
            "food_entry": {
                "food_entry_id": "1", "food_entry_name": "Protein Bar",
                "meal": "other", "calories": "200",
                "carbohydrate": "20", "protein": "25", "fat": "8",
            }
        }
    }
    respx.get(FATSECRET_API_URL).mock(return_value=httpx.Response(200, json=single_entry_fixture))
    result = connector.fetch_food_entries(date(2026, 3, 20))
    assert result.calories_total == pytest.approx(200.0)
    assert len(result.meals) == 1
    assert result.meals[0].name == "Other"
