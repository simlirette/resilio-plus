from unittest.mock import patch
from app.schemas.food import FoodItem

_CHICKEN = FoodItem(
    id="usda_789",
    source="usda",
    name="Chicken Breast",
    name_en="Chicken Breast",
    calories_per_100g=165.0,
    protein_g=31.0,
    carbs_g=0.0,
    fat_g=3.6,
)


def test_search_returns_200(api_client, auth_state):
    with patch(
        "app.routes.food_search.nutrition_search", return_value=[_CHICKEN]
    ):
        resp = api_client.get(
            "/nutrition/search?q=chicken",
            headers=auth_state["headers"],
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == "usda_789"
    assert body[0]["source"] == "usda"


def test_search_empty_q_returns_422(api_client, auth_state):
    resp = api_client.get(
        "/nutrition/search?q=",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 422


def test_search_unauthenticated_returns_401(api_client):
    resp = api_client.get("/nutrition/search?q=chicken")
    assert resp.status_code == 401


def test_fetch_food_item_returns_200(api_client, auth_state):
    with patch(
        "app.routes.food_search.nutrition_fetch", return_value=_CHICKEN
    ):
        resp = api_client.get(
            "/nutrition/food/usda_789",
            headers=auth_state["headers"],
        )
    assert resp.status_code == 200
    assert resp.json()["id"] == "usda_789"


def test_fetch_unknown_food_id_returns_404(api_client, auth_state):
    with patch("app.routes.food_search.nutrition_fetch", return_value=None):
        resp = api_client.get(
            "/nutrition/food/usda_9999",
            headers=auth_state["headers"],
        )
    assert resp.status_code == 404
