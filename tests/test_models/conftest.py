"""Shared fixtures for test_models."""
from datetime import date, datetime, timezone

import pytest

from app.models.athlete_state import (
    AllostaticComponents,
    AllostaticEntry,
    AllostaticSummary,
    AthleteMetrics,
    AthleteState,
    ConnectorSnapshot,
    DailyJournal,
    EnergyCheckIn,
    EnergySnapshot,
    HormonalProfile,
    MuscleStrainScore,
    PlanSnapshot,
    RecoveryVetoV3,
    SyncSource,
)
from app.schemas.athlete import AthleteProfile, Sport


@pytest.fixture
def full_state() -> AthleteState:
    """A fully populated AthleteState for view testing."""
    profile = AthleteProfile(
        name="Alice",
        age=28,
        sex="F",
        weight_kg=60.0,
        height_cm=168.0,
        sports=[Sport.RUNNING, Sport.LIFTING],
        primary_sport=Sport.RUNNING,
        goals=["marathon_sub4"],
        available_days=[1, 3, 5, 6],
        hours_per_week=8.0,
    )
    metrics = AthleteMetrics(
        date=date(2026, 4, 13),
        hrv_rmssd=65.0,
        hrv_history_7d=[60.0, 62.0, 65.0, 58.0, 70.0, 64.0, 65.0],
        sleep_hours=7.5,
        terra_sleep_score=82.0,
        resting_hr=48.0,
        acwr=1.1,
        acwr_status="safe",
        readiness_score=87.0,
        muscle_strain=MuscleStrainScore(
            quads=72.0,
            posterior_chain=55.0,
            glutes=60.0,
            calves=45.0,
            chest=30.0,
            upper_pull=80.0,
            shoulders=40.0,
            triceps=35.0,
            biceps=50.0,
            core=65.0,
            computed_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
        ),
    )
    connectors = ConnectorSnapshot()
    plan = PlanSnapshot(week_number=3, phase="build")
    energy = EnergySnapshot(
        timestamp=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
        allostatic_score=30.0,
        cognitive_load=25.0,
        energy_availability=45.0,
        sleep_quality=80.0,
        recommended_intensity_cap=1.0,
        veto_triggered=False,
    )
    recovery = RecoveryVetoV3(
        status="green",
        hrv_component="green",
        acwr_component="green",
        ea_component="green",
        allostatic_component="green",
        final_intensity_cap=1.0,
        veto_triggered=False,
        veto_reasons=[],
    )
    hormonal = HormonalProfile(
        enabled=True,
        tracking_source="manual",
        current_phase="follicular",
    )
    allostatic = AllostaticSummary(
        history_28d=[
            AllostaticEntry(
                date=date(2026, 4, i),
                allostatic_score=float(30 + i),
                components=AllostaticComponents(hrv=20.0, sleep=30.0),
                intensity_cap_applied=1.0,
            )
            for i in range(1, 8)
        ],
        trend="stable",
        avg_score_7d=33.0,
    )
    journal = DailyJournal(
        date=date(2026, 4, 13),
        check_in=EnergyCheckIn(work_intensity="normal", stress_level="none"),
        comment="Felt good.",
        mood_score=8,
    )
    return AthleteState(
        athlete_id="fixture-athlete",
        last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
        sync_sources=[SyncSource(
            name="strava",
            last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            status="ok",
        )],
        profile=profile,
        metrics=metrics,
        connectors=connectors,
        plan=plan,
        energy=energy,
        recovery=recovery,
        hormonal=hormonal,
        allostatic=allostatic,
        journal=journal,
    )
