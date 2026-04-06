"""
Food search connector — USDA FoodData Central + Open Food Facts.
Pas de stockage en DB en S4 — retour JSON uniquement.
"""

import httpx

from core.config import settings

# USDA nutrient IDs (par 100g)
_NUTRIENT_IDS = {
    1008: "calories",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carbs_g",
}


class FoodSearchConnector:
    USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    OFF_BASE_URL = "https://world.openfoodfacts.org/api/v2"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport)

    async def search_usda(self, query: str, page_size: int = 5) -> list[dict]:
        """
        Recherche USDA FoodData Central par texte.
        Retourne une liste de { fdcId, description, nutrients }.
        """
        async with self._client() as client:
            resp = await client.get(
                f"{self.USDA_BASE_URL}/foods/search",
                params={
                    "query": query,
                    "pageSize": page_size,
                    "api_key": settings.USDA_API_KEY or "DEMO_KEY",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for food in data.get("foods", []):
            nutrients: dict[str, float] = {v: 0.0 for v in _NUTRIENT_IDS.values()}
            for nutrient in food.get("foodNutrients", []):
                nid = nutrient.get("nutrientId")
                if nid in _NUTRIENT_IDS:
                    nutrients[_NUTRIENT_IDS[nid]] = float(nutrient.get("value", 0))
            results.append({
                "fdcId": food.get("fdcId"),
                "description": food.get("description", ""),
                "nutrients": nutrients,
            })
        return results

    async def search_barcode(self, barcode: str) -> dict | None:
        """
        Recherche Open Food Facts par code-barres.
        Retourne { name, nutrients } ou None si non trouvé.
        """
        async with self._client() as client:
            resp = await client.get(
                f"{self.OFF_BASE_URL}/product/{barcode}",
                params={"fields": "nutriments,product_name"},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != 1:
            return None

        product = data.get("product", {})
        nutriments = product.get("nutriments", {})

        return {
            "name": product.get("product_name", ""),
            "nutrients": {
                "calories": float(nutriments.get("energy-kcal_100g", 0)),
                "protein_g": float(nutriments.get("proteins_100g", 0)),
                "fat_g": float(nutriments.get("fat_100g", 0)),
                "carbs_g": float(nutriments.get("carbohydrates_100g", 0)),
            },
        }
