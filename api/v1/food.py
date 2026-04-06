"""
FastAPI router — recherche alimentaire USDA + Open Food Facts.
Pas d'auth requise — données publiques (JWT en S11 si nécessaire).
"""

from fastapi import APIRouter, HTTPException, Query

from connectors.food_search import FoodSearchConnector

router = APIRouter()
_food = FoodSearchConnector()


@router.get("/food/search")
async def food_search(
    q: str = Query(..., min_length=1),
    page_size: int = Query(default=5, ge=1, le=20),
) -> dict:
    """Recherche USDA FoodData Central par texte libre."""
    results = await _food.search_usda(q, page_size=page_size)
    return {"results": results}


@router.get("/food/barcode/{barcode}")
async def food_barcode(barcode: str) -> dict:
    """Recherche Open Food Facts par code-barres EAN."""
    result = await _food.search_barcode(barcode)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Product with barcode {barcode} not found"
        )
    return result
