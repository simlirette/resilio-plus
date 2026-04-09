"""
Plan routes — api/v1/plan.py
POST /plan/running : plan de course hebdomadaire Runna/Garmin-compatible.
POST /plan/lifting : plan de musculation hebdomadaire Hevy-compatible.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.lifting_coach.agent import LiftingCoachAgent
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
