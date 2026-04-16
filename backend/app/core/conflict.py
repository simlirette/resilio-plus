from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from ..agents.base import AgentRecommendation
from ..schemas.plan import WorkoutSlot


class ConflictSeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Conflict:
    severity: ConflictSeverity
    rule: str
    agents: list[str] = field(default_factory=list)
    message: str = ""


# workout_type keywords that classify a session as HIIT/interval
_HIIT_KEYWORDS = ("hiit", "interval", "vo2max", "repetition", "speed")
# workout_type prefixes/keywords that classify as Z2/MICT (no interference with strength)
_Z2_KEYWORDS = ("z1", "z2", "easy", "recovery", "mict", "base")


def _is_hiit(workout_type: str) -> bool:
    wt = workout_type.lower()
    return any(k in wt for k in _HIIT_KEYWORDS)


def _is_z2(workout_type: str) -> bool:
    wt = workout_type.lower()
    return any(k in wt for k in _Z2_KEYWORDS)


def _sessions_by_date(
    recommendations: list[AgentRecommendation],
) -> dict[date, list[tuple[str, WorkoutSlot]]]:
    """Group (agent_name, session) pairs by date."""
    by_date: dict[date, list[tuple[str, WorkoutSlot]]] = {}
    for rec in recommendations:
        for session in rec.suggested_sessions:
            by_date.setdefault(session.date, []).append((rec.agent_name, session))
    return by_date


def detect_conflicts(recommendations: list[AgentRecommendation]) -> list[Conflict]:
    """Detect force/endurance scheduling conflicts per Supplement §1.2.

    Rules (checked per day):
    1. HIIT/interval + lifting same day → CRITICAL
    2. Non-swimming endurance (non-Z2) + lifting same day → WARNING
    3. Z2/MICT + lifting same day → no conflict (§1.2 exception)
    4. Swimming + lifting same day → WARNING (reduced severity)
    """
    conflicts: list[Conflict] = []

    by_date = _sessions_by_date(recommendations)

    for day, day_sessions in by_date.items():
        lifting_sessions = [(a, s) for a, s in day_sessions if a == "lifting"]
        endurance_sessions = [
            (a, s) for a, s in day_sessions if a in ("running", "biking", "swimming")
        ]

        if not lifting_sessions or not endurance_sessions:
            continue

        for lift_agent, lift_slot in lifting_sessions:
            for end_agent, end_slot in endurance_sessions:
                wt = end_slot.workout_type

                # Rule 1: HIIT + strength → CRITICAL
                if _is_hiit(wt):
                    conflicts.append(
                        Conflict(
                            severity=ConflictSeverity.CRITICAL,
                            rule="hiit_strength_same_session",
                            agents=[end_agent, lift_agent],
                            message=(
                                f"{end_agent} has HIIT session and {lift_agent} on the same day. "
                                "HIIT + strength training: maximal interference. "
                                "Separate by at least 24h."
                            ),
                        )
                    )
                    continue

                # Rule 3: Z2/MICT → explicitly no conflict
                if _is_z2(wt):
                    continue

                # Rule 4: Swimming (non-HIIT, non-Z2) → reduced WARNING
                if end_agent == "swimming":
                    conflicts.append(
                        Conflict(
                            severity=ConflictSeverity.WARNING,
                            rule="swimming_before_strength_reduced",
                            agents=[end_agent, lift_agent],
                            message=(
                                f"Swimming and {lift_agent} on the same day. "
                                "Swimming is less inflammatory than running — minor interference."
                            ),
                        )
                    )
                    continue

                # Rule 2: Other endurance (tempo, progression, etc.) + strength → WARNING
                conflicts.append(
                    Conflict(
                        severity=ConflictSeverity.WARNING,
                        rule="endurance_before_strength_gap",
                        agents=[end_agent, lift_agent],
                        message=(
                            f"{end_agent} ({wt}) and {lift_agent} on the same day. "
                            "Endurance before strength: 3h gap needed to avoid mTOR/AMPK"
                            " interference."
                        ),
                    )
                )

    return conflicts
