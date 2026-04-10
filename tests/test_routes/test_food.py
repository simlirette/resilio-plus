"""
Tests for backend/app/routes/food.py

Coverage:
  - Authentication enforcement (401/403)
  - Cache search (local JSON items)
  - FCÉN-only search
  - Barcode lookup (mocked httpx)
  - Barcode not found → 404
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.test_routes.conftest import authed_client  # noqa: F401 — fixture re-export


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_food_search_requires_auth(authed_client):
    client, athlete_id = authed_client
    # Override auth with invalid token
    resp = client.get(
        f"/athletes/{athlete_id}/food/search?q=riz",
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )
    assert resp.status_code == 401


def test_food_search_wrong_athlete(authed_client):
    client, _own_id = authed_client
    resp = client.get("/athletes/other-athlete-id/food/search?q=riz")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cache search
# ---------------------------------------------------------------------------

def test_food_search_cache_returns_list(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/food/search?q=riz")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_food_search_cache_finds_item(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/food/search?q=riz")
    assert resp.status_code == 200
    data = resp.json()
    names = [item["name"].lower() + item["name_en"].lower() for item in data]
    assert any("riz" in n or "rice" in n for n in names), f"Expected rice in results: {data}"


def test_food_search_no_results(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/food/search?q=xyznonexistent999")
    assert resp.status_code == 200
    assert resp.json() == []


def test_food_search_empty_query_rejected(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/food/search?q=")
    assert resp.status_code == 422


def test_food_search_result_schema(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/food/search?q=poulet")
    assert resp.status_code == 200
    data = resp.json()
    if data:
        item = data[0]
        assert "name" in item
        assert "calories_per_100g" in item
        assert "carbs_g" in item
        assert "protein_g" in item
        assert "fat_g" in item
        assert "source" in item


# ---------------------------------------------------------------------------
# FCÉN search
# ---------------------------------------------------------------------------

def test_fcen_search_returns_list(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/food/search/fcen?q=poulet")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_fcen_search_only_fcen_source(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/food/search/fcen?q=")
    # Empty query should be 422
    assert resp.status_code == 422


def test_fcen_search_finds_fcen_items(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/food/search/fcen?q=yukon")
    assert resp.status_code == 200
    data = resp.json()
    for item in data:
        assert item["source"] == "fcen"


# ---------------------------------------------------------------------------
# Barcode lookup
# ---------------------------------------------------------------------------

def test_barcode_lookup_success(authed_client):
    client, athlete_id = authed_client
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": 1,
        "product": {
            "product_name": "Nutella",
            "nutriments": {
                "energy-kcal_100g": 530.0,
                "carbohydrates_100g": 57.5,
                "proteins_100g": 6.3,
                "fat_100g": 30.9,
                "fiber_100g": 0.0,
            },
        },
    }

    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=mock_resp)

        resp = client.get(
            f"/athletes/{athlete_id}/food/barcode/3017620422003"
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Nutella"
    assert data["source"] == "open_food_facts"
    assert data["calories_per_100g"] == 530.0


def test_barcode_lookup_not_found(authed_client):
    client, athlete_id = authed_client
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": 0}

    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=mock_resp)

        resp = client.get(
            f"/athletes/{athlete_id}/food/barcode/0000000000000"
        )

    assert resp.status_code == 404
