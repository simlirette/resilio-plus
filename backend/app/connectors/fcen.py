"""
FCÉN (Fichier canadien sur les éléments nutritifs) connector.

Reads data/fcen_nutrients.csv — Health Canada's nutrient database.
Provides fuzzy food search returning macros + key micros per 100g.

CSV format (Health Canada export):
    food_id, food_name_fr, food_name_en, energy_kcal, protein_g,
    fat_g, carb_g, fiber_g, sugar_g, sodium_mg, calcium_mg,
    iron_mg, vitamin_c_mg
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from pathlib import Path

_CSV_PATH = Path(__file__).parent.parent.parent.parent / "data" / "fcen_nutrients.csv"

# Column name aliases — tolerant of minor formatting differences in CSV
_COL_ALIASES: dict[str, list[str]] = {
    "food_id":      ["food_id", "id", "fdcid"],
    "name_fr":      ["food_name_fr", "nom_fr", "description_fr", "name_fr"],
    "name_en":      ["food_name_en", "name_en", "description", "name"],
    "energy_kcal":  ["energy_kcal", "energy_(kcal)", "calories", "energy"],
    "protein_g":    ["protein_g", "protein_(g)", "protein"],
    "fat_g":        ["fat_g", "total_fat_(g)", "total_fat_g", "fat"],
    "carb_g":       ["carb_g", "carbohydrate_(g)", "carbohydrate_g", "carbohydrate"],
    "fiber_g":      ["fiber_g", "dietary_fiber_(g)", "fiber"],
    "sugar_g":      ["sugar_g", "total_sugars_(g)", "sugars_g"],
    "sodium_mg":    ["sodium_mg", "sodium_(mg)", "sodium"],
    "calcium_mg":   ["calcium_mg", "calcium_(mg)", "calcium"],
    "iron_mg":      ["iron_mg", "iron_(mg)", "iron"],
    "vitamin_c_mg": ["vitamin_c_mg", "vitamin_c_(mg)", "vitamin_c"],
}


@dataclass
class FcenFood:
    food_id: str
    name_fr: str
    name_en: str
    energy_kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    fiber_g: float
    sugar_g: float | None
    sodium_mg: float | None
    calcium_mg: float | None
    iron_mg: float | None
    vitamin_c_mg: float | None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items()}


def _resolve_header(header: str, aliases: list[str]) -> bool:
    return header.strip().lower().replace(" ", "_") in aliases


def _map_columns(fieldnames: list[str]) -> dict[str, str | None]:
    """Return mapping from our canonical name → actual CSV column name."""
    lower_fields = {f.strip().lower().replace(" ", "_"): f for f in fieldnames}
    result: dict[str, str | None] = {}
    for canonical, aliases in _COL_ALIASES.items():
        matched = next((lower_fields[a] for a in aliases if a in lower_fields), None)
        result[canonical] = matched
    return result


def _safe_float(value: str | None) -> float | None:
    if not value or value.strip() == "":
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def _load_fcen(path: Path = _CSV_PATH) -> list[FcenFood]:
    if not path.exists():
        return []

    items: list[FcenFood] = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        col = _map_columns(list(reader.fieldnames or []))

        def _get(row: dict, key: str) -> str | None:
            col_name = col.get(key)
            return row.get(col_name) if col_name else None

        for row in reader:
            name_fr = (_get(row, "name_fr") or "").strip()
            name_en = (_get(row, "name_en") or "").strip()
            if not name_fr and not name_en:
                continue

            energy = _safe_float(_get(row, "energy_kcal"))
            protein = _safe_float(_get(row, "protein_g"))
            fat = _safe_float(_get(row, "fat_g"))
            carb = _safe_float(_get(row, "carb_g"))
            fiber = _safe_float(_get(row, "fiber_g"))

            items.append(
                FcenFood(
                    food_id=(_get(row, "food_id") or "").strip(),
                    name_fr=name_fr or name_en,
                    name_en=name_en or name_fr,
                    energy_kcal=energy or 0.0,
                    protein_g=protein or 0.0,
                    fat_g=fat or 0.0,
                    carb_g=carb or 0.0,
                    fiber_g=fiber or 0.0,
                    sugar_g=_safe_float(_get(row, "sugar_g")),
                    sodium_mg=_safe_float(_get(row, "sodium_mg")),
                    calcium_mg=_safe_float(_get(row, "calcium_mg")),
                    iron_mg=_safe_float(_get(row, "iron_mg")),
                    vitamin_c_mg=_safe_float(_get(row, "vitamin_c_mg")),
                )
            )
    return items


class FcenConnector:
    """
    Reads FCÉN nutrient database CSV and provides fuzzy food search.

    The database is loaded once at instantiation and kept in memory.
    For the production server, instantiate once at module level (see routes/food.py).
    """

    def __init__(self, csv_path: Path = _CSV_PATH) -> None:
        self._items = _load_fcen(csv_path)

    @property
    def loaded(self) -> bool:
        return len(self._items) > 0

    def search(self, query: str, limit: int = 20) -> list[FcenFood]:
        """
        Case-insensitive substring search on both French and English names.

        Falls back to fuzzy matching (difflib) when no substring match found.
        Returns up to `limit` results sorted by match quality.
        """
        q = query.strip().lower()
        if not q:
            return []

        # 1. Exact substring matches (fast path)
        exact: list[FcenFood] = []
        for item in self._items:
            if q in item.name_fr.lower() or q in item.name_en.lower():
                exact.append(item)
        if exact:
            return exact[:limit]

        # 2. Fuzzy fallback — word-level token overlap
        import difflib

        scored: list[tuple[float, FcenFood]] = []
        for item in self._items:
            score = max(
                difflib.SequenceMatcher(None, q, item.name_fr.lower()).ratio(),
                difflib.SequenceMatcher(None, q, item.name_en.lower()).ratio(),
            )
            if score > 0.4:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]
