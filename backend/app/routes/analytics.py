import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db.models import AthleteModel, SessionLogModel
from ..dependencies import get_db, get_current_athlete_id
from ..core.analytics_logic import (
    compute_acwr_series,
    compute_ctl_atl_tsb,
    compute_sport_breakdown,
    compute_performance_trends,
)

router = APIRouter(prefix="/athletes", tags=["analytics"])


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return current_id


def _session_rows(athlete_id: str, db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(SessionLogModel)
        .filter(SessionLogModel.athlete_id == athlete_id)
        .all()
    )
    result = []
    for r in rows:
        session_date = r.logged_at.date().isoformat() if r.logged_at else None
        total_load = float(r.actual_duration_min or 0)
        duration_minutes = r.actual_duration_min or 0
        try:
            actual_data = json.loads(r.actual_data_json) if r.actual_data_json else {}
        except (json.JSONDecodeError, TypeError):
            actual_data = {}
        sport = actual_data.get("sport") if actual_data else None
        result.append({
            "session_date": session_date,
            "total_load": total_load,
            "sport": sport,
            "duration_minutes": duration_minutes,
            "actual_data_json": r.actual_data_json,
        })
    return result


@router.get("/{athlete_id}/analytics/load")
def get_load_analytics(
    athlete_id: str,
    _: Annotated[str, Depends(_require_own)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = _session_rows(athlete_id, db)
    return {
        "acwr": compute_acwr_series(rows),
        "training_load": compute_ctl_atl_tsb(rows),
    }


@router.get("/{athlete_id}/analytics/sport-breakdown")
def get_sport_breakdown(
    athlete_id: str,
    _: Annotated[str, Depends(_require_own)],
    db: Session = Depends(get_db),
) -> dict[str, int]:
    rows = _session_rows(athlete_id, db)
    return compute_sport_breakdown(rows)


@router.get("/{athlete_id}/analytics/performance")
def get_performance_analytics(
    athlete_id: str,
    _: Annotated[str, Depends(_require_own)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = _session_rows(athlete_id, db)
    return compute_performance_trends(rows)
