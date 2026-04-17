"""Seed data — Marc Leblanc (competitive triathlete, male).

6 weeks of history ending 2026-04-13:
  - Weeks 1-2: base build
  - Week 3: ACWR spike (1.4 — caution), volume too high
  - Weeks 4-5: normalization
  - Week 6 (current): stable at 1.1
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from app.db.models import (
    AthleteModel,
    ConnectorCredentialModel,
    NutritionPlanModel,
    SessionLogModel,
    TrainingPlanModel,
    UserModel,
    WeeklyReviewModel,
)
from app.models.schemas import AllostaticEntryModel, EnergySnapshotModel
from passlib.context import CryptContext
from sqlalchemy.orm import Session

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

MARC_ID = "athlete-marc-001"
MARC_EMAIL = "marc@resilio.dev"
MARC_PLAN_ID = "plan-marc-001"
REF_DATE = date(2026, 4, 13)
WEEK_START = REF_DATE - timedelta(days=REF_DATE.weekday())


def _id() -> str:
    return str(uuid.uuid4())


def _already_inserted(session: Session) -> bool:
    return session.get(AthleteModel, MARC_ID) is not None


def insert_marc(session: Session) -> None:
    """Insert Marc persona. Idempotent."""
    if _already_inserted(session):
        return

    # --- Athlete ---
    athlete = AthleteModel(
        id=MARC_ID,
        name="Marc Leblanc",
        age=34,
        sex="M",
        weight_kg=75.0,
        height_cm=180.0,
        primary_sport="running",
        target_race_date=date(2026, 9, 7),
        hours_per_week=12.0,
        sleep_hours_typical=7.0,
        stress_level=4,
        job_physical=False,
        max_hr=182,
        resting_hr=46,
        ftp_watts=265,
        vdot=52.0,
        coaching_mode="active",
        sports_json=json.dumps(["running", "cycling", "swimming"]),
        goals_json=json.dumps(["ironman_70_3"]),
        available_days_json=json.dumps([1, 2, 3, 4, 5, 6, 7]),
        equipment_json=json.dumps(["road_bike", "wetsuit", "power_meter"]),
    )
    session.add(athlete)

    # --- User ---
    session.add(
        UserModel(
            id=_id(),
            email=MARC_EMAIL,
            hashed_password=_pwd_ctx.hash("marc2026"),
            athlete_id=MARC_ID,
            created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
    )

    # --- Strava connector credential (fake token for dev) ---
    session.add(
        ConnectorCredentialModel(
            id=_id(),
            athlete_id=MARC_ID,
            provider="strava",
            access_token="fake_strava_access_token_marc_dev_only",
            refresh_token="fake_strava_refresh_token_marc_dev_only",
            expires_at=1800000000,
            extra_json=json.dumps({"athlete_id": 99999999, "scope": "activity:read_all"}),
        )
    )

    # --- Training plan ---
    plan_start = REF_DATE - timedelta(days=41)
    plan = TrainingPlanModel(
        id=MARC_PLAN_ID,
        athlete_id=MARC_ID,
        start_date=plan_start,
        end_date=REF_DATE + timedelta(days=7),
        phase="build",
        total_weekly_hours=12.0,
        acwr=1.10,
        weekly_slots_json=json.dumps(
            [
                {"day": 1, "sport": "running", "duration_min": 60, "session_type": "easy"},
                {"day": 2, "sport": "cycling", "duration_min": 90, "session_type": "base"},
                {"day": 3, "sport": "swimming", "duration_min": 45, "session_type": "technique"},
                {"day": 4, "sport": "running", "duration_min": 75, "session_type": "tempo"},
                {"day": 5, "sport": "cycling", "duration_min": 75, "session_type": "intervals"},
                {"day": 6, "sport": "running", "duration_min": 100, "session_type": "long"},
                {"day": 7, "sport": "swimming", "duration_min": 50, "session_type": "endurance"},
            ]
        ),
        status="active",
        created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    session.add(plan)

    # --- Nutrition plan ---
    session.add(
        NutritionPlanModel(
            id=_id(),
            athlete_id=MARC_ID,
            weight_kg=75.0,
            targets_json=json.dumps(
                {
                    "protein_g": 135,
                    "carbs_g_easy": 280,
                    "carbs_g_hard": 420,
                    "fat_g": 80,
                    "calories_rest": 2400,
                    "calories_training": 3200,
                }
            ),
        )
    )

    # --- Session logs (41 total: 7+7+7+7+7+6) ---
    _sessions = [
        # Week 1
        (41, "easy", "running", 62, 5, False),
        (40, "base", "cycling", 88, 6, False),
        (39, "technique", "swimming", 44, 5, False),
        (38, "tempo", "running", 74, 7, False),
        (37, "intervals", "cycling", 72, 7, False),
        (36, "long", "running", 98, 6, False),
        (35, "endurance", "swimming", 52, 5, False),
        # Week 2
        (34, "easy", "running", 60, 5, False),
        (33, "base", "cycling", 92, 6, False),
        (32, "technique", "swimming", 45, 5, False),
        (31, "tempo", "running", 76, 7, False),
        (30, "intervals", "cycling", 78, 8, False),
        (29, "long", "running", 105, 7, False),
        (28, "endurance", "swimming", 50, 6, False),
        # Week 3 — ACWR spike
        (27, "easy", "running", 70, 6, False),
        (26, "base", "cycling", 120, 7, False),
        (25, "technique", "swimming", 60, 6, False),
        (24, "tempo", "running", 85, 8, False),
        (23, "intervals", "cycling", 95, 9, False),
        (22, "long", "running", 130, 8, False),
        (21, "endurance", "swimming", 65, 7, False),
        # Week 4 — back off
        (20, "easy", "running", 55, 5, False),
        (19, "base", "cycling", 80, 6, False),
        (18, "technique", "swimming", 40, 5, False),
        (17, "tempo", "running", 65, 6, False),
        (16, "intervals", "cycling", 0, None, True),
        (15, "long", "running", 90, 6, False),
        (14, "endurance", "swimming", 48, 5, False),
        # Week 5 — normalization
        (13, "easy", "running", 60, 6, False),
        (12, "base", "cycling", 88, 6, False),
        (11, "technique", "swimming", 44, 5, False),
        (10, "tempo", "running", 75, 7, False),
        (9, "intervals", "cycling", 75, 7, False),
        (8, "long", "running", 100, 7, False),
        (7, "endurance", "swimming", 50, 6, False),
        # Week 6 (current)
        (6, "easy", "running", 62, 6, False),
        (5, "base", "cycling", 90, 6, False),
        (4, "technique", "swimming", 45, 5, False),
        (3, "tempo", "running", 76, 7, False),
        (2, "intervals", "cycling", 76, 7, False),
        (1, "long", "running", 102, 7, False),
    ]
    for days_ago, stype, sport, dur, rpe, skipped in _sessions:
        log_date = REF_DATE - timedelta(days=days_ago)
        session.add(
            SessionLogModel(
                id=_id(),
                athlete_id=MARC_ID,
                plan_id=MARC_PLAN_ID,
                session_id=f"marc-{log_date.isoformat()}-{stype}",
                actual_duration_min=dur if not skipped else None,
                skipped=skipped,
                rpe=rpe,
                notes="" if not skipped else "Planned rest — high ACWR",
                actual_data_json=json.dumps({}),
                logged_at=datetime(
                    log_date.year, log_date.month, log_date.day, 7, 30, tzinfo=timezone.utc
                ),
            )
        )

    # --- Allostatic entries (28 days) ---
    _allostatic_scores = [
        28,
        30,
        29,
        30,
        32,
        30,
        28,
        35,
        40,
        45,
        42,
        38,
        35,
        32,
        30,
        28,
        28,
        27,
        29,
        28,
        27,
        28,
        30,
        29,
        31,
        30,
        28,
        27,
    ]
    for i, score in enumerate(_allostatic_scores):
        entry_date = REF_DATE - timedelta(days=27 - i)
        session.add(
            AllostaticEntryModel(
                id=_id(),
                athlete_id=MARC_ID,
                entry_date=entry_date,
                allostatic_score=float(score),
                components_json=json.dumps(
                    {
                        "hrv": max(0.0, float(score - 8)),
                        "sleep": float(score * 0.75),
                        "work": 18.0,
                        "stress": 12.0,
                    }
                ),
                intensity_cap_applied=0.9 if score > 42 else 1.0,
            )
        )

    # --- Energy snapshots (14 days) ---
    _hrv_values = [70, 68, 65, 62, 58, 62, 65, 68, 70, 71, 70, 72, 71, 70]
    _sleep_values = [7.2, 7.0, 6.8, 7.0, 6.5, 7.0, 7.2, 7.2, 7.3, 7.0, 7.2, 7.1, 7.0, 7.2]
    for i in range(14):
        snap_date = REF_DATE - timedelta(days=13 - i)
        slp = _sleep_values[i]
        allostatic = _allostatic_scores[14 + i]
        session.add(
            EnergySnapshotModel(
                id=_id(),
                athlete_id=MARC_ID,
                timestamp=datetime(
                    snap_date.year, snap_date.month, snap_date.day, 6, 30, tzinfo=timezone.utc
                ),
                allostatic_score=float(allostatic),
                cognitive_load=18.0,
                energy_availability=48.0,
                cycle_phase=None,
                sleep_quality=float(slp / 9.0 * 100),
                recommended_intensity_cap=0.9 if allostatic > 42 else 1.0,
                veto_triggered=False,
                legs_feeling="normal",
                stress_level="none",
            )
        )

    # --- Weekly reviews ---
    session.add(
        WeeklyReviewModel(
            id=_id(),
            athlete_id=MARC_ID,
            plan_id=MARC_PLAN_ID,
            week_start=REF_DATE - timedelta(days=13),
            week_number=5,
            planned_hours=12.0,
            actual_hours=11.5,
            acwr=1.12,
            readiness_score=80.0,
            hrv_rmssd=68.0,
            sleep_hours_avg=7.1,
            athlete_comment="Good week. Legs felt heavy Tuesday but recovered by Thursday.",
            results_json=json.dumps({"completed": 6, "skipped": 1}),
        )
    )
    session.add(
        WeeklyReviewModel(
            id=_id(),
            athlete_id=MARC_ID,
            plan_id=MARC_PLAN_ID,
            week_start=WEEK_START,
            week_number=6,
            planned_hours=12.0,
            actual_hours=11.8,
            acwr=1.10,
            readiness_score=85.0,
            hrv_rmssd=70.0,
            sleep_hours_avg=7.1,
            athlete_comment="Strong week. Bike power up 8W vs last month.",
            results_json=json.dumps({"completed": 6, "skipped": 0}),
        )
    )
