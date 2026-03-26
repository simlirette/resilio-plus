from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class MacroPhase(str, Enum):
    # week-count thresholds = weeks_remaining until race date
    GENERAL_PREP    = "general_prep"       # > 22 weeks
    SPECIFIC_PREP   = "specific_prep"      # 14–22 weeks
    PRE_COMPETITION = "pre_competition"    # 7–13 weeks
    COMPETITION     = "competition"        # 1–6 weeks
    TRANSITION      = "transition"         # post-race (≤ 0 weeks)


class TIDStrategy(str, Enum):
    PYRAMIDAL = "pyramidal"
    POLARIZED = "polarized"
    MIXED     = "mixed"


@dataclass
class PeriodizationPhase:
    phase: MacroPhase
    weeks_remaining: int
    tid_recommendation: TIDStrategy
    volume_modifier: float


_PHASE_TABLE: list[tuple[int, MacroPhase, TIDStrategy, float]] = [
    # (min_weeks_remaining, phase, tid, volume_modifier) — evaluated top-down
    (23, MacroPhase.GENERAL_PREP,    TIDStrategy.PYRAMIDAL, 1.0),
    (14, MacroPhase.SPECIFIC_PREP,   TIDStrategy.MIXED,     0.9),
    (7,  MacroPhase.PRE_COMPETITION, TIDStrategy.POLARIZED, 0.8),
    (1,  MacroPhase.COMPETITION,     TIDStrategy.POLARIZED, 0.5),
    (0,  MacroPhase.TRANSITION,      TIDStrategy.MIXED,     0.6),
]


def get_current_phase(target_race_date: date | None, today: date) -> PeriodizationPhase:
    """Determine macro-annual training phase from weeks remaining until race.

    If target_race_date is None, defaults to GENERAL_PREP.
    weeks_remaining = (target_race_date - today).days // 7
    """
    if target_race_date is None:
        return PeriodizationPhase(
            phase=MacroPhase.GENERAL_PREP,
            weeks_remaining=-1,
            tid_recommendation=TIDStrategy.PYRAMIDAL,
            volume_modifier=1.0,
        )

    weeks_remaining = (target_race_date - today).days // 7

    for min_weeks, phase, tid, vol in _PHASE_TABLE:
        if weeks_remaining >= min_weeks:
            return PeriodizationPhase(
                phase=phase,
                weeks_remaining=weeks_remaining,
                tid_recommendation=tid,
                volume_modifier=vol,
            )

    # weeks_remaining < 0 (post-race) → TRANSITION
    return PeriodizationPhase(
        phase=MacroPhase.TRANSITION,
        weeks_remaining=weeks_remaining,
        tid_recommendation=TIDStrategy.MIXED,
        volume_modifier=0.6,
    )
