from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_current_athlete_id, get_db
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
