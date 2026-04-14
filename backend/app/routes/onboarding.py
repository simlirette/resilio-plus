import json
import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.security import create_access_token, hash_password
from ..db.models import AthleteModel, UserModel
from ..dependencies import get_db
from ..routes.athletes import athlete_model_to_response
from ..routes.plans import _create_plan_for_athlete
from ..schemas.auth import OnboardingRequest, OnboardingResponse
from ..schemas.plan import TrainingPlanResponse

router = APIRouter(prefix="/athletes", tags=["onboarding"])

DB = Annotated[Session, Depends(get_db)]


@router.post("/onboarding", response_model=OnboardingResponse, status_code=201)
def onboard_athlete(req: OnboardingRequest, db: DB) -> OnboardingResponse:
    existing = db.query(UserModel).filter(UserModel.email == req.email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    athlete_id = str(uuid.uuid4())
    athlete_model = AthleteModel(
        id=athlete_id,
        name=req.name,
        age=req.age,
        sex=req.sex,
        weight_kg=req.weight_kg,
        height_cm=req.height_cm,
        primary_sport=req.primary_sport.value,
        target_race_date=req.target_race_date,
        hours_per_week=req.hours_per_week,
        sleep_hours_typical=req.sleep_hours_typical,
        stress_level=req.stress_level,
        job_physical=req.job_physical,
        max_hr=req.max_hr,
        resting_hr=req.resting_hr,
        ftp_watts=req.ftp_watts,
        vdot=req.vdot,
        css_per_100m=req.css_per_100m,
        sports_json=json.dumps([s.value for s in req.sports]),
        goals_json=json.dumps(req.goals),
        available_days_json=json.dumps(req.available_days),
        equipment_json=json.dumps(req.equipment),
        coaching_mode=req.coaching_mode,
    )
    db.add(athlete_model)
    db.flush()

    user = UserModel(
        id=str(uuid.uuid4()),
        email=req.email,
        hashed_password=hash_password(req.password),
        athlete_id=athlete_id,
    )
    db.add(user)
    db.flush()

    athlete = athlete_model_to_response(athlete_model)
    end_date = req.plan_start_date + timedelta(days=6)
    plan_model = _create_plan_for_athlete(athlete_id, athlete, req.plan_start_date, end_date, db)

    from ..routes.auth import _issue_refresh_token
    access_token = create_access_token(athlete_id=athlete_id)
    refresh_token = _issue_refresh_token(user.id, db)
    db.commit()
    return OnboardingResponse(
        athlete=athlete,
        plan=TrainingPlanResponse.from_model(plan_model),
        access_token=access_token,
        refresh_token=refresh_token,
    )
