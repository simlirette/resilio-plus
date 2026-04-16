from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.acwr import ACWRResult, ACWRStatus, compute_acwr
from ..core.conflict import Conflict, ConflictSeverity, detect_conflicts
from ..core.fatigue import GlobalFatigue, aggregate_fatigue
from ..core.goal_analysis import analyze_goals
from ..core.periodization import PeriodizationPhase, get_current_phase
from ..observability.metrics import track_agent_call
from ..schemas.plan import WorkoutSlot
from .prompts import HEAD_COACH_PROMPT

_SYSTEM_PROMPT = HEAD_COACH_PROMPT


@dataclass
class WeeklyPlan:
    phase: PeriodizationPhase
    acwr: ACWRResult
    global_fatigue: GlobalFatigue
    conflicts: list[Conflict]
    sessions: list[WorkoutSlot]
    readiness_level: str  # "green" | "yellow" | "red"
    notes: list[str] = field(default_factory=list)


class HeadCoach:
    """Orchestrates specialist agents and arbitrates a coherent weekly training plan."""

    def __init__(self, agents: list[BaseAgent]) -> None:
        self.agents = agents

    def build_week(
        self,
        context: AgentContext,
        load_history: list[float],
    ) -> WeeklyPlan:
        """Build a weekly training plan by orchestrating all specialist agents.

        Args:
            context: Planning context including athlete profile and connector data.
            load_history: Daily loads in oldest-first chronological order (from DB).
                          HeadCoach appends the new week's total load before computing ACWR.
        """
        with track_agent_call("head_coach"):
            # 0. Compute goal-driven sport budgets and inject into context
            budgets = analyze_goals(context.athlete)
            context = dataclasses.replace(
                context,
                sport_budgets={s.value: h for s, h in budgets.items()},
            )

            # 1. Invoke all specialist agents
            recommendations: list[AgentRecommendation] = []
            for a in self.agents:
                with track_agent_call(f"{a.name}_coach"):
                    recommendations.append(a.analyze(context))

            # 2. Compute unified cross-sport ACWR
            weekly_load = sum(r.weekly_load for r in recommendations)
            acwr = compute_acwr(load_history + [weekly_load])

            # 3. Aggregate FatigueScores
            global_fatigue = aggregate_fatigue([r.fatigue_score for r in recommendations])

            # 4. Determine macro phase
            phase = get_current_phase(
                context.athlete.target_race_date,
                context.date_range[0],
            )

            # 5. Detect inter-agent conflicts
            conflicts = detect_conflicts(recommendations)

            # 6. Compute global readiness (minimum modifier drives decisions)
            readiness_modifier = (
                min(r.readiness_modifier for r in recommendations) if recommendations else 1.0
            )
            readiness_level = self._modifier_to_level(readiness_modifier)

            # 7. Collect agent notes
            notes = [r.notes for r in recommendations if r.notes]

            # 8. Arbitrate final session list
            all_sessions = [s for r in recommendations for s in r.suggested_sessions]
            sessions = self._arbitrate(all_sessions, conflicts, acwr, readiness_modifier)

            return WeeklyPlan(
                phase=phase,
                acwr=acwr,
                global_fatigue=global_fatigue,
                conflicts=conflicts,
                sessions=sessions,
                readiness_level=readiness_level,
                notes=notes,
            )

    def _modifier_to_level(self, modifier: float) -> str:
        if modifier >= 0.9:
            return "green"
        if modifier >= 0.6:
            return "yellow"
        return "red"

    def _arbitrate(
        self,
        sessions: list[WorkoutSlot],
        conflicts: list[Conflict],
        acwr: ACWRResult,
        readiness_modifier: float,
    ) -> list[WorkoutSlot]:
        # Work on copies to avoid mutating inputs (WorkoutSlot is a Pydantic BaseModel)
        result = [s.model_copy() for s in sessions]

        # Rule 1: RED readiness → convert all sessions to Z1
        if readiness_modifier < 0.6:
            result = [s.model_copy(update={"workout_type": "easy_z1"}) for s in result]
            return result  # No further arbitration needed on Z1 sessions

        # Rule 2: DANGER ACWR → scale all session durations by 0.75 (25% reduction)
        if acwr.status == ACWRStatus.DANGER:
            result = [
                s.model_copy(update={"duration_min": max(1, int(s.duration_min * 0.75))})
                for s in result
            ]

        # Rule 3: CRITICAL conflicts → drop shorter session of conflicting pair
        for conflict in conflicts:
            if conflict.severity != ConflictSeverity.CRITICAL:
                continue
            # Find sessions belonging to the conflicting agents on the same date
            agents_in_conflict = set(conflict.agents)
            candidate_sessions = [
                s
                for s in result
                if s.sport.value in agents_in_conflict
                or any(a in s.workout_type for a in agents_in_conflict)
            ]
            if len(candidate_sessions) >= 2:
                # Drop shorter session (tiebreaker: alphabetically later sport name)
                shortest_duration = min(s.duration_min for s in candidate_sessions)
                candidates_shortest = [
                    s for s in candidate_sessions if s.duration_min == shortest_duration
                ]
                if len(candidates_shortest) == 1:
                    to_drop = candidates_shortest[0]
                else:
                    # Tiebreak: drop alphabetically later sport name
                    to_drop = max(candidates_shortest, key=lambda s: s.sport.value)
                result = [s for s in result if s is not to_drop]

        return result
