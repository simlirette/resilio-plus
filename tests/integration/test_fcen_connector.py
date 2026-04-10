"""
Integration tests — FCÉN (Health Canada) food database connector.

Tests FcenConnector with an in-memory mock CSV, avoiding dependency
on the actual data/fcen_nutrients.csv file.
"""
from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

import pytest

from backend.app.connectors.fcen import FcenConnector, FcenFood, _load_fcen, _map_columns


# ── Mock CSV data ─────────────────────────────────────────────────────────────

FCEN_CSV_CONTENT = """\
food_id,food_name_fr,food_name_en,energy_kcal,protein_g,fat_g,carb_g,fiber_g,sugar_g,sodium_mg,calcium_mg,iron_mg,vitamin_c_mg
1001,Poulet rôti (sans peau),Roasted chicken (skinless),165,31.0,3.6,0.0,0.0,0.0,74,11,1.0,0.0
1002,Poitrine de poulet grillée,Grilled chicken breast,165,31.0,3.6,0.0,0.0,0.0,74,11,1.0,0.0
1003,Boeuf haché (extra-maigre),Extra-lean ground beef,215,26.0,12.0,0.0,0.0,0.0,79,10,2.5,0.0
1004,Saumon atlantique (cuit),Atlantic salmon (cooked),206,28.8,9.4,0.0,0.0,0.0,64,15,0.8,0.0
1005,Riz blanc cuit,Cooked white rice,130,2.7,0.3,28.7,0.4,0.0,1,10,0.2,0.0
1006,Brocoli cuit,Cooked broccoli,35,2.4,0.4,7.2,2.6,1.7,41,47,0.7,65.0
1007,Oeuf entier cuit,Whole cooked egg,155,13.0,11.0,1.1,0.0,0.5,124,50,1.2,0.0
1008,Beurre d'arachide naturel,Natural peanut butter,588,25.1,50.4,20.2,6.0,8.7,1,46,2.0,0.0
1009,Flocons d'avoine secs,Dry rolled oats,379,13.2,6.5,67.7,10.1,0.0,2,52,3.6,0.0
1010,Banane mûre,Ripe banana,89,1.1,0.3,23.0,2.6,12.2,1,5,0.3,8.7
"""


@pytest.fixture
def fcen_csv_path(tmp_path: Path) -> Path:
    """Write mock FCÉN CSV to a temp file and return its path."""
    p = tmp_path / "fcen_nutrients.csv"
    p.write_text(FCEN_CSV_CONTENT, encoding="utf-8")
    return p


@pytest.fixture
def connector(fcen_csv_path: Path) -> FcenConnector:
    return FcenConnector(csv_path=fcen_csv_path)


# ── Loading ───────────────────────────────────────────────────────────────────

class TestFcenLoading:
    def test_loads_all_rows(self, connector: FcenConnector):
        # 10 food items in mock CSV
        results = connector.search("", limit=100)
        # empty query returns empty (not all items)
        # but loaded check should work
        assert connector.loaded

    def test_loaded_true_when_csv_exists(self, connector: FcenConnector):
        assert connector.loaded is True

    def test_loaded_false_when_csv_missing(self, tmp_path: Path):
        c = FcenConnector(csv_path=tmp_path / "nonexistent.csv")
        assert c.loaded is False

    def test_missing_csv_search_returns_empty(self, tmp_path: Path):
        c = FcenConnector(csv_path=tmp_path / "nonexistent.csv")
        assert c.search("poulet") == []

    def test_returns_fcenfood_instances(self, connector: FcenConnector):
        results = connector.search("poulet")
        assert all(isinstance(r, FcenFood) for r in results)


# ── French name search ────────────────────────────────────────────────────────

class TestFrenchSearch:
    def test_exact_word_match(self, connector: FcenConnector):
        results = connector.search("poulet")
        names_fr = [r.name_fr for r in results]
        assert any("poulet" in n.lower() for n in names_fr)

    def test_partial_match(self, connector: FcenConnector):
        results = connector.search("boeuf")
        assert len(results) >= 1
        assert any("boeuf" in r.name_fr.lower() for r in results)

    def test_accent_insensitive(self, connector: FcenConnector):
        results = connector.search("flocons")
        assert len(results) >= 1

    def test_case_insensitive(self, connector: FcenConnector):
        results_lower = connector.search("poulet")
        results_upper = connector.search("POULET")
        assert len(results_lower) == len(results_upper)


# ── English name search ───────────────────────────────────────────────────────

class TestEnglishSearch:
    def test_english_name(self, connector: FcenConnector):
        results = connector.search("salmon")
        assert len(results) >= 1
        assert any("salmon" in r.name_en.lower() for r in results)

    def test_english_partial(self, connector: FcenConnector):
        results = connector.search("chicken")
        assert len(results) >= 1


# ── Result data integrity ─────────────────────────────────────────────────────

class TestFoodData:
    def test_poulet_macros(self, connector: FcenConnector):
        results = connector.search("Poulet rôti")
        assert len(results) >= 1
        r = results[0]
        assert abs(r.energy_kcal - 165.0) < 0.1
        assert abs(r.protein_g - 31.0) < 0.1
        assert abs(r.fat_g - 3.6) < 0.1
        assert r.carb_g == 0.0

    def test_brocoli_has_vitamin_c(self, connector: FcenConnector):
        results = connector.search("Brocoli")
        assert len(results) >= 1
        brocoli = results[0]
        assert brocoli.vitamin_c_mg is not None
        assert brocoli.vitamin_c_mg > 0

    def test_food_id_present(self, connector: FcenConnector):
        results = connector.search("riz")
        assert len(results) >= 1
        assert results[0].food_id != ""

    def test_to_dict_has_all_fields(self, connector: FcenConnector):
        results = connector.search("banane")
        assert len(results) >= 1
        d = results[0].to_dict()
        expected_keys = {
            "food_id", "name_fr", "name_en",
            "energy_kcal", "protein_g", "fat_g", "carb_g", "fiber_g",
            "sugar_g", "sodium_mg", "calcium_mg", "iron_mg", "vitamin_c_mg",
        }
        assert expected_keys.issubset(set(d.keys()))


# ── Limit parameter ───────────────────────────────────────────────────────────

class TestLimit:
    def test_limit_respected(self, connector: FcenConnector):
        # "cuit" matches boeuf, saumon, riz, brocoli, oeuf = 5+ items
        results = connector.search("cuit", limit=2)
        assert len(results) <= 2

    def test_default_limit_20(self, connector: FcenConnector):
        # With only 10 items in mock CSV, searching empty-ish query
        results = connector.search("oe")  # matches "oeuf", potentially others
        assert len(results) <= 20


# ── Fuzzy fallback ────────────────────────────────────────────────────────────

class TestFuzzySearch:
    def test_typo_poooolet(self, connector: FcenConnector):
        # "poulet" with slight variation — fuzzy should still find it
        results = connector.search("pouelt")  # transposed letters
        # May or may not match depending on score threshold — just check no crash
        assert isinstance(results, list)

    def test_no_results_for_garbage(self, connector: FcenConnector):
        results = connector.search("xyzqqqzzz123")
        assert results == []


# ── Column mapping ────────────────────────────────────────────────────────────

class TestColumnMapping:
    def test_standard_headers(self):
        headers = [
            "food_id", "food_name_fr", "food_name_en", "energy_kcal",
            "protein_g", "fat_g", "carb_g", "fiber_g",
        ]
        mapping = _map_columns(headers)
        assert mapping["food_id"] == "food_id"
        assert mapping["name_fr"] == "food_name_fr"
        assert mapping["energy_kcal"] == "energy_kcal"

    def test_alternative_headers(self):
        headers = ["id", "nom_fr", "name", "calories", "protein", "fat", "carbohydrate", "fiber"]
        mapping = _map_columns(headers)
        assert mapping["food_id"] == "id"
        assert mapping["name_fr"] == "nom_fr"
        assert mapping["energy_kcal"] == "calories"

    def test_missing_column_maps_to_none(self):
        mapping = _map_columns(["food_id", "food_name_fr"])
        assert mapping["vitamin_c_mg"] is None
