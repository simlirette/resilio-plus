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
