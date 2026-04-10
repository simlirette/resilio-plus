"""
Food database routes — search and barcode lookup.

Data sources:
  - Local cache: data/food_database_cache.json (USDA + FCÉN items)
  - USDA FoodData Central: api.nal.usda.gov (requires FOOD_API_KEY env var)
  - Open Food Facts: world.openfoodfacts.org (barcode lookup, no key required)

All endpoints require the authenticated athlete to own the resource.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from ..db.models import AthleteModel
from ..dependencies import get_db, get_current_athlete_id
from sqlalchemy.orm import Session

router = APIRouter(prefix="/athletes", tags=["food"])

# ---------------------------------------------------------------------------
# Load local cache once at module import
# ---------------------------------------------------------------------------
_CACHE_PATH = Path(__file__).parent.parent.parent.parent / "data" / "food_database_cache.json"

def _load_cache() -> list[dict]:
    try:
        with open(_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", [])
    except FileNotFoundError:
        return []

_CACHE: list[dict] = _load_cache()

# ---------------------------------------------------------------------------
# External API constants
# ---------------------------------------------------------------------------
_USDA_BASE = "https://api.nal.usda.gov/fdc/v1"
_OFF_BASE = "https://world.openfoodfacts.org"

DB = Annotated[Session, Depends(get_db)]


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
    db: DB,
) -> str:
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.id != current_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return current_id


def _search_cache(query: str, source_filter: str | None = None) -> list[dict]:
    """Case-insensitive substring search on name and name_fr."""
    q = query.lower().strip()
    results = []
    for item in _CACHE:
        if source_filter and item.get("source") != source_filter:
            continue
        name = item.get("name", "").lower()
        name_fr = item.get("name_fr", "").lower()
        if q in name or q in name_fr:
            results.append(_item_to_dict(item))
    return results


def _item_to_dict(item: dict) -> dict:
    return {
        "name": item.get("name_fr") or item.get("name", ""),
        "name_en": item.get("name", ""),
        "calories_per_100g": item.get("calories_per_100g", 0.0),
        "carbs_g": item.get("carbs_g", 0.0),
        "protein_g": item.get("protein_g", 0.0),
        "fat_g": item.get("fat_g", 0.0),
        "fiber_g": item.get("fiber_g", 0.0),
        "source": item.get("source", "cache"),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{athlete_id}/food/search")
async def search_food(
    athlete_id: str,
    q: Annotated[str, Query(min_length=1)],
    _: Annotated[str, Depends(_require_own)],
) -> list[dict]:
    """
    Search local cache first, then USDA FoodData Central (if API key set).
    Returns merged results sorted by source: cache → usda.
    """
    results = _search_cache(q)

    api_key = os.getenv("FOOD_API_KEY", "")
    if api_key:
        usda_results = await _search_usda(q, api_key)
        results.extend(usda_results)

    return results


@router.get("/{athlete_id}/food/search/fcen")
def search_fcen(
    athlete_id: str,
    q: Annotated[str, Query(min_length=1)],
    _: Annotated[str, Depends(_require_own)],
) -> list[dict]:
    """Search local FCÉN (Santé Canada) items only."""
    return _search_cache(q, source_filter="fcen")


@router.get("/{athlete_id}/food/barcode/{barcode}")
async def get_by_barcode(
    athlete_id: str,
    barcode: str,
    _: Annotated[str, Depends(_require_own)],
) -> dict:
    """
    Look up a product by barcode via Open Food Facts.
    Returns 404 if the product is not found.
    """
    item = await _off_barcode(barcode)
    if item is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return item


# ---------------------------------------------------------------------------
# Internal async helpers
# ---------------------------------------------------------------------------

async def _search_usda(query: str, api_key: str) -> list[dict]:
    params = {"query": query, "api_key": api_key, "pageSize": 10}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"{_USDA_BASE}/foods/search", params=params)
        if resp.status_code != 200:
            return []
        foods = resp.json().get("foods", [])
        return [_parse_usda(f) for f in foods[:10]]
    except Exception:
        return []


def _parse_usda(food: dict) -> dict:
    nutrients = food.get("foodNutrients", [])
    def _nv(name: str) -> float:
        for n in nutrients:
            if n.get("nutrientName", "").startswith(name):
                return float(n.get("value") or 0.0)
        return 0.0
    return {
        "name": food.get("description", "Unknown"),
        "name_en": food.get("description", "Unknown"),
        "calories_per_100g": _nv("Energy"),
        "carbs_g": _nv("Carbohydrate"),
        "protein_g": _nv("Protein"),
        "fat_g": _nv("Total lipid"),
        "fiber_g": _nv("Fiber"),
        "source": "usda",
    }


async def _off_barcode(barcode: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"{_OFF_BASE}/api/v0/product/{barcode}.json")
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != 1:
            return None
        p = data.get("product", {})
        n = p.get("nutriments", {})
        name = p.get("product_name", "").strip()
        if not name:
            return None
        return {
            "name": name,
            "name_en": name,
            "calories_per_100g": float(n.get("energy-kcal_100g") or 0.0),
            "carbs_g": float(n.get("carbohydrates_100g") or 0.0),
            "protein_g": float(n.get("proteins_100g") or 0.0),
            "fat_g": float(n.get("fat_100g") or 0.0),
            "fiber_g": float(n.get("fiber_100g") or 0.0),
            "source": "open_food_facts",
        }
    except Exception:
        return None
