"""
Plan routes — api/v1/plan.py
POST /plan/running : plan de course hebdomadaire Runna/Garmin-compatible.
POST /plan/lifting : plan de musculation hebdomadaire Hevy-compatible.
POST /plan/recovery : verdict gate keeper — readiness score + modification params.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.lifting_coach.agent import LiftingCoachAgent
from agents.nutrition_coach.agent import NutritionCoachAgent
from agents.recovery_coach.agent import RecoveryCoachAgent
from agents.running_coach.agent import RunningCoachAgent
from models.athlete_state import AthleteState

router = APIRouter()


class RunningPlanRequest(BaseModel):
    athlete_state: dict


@router.post("/running")
def generate_running_plan(body: RunningPlanRequest) -> dict:
    """
    Génère un plan de course hebdomadaire Runna/Garmin-compatible.

    Body: {"athlete_state": <AthleteState as dict>}
    Returns: plan dict avec sessions[], coaching_notes[], métadonnées phase/TID.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    agent = RunningCoachAgent()
    return agent.run(state)


class LiftingPlanRequest(BaseModel):
    athlete_state: dict


@router.post("/lifting")
def generate_lifting_plan(body: LiftingPlanRequest) -> dict:
    """
    Génère un plan de musculation hebdomadaire Hevy-compatible.

    Body: {"athlete_state": <AthleteState as dict>}
    Returns: plan dict avec sessions[].hevy_workout, coaching_notes[], métadonnées DUP.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    agent = LiftingCoachAgent()
    return agent.run(state)


class RecoveryPlanRequest(BaseModel):
    athlete_state: dict


@router.post("/recovery")
def generate_recovery_plan(body: RecoveryPlanRequest) -> dict:
    """
    Évalue la capacité physiologique de l'athlète — verdict gate keeper.

    Body: {"athlete_state": <AthleteState as dict>}
    Returns: verdict dict avec readiness_score, color, factors, modification_params,
             overtraining_alert, notes.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    agent = RecoveryCoachAgent()
    return agent.run(state)


class NutritionPlanRequest(BaseModel):
    athlete_state: dict


@router.post("/nutrition")
def generate_nutrition_plan(body: NutritionPlanRequest) -> dict:
    """
    Génère le plan nutritionnel hebdomadaire (7 jours).

    Body: {"athlete_state": <AthleteState as dict>}
    Returns: plan dict avec daily_plans[], weekly_summary, notes.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    agent = NutritionCoachAgent()
    return agent.run(state)
