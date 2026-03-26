from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.fatigue import FatigueScore


@dataclass
class GlobalFatigue:
    total_local_muscular: float
    total_cns_load: float
    total_metabolic_cost: float
    peak_recovery_hours: float
    all_affected_muscles: list[str] = field(default_factory=list)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _ordered_union(lists: list[list[str]]) -> list[str]:
    """Return deduplicated union preserving insertion order."""
    seen: set[str] = set()
    result: list[str] = []
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
    return result


def aggregate_fatigue(scores: list[FatigueScore]) -> GlobalFatigue:
    """Aggregate multiple FatigueScores into a single GlobalFatigue.

    Empty list returns all-zero GlobalFatigue with empty muscle list.
    Each dimension is summed then clamped to [0, 100].
    peak_recovery_hours = max recovery across all scores.
    all_affected_muscles = ordered union (deduped, insertion order preserved).
    """
    if not scores:
        return GlobalFatigue(0.0, 0.0, 0.0, 0.0, [])

    return GlobalFatigue(
        total_local_muscular=_clamp(sum(s.local_muscular for s in scores)),
        total_cns_load=_clamp(sum(s.cns_load for s in scores)),
        total_metabolic_cost=_clamp(sum(s.metabolic_cost for s in scores)),
        peak_recovery_hours=max(s.recovery_hours for s in scores),
        all_affected_muscles=_ordered_union([s.affected_muscles for s in scores]),
    )
