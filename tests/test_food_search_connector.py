"""
Tests unitaires FoodSearchConnector.
Tous les appels HTTP sont interceptés via httpx.MockTransport.
"""

import httpx
import pytest

from connectors.food_search import FoodSearchConnector

# ── test_search_usda_returns_results ─────────────────────────────────────────

async def test_search_usda_returns_results():
    usda_response = {
        "foods": [
            {
                "fdcId": 171705,
                "description": "Chicken, broilers or fryers, breast",
                "foodNutrients": [
                    {"nutrientId": 1008, "value": 165.0},  # calories
                    {"nutrientId": 1003, "value": 31.0},    # protein
                    {"nutrientId": 1004, "value": 3.6},     # fat
                    {"nutrientId": 1005, "value": 0.0},     # carbs
                ],
            }
        ]
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "foods/search" in str(request.url)
        return httpx.Response(200, json=usda_response)

    connector = FoodSearchConnector(transport=httpx.MockTransport(mock_handler))
    results = await connector.search_usda("chicken")

    assert len(results) == 1
    assert results[0]["fdcId"] == 171705
    assert results[0]["description"] == "Chicken, broilers or fryers, breast"
    assert results[0]["nutrients"]["protein_g"] == pytest.approx(31.0)
    assert results[0]["nutrients"]["calories"] == pytest.approx(165.0)
    assert results[0]["nutrients"]["fat_g"] == pytest.approx(3.6)
    assert results[0]["nutrients"]["carbs_g"] == pytest.approx(0.0)


# ── test_search_barcode_found ─────────────────────────────────────────────────

async def test_search_barcode_found():
    off_response = {
        "status": 1,
        "product": {
            "product_name": "Nutella",
            "nutriments": {
                "energy-kcal_100g": 539.0,
                "proteins_100g": 6.3,
                "fat_100g": 30.9,
                "carbohydrates_100g": 57.5,
            },
        },
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "3017624010701" in str(request.url)
        return httpx.Response(200, json=off_response)

    connector = FoodSearchConnector(transport=httpx.MockTransport(mock_handler))
    result = await connector.search_barcode("3017624010701")

    assert result is not None
    assert result["name"] == "Nutella"
    assert result["nutrients"]["calories"] == pytest.approx(539.0)
    assert result["nutrients"]["protein_g"] == pytest.approx(6.3)
    assert result["nutrients"]["fat_g"] == pytest.approx(30.9)
    assert result["nutrients"]["carbs_g"] == pytest.approx(57.5)


# ── test_search_barcode_not_found ─────────────────────────────────────────────

async def test_search_barcode_not_found():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": 0, "product": {}})

    connector = FoodSearchConnector(transport=httpx.MockTransport(mock_handler))
    result = await connector.search_barcode("0000000000000")

    assert result is None
