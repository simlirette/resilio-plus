"""Seed data — Alice Dupont (recreational runner + lifting, female).

6 weeks of history ending 2026-04-13:
  - Weeks 1-3: normal training (4 runs + 2 lifts/week)
  - Week 4: recovery dip (sleep 5.5h, HRV drop, veto triggered)
  - Week 5: recovery, reduced load
  - Week 6 (current): back to normal
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.models import (
    AthleteModel,
    NutritionPlanModel,
    SessionLogModel,
    TrainingPlanModel,
    UserModel,
    WeeklyReviewModel,
)
from app.models.schemas import (
    AllostaticEntryModel,
    EnergySnapshotModel,
    HeadCoachMessageModel,
    HormonalProfileModel,
)

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALICE_ID = "athlete-alice-001"
ALICE_EMAIL = "alice@resilio.dev"
ALICE_PLAN_ID = "plan-alice-001"
REF_DATE = date(2026, 4, 13)
WEEK_START = REF_DATE - timedelta(days=REF_DATE.weekday())  # Monday 2026-04-07


def _id() -> str:
    return str(uuid.uuid4())


def _already_inserted(session: Session) -> bool:
    return session.get(AthleteModel, ALICE_ID) is not None


def insert_alice(session: Session) -> None:
    """Insert Alice persona. Idempotent."""
    if _already_inserted(session):
        return

    # --- Athlete ---
    athlete = AthleteModel(
        id=ALICE_ID,
        name="Alice Dupont",
        age=28,
        sex="F",
        weight_kg=60.0,
        height_cm=168.0,
        primary_sport="running",
        target_race_date=date(2026, 10, 18),
        hours_per_week=8.0,
        sleep_hours_typical=7.5,
        stress_level=3,
        job_physical=False,
        max_hr=188,
        resting_hr=52,
        vdot=44.0,
        coaching_mode="active",
        sports_json=json.dumps(["running", "lifting"]),
        goals_json=json.dumps(["marathon_sub4"]),
        available_days_json=json.dumps([1, 3, 5, 6]),
        equipment_json=json.dumps(["barbell", "dumbbells"]),
    )
    session.add(athlete)

    # --- User ---
    session.add(UserModel(
        id=_id(),
        email=ALICE_EMAIL,
        hashed_password=_pwd_ctx.hash("alice2026"),
        athlete_id=ALICE_ID,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    ))

    # --- Hormonal profile ---
    session.add(HormonalProfileModel(
        id=_id(),
        athlete_id=ALICE_ID,
        enabled=True,
        cycle_length_days=28,
        current_cycle_day=7,
        current_phase="follicular",
        last_period_start=date(2026, 4, 7),
        tracking_source="manual",
    ))

    # --- Training plan ---
    plan_start = REF_DATE - timedelta(days=41)
    plan = TrainingPlanModel(
        id=ALICE_PLAN_ID,
        athlete_id=ALICE_ID,
        start_date=plan_start,
        end_date=REF_DATE + timedelta(days=7),
        phase="base",
        total_weekly_hours=8.0,
        acwr=1.08,
        weekly_slots_json=json.dumps([
            {"day": 1, "sport": "running", "duration_min": 60, "session_type": "easy"},
            {"day": 3, "sport": "lifting", "duration_min": 60, "session_type": "strength"},
            {"day": 4, "sport": "running", "duration_min": 50, "session_type": "tempo"},
            {"day": 5, "sport": "lifting", "duration_min": 55, "session_type": "strength"},
            {"day": 6, "sport": "running", "duration_min": 90, "session_type": "long"},
            {"day": 7, "sport": "running", "duration_min": 45, "session_type": "easy"},
        ]),
        status="active",
        created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    session.add(plan)

    # --- Nutrition plan ---
    session.add(NutritionPlanModel(
        id=_id(),
        athlete_id=ALICE_ID,
        weight_kg=60.0,
        targets_json=json.dumps({
            "protein_g": 108,
            "carbs_g_easy": 200,
            "carbs_g_hard": 300,
            "fat_g": 65,
            "calories_rest": 1800,
            "calories_training": 2300,
        }),
    ))

    # --- Session logs (35 total across 6 weeks) ---
    _sessions = [
        # (days_ago, session_type, sport, duration_min, rpe, skipped)
        # Week 1
        (41, "easy", "running", 58, 5, False),
        (39, "strength", "lifting", 62, 7, False),
        (38, "tempo", "running", 52, 7, False),
        (37, "strength", "lifting", 58, 6, False),
        (36, "long", "running", 92, 6, False),
        (35, "easy", "running", 44, 5, False),
        # Week 2
        (34, "easy", "running", 60, 6, False),
        (32, "strength", "lifting", 65, 7, False),
        (31, "tempo", "running", 51, 7, False),
        (30, "strength", "lifting", 60, 7, False),
        (29, "long", "running", 95, 6, False),
        (28, "easy", "running", 45, 5, False),
        # Week 3 — heavy
        (27, "easy", "running", 62, 6, False),
        (25, "strength", "lifting", 68, 8, False),
        (24, "tempo", "running", 54, 8, False),
        (23, "strength", "lifting", 65, 8, False),
        (22, "long", "running", 100, 8, False),
        (21, "easy", "running", 50, 6, False),
        # Week 4 — recovery dip
        (20, "easy", "running", 40, 5, False),
        (18, "strength", "lifting", 0, None, True),
        (17, "tempo", "running", 30, 4, False),
        (16, "strength", "lifting", 45, 5, False),
        (15, "long", "running", 60, 5, False),
        (14, "easy", "running", 35, 4, False),
        # Week 5 — recovery
        (13, "easy", "running", 55, 5, False),
        (11, "strength", "lifting", 65, 7, False),
        (10, "tempo", "running", 50, 6, False),
        (9, "strength", "lifting", 70, 8, False),
        (8, "long", "running", 88, 6, False),
        (7, "easy", "running", 43, 5, False),
        # Week 6
        (6, "easy", "running", 60, 6, False),
        (4, "strength", "lifting", 63, 7, False),
        (3, "tempo", "running", 52, 7, False),
        (2, "strength", "lifting", 60, 7, False),
        (1, "long", "running", 90, 6, False),
    ]
    for days_ago, stype, sport, dur, rpe, skipped in _sessions:
        log_date = REF_DATE - timedelta(days=days_ago)
        session.add(SessionLogModel(
            id=_id(),
            athlete_id=ALICE_ID,
            plan_id=ALICE_PLAN_ID,
            session_id=f"alice-{log_date.isoformat()}-{stype}",
            actual_duration_min=dur if not skipped else None,
            skipped=skipped,
            rpe=rpe,
            notes="" if not skipped else "Skipped — fatigue",
            actual_data_json=json.dumps({}),
            logged_at=datetime(log_date.year, log_date.month, log_date.day, 9, 0, tzinfo=timezone.utc),
        ))

    # --- Allostatic entries (28 days) ---
    _allostatic_scores = [
        28, 30, 29, 32, 31, 28, 27,
        35, 38, 42, 55, 68, 72, 65,
        55, 45, 38, 32, 30, 28, 27,
        26, 28, 30, 29, 31, 28, 27,
    ]
    for i, score in enumerate(_allostatic_scores):
        entry_date = REF_DATE - timedelta(days=27 - i)
        cap = 0.6 if score > 65 else (0.8 if score > 50 else 1.0)
        session.add(AllostaticEntryModel(
            id=_id(),
            athlete_id=ALICE_ID,
            entry_date=entry_date,
            allostatic_score=float(score),
            components_json=json.dumps({
                "hrv": max(0.0, float(score - 10)),
                "sleep": float(score * 0.8),
                "work": 20.0,
                "stress": 15.0,
            }),
            intensity_cap_applied=cap,
        ))

    # --- Energy snapshots (14 days) ---
    _hrv_values = [62, 58, 55, 42, 38, 35, 40, 48, 55, 60, 62, 64, 65, 63]
    _sleep_values = [7.5, 7.2, 6.8, 5.5, 5.8, 6.0, 6.5, 7.0, 7.2, 7.5, 7.5, 7.3, 7.5, 7.2]
    for i in range(14):
        snap_date = REF_DATE - timedelta(days=13 - i)
        hrv = _hrv_values[i]
        slp = _sleep_values[i]
        allostatic = _allostatic_scores[14 + i]
        veto = hrv < 40 or slp < 6.0
        session.add(EnergySnapshotModel(
            id=_id(),
            athlete_id=ALICE_ID,
            timestamp=datetime(snap_date.year, snap_date.month, snap_date.day, 7, 0, tzinfo=timezone.utc),
            allostatic_score=float(allostatic),
            cognitive_load=20.0,
            energy_availability=40.0 if veto else 42.0,
            cycle_phase="follicular" if i >= 7 else "menstrual",
            sleep_quality=float(slp / 9.0 * 100),
            recommended_intensity_cap=0.6 if veto else 1.0,
            veto_triggered=veto,
            veto_reason="HRV below 70% baseline and sleep below 6h" if veto else None,
            legs_feeling="heavy" if allostatic > 60 else "normal",
            stress_level="none",
        ))

    # --- Weekly reviews (weeks 5 and 6) ---
    session.add(WeeklyReviewModel(
        id=_id(),
        athlete_id=ALICE_ID,
        plan_id=ALICE_PLAN_ID,
        week_start=REF_DATE - timedelta(days=13),
        week_number=5,
        planned_hours=8.0,
        actual_hours=6.5,
        acwr=0.92,
        readiness_score=72.0,
        hrv_rmssd=55.0,
        sleep_hours_avg=7.0,
        athlete_comment="Recovery week, felt better by Thursday.",
        results_json=json.dumps({"completed": 5, "skipped": 1}),
    ))
    session.add(WeeklyReviewModel(
        id=_id(),
        athlete_id=ALICE_ID,
        plan_id=ALICE_PLAN_ID,
        week_start=WEEK_START,
        week_number=6,
        planned_hours=8.0,
        actual_hours=7.5,
        acwr=1.08,
        readiness_score=84.0,
        hrv_rmssd=63.0,
        sleep_hours_avg=7.4,
        athlete_comment="Back on track.",
        results_json=json.dumps({"completed": 5, "skipped": 0}),
    ))

    # --- Head Coach message (recovery dip alert) ---
    session.add(HeadCoachMessageModel(
        id=_id(),
        athlete_id=ALICE_ID,
        pattern_type="reds_signal",
        message=(
            "HRV dropped to 35ms (−44% from baseline) and sleep averaged 5.8h "
            "over 3 consecutive nights. Intensity cap set to 60% for the next 48h. "
            "Prioritize sleep and reduce training volume this week."
        ),
        created_at=datetime(2026, 3, 27, 8, 0, tzinfo=timezone.utc),
        is_read=False,
    ))
