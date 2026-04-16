import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    foods: dict[str, dict[str, Any]] = {}
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
            existing.name_en = names["name_en"]
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
            db.add(
                FoodCacheModel(
                    id=f"fcen_{food_id}",
                    source="fcen",
                    name=names["name_en"],
                    name_en=names["name_en"],
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
                )
            )
            inserted += 1

    db.commit()
    logger.info("Loaded %d new FCÉN items.", inserted)
    return inserted
