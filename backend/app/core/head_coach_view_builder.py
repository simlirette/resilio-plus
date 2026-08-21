"""HeadCoachView builder — assembles what the coach knows before it answers.

The database session is optional on purpose: onboarding, followup and recovery
call this with an athlete row alone, and a broken or absent database must
degrade to the profile-only view rather than break a conversation turn.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..db.models import AthleteModel
from ..schemas.head_coach_view import HeadCoachView

logger = logging.getLogger(__name__)

RECENT_SESSION_LIMIT = 10
RECENT_SESSION_DAYS = 14


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _athlete_today(athlete: AthleteModel) -> date:
    """Today as the athlete experiences it, falling back to UTC."""
    now = _utcnow()
    name = getattr(athlete, "timezone", None)
    if name:
        try:
            from zoneinfo import ZoneInfo

            return now.astimezone(ZoneInfo(str(name))).date()
        except Exception:
            logger.warning(
                "athlete_timezone_unreadable",
                extra={"athlete_id": getattr(athlete, "id", None)},
            )
    return now.date()


def build_head_coach_view(
    athlete: AthleteModel,
    db: Any | None = None,
) -> HeadCoachView:
    """Build a HeadCoachView from the athlete record and, if given, live state.

    Args:
        athlete: ORM model with current journey state.
        db:      Optional session. Without it the view carries profile and goal
                 only — no plan, no ACWR, no recent sessions.
    """
    sports: list[str] = _json_list(_opt(athlete.sports_json, str))
    goals: list[str] = _json_list(_opt(athlete.goals_json, str))
    race_date = _opt(athlete.target_race_date, date)
    if isinstance(race_date, datetime):
        race_date = race_date.date()

    today = _athlete_today(athlete)

    view = HeadCoachView(
        athlete_id=athlete.id,
        today=today,
        journey_phase=athlete.journey_phase,
        sports=sports,
        primary_sport=athlete.primary_sport,
        hours_per_week=athlete.hours_per_week,
        coaching_mode=getattr(athlete, "coaching_mode", "full"),
        clinical_context_flag=getattr(athlete, "clinical_context_flag", None),
        age=_opt(athlete.age, int),
        sex=_opt(athlete.sex, str),
        weight_kg=_opt(athlete.weight_kg, int, float),
        height_cm=_opt(athlete.height_cm, int, float),
        vdot=_opt(athlete.vdot, int, float),
        vdot_source="declared" if _opt(athlete.vdot, int, float) else None,
        ftp_watts=_opt(athlete.ftp_watts, int),
        css_per_100m=_opt(athlete.css_per_100m, int, float),
        max_hr=_opt(athlete.max_hr, int),
        resting_hr=_opt(athlete.resting_hr, int),
        goals=goals,
        target_race_date=race_date,
        weeks_to_race=_weeks_to_race(race_date, today),
        days_to_race=_days_to_race(race_date, today),
    )

    if db is None:
        return view

    try:
        view.active_plan_summary = _active_plan_summary(athlete.id, db)
        view.recent_sessions = _recent_sessions(athlete.id, db)
        _attach_load_state(view, athlete.id, db)
        _attach_estimated_vdot(view, athlete.id, db)
        _attach_snapshot(view, athlete.id, db)
    except Exception:
        # A conversation turn is worth more than a complete view.
        logger.warning(
            "head_coach_view_partial", extra={"athlete_id": athlete.id}, exc_info=True
        )

    return view


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _opt(value: Any, *types: type) -> Any:
    """Return value only if it is one of `types`, else None.

    Callers hand us whatever the ORM row holds. Anything unexpected - a test
    double, a column the migration has not filled - becomes None instead of
    failing validation and taking the whole conversation turn with it.
    """
    if isinstance(value, bool) and bool not in types:
        return None
    return value if isinstance(value, types) else None


def _json_list(raw: str | None) -> list[Any]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def _weeks_to_race(race_date: date | None, today: date) -> int | None:
    if not isinstance(race_date, date):
        return None
    return max(0, (race_date - today).days // 7)


def _days_to_race(race_date: date | None, today: date) -> int | None:
    """Signed on purpose: a race already run should read as stale, not as today."""
    if not isinstance(race_date, date):
        return None
    return (race_date - today).days


def _active_plan_summary(athlete_id: str, db: Any) -> dict[str, Any] | None:
    """The plan the coach itself wrote — it could not see it before."""
    from sqlalchemy import desc

    from ..db.models import TrainingPlanModel

    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )
    if plan is None:
        return None

    slots = _json_list(plan.weekly_slots_json)
    return {
        "phase": plan.phase,
        "start_date": plan.start_date.isoformat() if plan.start_date else None,
        "end_date": plan.end_date.isoformat() if plan.end_date else None,
        "total_weekly_hours": plan.total_weekly_hours,
        "acwr": plan.acwr,
        "status": getattr(plan, "status", "active"),
        "sessions_total": len(slots),
        "sessions": [
            {
                "date": slot.get("date"),
                "sport": slot.get("sport"),
                "workout_type": slot.get("workout_type"),
                "duration_min": slot.get("duration_min"),
                "notes": slot.get("notes", ""),
            }
            for slot in slots
            if isinstance(slot, dict)
        ],
    }


def _recent_sessions(athlete_id: str, db: Any) -> list[dict[str, Any]]:
    """What the athlete actually did, newest first."""
    from sqlalchemy import desc

    from ..db.models import StravaActivityModel

    since = datetime.now(timezone.utc) - timedelta(days=RECENT_SESSION_DAYS)
    rows = (
        db.query(StravaActivityModel)
        .filter(
            StravaActivityModel.athlete_id == athlete_id,
            StravaActivityModel.started_at >= since,
        )
        .order_by(desc(StravaActivityModel.started_at))
        .limit(RECENT_SESSION_LIMIT)
        .all()
    )
    sessions: list[dict[str, Any]] = []
    for row in rows:
        entry: dict[str, Any] = {
            "date": row.started_at.date().isoformat(),
            "sport": row.sport_type,
            "duration_min": round((row.duration_s or 0) / 60),
        }
        if row.distance_m:
            entry["distance_km"] = round(row.distance_m / 1000.0, 1)
        if row.avg_hr:
            entry["avg_hr"] = row.avg_hr
        if row.perceived_exertion:
            entry["rpe"] = row.perceived_exertion
        sessions.append(entry)
    return sessions


def _attach_estimated_vdot(view: HeadCoachView, athlete_id: str, db: Any) -> None:
    """Fill in the VDOT the planner would infer, when none was declared.

    ``RunningCoach.analyze`` falls back to ``estimate_vdot`` on the athlete's
    recent Strava runs and never writes the result back, so reading the column
    alone left the conversational coach blind to a number the planner was
    already prescribing paces from.

    Labelled as an estimate: it comes from whatever pace the athlete happened
    to run, not from a tested effort.
    """
    from ..db.models import StravaActivityModel
    from ..schemas.connector import StravaActivity
    from .running_logic import estimate_vdot, qualifies_for_vdot

    if view.vdot is not None:
        return

    rows = db.query(StravaActivityModel).filter(
        StravaActivityModel.athlete_id == athlete_id
    ).all()
    activities = [
        StravaActivity(
            id=str(row.id),
            name=row.name or "",
            sport_type=row.sport_type or "",
            date=row.started_at.date() if row.started_at else date.today(),
            duration_seconds=int(row.duration_s or 0),
            distance_meters=row.distance_m,
            perceived_exertion=row.perceived_exertion,
        )
        for row in rows
    ]
    if not activities:
        return

    # One predicate, shared with the estimator -- an inline copy here drifted
    # from it within a single commit.
    if not any(qualifies_for_vdot(a) for a in activities):
        return

    view.vdot = estimate_vdot(activities)
    view.vdot_source = "estimated_from_recent_runs"


def _attach_load_state(view: HeadCoachView, athlete_id: str, db: Any) -> None:
    from .acwr import compute_acwr
    from .load_history import daily_training_loads

    loads = daily_training_loads(athlete_id, db)
    if not any(loads):
        return
    result = compute_acwr(loads)
    view.acwr_ratio = round(result.ratio, 2)
    view.acwr_status = result.status.value


def _attach_snapshot(view: HeadCoachView, athlete_id: str, db: Any) -> None:
    """Readiness and muscle strain from the most recent daily snapshot."""
    from sqlalchemy import desc

    from ..jobs.models import AthleteStateSnapshotModel

    snapshot = (
        db.query(AthleteStateSnapshotModel)
        .filter(AthleteStateSnapshotModel.athlete_id == athlete_id)
        .order_by(desc(AthleteStateSnapshotModel.snapshot_date))
        .first()
    )
    if snapshot is None:
        return

    # Only a measured readiness reaches the coach. An unmeasured 1.0 is the
    # absence of a signal, and reads as 'fully recovered' in the prompt.
    if getattr(snapshot, "readiness_source", None) == "measured":
        view.readiness = snapshot.readiness
    strain = json.loads(snapshot.strain_json or "{}")
    if isinstance(strain, dict):
        view.muscle_strain = {
            key: float(value)
            for key, value in strain.items()
            if isinstance(value, (int, float))
        }
