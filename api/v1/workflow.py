"""
Workflow routes — api/v1/workflow.py
POST /workflow/plan              : run the full Head Coach LangGraph workflow
POST /workflow/plan/resume       : resume an interrupted workflow
POST /workflow/onboarding/init   : initialize AthleteState with constraint matrix
POST /workflow/weekly-review     : run the H1-H4 weekly review loop
"""
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents.head_coach.graph import head_coach_graph, weekly_review_graph
from core.constraint_matrix import build_constraint_matrix
from models.athlete_state import AthleteState
from models.weekly_review import ActualWorkout, WeeklyReviewState

router = APIRouter()


class PlanRequest(BaseModel):
    athlete_state: dict
    thread_id: str | None = None


class ResumeRequest(BaseModel):
    thread_id: str
    user_decision: str


@router.post("/plan")
def generate_plan(body: PlanRequest):
    """
    Run the Head Coach LangGraph workflow.

    Returns 200 {status:"complete", unified_plan} if graph reaches END,
    or 202 {status:"awaiting_decision", thread_id, pending_decision} if interrupted.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    thread_id = body.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = head_coach_graph.invoke(state, config=config)

    graph_state = head_coach_graph.get_state(config)
    if graph_state.next:
        pending = result.get("pending_decision") if isinstance(result, dict) else None
        return JSONResponse(
            status_code=202,
            content={
                "status": "awaiting_decision",
                "thread_id": thread_id,
                "pending_decision": pending,
            },
        )

    unified_plan = result.get("unified_plan") if isinstance(result, dict) else None
    return {"status": "complete", "unified_plan": unified_plan}


@router.post("/plan/resume")
def resume_plan(body: ResumeRequest):
    """
    Resume a workflow interrupted for human-in-the-loop decision.

    Returns same format as /plan (200 complete or 202 awaiting).
    """
    config = {"configurable": {"thread_id": body.thread_id}}

    graph_state = head_coach_graph.get_state(config)
    if not graph_state.next:
        raise HTTPException(status_code=404, detail="Thread not found or already complete.")

    result = head_coach_graph.invoke(
        {"user_decision_input": body.user_decision},
        config=config,
    )

    graph_state = head_coach_graph.get_state(config)
    if graph_state.next:
        pending = result.get("pending_decision") if isinstance(result, dict) else None
        return JSONResponse(
            status_code=202,
            content={
                "status": "awaiting_decision",
                "thread_id": body.thread_id,
                "pending_decision": pending,
            },
        )

    unified_plan = result.get("unified_plan") if isinstance(result, dict) else None
    return {"status": "complete", "unified_plan": unified_plan}


class WeeklyReviewRequest(BaseModel):
    athlete_state: dict
    actual_workouts: list[dict] = []


@router.post("/weekly-review")
def weekly_review(body: WeeklyReviewRequest) -> dict:
    """
    Run the weekly review loop (H1-H4).

    Body: {"athlete_state": <AthleteState as dict>, "actual_workouts": [<ActualWorkout as dict>]}
    Returns: report dict with completion_rate, ACWR update, adjustments, next_week_notes.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    try:
        workouts = [ActualWorkout.model_validate(w) for w in body.actual_workouts]
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    review_state = WeeklyReviewState(athlete_state=state, actual_workouts=workouts)

    result = weekly_review_graph.invoke(review_state)
    return result["report"] if isinstance(result, dict) else result.report


@router.post("/onboarding/init")
def init_onboarding(body: dict):
    """
    Accept a complete athlete profile dict, validate as AthleteState,
    build the constraint matrix, and return the initialized state.
    """
    try:
        state = AthleteState.model_validate(body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    matrix = build_constraint_matrix(state)
    # Store in constraint_matrix.schedule (preserving existing _daily_loads_28d if any)
    for day, info in matrix.items():
        if day not in ("total_sessions", "running_days", "lifting_days"):
            state.constraint_matrix.schedule[day] = info

    result = state.model_dump(mode="json")
    result["constraint_matrix_summary"] = {
        "total_sessions": matrix["total_sessions"],
        "running_days": matrix["running_days"],
        "lifting_days": matrix["lifting_days"],
    }
    return result
