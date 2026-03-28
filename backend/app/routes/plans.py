import json
import uuid
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.head_coach import HeadCoach
from app.agents.lifting_coach import LiftingCoach
from app.agents.running_coach import RunningCoach
from app.core.periodization import get_current_phase
from app.db.models import AthleteModel, TrainingPlanModel
from app.dependencies import get_db
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.plan import TrainingPlanResponse

router = APIRouter(prefix="/athletes", tags=["plans"])

DB = Annotated[Session, Depends(get_db)]


class PlanRequest(BaseModel):
    start_date: date
    end_date: date


def _athlete_model_to_profile(m: AthleteModel) -> AthleteProfile:
    return AthleteProfile(
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


@router.post("/{athlete_id}/plan", response_model=TrainingPlanResponse, status_code=201)
def generate_plan(athlete_id: str, req: PlanRequest, db: DB) -> TrainingPlanResponse:
    athlete_model = db.get(AthleteModel, athlete_id)
    if athlete_model is None:
        raise HTTPException(status_code=404)

    athlete = _athlete_model_to_profile(athlete_model)

    phase_obj = get_current_phase(athlete.target_race_date, req.start_date)
    phase = phase_obj.phase.value  # PeriodizationPhase → MacroPhase → str

    if athlete.target_race_date:
        weeks_remaining = max(0, (athlete.target_race_date - req.start_date).days // 7)
    else:
        weeks_remaining = 0

    context = AgentContext(
        athlete=athlete,
        date_range=(req.start_date, req.end_date),
        phase=phase,
        strava_activities=[],
        hevy_workouts=[],
        terra_health=[],
        fatsecret_days=[],
        week_number=1,
        weeks_remaining=weeks_remaining,
    )

    coach = HeadCoach(agents=[RunningCoach(), LiftingCoach()])
    weekly_plan = coach.build_week(context, load_history=[])

    plan_model = TrainingPlanModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        start_date=req.start_date,
        end_date=req.end_date,
        phase=weekly_plan.phase.phase.value,  # PeriodizationPhase → MacroPhase → str
        total_weekly_hours=sum(s.duration_min for s in weekly_plan.sessions) / 60,
        acwr=weekly_plan.acwr.ratio,
        weekly_slots_json=json.dumps(
            [s.model_dump(mode="json") for s in weekly_plan.sessions]
        ),
        created_at=datetime.now(timezone.utc),
    )
    db.add(plan_model)
    db.commit()
    db.refresh(plan_model)
    return TrainingPlanResponse.from_model(plan_model)


@router.get("/{athlete_id}/plan", response_model=TrainingPlanResponse)
def get_latest_plan(athlete_id: str, db: DB) -> TrainingPlanResponse:
    athlete = db.get(AthleteModel, athlete_id)
    if athlete is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="No plan found for this athlete")
    return TrainingPlanResponse.from_model(plan)
