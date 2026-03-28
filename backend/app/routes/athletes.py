import json
import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import AthleteModel
from app.dependencies import get_db
from app.schemas.athlete import AthleteCreate, AthleteResponse, AthleteUpdate, Sport

router = APIRouter(prefix="/athletes", tags=["athletes"])

DB = Annotated[Session, Depends(get_db)]


def _model_to_response(m: AthleteModel) -> AthleteResponse:
    return AthleteResponse(
        id=UUID(m.id),
        name=m.name,
        age=m.age,
        sex=m.sex,
        weight_kg=m.weight_kg,
        height_cm=m.height_cm,
        sports=[Sport(v) for v in json.loads(m.sports_json)],
        primary_sport=Sport(m.primary_sport),
        goals=json.loads(m.goals_json),
        target_race_date=m.target_race_date,
        available_days=json.loads(m.available_days_json),
        hours_per_week=m.hours_per_week,
        equipment=json.loads(m.equipment_json),
        max_hr=m.max_hr,
        resting_hr=m.resting_hr,
        ftp_watts=m.ftp_watts,
        vdot=m.vdot,
        css_per_100m=m.css_per_100m,
        sleep_hours_typical=m.sleep_hours_typical,
        stress_level=m.stress_level,
        job_physical=m.job_physical,
    )


@router.get("/", response_model=list[AthleteResponse])
def list_athletes(db: DB) -> list[AthleteResponse]:
    return [_model_to_response(m) for m in db.query(AthleteModel).all()]


@router.post("/", response_model=AthleteResponse, status_code=201)
def create_athlete(data: AthleteCreate, db: DB) -> AthleteResponse:
    model = AthleteModel(
        id=str(uuid.uuid4()),
        name=data.name,
        age=data.age,
        sex=data.sex,
        weight_kg=data.weight_kg,
        height_cm=data.height_cm,
        primary_sport=data.primary_sport.value,
        target_race_date=data.target_race_date,
        hours_per_week=data.hours_per_week,
        sleep_hours_typical=data.sleep_hours_typical,
        stress_level=data.stress_level,
        job_physical=data.job_physical,
        max_hr=data.max_hr,
        resting_hr=data.resting_hr,
        ftp_watts=data.ftp_watts,
        vdot=data.vdot,
        css_per_100m=data.css_per_100m,
        sports_json=json.dumps([v.value for v in data.sports]),
        goals_json=json.dumps(data.goals),
        available_days_json=json.dumps(data.available_days),
        equipment_json=json.dumps(data.equipment),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return _model_to_response(model)


@router.get("/{athlete_id}", response_model=AthleteResponse)
def get_athlete(athlete_id: str, db: DB) -> AthleteResponse:
    model = db.get(AthleteModel, athlete_id)
    if model is None:
        raise HTTPException(status_code=404)
    return _model_to_response(model)


@router.put("/{athlete_id}", response_model=AthleteResponse)
def update_athlete(athlete_id: str, data: AthleteUpdate, db: DB) -> AthleteResponse:
    model = db.get(AthleteModel, athlete_id)
    if model is None:
        raise HTTPException(status_code=404)
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "sports":
            model.sports_json = json.dumps([v.value for v in value])
        elif key == "goals":
            model.goals_json = json.dumps(value)
        elif key == "available_days":
            model.available_days_json = json.dumps(value)
        elif key == "equipment":
            model.equipment_json = json.dumps(value)
        elif key == "primary_sport":
            model.primary_sport = value.value
        else:
            setattr(model, key, value)
    db.commit()
    db.refresh(model)
    return _model_to_response(model)


@router.delete("/{athlete_id}", status_code=204)
def delete_athlete(athlete_id: str, db: DB) -> None:
    model = db.get(AthleteModel, athlete_id)
    if model is None:
        raise HTTPException(status_code=404)
    db.delete(model)
    db.commit()
