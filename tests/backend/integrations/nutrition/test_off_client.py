import pytest
import respx
import httpx
from app.integrations.nutrition.off_client import search, fetch

_OFF_SEARCH = "https://world.openfoodfacts.org/cgi/search.pl"

_NUTELLA_PRODUCT = {
    "code": "3017620422003",
    "product_name": "Nutella",
    "nutriments": {
        "energy-kcal_100g": 539.0,
        "proteins_100g": 6.3,
        "carbohydrates_100g": 57.5,
        "fat_100g": 30.9,
        "fiber_100g": 2.0,
        "sodium_100g": 0.107,
        "sugars_100g": 56.3,
    },
}


@respx.mock
def test_search_returns_food_items():
    respx.get(_OFF_SEARCH).mock(
        return_value=httpx.Response(200, json={"products": [_NUTELLA_PRODUCT]})
    )
    results = search("nutella")
    assert len(results) == 1
    assert results[0].id == "off_3017620422003"
    assert results[0].source == "off"
    assert results[0].name == "Nutella"
    assert results[0].calories_per_100g == 539.0
    assert results[0].protein_g == 6.3
    assert results[0].sodium_mg == pytest.approx(107.0, abs=0.1)


@respx.mock
def test_search_skips_products_without_name():
    respx.get(_OFF_SEARCH).mock(
        return_value=httpx.Response(200, json={
            "products": [{"code": "123", "product_name": "", "nutriments": {}}]
        })
    )
    results = search("x")
    assert results == []


@respx.mock
def test_search_returns_empty_on_http_error():
    respx.get(_OFF_SEARCH).mock(return_value=httpx.Response(503))
    results = search("anything")
    assert results == []


@respx.mock
def test_fetch_by_barcode_returns_food_item():
    respx.get("https://world.openfoodfacts.org/api/v0/product/3017620422003.json").mock(
        return_value=httpx.Response(200, json={"status": 1, "product": _NUTELLA_PRODUCT})
    )
    item = fetch("3017620422003")
    assert item is not None
    assert item.id == "off_3017620422003"
    assert item.fat_g == 30.9


@respx.mock
def test_fetch_returns_none_when_status_not_1():
    respx.get("https://world.openfoodfacts.org/api/v0/product/000.json").mock(
        return_value=httpx.Response(200, json={"status": 0})
    )
    item = fetch("000")
    assert item is None


@respx.mock
def test_fetch_returns_none_on_timeout():
    respx.get("https://world.openfoodfacts.org/api/v0/product/111.json").mock(
        side_effect=httpx.TimeoutException("timeout")
    )
    item = fetch("111")
    assert item is None
