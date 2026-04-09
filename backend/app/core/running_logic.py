from __future__ import annotations

from datetime import date, timedelta

from ..core.periodization import TIDStrategy
from ..schemas.athlete import Sport
from ..schemas.connector import StravaActivity
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot

# VDOT lookup table (Jack Daniels, simplified)
# (vdot, easy_pace_s_per_km, threshold_pace_s_per_km)
_VDOT_TABLE: list[tuple[int, int, int]] = [
    (30, 450, 390), (33, 425, 368), (35, 405, 350), (38, 383, 332),
    (40, 370, 315), (43, 350, 300), (45, 340, 290), (48, 322, 275),
    (50, 315, 270), (53, 300, 258), (55, 295, 250), (58, 280, 238),
    (60, 275, 235), (65, 258, 220), (70, 242, 207),
]


def estimate_vdot(
    activities: list[StravaActivity],
    reference_date: date | None = None,
) -> float:
    """Estimate VDOT from recent run activities. Returns 35.0 (beginner) if no data.

    Filters to last 30 days, sport_type == "Run", distance >= 1000m.
    Computes pace per km and finds the nearest VDOT row by easy_pace.
    Returns the maximum VDOT found across all valid activities.
    """
    from datetime import date as _date
    ref = reference_date or _date.today()
    cutoff = ref - timedelta(days=30)
    runs = [
        a for a in activities
        if a.sport_type == "Run"
        and a.date >= cutoff
        and a.distance_meters is not None
        and a.distance_meters >= 1000
    ]
    if not runs:
        return 35.0

    best = 0
    for a in runs:
        pace = a.duration_seconds / (a.distance_meters / 1000)  # s/km
        row = min(_VDOT_TABLE, key=lambda r: abs(r[1] - pace))
        if row[0] > best:
            best = row[0]

    return float(best) if best > 0 else 35.0


def compute_running_fatigue(activities: list[StravaActivity]) -> FatigueScore:
    """Compute FatigueScore from a pre-filtered list of running activities.

    Caller must pre-filter to the relevant time window (e.g., last 7 days).
    This function does NOT filter by date.
    """
    if not activities:
        return FatigueScore(
            local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
            recovery_hours=0.0, affected_muscles=[],
        )

    total_km = sum((a.distance_meters or 0.0) / 1000.0 for a in activities)
    hiit_count = sum(1 for a in activities if _is_hiit(a))

    metabolic = sum(
        (a.duration_seconds / 60.0) * ((a.perceived_exertion or 5) / 10.0)
        for a in activities
    ) / 10.0

    if any(_is_hiit(a) for a in activities):
        recovery = 24.0
    elif any(
        a.perceived_exertion is not None and 6 <= a.perceived_exertion <= 7
        for a in activities
    ):
        recovery = 12.0
    else:
        recovery = 6.0

    return FatigueScore(
        local_muscular=min(100.0, total_km * 3.0),
        cns_load=min(100.0, float(hiit_count) * 20.0),
        metabolic_cost=min(100.0, metabolic),
        recovery_hours=recovery,
        affected_muscles=["quads", "calves", "hamstrings"],
    )


def _is_hiit(a: StravaActivity) -> bool:
    """HIIT = RPE >= 8, OR short effort (<30min) with high average HR (>160 bpm)."""
    if a.perceived_exertion is not None and a.perceived_exertion >= 8:
        return True
    if a.duration_seconds < 1800 and a.average_hr is not None and a.average_hr > 160:
        return True
    return False


def generate_running_sessions(
    vdot: float,
    week_number: int,
    weeks_remaining: int,
    available_days: list[int],   # 0=Mon ... 6=Sun
    hours_budget: float,
    volume_modifier: float,
    tid_strategy: TIDStrategy,
    week_start: date,            # Monday of the planning week
) -> list[WorkoutSlot]:
    """Generate weekly running sessions as WorkoutSlots.

    Wave loading: week_number % 4 == 0 -> deload (60%). Otherwise 5% progressive
    overload per week in block. Taper (weeks_remaining <= 2) overrides to 50%.
    80/20 TID: 80% Z1, 20% quality. Quality selection by tid_strategy.
    Each WorkoutSlot.fatigue_score is zeroed (placeholder; aggregate computed separately).
    """
    if not available_days:
        return []

    # 1. Wave loading (deload check MUST come first)
    base_minutes = hours_budget * 60.0 * volume_modifier
    if week_number % 4 == 0:
        weekly_minutes = base_minutes * 0.6
    else:
        weekly_minutes = base_minutes * (1.0 + 0.05 * ((week_number % 4) - 1))

    # 2. Tapering override
    if weeks_remaining <= 2:
        weekly_minutes = base_minutes * 0.5

    # 3. Build (workout_type, duration_min) list
    raw: list[tuple[str, int]] = []

    if weeks_remaining <= 2:
        z1_dur = max(30, int(weekly_minutes * 0.9))
        raw.append(("easy_z1", min(90, z1_dur)))
        raw.append(("activation_z3", 20))
    else:
        quality_min = int(weekly_minutes * 0.2)
        z1_min = int(weekly_minutes * 0.8)

        # Quality sessions by TID strategy
        if tid_strategy == TIDStrategy.PYRAMIDAL:
            raw.append(("tempo_z2", min(60, max(20, quality_min))))
        elif tid_strategy == TIDStrategy.MIXED:
            tempo_dur = min(40, quality_min)
            raw.append(("tempo_z2", tempo_dur))
            vo2_budget = quality_min - tempo_dur
            if vo2_budget >= 20:
                raw.append(("vo2max_z3", min(45, vo2_budget)))
        elif tid_strategy == TIDStrategy.POLARIZED:
            raw.append(("vo2max_z3", min(45, quality_min)))

        # Z1 sessions
        remaining_z1 = z1_min
        if hours_budget >= 6.0 and remaining_z1 >= 60:
            long_dur = min(120, remaining_z1)
            raw.append(("long_run_z1", long_dur))
            remaining_z1 -= long_dur

        while remaining_z1 >= 30:
            dur = min(90, remaining_z1)
            raw.append(("easy_z1", max(30, dur)))
            remaining_z1 -= dur

    # 4. Assign days: longest sessions -> weekend (5-6) first
    raw_sorted = sorted(raw, key=lambda t: t[1], reverse=True)

    weekend = sorted(d for d in available_days if d >= 5)
    weekday = sorted(d for d in available_days if d < 5)
    if not weekend:
        last = max(available_days)
        day_pool = [last] + sorted(d for d in available_days if d != last)
    else:
        day_pool = weekend + weekday

    sessions_to_place = raw_sorted[:len(day_pool)]

    _Z = FatigueScore(
        local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
        recovery_hours=0.0, affected_muscles=[],
    )

    return [
        WorkoutSlot(
            date=week_start + timedelta(days=day_pool[i]),
            sport=Sport.RUNNING,
            workout_type=wtype,
            duration_min=dur,
            fatigue_score=_Z,
        )
        for i, (wtype, dur) in enumerate(sessions_to_place)
    ]
