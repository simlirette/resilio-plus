import logging
import os
from typing import Any

import httpx

from ...schemas.food import FoodItem

logger = logging.getLogger(__name__)

_USDA_BASE = "https://api.nal.usda.gov/fdc/v1"


def _nv_search(nutrients: list[dict[str, Any]], name_prefix: str) -> float | None:
    """Extract nutrient value from search-response nutrients (flat list with nutrientName/value)."""
    for n in nutrients:
        if n.get("nutrientName", "").startswith(name_prefix):
            val = n.get("value")
            return float(val) if val is not None else None
    return None


def _nv_fetch(nutrients: list[dict[str, Any]], name_prefix: str) -> float | None:
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


def _parse_search(food: dict[str, Any]) -> FoodItem:
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


def _parse_fetch(data: dict[str, Any]) -> FoodItem:
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
