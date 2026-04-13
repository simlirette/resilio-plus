"""Tests for AthleteState V1 sub-models and root model."""
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

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
    PlanSnapshot,
    RecoveryVetoV3,
    SyncSource,
)
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.connector import HevyWorkout, StravaActivity
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot


class TestEnergyCheckIn:
    def test_valid_full(self):
        ci = EnergyCheckIn(
            work_intensity="heavy",
            stress_level="mild",
            cycle_phase="follicular",
        )
        assert ci.work_intensity == "heavy"
        assert ci.stress_level == "mild"
        assert ci.cycle_phase == "follicular"

    def test_valid_no_cycle(self):
        ci = EnergyCheckIn(work_intensity="normal", stress_level="none")
        assert ci.cycle_phase is None

    def test_invalid_work_intensity_raises(self):
        with pytest.raises(ValidationError):
            EnergyCheckIn(work_intensity="extreme", stress_level="none")

    def test_invalid_stress_level_raises(self):
        with pytest.raises(ValidationError):
            EnergyCheckIn(work_intensity="normal", stress_level="high")

    def test_invalid_cycle_phase_raises(self):
        with pytest.raises(ValidationError):
            EnergyCheckIn(work_intensity="normal", stress_level="none", cycle_phase="unknown")


class TestAllostaticComponents:
    def test_full_components(self):
        c = AllostaticComponents(hrv=30.0, sleep=40.0, work=65.0, stress=30.0, cycle=10.0, ea=0.0)
        assert c.hrv == 30.0
        assert c.ea == 0.0

    def test_empty_components(self):
        c = AllostaticComponents()
        assert c.hrv is None
        assert c.sleep is None

    def test_component_above_100_raises(self):
        with pytest.raises(ValidationError):
            AllostaticComponents(hrv=101.0)

    def test_component_below_0_raises(self):
        with pytest.raises(ValidationError):
            AllostaticComponents(sleep=-1.0)

    def test_unknown_fields_are_ignored(self):
        # Pydantic v2 default: extra fields are ignored, not rejected.
        c = AllostaticComponents(hrv=50.0, unknown_key=99.0)
        assert not hasattr(c, "unknown_key")

    def test_allostatic_entry_accepts_components_model(self):
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=55.0,
            components=AllostaticComponents(hrv=30.0, sleep=40.0),
            intensity_cap_applied=0.85,
        )
        assert entry.components.hrv == 30.0

    def test_allostatic_entry_accepts_dict_coercion(self):
        """Pydantic v2 coerces dict → AllostaticComponents automatically."""
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=55.0,
            components={"hrv": 30.0, "sleep": 40.0},
            intensity_cap_applied=0.85,
        )
        assert entry.components.hrv == 30.0

    def test_allostatic_entry_accepts_empty_dict(self):
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=0.0,
            components={},
            intensity_cap_applied=1.0,
        )
        assert entry.components.hrv is None


class TestSyncSource:
    def test_valid_ok(self):
        s = SyncSource(
            name="strava",
            last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            status="ok",
        )
        assert s.name == "strava"
        assert s.status == "ok"

    def test_invalid_name_raises(self):
        with pytest.raises(ValidationError):
            SyncSource(
                name="garmin",
                last_synced_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
                status="ok",
            )

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            SyncSource(
                name="terra",
                last_synced_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
                status="pending",
            )


class TestAthleteMetrics:
    def test_minimal(self):
        m = AthleteMetrics(date=date(2026, 4, 13))
        assert m.hrv_rmssd is None
        assert m.acwr is None
        assert m.hrv_history_7d == []

    def test_full(self):
        m = AthleteMetrics(
            date=date(2026, 4, 13),
            hrv_rmssd=65.4,
            hrv_history_7d=[60.0, 62.0, 65.4, 58.0, 70.0, 64.0, 65.4],
            sleep_hours=7.5,
            terra_sleep_score=82.0,
            resting_hr=48.0,
            acwr=1.1,
            acwr_status="safe",
            readiness_score=87.0,
            fatigue_score=FatigueScore(
                local_muscular=20.0, cns_load=15.0,
                metabolic_cost=18.0, recovery_hours=24.0, affected_muscles=[],
            ),
        )
        assert m.hrv_rmssd == 65.4
        assert m.acwr_status == "safe"
        assert len(m.hrv_history_7d) == 7

    def test_invalid_acwr_status_raises(self):
        with pytest.raises(ValidationError):
            AthleteMetrics(date=date(2026, 4, 13), acwr_status="warning")


def _make_strava() -> StravaActivity:
    return StravaActivity(
        id="strava_1",
        name="Morning run",
        sport_type="Run",
        date=date(2026, 4, 12),
        duration_seconds=3600,
    )


def _make_hevy() -> HevyWorkout:
    return HevyWorkout(
        id="hevy_1",
        title="Upper A",
        date=date(2026, 4, 11),
        duration_seconds=3600,
        exercises=[],
    )


class TestConnectorSnapshot:
    def test_empty(self):
        cs = ConnectorSnapshot()
        assert cs.strava_last_activity is None
        assert cs.strava_activities_7d == []
        assert cs.hevy_last_workout is None
        assert cs.hevy_workouts_7d == []

    def test_with_strava(self):
        activity = _make_strava()
        cs = ConnectorSnapshot(
            strava_last_activity=activity,
            strava_activities_7d=[activity],
        )
        assert cs.strava_last_activity.id == "strava_1"
        assert len(cs.strava_activities_7d) == 1

    def test_with_hevy(self):
        workout = _make_hevy()
        cs = ConnectorSnapshot(
            hevy_last_workout=workout,
            hevy_workouts_7d=[workout],
        )
        assert cs.hevy_last_workout.id == "hevy_1"


def _make_slot() -> WorkoutSlot:
    return WorkoutSlot(
        date=date(2026, 4, 14),
        sport=Sport.RUNNING,
        workout_type="easy_z1",
        duration_min=45,
        fatigue_score=FatigueScore(
            local_muscular=10.0, cns_load=5.0,
            metabolic_cost=10.0, recovery_hours=12.0, affected_muscles=[],
        ),
    )


class TestPlanSnapshot:
    def test_defaults(self):
        ps = PlanSnapshot()
        assert ps.today == []
        assert ps.week == []
        assert ps.week_number == 1
        assert ps.phase == "base"

    def test_with_sessions(self):
        slot = _make_slot()
        ps = PlanSnapshot(today=[slot], week=[slot], week_number=3, phase="build")
        assert len(ps.today) == 1
        assert ps.week_number == 3
        assert ps.phase == "build"


class TestAllostaticSummary:
    def test_defaults(self):
        s = AllostaticSummary()
        assert s.history_28d == []
        assert s.trend == "stable"
        assert s.avg_score_7d == 0.0

    def test_invalid_trend_raises(self):
        with pytest.raises(ValidationError):
            AllostaticSummary(trend="worsening")

    def test_with_history(self):
        entries = [
            AllostaticEntry(
                date=date(2026, 4, i),
                allostatic_score=float(30 + i),
                components=AllostaticComponents(),
                intensity_cap_applied=1.0,
            )
            for i in range(1, 8)
        ]
        s = AllostaticSummary(history_28d=entries, trend="improving", avg_score_7d=34.0)
        assert len(s.history_28d) == 7
        assert s.trend == "improving"


class TestDailyJournal:
    def test_minimal(self):
        j = DailyJournal(date=date(2026, 4, 13))
        assert j.check_in is None
        assert j.comment is None
        assert j.mood_score is None

    def test_full(self):
        j = DailyJournal(
            date=date(2026, 4, 13),
            check_in=EnergyCheckIn(work_intensity="normal", stress_level="mild"),
            comment="Felt tired after yesterday's long run.",
            mood_score=7,
        )
        assert j.check_in.work_intensity == "normal"
        assert j.comment == "Felt tired after yesterday's long run."
        assert j.mood_score == 7

    def test_mood_below_1_raises(self):
        with pytest.raises(ValidationError):
            DailyJournal(date=date(2026, 4, 13), mood_score=0)

    def test_mood_above_10_raises(self):
        with pytest.raises(ValidationError):
            DailyJournal(date=date(2026, 4, 13), mood_score=11)


def _make_athlete_profile() -> AthleteProfile:
    return AthleteProfile(
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


def _make_veto() -> RecoveryVetoV3:
    return RecoveryVetoV3(
        status="green",
        hrv_component="green",
        acwr_component="green",
        ea_component="green",
        allostatic_component="green",
        final_intensity_cap=1.0,
        veto_triggered=False,
        veto_reasons=[],
    )


class TestAthleteState:
    def test_minimal_valid(self):
        state = AthleteState(
            athlete_id="athlete-001",
            last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            sync_sources=[],
            profile=_make_athlete_profile(),
            metrics=AthleteMetrics(date=date(2026, 4, 13)),
            connectors=ConnectorSnapshot(),
            plan=PlanSnapshot(),
            recovery=_make_veto(),
            allostatic=AllostaticSummary(),
        )
        assert state.athlete_id == "athlete-001"
        assert state.energy is None
        assert state.hormonal is None
        assert state.journal is None

    def test_with_all_optional_sections(self):
        snap = EnergySnapshot(
            timestamp=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            allostatic_score=30.0,
            cognitive_load=25.0,
            energy_availability=45.0,
            sleep_quality=80.0,
            recommended_intensity_cap=1.0,
            veto_triggered=False,
        )
        hormonal = HormonalProfile(enabled=True, tracking_source="manual", current_phase="follicular")
        journal = DailyJournal(
            date=date(2026, 4, 13),
            check_in=EnergyCheckIn(work_intensity="normal", stress_level="none"),
            comment="Good day.",
            mood_score=8,
        )
        state = AthleteState(
            athlete_id="athlete-002",
            last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            sync_sources=[SyncSource(
                name="strava",
                last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
                status="ok",
            )],
            profile=_make_athlete_profile(),
            metrics=AthleteMetrics(date=date(2026, 4, 13), hrv_rmssd=65.0, acwr=1.1, acwr_status="safe"),
            connectors=ConnectorSnapshot(),
            plan=PlanSnapshot(week_number=3, phase="build"),
            energy=snap,
            recovery=_make_veto(),
            hormonal=hormonal,
            allostatic=AllostaticSummary(trend="improving", avg_score_7d=32.0),
            journal=journal,
        )
        assert state.energy.allostatic_score == 30.0
        assert state.hormonal.current_phase == "follicular"
        assert state.journal.mood_score == 8
        assert state.plan.phase == "build"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            AthleteState(
                athlete_id="athlete-003",
                last_synced_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
                sync_sources=[],
                # missing profile, metrics, connectors, plan, recovery
            )
