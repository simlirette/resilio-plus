"""
ATHLETES ROUTES — Resilio+
GET /athletes/me — Return authenticated athlete's profile.
"""
from fastapi import APIRouter, Depends

from api.deps import get_current_athlete
from models.database import Athlete

router = APIRouter()


@router.get("/me")
async def get_me(athlete: Athlete = Depends(get_current_athlete)) -> dict:
    return {
        "id": str(athlete.id),
        "email": athlete.email,
        "first_name": athlete.first_name,
        "age": athlete.age,
        "sex": athlete.sex,
        "weight_kg": athlete.weight_kg,
        "height_cm": athlete.height_cm,
        "body_fat_percent": athlete.body_fat_percent,
        "resting_hr": athlete.resting_hr,
        "max_hr_measured": athlete.max_hr_measured,
    }
