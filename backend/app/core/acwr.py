from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ACWRStatus(str, Enum):
    UNDERTRAINED = "undertrained"
    SAFE = "safe"
    CAUTION = "caution"
    DANGER = "danger"


@dataclass
class ACWRResult:
    acute_7d: float
    chronic_28d: float
    ratio: float
    status: ACWRStatus
    max_safe_weekly_load: float


_LAMBDA_ACUTE = 2 / (7 + 1)  # 0.25
_LAMBDA_CHRONIC = 2 / (28 + 1)  # ≈ 0.0690


def _ewma(loads: list[float], lam: float) -> float:
    """Compute EWMA over loads (oldest-first). Seed = first element."""
    if not loads:
        return 0.0
    ewma = loads[0]
    for load in loads[1:]:
        ewma = load * lam + ewma * (1 - lam)
    return ewma


def _ratio_to_status(ratio: float) -> ACWRStatus:
    if ratio < 0.8:
        return ACWRStatus.UNDERTRAINED
    if ratio < 1.3:
        return ACWRStatus.SAFE
    if ratio < 1.5:
        return ACWRStatus.CAUTION
    return ACWRStatus.DANGER


def compute_acwr(daily_loads: list[float]) -> ACWRResult:
    """Compute EWMA-based ACWR from oldest-first daily load history.

    Args:
        daily_loads: List of daily loads in chronological order (index 0 = oldest).
                     Empty list returns safe zero result.
    """
    if not daily_loads:
        return ACWRResult(
            acute_7d=0.0,
            chronic_28d=0.0,
            ratio=0.0,
            status=ACWRStatus.SAFE,
            max_safe_weekly_load=0.0,
        )

    acute = _ewma(daily_loads, _LAMBDA_ACUTE)
    chronic = _ewma(daily_loads, _LAMBDA_CHRONIC)

    ratio = acute / chronic if chronic > 0 else 0.0
    status = _ratio_to_status(ratio)
    max_safe = chronic * 1.1

    return ACWRResult(
        acute_7d=round(acute, 4),
        chronic_28d=round(chronic, 4),
        ratio=round(ratio, 4),
        status=status,
        max_safe_weekly_load=round(max_safe, 4),
    )
