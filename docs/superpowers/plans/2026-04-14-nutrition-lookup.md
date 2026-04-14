# Nutrition Lookup Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified food search + nutrition data service backed by USDA FoodData Central, Open Food Facts, and Canadian Nutrient File (FCÉN), with SQLite-cached TTL results and two new endpoints: `GET /nutrition/search` and `GET /nutrition/food/{food_id}`.

**Architecture:** Cache-first search (SQLite `food_cache` table) with parallel fan-out to USDA + OFF on miss; FCÉN data is pre-loaded via a bootstrap script and never expires. All three sources return the unified `FoodItem` schema with source-prefixed IDs (`usda_789`, `off_3017620422003`, `fcen_456`).

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, `httpx` (sync), `respx` (test mocking), Pydantic v2, pytest.

---

## File Structure

| Action | Path | Responsibility |
|---|---|---|
| Create | `backend/app/schemas/food.py` | `FoodItem` Pydantic model |
| Modify | `backend/app/db/models.py` | Add `FoodCacheModel` |
| Create | `alembic/versions/0007_food_cache.py` | Migration: CREATE TABLE food_cache |
| Create | `backend/app/integrations/nutrition/__init__.py` | Package marker |
| Create | `backend/app/integrations/nutrition/usda_client.py` | Sync httpx: search + fetch from USDA FDC |
| Create | `backend/app/integrations/nutrition/off_client.py` | Sync httpx: search + fetch from Open Food Facts |
| Create | `backend/app/integrations/nutrition/fcen_loader.py` | JOIN 3 FCÉN CSVs → bulk-upsert permanent rows |
| Create | `backend/scripts/load_fcen.py` | CLI: `python -m scripts.load_fcen` |
| Create | `backend/app/integrations/nutrition/unified_service.py` | `search()` + `fetch()` with cache + fan-out |
| Create | `backend/app/routes/food_search.py` | GET /nutrition/search, GET /nutrition/food/{id} |
| Delete | `backend/app/routes/food.py` | Replaced by food_search.py |
| Modify | `backend/app/main.py` | Swap food_router → food_search_router |
| Modify | `.env.example` | Add USDA_API_KEY |
| Create | `tests/backend/integrations/nutrition/__init__.py` | Package marker |
| Create | `tests/backend/integrations/nutrition/test_food_schema.py` | FoodItem + FoodCacheModel smoke tests |
| Create | `tests/backend/integrations/nutrition/test_usda_client.py` | respx mock tests for USDA client |
| Create | `tests/backend/integrations/nutrition/test_off_client.py` | respx mock tests for OFF client |
| Create | `tests/backend/integrations/nutrition/test_fcen_loader.py` | Loader correctness + idempotency |
| Create | `tests/backend/integrations/nutrition/test_unified_service.py` | Cache hit/miss/expiry/fallback |
| Create | `tests/backend/api/test_food_search.py` | API-level endpoint tests |
| Create | `tests/fixtures/fcen/FOOD NAME.csv` | 3-row fixture for loader tests |
| Create | `tests/fixtures/fcen/NUTRIENT NAME.csv` | Nutrient ID mapping fixture |
| Create | `tests/fixtures/fcen/NUTRIENT AMOUNT.csv` | Nutrient amounts fixture |
| Modify | `docs/backend/INTEGRATIONS.md` | Add nutrition section |

---

## Task 1: FoodItem schema + FoodCacheModel + Alembic migration 0007

**Files:**
- Create: `backend/app/schemas/food.py`
- Modify: `backend/app/db/models.py`
- Create: `alembic/versions/0007_food_cache.py`
- Create: `tests/backend/integrations/nutrition/__init__.py`
- Create: `tests/backend/integrations/nutrition/test_food_schema.py`

- [ ] **Step 1: Pull latest and verify tests pass**

```bash
git pull --rebase
cd backend && C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q --tb=no -q 2>&1 | tail -5
```

Expected: existing suite passes (2161+ tests).

- [ ] **Step 2: Write failing tests**

Create `tests/backend/integrations/nutrition/__init__.py` (empty).

Create `tests/backend/integrations/nutrition/test_food_schema.py`:

```python
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
```

Note: `db_session` fixture comes from `tests/backend/integrations/conftest.py` (already exists).

- [ ] **Step 3: Run failing tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_food_schema.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas.food'`

- [ ] **Step 4: Create `backend/app/schemas/food.py`**

```python
from pydantic import BaseModel


class FoodItem(BaseModel):
    id: str                          # "usda_789", "off_3017620422003", "fcen_456"
    source: str                      # "usda" | "off" | "fcen"
    name: str                        # display name (name_fr if available, else name_en)
    name_en: str
    name_fr: str | None = None
    calories_per_100g: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None = None
    sodium_mg: float | None = None
    sugar_g: float | None = None
```

- [ ] **Step 5: Add `FoodCacheModel` to `backend/app/db/models.py`**

Append at end of file (after the last model class):

```python
class FoodCacheModel(Base):
    __tablename__ = "food_cache"

    id = Column(String, primary_key=True)         # "usda_789" etc.
    source = Column(String, nullable=False)        # "usda" | "off" | "fcen"
    name = Column(String, nullable=False)
    name_fr = Column(String, nullable=True)
    calories_per_100g = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    sodium_mg = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    cached_at = Column(DateTime(timezone=True), nullable=False)
    ttl_hours = Column(Integer, nullable=True)     # NULL = permanent (FCÉN)
```

- [ ] **Step 6: Create `alembic/versions/0007_food_cache.py`**

```python
"""Add food_cache table

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-14 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "food_cache",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_fr", sa.String(), nullable=True),
        sa.Column("calories_per_100g", sa.Float(), nullable=True),
        sa.Column("protein_g", sa.Float(), nullable=True),
        sa.Column("carbs_g", sa.Float(), nullable=True),
        sa.Column("fat_g", sa.Float(), nullable=True),
        sa.Column("fiber_g", sa.Float(), nullable=True),
        sa.Column("sodium_mg", sa.Float(), nullable=True),
        sa.Column("sugar_g", sa.Float(), nullable=True),
        sa.Column("cached_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ttl_hours", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("food_cache")
```

- [ ] **Step 7: Run tests — expect pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_food_schema.py -v
```

Expected: 5 PASSED

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/food.py backend/app/db/models.py alembic/versions/0007_food_cache.py tests/backend/integrations/nutrition/__init__.py tests/backend/integrations/nutrition/test_food_schema.py
git commit -m "feat(nutrition): FoodItem schema, FoodCacheModel, Alembic migration 0007"
```

---

## Task 2: USDA client

**Files:**
- Create: `backend/app/integrations/nutrition/__init__.py`
- Create: `backend/app/integrations/nutrition/usda_client.py`
- Create: `tests/backend/integrations/nutrition/test_usda_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/integrations/nutrition/test_usda_client.py`:

```python
import os
import respx
import httpx
import pytest
from app.integrations.nutrition.usda_client import search, fetch


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "testkey")


_SEARCH_RESPONSE = {
    "foods": [
        {
            "fdcId": 789,
            "description": "Chicken Breast, Raw",
            "foodNutrients": [
                {"nutrientName": "Energy", "value": 165.0},
                {"nutrientName": "Protein", "value": 31.0},
                {"nutrientName": "Carbohydrate, by difference", "value": 0.0},
                {"nutrientName": "Total lipid (fat)", "value": 3.6},
                {"nutrientName": "Fiber, total dietary", "value": 0.0},
                {"nutrientName": "Sodium, Na", "value": 74.0},
                {"nutrientName": "Sugars, total including NLEA", "value": 0.0},
            ],
        }
    ]
}

_FETCH_RESPONSE = {
    "fdcId": 789,
    "description": "Chicken Breast, Raw",
    "foodNutrients": [
        {"nutrient": {"name": "Energy"}, "amount": 165.0},
        {"nutrient": {"name": "Protein"}, "amount": 31.0},
        {"nutrient": {"name": "Carbohydrate, by difference"}, "amount": 0.0},
        {"nutrient": {"name": "Total lipid (fat)"}, "amount": 3.6},
        {"nutrient": {"name": "Fiber, total dietary"}, "amount": 0.0},
        {"nutrient": {"name": "Sodium, Na"}, "amount": 74.0},
        {"nutrient": {"name": "Sugars, total including NLEA"}, "amount": 0.0},
    ],
}


@respx.mock
def test_search_returns_food_items():
    respx.get("https://api.nal.usda.gov/fdc/v1/foods/search").mock(
        return_value=httpx.Response(200, json=_SEARCH_RESPONSE)
    )
    results = search("chicken")
    assert len(results) == 1
    assert results[0].id == "usda_789"
    assert results[0].source == "usda"
    assert results[0].name == "Chicken Breast, Raw"
    assert results[0].name_en == "Chicken Breast, Raw"
    assert results[0].protein_g == 31.0
    assert results[0].calories_per_100g == 165.0


@respx.mock
def test_search_returns_empty_on_http_error():
    respx.get("https://api.nal.usda.gov/fdc/v1/foods/search").mock(
        return_value=httpx.Response(500)
    )
    results = search("chicken")
    assert results == []


def test_search_skipped_when_no_api_key(monkeypatch):
    monkeypatch.delenv("USDA_API_KEY", raising=False)
    results = search("chicken")
    assert results == []


@respx.mock
def test_fetch_returns_food_item():
    respx.get("https://api.nal.usda.gov/fdc/v1/food/789").mock(
        return_value=httpx.Response(200, json=_FETCH_RESPONSE)
    )
    item = fetch("789")
    assert item is not None
    assert item.id == "usda_789"
    assert item.source == "usda"
    assert item.calories_per_100g == 165.0
    assert item.sodium_mg == 74.0


@respx.mock
def test_fetch_returns_none_on_404():
    respx.get("https://api.nal.usda.gov/fdc/v1/food/999").mock(
        return_value=httpx.Response(404)
    )
    item = fetch("999")
    assert item is None
```

- [ ] **Step 2: Run failing tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_usda_client.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.integrations.nutrition.usda_client'`

- [ ] **Step 3: Create package marker**

Create `backend/app/integrations/nutrition/__init__.py` (empty).

- [ ] **Step 4: Create `backend/app/integrations/nutrition/usda_client.py`**

```python
import logging
import os

import httpx

from ...schemas.food import FoodItem

logger = logging.getLogger(__name__)

_USDA_BASE = "https://api.nal.usda.gov/fdc/v1"


def _nv_search(nutrients: list[dict], name_prefix: str) -> float | None:
    """Extract nutrient value from search-response nutrients (flat list with nutrientName/value)."""
    for n in nutrients:
        if n.get("nutrientName", "").startswith(name_prefix):
            val = n.get("value")
            return float(val) if val is not None else None
    return None


def _nv_fetch(nutrients: list[dict], name_prefix: str) -> float | None:
    """Extract nutrient value from detail-response nutrients (nested: nutrient.name / amount)."""
    for n in nutrients:
        nutrient = n.get("nutrient", {})
        if nutrient.get("name", "").startswith(name_prefix):
            val = n.get("amount")
            return float(val) if val is not None else None
    return None


def search(q: str) -> list[FoodItem]:
    api_key = os.getenv("USDA_API_KEY", "")
    if not api_key:
        logger.warning("USDA_API_KEY not set — skipping USDA search")
        return []
    try:
        with httpx.Client(timeout=8) as client:
            resp = client.get(
                f"{_USDA_BASE}/foods/search",
                params={"query": q, "api_key": api_key, "pageSize": 10},
            )
        resp.raise_for_status()
        foods = resp.json().get("foods", [])[:10]
        return [_parse_search(f) for f in foods]
    except Exception as exc:
        logger.warning("USDA search failed: %s", exc)
        return []


def fetch(fdc_id: str) -> FoodItem | None:
    api_key = os.getenv("USDA_API_KEY", "")
    if not api_key:
        logger.warning("USDA_API_KEY not set — skipping USDA fetch")
        return None
    try:
        with httpx.Client(timeout=8) as client:
            resp = client.get(
                f"{_USDA_BASE}/food/{fdc_id}",
                params={"api_key": api_key},
            )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _parse_fetch(resp.json())
    except Exception as exc:
        logger.warning("USDA fetch failed for %s: %s", fdc_id, exc)
        return None


def _parse_search(food: dict) -> FoodItem:
    nutrients = food.get("foodNutrients", [])
    fdc_id = food.get("fdcId", 0)
    name = food.get("description", "Unknown")
    return FoodItem(
        id=f"usda_{fdc_id}",
        source="usda",
        name=name,
        name_en=name,
        calories_per_100g=_nv_search(nutrients, "Energy") or 0.0,
        protein_g=_nv_search(nutrients, "Protein") or 0.0,
        carbs_g=_nv_search(nutrients, "Carbohydrate") or 0.0,
        fat_g=_nv_search(nutrients, "Total lipid") or 0.0,
        fiber_g=_nv_search(nutrients, "Fiber"),
        sodium_mg=_nv_search(nutrients, "Sodium"),
        sugar_g=_nv_search(nutrients, "Sugars"),
    )


def _parse_fetch(data: dict) -> FoodItem:
    nutrients = data.get("foodNutrients", [])
    fdc_id = data.get("fdcId", 0)
    name = data.get("description", "Unknown")
    return FoodItem(
        id=f"usda_{fdc_id}",
        source="usda",
        name=name,
        name_en=name,
        calories_per_100g=_nv_fetch(nutrients, "Energy") or 0.0,
        protein_g=_nv_fetch(nutrients, "Protein") or 0.0,
        carbs_g=_nv_fetch(nutrients, "Carbohydrate") or 0.0,
        fat_g=_nv_fetch(nutrients, "Total lipid") or 0.0,
        fiber_g=_nv_fetch(nutrients, "Fiber"),
        sodium_mg=_nv_fetch(nutrients, "Sodium"),
        sugar_g=_nv_fetch(nutrients, "Sugars"),
    )
```

- [ ] **Step 5: Run tests — expect pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_usda_client.py -v
```

Expected: 5 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/integrations/nutrition/__init__.py backend/app/integrations/nutrition/usda_client.py tests/backend/integrations/nutrition/test_usda_client.py
git commit -m "feat(nutrition): USDA FoodData Central sync client"
```

---

## Task 3: Open Food Facts client

**Files:**
- Create: `backend/app/integrations/nutrition/off_client.py`
- Create: `tests/backend/integrations/nutrition/test_off_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/integrations/nutrition/test_off_client.py`:

```python
import respx
import httpx
from app.integrations.nutrition.off_client import search, fetch

_OFF_SEARCH = "https://world.openfoodfacts.org/cgi/search.pl"
_OFF_FETCH = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

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


import pytest
```

- [ ] **Step 2: Run failing tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_off_client.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.integrations.nutrition.off_client'`

- [ ] **Step 3: Create `backend/app/integrations/nutrition/off_client.py`**

```python
import logging

import httpx

from ...schemas.food import FoodItem

logger = logging.getLogger(__name__)

_OFF_BASE = "https://world.openfoodfacts.org"


def _parse_product(product: dict, product_id: str) -> FoodItem | None:
    name = (product.get("product_name") or "").strip()
    if not name:
        return None
    n = product.get("nutriments", {})
    return FoodItem(
        id=f"off_{product_id}",
        source="off",
        name=name,
        name_en=name,
        calories_per_100g=float(n.get("energy-kcal_100g") or 0.0),
        protein_g=float(n.get("proteins_100g") or 0.0),
        carbs_g=float(n.get("carbohydrates_100g") or 0.0),
        fat_g=float(n.get("fat_100g") or 0.0),
        fiber_g=float(n["fiber_100g"]) if "fiber_100g" in n else None,
        sodium_mg=float(n["sodium_100g"]) * 1000 if "sodium_100g" in n else None,
        sugar_g=float(n["sugars_100g"]) if "sugars_100g" in n else None,
    )


def search(q: str) -> list[FoodItem]:
    try:
        with httpx.Client(timeout=8) as client:
            resp = client.get(
                f"{_OFF_BASE}/cgi/search.pl",
                params={"search_terms": q, "json": "1", "page_size": 10},
            )
        resp.raise_for_status()
        products = resp.json().get("products", [])[:10]
        items = []
        for p in products:
            barcode = p.get("code", "")
            item = _parse_product(p, barcode)
            if item:
                items.append(item)
        return items
    except Exception as exc:
        logger.warning("OFF search failed: %s", exc)
        return []


def fetch(barcode: str) -> FoodItem | None:
    try:
        with httpx.Client(timeout=8) as client:
            resp = client.get(f"{_OFF_BASE}/api/v0/product/{barcode}.json")
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != 1:
            return None
        return _parse_product(data.get("product", {}), barcode)
    except Exception as exc:
        logger.warning("OFF fetch failed for %s: %s", barcode, exc)
        return None
```

- [ ] **Step 4: Run tests — expect pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_off_client.py -v
```

Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/nutrition/off_client.py tests/backend/integrations/nutrition/test_off_client.py
git commit -m "feat(nutrition): Open Food Facts sync client (search + barcode fetch)"
```

---

## Task 4: FCÉN loader + bootstrap script

**Files:**
- Create: `backend/app/integrations/nutrition/fcen_loader.py`
- Create: `backend/scripts/load_fcen.py`
- Create: `tests/fixtures/fcen/FOOD NAME.csv`
- Create: `tests/fixtures/fcen/NUTRIENT NAME.csv`
- Create: `tests/fixtures/fcen/NUTRIENT AMOUNT.csv`
- Create: `tests/backend/integrations/nutrition/test_fcen_loader.py`

- [ ] **Step 1: Write failing tests**

Create `tests/fixtures/fcen/FOOD NAME.csv`:

```
FoodID,FoodDescription,FoodDescriptionF
1,Beef Steak,"Boeuf, bifteck"
2,Chicken Breast,"Poulet, poitrine"
3,Milk 2%,Lait 2%
```

Create `tests/fixtures/fcen/NUTRIENT NAME.csv`:

```
NutrientID,NutrientName
208,Energy (kcal)
203,Protein
204,Total Fat
205,Carbohydrate
291,Dietary Fibre
307,Sodium
269,Sugars
```

Create `tests/fixtures/fcen/NUTRIENT AMOUNT.csv`:

```
FoodID,NutrientID,NutrientValue
1,208,207.0
1,203,26.0
1,204,11.0
1,205,0.0
1,307,55.0
2,208,165.0
2,203,31.0
2,204,3.6
2,205,0.0
3,208,52.0
3,203,3.4
3,204,2.0
3,205,5.0
3,291,0.0
3,269,5.0
```

Create `tests/backend/integrations/nutrition/test_fcen_loader.py`:

```python
from pathlib import Path
import pytest
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
```

- [ ] **Step 2: Run failing tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_fcen_loader.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.integrations.nutrition.fcen_loader'`

- [ ] **Step 3: Create `backend/app/integrations/nutrition/fcen_loader.py`**

```python
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from ...db.models import FoodCacheModel

logger = logging.getLogger(__name__)

# NutrientID → internal field name
_NUTRIENT_IDS: dict[str, str] = {
    "208": "energy",
    "203": "protein",
    "204": "fat",
    "205": "carbohydrate",
    "291": "fibre",
    "307": "sodium",
    "269": "sugars",
}


def load_fcen(
    food_name_csv: Path,
    nutrient_amount_csv: Path,
    nutrient_name_csv: Path,
    db: Session,
) -> int:
    """
    Parse FCÉN multi-file CSV set and upsert into food_cache with ttl_hours=NULL.

    Returns number of NEW rows inserted (re-runs return 0 if all rows already exist).
    """
    # 1. Load food names: FoodID → {name_en, name_fr}
    foods: dict[str, dict] = {}
    with open(food_name_csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            foods[row["FoodID"]] = {
                "name_en": row["FoodDescription"].strip(),
                "name_fr": row.get("FoodDescriptionF", "").strip() or None,
            }

    # 2. Load nutrient name map: NutrientID → field name (filter to known IDs)
    nutrient_map: dict[str, str] = {}
    with open(nutrient_name_csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            nid = row["NutrientID"]
            if nid in _NUTRIENT_IDS:
                nutrient_map[nid] = _NUTRIENT_IDS[nid]

    # 3. Load nutrient amounts → pivot per food
    nutrient_data: dict[str, dict[str, float]] = {}
    with open(nutrient_amount_csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            food_id = row["FoodID"]
            nid = row["NutrientID"]
            if nid not in nutrient_map:
                continue
            field = nutrient_map[nid]
            if food_id not in nutrient_data:
                nutrient_data[food_id] = {}
            val_str = row.get("NutrientValue", "").strip()
            nutrient_data[food_id][field] = float(val_str) if val_str else 0.0

    # 4. Upsert into food_cache
    now = datetime.now(timezone.utc)
    inserted = 0
    for food_id, names in foods.items():
        nd = nutrient_data.get(food_id, {})
        energy = nd.get("energy")
        if energy is None:
            continue  # skip foods with no energy data

        existing = db.get(FoodCacheModel, f"fcen_{food_id}")
        if existing:
            existing.name = names["name_en"]
            existing.name_fr = names["name_fr"]
            existing.calories_per_100g = energy
            existing.protein_g = nd.get("protein", 0.0)
            existing.carbs_g = nd.get("carbohydrate", 0.0)
            existing.fat_g = nd.get("fat", 0.0)
            existing.fiber_g = nd.get("fibre")
            existing.sodium_mg = nd.get("sodium")
            existing.sugar_g = nd.get("sugars")
            existing.cached_at = now
        else:
            db.add(FoodCacheModel(
                id=f"fcen_{food_id}",
                source="fcen",
                name=names["name_en"],
                name_fr=names["name_fr"],
                calories_per_100g=energy,
                protein_g=nd.get("protein", 0.0),
                carbs_g=nd.get("carbohydrate", 0.0),
                fat_g=nd.get("fat", 0.0),
                fiber_g=nd.get("fibre"),
                sodium_mg=nd.get("sodium"),
                sugar_g=nd.get("sugars"),
                cached_at=now,
                ttl_hours=None,
            ))
            inserted += 1

    db.commit()
    logger.info("Loaded %d new FCÉN items.", inserted)
    return inserted
```

- [ ] **Step 4: Create `backend/scripts/load_fcen.py`**

```python
"""
FCÉN bootstrap script.

Usage:
    python -m scripts.load_fcen \
        --food-csv path/to/FOOD_NAME.csv \
        --nutrient-amount-csv path/to/NUTRIENT_AMOUNT.csv \
        --nutrient-name-csv path/to/NUTRIENT_NAME.csv \
        [--db-url sqlite:///path/to/db.sqlite]

Expected: ~6000 items, ~5s.
Re-running is safe (idempotent upsert).
"""
import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Load FCÉN data into food_cache table.")
    parser.add_argument("--food-csv", required=True, help="Path to FOOD NAME.csv")
    parser.add_argument("--nutrient-amount-csv", required=True, help="Path to NUTRIENT AMOUNT.csv")
    parser.add_argument("--nutrient-name-csv", required=True, help="Path to NUTRIENT NAME.csv")
    parser.add_argument("--db-url", default=None, help="SQLAlchemy DB URL (default: app engine)")
    args = parser.parse_args()

    if args.db_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(args.db_url)
        Session = sessionmaker(engine)
    else:
        from app.db.database import engine
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(engine)

    from app.integrations.nutrition.fcen_loader import load_fcen

    with Session() as db:
        count = load_fcen(
            food_name_csv=Path(args.food_csv),
            nutrient_amount_csv=Path(args.nutrient_amount_csv),
            nutrient_name_csv=Path(args.nutrient_name_csv),
            db=db,
        )
    print(f"Loaded {count} FCÉN items.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests — expect pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_fcen_loader.py -v
```

Expected: 4 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/integrations/nutrition/fcen_loader.py backend/scripts/load_fcen.py "tests/fixtures/fcen/FOOD NAME.csv" "tests/fixtures/fcen/NUTRIENT NAME.csv" "tests/fixtures/fcen/NUTRIENT AMOUNT.csv" tests/backend/integrations/nutrition/test_fcen_loader.py
git commit -m "feat(nutrition): FCÉN multi-file loader + load_fcen CLI script"
```

---

## Task 5: NutritionLookupService (unified search + fetch)

**Files:**
- Create: `backend/app/integrations/nutrition/unified_service.py`
- Create: `tests/backend/integrations/nutrition/test_unified_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/integrations/nutrition/test_unified_service.py`:

```python
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

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
```

- [ ] **Step 2: Run failing tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_unified_service.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.integrations.nutrition.unified_service'`

- [ ] **Step 3: Create `backend/app/integrations/nutrition/unified_service.py`**

```python
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ...db.models import FoodCacheModel
from ...schemas.food import FoodItem
from . import usda_client, off_client


def _is_expired(row: FoodCacheModel) -> bool:
    if row.ttl_hours is None:
        return False
    expiry = row.cached_at + timedelta(hours=row.ttl_hours)
    return datetime.now(timezone.utc) > expiry


def _row_to_food_item(row: FoodCacheModel) -> FoodItem:
    return FoodItem(
        id=row.id,
        source=row.source,
        name=row.name_fr or row.name,
        name_en=row.name,
        name_fr=row.name_fr,
        calories_per_100g=row.calories_per_100g or 0.0,
        protein_g=row.protein_g or 0.0,
        carbs_g=row.carbs_g or 0.0,
        fat_g=row.fat_g or 0.0,
        fiber_g=row.fiber_g,
        sodium_mg=row.sodium_mg,
        sugar_g=row.sugar_g,
    )


def _upsert_items(items: list[FoodItem], ttl_hours: int, db: Session) -> None:
    now = datetime.now(timezone.utc)
    for item in items:
        existing = db.get(FoodCacheModel, item.id)
        if existing:
            existing.name = item.name_en
            existing.name_fr = item.name_fr
            existing.calories_per_100g = item.calories_per_100g
            existing.protein_g = item.protein_g
            existing.carbs_g = item.carbs_g
            existing.fat_g = item.fat_g
            existing.fiber_g = item.fiber_g
            existing.sodium_mg = item.sodium_mg
            existing.sugar_g = item.sugar_g
            existing.cached_at = now
            existing.ttl_hours = ttl_hours
        else:
            db.add(FoodCacheModel(
                id=item.id,
                source=item.source,
                name=item.name_en,
                name_fr=item.name_fr,
                calories_per_100g=item.calories_per_100g,
                protein_g=item.protein_g,
                carbs_g=item.carbs_g,
                fat_g=item.fat_g,
                fiber_g=item.fiber_g,
                sodium_mg=item.sodium_mg,
                sugar_g=item.sugar_g,
                cached_at=now,
                ttl_hours=ttl_hours,
            ))
    db.commit()


def _cache_query(q: str, db: Session, source_filter: str | None = None):
    pattern = f"%{q.lower()}%"
    query = db.query(FoodCacheModel).filter(
        (func.lower(FoodCacheModel.name).like(pattern))
        | (func.lower(FoodCacheModel.name_fr).like(pattern))
    )
    if source_filter:
        query = query.filter(FoodCacheModel.source == source_filter)
    return query.limit(20).all()


def search(q: str, db: Session) -> list[FoodItem]:
    rows = _cache_query(q, db)
    fresh = [r for r in rows if not _is_expired(r)]
    if fresh:
        return [_row_to_food_item(r) for r in fresh]

    # Cache miss — fan-out to FCÉN (already in DB), USDA, OFF
    fcen_rows = _cache_query(q, db, source_filter="fcen")
    fcen_items = [_row_to_food_item(r) for r in fcen_rows]
    usda_items = usda_client.search(q)
    off_items = off_client.search(q)

    if usda_items:
        _upsert_items(usda_items, ttl_hours=168, db=db)
    if off_items:
        _upsert_items(off_items, ttl_hours=24, db=db)

    # Merge: fcen → usda → off, deduplicate by id, max 20
    seen: set[str] = set()
    merged: list[FoodItem] = []
    for item in fcen_items + usda_items + off_items:
        if item.id not in seen:
            seen.add(item.id)
            merged.append(item)
        if len(merged) >= 20:
            break
    return merged


def fetch(food_id: str, db: Session) -> FoodItem | None:
    row = db.get(FoodCacheModel, food_id)
    if row and not _is_expired(row):
        return _row_to_food_item(row)

    if food_id.startswith("usda_"):
        item = usda_client.fetch(food_id[5:])
        ttl = 168
    elif food_id.startswith("off_"):
        item = off_client.fetch(food_id[4:])
        ttl = 24
    elif food_id.startswith("fcen_"):
        return None  # static data; not in cache = not available
    else:
        return None

    if item:
        _upsert_items([item], ttl_hours=ttl, db=db)
    return item
```

- [ ] **Step 4: Run tests — expect pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/nutrition/test_unified_service.py -v
```

Expected: 11 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/nutrition/unified_service.py tests/backend/integrations/nutrition/test_unified_service.py
git commit -m "feat(nutrition): NutritionLookupService — cache-first search + TTL expiry + fan-out"
```

---

## Task 6: Routes + cleanup + main.py update

**Files:**
- Create: `backend/app/routes/food_search.py`
- Delete: `backend/app/routes/food.py`
- Modify: `backend/app/main.py`
- Modify: `.env.example`
- Create: `tests/backend/api/test_food_search.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/api/test_food_search.py`:

```python
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
```

- [ ] **Step 2: Run failing tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_food_search.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.routes.food_search'` (or import error from food.py still being present)

- [ ] **Step 3: Create `backend/app/routes/food_search.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_athlete_id
from ..integrations.nutrition.unified_service import fetch as nutrition_fetch
from ..integrations.nutrition.unified_service import search as nutrition_search
from ..schemas.food import FoodItem

router = APIRouter(prefix="/nutrition", tags=["food-search"])

DB = Annotated[Session, Depends(get_db)]


@router.get("/search", response_model=list[FoodItem])
def search_food(
    q: Annotated[str, Query(min_length=1)],
    db: DB,
    _athlete_id: Annotated[str, Depends(get_current_athlete_id)],
    limit: int = Query(default=20, ge=1, le=50),
) -> list[FoodItem]:
    return nutrition_search(q, db)[:limit]


@router.get("/food/{food_id}", response_model=FoodItem)
def get_food_item(
    food_id: str,
    db: DB,
    _athlete_id: Annotated[str, Depends(get_current_athlete_id)],
) -> FoodItem:
    item = nutrition_fetch(food_id, db)
    if item is None:
        raise HTTPException(status_code=404, detail="Food item not found")
    return item
```

- [ ] **Step 4: Update `backend/app/main.py`**

Replace:
```python
from .routes.food import router as food_router
```
With:
```python
from .routes.food_search import router as food_search_router
```

Replace:
```python
app.include_router(food_router)
```
With:
```python
app.include_router(food_search_router)
```

- [ ] **Step 5: Delete `backend/app/routes/food.py`**

```bash
git rm backend/app/routes/food.py
```

- [ ] **Step 6: Add `USDA_API_KEY` to `.env.example`**

Append to `.env.example`:

```bash
# USDA FoodData Central API key (replaces FOOD_API_KEY)
# Free tier: https://fdc.nal.usda.gov/api-key-signup.html
USDA_API_KEY=your_key_here
```

- [ ] **Step 7: Run tests — expect pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_food_search.py -v
```

Expected: 5 PASSED

- [ ] **Step 8: Run full suite**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q --tb=short 2>&1 | tail -10
```

Expected: all tests pass (2161+ prior + ~30 new).

- [ ] **Step 9: Commit**

```bash
git add backend/app/routes/food_search.py backend/app/main.py .env.example
git commit -m "feat(nutrition): /nutrition/search + /nutrition/food/{id} routes; remove food.py"
```

---

## Task 7: INTEGRATIONS.md nutrition section

**Files:**
- Modify: `docs/backend/INTEGRATIONS.md`

- [ ] **Step 1: Add nutrition section to `docs/backend/INTEGRATIONS.md`**

Append the following section to the file:

```markdown
---

## Nutrition Lookup (V3-P)

Unified food search backed by three sources with TTL-cached SQLite storage.

### Sources

| Source | ID prefix | TTL | Key required |
|---|---|---|---|
| USDA FoodData Central | `usda_{fdcId}` | 7 days (168h) | `USDA_API_KEY` env var |
| Open Food Facts | `off_{barcode}` | 24 hours | None |
| Canadian Nutrient File (FCÉN) | `fcen_{FoodID}` | Permanent (NULL) | N/A — bootstrap script |

### Endpoints

```
GET /nutrition/search?q=<str>&limit=20
Authorization: Bearer <token>
→ 200: list[FoodItem]
→ 422: if q is empty

GET /nutrition/food/{food_id}
Authorization: Bearer <token>
→ 200: FoodItem
→ 404: if not found in cache or any source
```

### Search flow

1. Cache lookup (SQLite `food_cache` table, `name LIKE %q%`)
2. If ≥ 1 non-expired result → return immediately
3. Cache miss → fan-out: FCÉN (re-query DB) + USDA + OFF (sequential, graceful fallback)
4. Merge order: fcen → usda → off, deduplicate by id, max 20
5. Upsert USDA (168h TTL) and OFF (24h TTL) results to cache

### FoodItem schema

```python
class FoodItem(BaseModel):
    id: str                 # "usda_789", "off_3017620422003", "fcen_456"
    source: str             # "usda" | "off" | "fcen"
    name: str               # display name (name_fr if available, else name_en)
    name_en: str
    name_fr: str | None = None
    calories_per_100g: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None = None
    sodium_mg: float | None = None
    sugar_g: float | None = None
```

### FCÉN Bootstrap

Health Canada FCÉN is a multi-file relational dataset (~6000 foods). Bootstrap once:

```bash
python -m scripts.load_fcen \
    --food-csv path/to/FOOD_NAME.csv \
    --nutrient-amount-csv path/to/NUTRIENT_AMOUNT.csv \
    --nutrient-name-csv path/to/NUTRIENT_NAME.csv
```

Re-running is idempotent. FCÉN rows have `ttl_hours=NULL` (permanent, never re-fetched).

### Environment variables

| Variable | Purpose |
|---|---|
| `USDA_API_KEY` | USDA FDC API key. If unset, USDA source is skipped gracefully. |

### Module locations

| File | Responsibility |
|---|---|
| `backend/app/integrations/nutrition/usda_client.py` | USDA search + fetch (sync httpx) |
| `backend/app/integrations/nutrition/off_client.py` | OFF search + barcode fetch (sync httpx) |
| `backend/app/integrations/nutrition/fcen_loader.py` | JOIN 3 FCÉN CSVs → bulk-upsert |
| `backend/app/integrations/nutrition/unified_service.py` | Cache-first search/fetch orchestration |
| `backend/app/routes/food_search.py` | FastAPI router (prefix: `/nutrition`) |
| `backend/scripts/load_fcen.py` | CLI bootstrap script |
```

- [ ] **Step 2: Commit**

```bash
git add docs/backend/INTEGRATIONS.md
git commit -m "docs(nutrition): add FCÉN + USDA + OFF integration reference to INTEGRATIONS.md"
```

- [ ] **Step 3: Final full suite run**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q --tb=short 2>&1 | tail -5
```

Expected: all tests pass.
