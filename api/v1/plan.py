"""
Plan routes — api/v1/plan.py
POST /plan/running : génère un plan de course hebdomadaire Runna/Garmin-compatible.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
