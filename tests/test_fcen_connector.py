"""Tests unitaires FcenConnector — recherche locale CSV FCÉN."""

import pytest
from connectors.fcen import FcenConnector


@pytest.fixture
def connector():
    return FcenConnector()


def test_search_french_returns_results(connector):
    """Recherche en français retourne des résultats."""
    results = connector.search("poulet", limit=5)
    assert isinstance(results, list)
    # At least one result with 'poulet' in FR name
    assert any("poulet" in r["description_fr"].lower() for r in results)


def test_search_english_returns_results(connector):
    """Recherche en anglais retourne des résultats."""
    results = connector.search("chicken", limit=5)
    assert isinstance(results, list)
    assert any("chicken" in r["description_en"].lower() for r in results)


def test_search_case_insensitive(connector):
    """Recherche insensible à la casse."""
    lower = connector.search("poulet", limit=5)
    upper = connector.search("POULET", limit=5)
    assert lower == upper


def test_search_limit_respected(connector):
    """Le paramètre limit est respecté."""
    results = connector.search("a", limit=3)  # 'a' matches many
    assert len(results) <= 3


def test_search_no_match_returns_empty(connector):
    """Terme inconnu retourne liste vide."""
    results = connector.search("xyznotexistqwerty123", limit=5)
    assert results == []


def test_result_structure(connector):
    """Chaque résultat a les clés attendues avec nutriments."""
    results = connector.search("riz", limit=1)
    assert len(results) == 1
    r = results[0]
    assert "food_code" in r
    assert "description_fr" in r
    assert "description_en" in r
    assert "source" in r and r["source"] == "fcen"
    assert "nutrients" in r
    nutrients = r["nutrients"]
    for key in ("calories", "protein_g", "fat_g", "carbs_g", "fiber_g"):
        assert key in nutrients
        assert isinstance(nutrients[key], float)


def test_db_loads_all_rows(connector):
    """La base contient au moins 20 aliments."""
    from connectors.fcen import _load_db
    db = _load_db()
    assert len(db) >= 20
