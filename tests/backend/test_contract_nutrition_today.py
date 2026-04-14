"""Contract tests — GET /athletes/{id}/nutrition-today."""


def test_nutrition_today_requires_auth(api_client, auth_state):
    resp = api_client.get(f"/athletes/{auth_state['athlete_id']}/nutrition-today")
    assert resp.status_code == 401


def test_nutrition_today_returns_200(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/nutrition-today",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "date" in body
    assert "day_type" in body
    assert "macro_target" in body


def test_nutrition_today_macro_target_fields(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/nutrition-today",
        headers=auth_state["headers"],
    )
    mt = resp.json()["macro_target"]
    assert "carbs_g_per_kg" in mt
    assert "protein_g_per_kg" in mt
    assert "fat_g_per_kg" in mt
    assert "calories_total" in mt
    assert mt["calories_total"] > 0


def test_nutrition_today_valid_day_type(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/nutrition-today",
        headers=auth_state["headers"],
    )
    valid = {"rest", "strength", "endurance_short", "endurance_long", "race"}
    assert resp.json()["day_type"] in valid


def test_nutrition_today_rest_fallback_for_past_date(api_client, auth_state):
    """Date with no planned sessions → day_type=rest."""
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/nutrition-today",
        headers=auth_state["headers"],
        params={"target_date": "2020-01-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["day_type"] == "rest"


def test_nutrition_today_403_for_other_athlete(api_client, auth_state):
    resp = api_client.get(
        "/athletes/00000000-0000-0000-0000-000000000000/nutrition-today",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 403
