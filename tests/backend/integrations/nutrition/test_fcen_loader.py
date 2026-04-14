from pathlib import Path
from app.integrations.nutrition.fcen_loader import load_fcen
from app.db.models import FoodCacheModel

_FIXTURE_DIR = Path(__file__).parents[3] / "fixtures" / "fcen"


def test_load_fcen_inserts_3_items(db_session):
    count = load_fcen(
        food_name_csv=_FIXTURE_DIR / "FOOD NAME.csv",
        nutrient_amount_csv=_FIXTURE_DIR / "NUTRIENT AMOUNT.csv",
        nutrient_name_csv=_FIXTURE_DIR / "NUTRIENT NAME.csv",
        db=db_session,
    )
    assert count == 3
    rows = db_session.query(FoodCacheModel).filter_by(source="fcen").all()
    assert len(rows) == 3


def test_load_fcen_correct_data(db_session):
    load_fcen(
        food_name_csv=_FIXTURE_DIR / "FOOD NAME.csv",
        nutrient_amount_csv=_FIXTURE_DIR / "NUTRIENT AMOUNT.csv",
        nutrient_name_csv=_FIXTURE_DIR / "NUTRIENT NAME.csv",
        db=db_session,
    )
    chicken = db_session.get(FoodCacheModel, "fcen_2")
    assert chicken is not None
    assert chicken.name == "Chicken Breast"
    assert chicken.name_en == "Chicken Breast"
    assert chicken.name_fr == "Poulet, poitrine"
    assert chicken.calories_per_100g == 165.0
    assert chicken.protein_g == 31.0


def test_load_fcen_is_idempotent(db_session):
    kwargs = dict(
        food_name_csv=_FIXTURE_DIR / "FOOD NAME.csv",
        nutrient_amount_csv=_FIXTURE_DIR / "NUTRIENT AMOUNT.csv",
        nutrient_name_csv=_FIXTURE_DIR / "NUTRIENT NAME.csv",
        db=db_session,
    )
    load_fcen(**kwargs)
    load_fcen(**kwargs)
    rows = db_session.query(FoodCacheModel).filter_by(source="fcen").all()
    assert len(rows) == 3


def test_load_fcen_items_have_null_ttl(db_session):
    load_fcen(
        food_name_csv=_FIXTURE_DIR / "FOOD NAME.csv",
        nutrient_amount_csv=_FIXTURE_DIR / "NUTRIENT AMOUNT.csv",
        nutrient_name_csv=_FIXTURE_DIR / "NUTRIENT NAME.csv",
        db=db_session,
    )
    rows = db_session.query(FoodCacheModel).filter_by(source="fcen").all()
    assert all(r.ttl_hours is None for r in rows)
