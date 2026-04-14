import pytest
from app.schemas.food import FoodItem
from app.db.models import FoodCacheModel
from datetime import datetime, timezone


def test_food_item_name_prefers_fr():
    item = FoodItem(
        id="fcen_1",
        source="fcen",
        name="Beef",
        name_en="Beef",
        name_fr="Boeuf",
        calories_per_100g=207.0,
        protein_g=26.0,
        carbs_g=0.0,
        fat_g=11.0,
    )
    assert item.name_fr == "Boeuf"


def test_food_item_name_fr_optional():
    item = FoodItem(
        id="usda_789",
        source="usda",
        name="Chicken",
        name_en="Chicken",
        calories_per_100g=165.0,
        protein_g=31.0,
        carbs_g=0.0,
        fat_g=3.6,
    )
    assert item.name_fr is None


def test_food_item_missing_nutrients_are_none():
    item = FoodItem(
        id="usda_789",
        source="usda",
        name="Chicken",
        name_en="Chicken",
        calories_per_100g=165.0,
        protein_g=31.0,
        carbs_g=0.0,
        fat_g=3.6,
    )
    assert item.fiber_g is None
    assert item.sodium_mg is None
    assert item.sugar_g is None


def test_food_cache_model_inserts_to_db(db_session):
    row = FoodCacheModel(
        id="usda_789",
        source="usda",
        name="Chicken Breast",
        name_fr=None,
        calories_per_100g=165.0,
        protein_g=31.0,
        carbs_g=0.0,
        fat_g=3.6,
        fiber_g=None,
        sodium_mg=None,
        sugar_g=None,
        cached_at=datetime.now(timezone.utc),
        ttl_hours=168,
    )
    db_session.add(row)
    db_session.commit()
    retrieved = db_session.get(FoodCacheModel, "usda_789")
    assert retrieved is not None
    assert retrieved.protein_g == 31.0
    assert retrieved.ttl_hours == 168


def test_food_cache_model_fcen_has_null_ttl(db_session):
    row = FoodCacheModel(
        id="fcen_1",
        source="fcen",
        name="Beef Steak",
        name_fr="Boeuf, bifteck",
        calories_per_100g=207.0,
        protein_g=26.0,
        carbs_g=0.0,
        fat_g=11.0,
        fiber_g=None,
        sodium_mg=None,
        sugar_g=None,
        cached_at=datetime.now(timezone.utc),
        ttl_hours=None,
    )
    db_session.add(row)
    db_session.commit()
    retrieved = db_session.get(FoodCacheModel, "fcen_1")
    assert retrieved.ttl_hours is None
