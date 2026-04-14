from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ...db.models import FoodCacheModel
from ...schemas.food import FoodItem
from . import usda_client, off_client


def _is_expired(row: FoodCacheModel) -> bool:
    if row.ttl_hours is None:
        return False
    cached_at = row.cached_at
    # SQLite returns naive datetimes; treat them as UTC
    if cached_at.tzinfo is None:
        cached_at = cached_at.replace(tzinfo=timezone.utc)
    expiry = cached_at + timedelta(hours=row.ttl_hours)
    return datetime.now(timezone.utc) > expiry


def _row_to_food_item(row: FoodCacheModel) -> FoodItem:
    return FoodItem(
        id=row.id,
        source=row.source,
        name=row.name_fr or row.name,
        name_en=row.name_en or row.name,
        name_fr=row.name_fr,
        calories_per_100g=row.calories_per_100g or 0.0,
        protein_g=row.protein_g or 0.0,
        carbs_g=row.carbs_g or 0.0,
        fat_g=row.fat_g or 0.0,
        fiber_g=row.fiber_g,
        sodium_mg=row.sodium_mg,
        sugar_g=row.sugar_g,
    )


def _upsert_items(items: list[FoodItem], ttl_hours: int, db: Session) -> None:
    now = datetime.now(timezone.utc)
    for item in items:
        existing = db.get(FoodCacheModel, item.id)
        if existing:
            existing.name = item.name_en
            existing.name_en = item.name_en
            existing.name_fr = item.name_fr
            existing.calories_per_100g = item.calories_per_100g
            existing.protein_g = item.protein_g
            existing.carbs_g = item.carbs_g
            existing.fat_g = item.fat_g
            existing.fiber_g = item.fiber_g
            existing.sodium_mg = item.sodium_mg
            existing.sugar_g = item.sugar_g
            existing.cached_at = now
            existing.ttl_hours = ttl_hours
        else:
            db.add(FoodCacheModel(
                id=item.id,
                source=item.source,
                name=item.name_en,
                name_en=item.name_en,
                name_fr=item.name_fr,
                calories_per_100g=item.calories_per_100g,
                protein_g=item.protein_g,
                carbs_g=item.carbs_g,
                fat_g=item.fat_g,
                fiber_g=item.fiber_g,
                sodium_mg=item.sodium_mg,
                sugar_g=item.sugar_g,
                cached_at=now,
                ttl_hours=ttl_hours,
            ))
    db.commit()


def _cache_query(q: str, db: Session, source_filter: str | None = None):
    pattern = f"%{q.lower()}%"
    query = db.query(FoodCacheModel).filter(
        (func.lower(FoodCacheModel.name).like(pattern))
        | (func.lower(FoodCacheModel.name_fr).like(pattern))
    )
    if source_filter:
        query = query.filter(FoodCacheModel.source == source_filter)
    return query.limit(20).all()


def search(q: str, db: Session) -> list[FoodItem]:
    rows = _cache_query(q, db)
    fresh = [r for r in rows if not _is_expired(r)]
    if fresh:
        return [_row_to_food_item(r) for r in fresh]

    # Cache miss — fan-out to FCÉN (already in DB), USDA, OFF
    fcen_rows = _cache_query(q, db, source_filter="fcen")
    fcen_items = [_row_to_food_item(r) for r in fcen_rows]
    usda_items = usda_client.search(q)
    off_items = off_client.search(q)

    if usda_items:
        _upsert_items(usda_items, ttl_hours=168, db=db)
    if off_items:
        _upsert_items(off_items, ttl_hours=24, db=db)

    # Merge: fcen → usda → off, deduplicate by id, max 20
    seen: set[str] = set()
    merged: list[FoodItem] = []
    for item in fcen_items + usda_items + off_items:
        if item.id not in seen:
            seen.add(item.id)
            merged.append(item)
        if len(merged) >= 20:
            break
    return merged


def fetch(food_id: str, db: Session) -> FoodItem | None:
    row = db.get(FoodCacheModel, food_id)
    if row and not _is_expired(row):
        return _row_to_food_item(row)

    if food_id.startswith("usda_"):
        item = usda_client.fetch(food_id[5:])
        ttl = 168
    elif food_id.startswith("off_"):
        item = off_client.fetch(food_id[4:])
        ttl = 24
    elif food_id.startswith("fcen_"):
        return None  # static data; not in cache = not available
    else:
        return None

    if item:
        _upsert_items([item], ttl_hours=ttl, db=db)
    return item
