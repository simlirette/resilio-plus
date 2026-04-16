"""Verify HeadCoach.build_week + specialist calls are tracked in metrics."""
from datetime import date

from app.agents.base import AgentContext, AgentRecommendation, BaseAgent
from app.agents.head_coach import HeadCoach
from app.observability.metrics import metrics
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.fatigue import FatigueScore


class _FakeRunningAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "running"

    def analyze(self, context):
        return AgentRecommendation(
            agent_name="running",
            fatigue_score=FatigueScore(
                local_muscular=10.0, cns_load=5.0, metabolic_cost=5.0,
                recovery_hours=1.0, affected_muscles=["quads"],
            ),
            weekly_load=100.0,
            suggested_sessions=[],
        )


def _minimal_profile() -> AthleteProfile:
    # Schema fields mirror tests/backend/agents/test_running_coach.py _athlete() helper
    return AthleteProfile(
        name="Test",
        age=30,
        sex="M",
        weight_kg=70.0,
        height_cm=175.0,
        sports=[Sport.RUNNING],
        primary_sport=Sport.RUNNING,
        goals=["finish 5K"],
        target_race_date=date(2026, 10, 15),
        available_days=[0, 2, 4],
        hours_per_week=5.0,
    )


def _reset():
    metrics.agent_calls_total.clear()
    metrics.agent_latency_ms.clear()


def test_head_coach_build_week_tracks_head_coach_metric():
    _reset()
    agents = [_FakeRunningAgent()]
    hc = HeadCoach(agents=agents)
    ctx = AgentContext(
        athlete=_minimal_profile(),
        date_range=(date(2026, 4, 14), date(2026, 4, 20)),
        phase="BASE",
    )
    try:
        hc.build_week(ctx, load_history=[])
    except Exception:
        # Even if downstream fails, the head_coach call should have been tracked
        pass
    assert metrics.agent_calls_total[("head_coach", "ok")] + metrics.agent_calls_total[("head_coach", "error")] == 1


def test_head_coach_build_week_tracks_specialist_metric():
    _reset()
    agents = [_FakeRunningAgent()]
    hc = HeadCoach(agents=agents)
    ctx = AgentContext(
        athlete=_minimal_profile(),
        date_range=(date(2026, 4, 14), date(2026, 4, 20)),
        phase="BASE",
    )
    try:
        hc.build_week(ctx, load_history=[])
    except Exception:
        pass
    assert metrics.agent_calls_total[("running_coach", "ok")] == 1
