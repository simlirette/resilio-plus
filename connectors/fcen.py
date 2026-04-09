"""
Connecteur FCÉN — Fichier canadien sur les éléments nutritifs (Santé Canada).
Chargement local CSV. Recherche par nom (FR ou EN), insensible à la casse.
"""

import csv
from pathlib import Path

_FCEN_CSV = Path(__file__).parents[1] / "data" / "fcen_nutrients.csv"

# Each row normalized to: {food_code, description_fr, description_en, nutrients}
_FOOD_DB: list[dict] | None = None


def _load_db() -> list[dict]:
    global _FOOD_DB
    if _FOOD_DB is None:
        rows = []
        with open(_FCEN_CSV, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    "food_code": row["food_code"],
                    "description_fr": row["food_description_fr"],
                    "description_en": row["food_description_en"],
                    "source": "fcen",
                    "nutrients": {
                        "calories": float(row["calories"]),
                        "protein_g": float(row["protein_g"]),
                        "fat_g": float(row["fat_g"]),
                        "carbs_g": float(row["carbs_g"]),
                        "fiber_g": float(row["fiber_g"]),
                    },
                })
        _FOOD_DB = rows
    return _FOOD_DB


class FcenConnector:
    """Recherche locale dans la base FCÉN (CSV Santé Canada)."""

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """
        Recherche par nom (FR ou EN), insensible à la casse, sous-chaîne.
        Retourne jusqu'à `limit` résultats.
        """
        q = query.lower().strip()
        results = []
        for food in _load_db():
            if q in food["description_fr"].lower() or q in food["description_en"].lower():
                results.append(food)
                if len(results) >= limit:
                    break
        return results
