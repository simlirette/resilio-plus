import os
import respx
import httpx
import pytest
from app.integrations.nutrition.usda_client import search, fetch


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "testkey")


_SEARCH_RESPONSE = {
    "foods": [
        {
            "fdcId": 789,
            "description": "Chicken Breast, Raw",
            "foodNutrients": [
                {"nutrientName": "Energy", "value": 165.0},
                {"nutrientName": "Protein", "value": 31.0},
                {"nutrientName": "Carbohydrate, by difference", "value": 0.0},
                {"nutrientName": "Total lipid (fat)", "value": 3.6},
                {"nutrientName": "Fiber, total dietary", "value": 0.0},
                {"nutrientName": "Sodium, Na", "value": 74.0},
                {"nutrientName": "Sugars, total including NLEA", "value": 0.0},
            ],
        }
    ]
}

_FETCH_RESPONSE = {
    "fdcId": 789,
    "description": "Chicken Breast, Raw",
    "foodNutrients": [
        {"nutrient": {"name": "Energy"}, "amount": 165.0},
        {"nutrient": {"name": "Protein"}, "amount": 31.0},
        {"nutrient": {"name": "Carbohydrate, by difference"}, "amount": 0.0},
        {"nutrient": {"name": "Total lipid (fat)"}, "amount": 3.6},
        {"nutrient": {"name": "Fiber, total dietary"}, "amount": 0.0},
        {"nutrient": {"name": "Sodium, Na"}, "amount": 74.0},
        {"nutrient": {"name": "Sugars, total including NLEA"}, "amount": 0.0},
    ],
}


@respx.mock
def test_search_returns_food_items():
    respx.get("https://api.nal.usda.gov/fdc/v1/foods/search").mock(
        return_value=httpx.Response(200, json=_SEARCH_RESPONSE)
    )
    results = search("chicken")
    assert len(results) == 1
    assert results[0].id == "usda_789"
    assert results[0].source == "usda"
    assert results[0].name == "Chicken Breast, Raw"
    assert results[0].name_en == "Chicken Breast, Raw"
    assert results[0].protein_g == 31.0
    assert results[0].calories_per_100g == 165.0


@respx.mock
def test_search_returns_empty_on_http_error():
    respx.get("https://api.nal.usda.gov/fdc/v1/foods/search").mock(
        return_value=httpx.Response(500)
    )
    results = search("chicken")
    assert results == []


def test_search_skipped_when_no_api_key(monkeypatch):
    monkeypatch.delenv("USDA_API_KEY", raising=False)
    results = search("chicken")
    assert results == []


@respx.mock
def test_fetch_returns_food_item():
    respx.get("https://api.nal.usda.gov/fdc/v1/food/789").mock(
        return_value=httpx.Response(200, json=_FETCH_RESPONSE)
    )
    item = fetch("789")
    assert item is not None
    assert item.id == "usda_789"
    assert item.source == "usda"
    assert item.calories_per_100g == 165.0
    assert item.sodium_mg == 74.0


@respx.mock
def test_fetch_returns_none_on_404():
    respx.get("https://api.nal.usda.gov/fdc/v1/food/999").mock(
        return_value=httpx.Response(404)
    )
    item = fetch("999")
    assert item is None
