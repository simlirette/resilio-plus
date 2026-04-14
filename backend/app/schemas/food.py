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
