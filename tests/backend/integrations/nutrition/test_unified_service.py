from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.db.models import FoodCacheModel
from app.integrations.nutrition.unified_service import fetch, search
from app.schemas.food import FoodItem

# db_session fixture from tests/backend/integrations/conftest.py


def _make_cache_row(
    db,
    food_id: str = "usda_789",
    name: str = "Chicken",
    source: str = "usda",
    ttl_hours: int | None = 168,
    hours_old: float = 0,
) -> FoodCacheModel:
    row = FoodCacheModel(
        id=food_id,
        source=source,
        name=name,
        name_en=name,
        name_fr=None,
        calories_per_100g=165.0,
        protein_g=31.0,
        carbs_g=0.0,
        fat_g=3.6,
        fiber_g=None,
        sodium_mg=None,
        sugar_g=None,
        cached_at=datetime.now(timezone.utc) - timedelta(hours=hours_old),
        ttl_hours=ttl_hours,
    )
    db.add(row)
    db.commit()
    return row


def _make_food_item(food_id: str = "usda_111", name: str = "Salmon") -> FoodItem:
    return FoodItem(
        id=food_id,
        source="usda",
        name=name,
        name_en=name,
        calories_per_100g=200.0,
        protein_g=25.0,
        carbs_g=0.0,
        fat_g=10.0,
    )


# ── search() ──────────────────────────────────────────────────────────────────

def test_search_cache_hit_returns_without_api_calls(db_session):
    _make_cache_row(db_session, name="chicken breast")
    with patch("app.integrations.nutrition.unified_service.usda_client") as mu:
        with patch("app.integrations.nutrition.unified_service.off_client") as mo:
            results = search("chicken", db_session)
    mu.search.assert_not_called()
    mo.search.assert_not_called()
    assert len(results) == 1
    assert results[0].id == "usda_789"


def test_search_cache_miss_fans_out_to_usda_and_off(db_session):
    item = _make_food_item()
    with patch("app.integrations.nutrition.unified_service.usda_client") as mu:
        with patch("app.integrations.nutrition.unified_service.off_client") as mo:
            mu.search.return_value = [item]
            mo.search.return_value = []
            results = search("salmon", db_session)
    mu.search.assert_called_once_with("salmon")
    mo.search.assert_called_once_with("salmon")
    assert len(results) == 1
    assert results[0].id == "usda_111"


def test_search_expired_row_triggers_api_refresh(db_session):
    _make_cache_row(db_session, name="chicken", hours_old=200)  # 200h > 168h TTL
    fresh = _make_food_item("usda_789", "Chicken")
    with patch("app.integrations.nutrition.unified_service.usda_client") as mu:
        with patch("app.integrations.nutrition.unified_service.off_client") as mo:
            mu.search.return_value = [fresh]
            mo.search.return_value = []
            results = search("chicken", db_session)
    mu.search.assert_called_once()
    assert len(results) == 1


def test_search_permanent_fcen_row_never_expires(db_session):
    _make_cache_row(
        db_session, food_id="fcen_1", source="fcen", name="boeuf",
        ttl_hours=None, hours_old=99999,
    )
    with patch("app.integrations.nutrition.unified_service.usda_client") as mu:
        with patch("app.integrations.nutrition.unified_service.off_client") as mo:
            results = search("boeuf", db_session)
    mu.search.assert_not_called()
    mo.search.assert_not_called()
    assert len(results) == 1


def test_search_usda_down_returns_off_results(db_session):
    off_item = FoodItem(
        id="off_123", source="off", name="Oatmeal", name_en="Oatmeal",
        calories_per_100g=370.0, protein_g=13.0, carbs_g=67.0, fat_g=7.0,
    )
    with patch("app.integrations.nutrition.unified_service.usda_client") as mu:
        with patch("app.integrations.nutrition.unified_service.off_client") as mo:
            mu.search.return_value = []
            mo.search.return_value = [off_item]
            results = search("oatmeal", db_session)
    assert any(r.id == "off_123" for r in results)


def test_search_all_sources_down_returns_empty(db_session):
    with patch("app.integrations.nutrition.unified_service.usda_client") as mu:
        with patch("app.integrations.nutrition.unified_service.off_client") as mo:
            mu.search.return_value = []
            mo.search.return_value = []
            results = search("xyz_no_results", db_session)
    assert results == []


def test_search_result_capped_at_20(db_session):
    items = [_make_food_item(f"usda_{i}", f"Food {i}") for i in range(25)]
    with patch("app.integrations.nutrition.unified_service.usda_client") as mu:
        with patch("app.integrations.nutrition.unified_service.off_client") as mo:
            mu.search.return_value = items
            mo.search.return_value = []
            results = search("food", db_session)
    assert len(results) <= 20


# ── fetch() ───────────────────────────────────────────────────────────────────

def test_fetch_cache_hit_returns_item(db_session):
    _make_cache_row(db_session)
    with patch("app.integrations.nutrition.unified_service.usda_client") as mu:
        item = fetch("usda_789", db_session)
    mu.fetch.assert_not_called()
    assert item is not None
    assert item.id == "usda_789"


def test_fetch_cache_miss_calls_usda(db_session):
    usda_item = _make_food_item("usda_789", "Chicken")
    with patch("app.integrations.nutrition.unified_service.usda_client") as mu:
        mu.fetch.return_value = usda_item
        item = fetch("usda_789", db_session)
    mu.fetch.assert_called_once_with("789")
    assert item is not None


def test_fetch_fcen_not_in_cache_returns_none(db_session):
    item = fetch("fcen_9999", db_session)
    assert item is None


def test_fetch_unknown_prefix_returns_none(db_session):
    item = fetch("unknown_123", db_session)
    assert item is None
