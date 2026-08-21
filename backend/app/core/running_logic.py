from __future__ import annotations

import json
import pathlib
from datetime import date, timedelta
from typing import Any

from ..core.periodization import TIDStrategy
from ..schemas.athlete import Sport
from ..schemas.connector import StravaActivity
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot

# ---------------------------------------------------------------------------
# VDOT paces from data/vdot_paces.json (Jack Daniels, full table)
# ---------------------------------------------------------------------------

_VDOT_PACES_PATH = pathlib.Path(__file__).parents[3] / "data" / "vdot_paces.json"
_VDOT_PACES: dict[str, dict[str, Any]] = {}


def _load_vdot_paces() -> dict[str, dict[str, Any]]:
    global _VDOT_PACES
    if not _VDOT_PACES:
        with _VDOT_PACES_PATH.open(encoding="utf-8") as f:
            raw = json.load(f)
        _VDOT_PACES = raw.get("vdot_paces", {})
    return _VDOT_PACES


def get_vdot_paces(vdot: float) -> dict[str, Any]:
    """Lookup Daniels paces for a VDOT value from data/vdot_paces.json.

    Returns a dict[str, Any] with keys:
      easy_min_per_km, easy_max_per_km, long_run_pace_per_km,
      threshold_pace_per_km, interval_pace_per_km, repetition_pace_per_km, etc.

    Clamps VDOT to the available range [20, 85] and rounds to nearest integer.
    Falls back to nearest available entry if exact match not found.
    Returns empty dict[str, Any] if data file unavailable.
    """
    try:
        paces = _load_vdot_paces()
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {}

    if not paces:
        return {}

    vdot_int = max(20, min(85, round(vdot)))
    key = str(vdot_int)
    if key in paces:
        return dict[str, Any](paces[key])

    # Fallback: nearest available VDOT
    available = sorted(int(k) for k in paces.keys())
    nearest = min(available, key=lambda v: abs(v - vdot_int))
    return dict[str, Any](paces.get(str(nearest), {}))


# HR zone descriptions (Daniels/Seiler hybrid — running_zones.json)
_HR_ZONES: dict[str, str] = {
    "easy_z1": "Z1 easy (60-74% HRmax)",
    "long_run_z1": "Z1 long run (60-74% HRmax)",
    "tempo_z2": "Z2 tempo (80-88% HRmax)",
    "vo2max_z3": "Z3 VO2max (95-100% HRmax)",
    "activation_z3": "Z3 activation (95-100% HRmax)",
}


def _build_pace_note(workout_type: str, paces: dict[str, Any]) -> str:
    """Build a human-readable pace + HR zone note for a WorkoutSlot."""
    if not paces:
        return ""
    zone = _HR_ZONES.get(workout_type, "")
    if workout_type == "easy_z1":
        easy_min = paces.get("easy_min_per_km", "")
        easy_max = paces.get("easy_max_per_km", "")
        pace_str = f"{easy_min}–{easy_max}/km" if easy_min and easy_max else ""
    elif workout_type == "long_run_z1":
        lr = paces.get("long_run_pace_per_km", "")
        easy_max = paces.get("easy_max_per_km", "")
        pace_str = f"{lr}/km" if lr else (f"≤{easy_max}/km" if easy_max else "")
    elif workout_type == "tempo_z2":
        t = paces.get("threshold_pace_per_km", "")
        pace_str = f"{t}/km" if t else ""
    elif workout_type in ("vo2max_z3", "activation_z3"):
        iv = paces.get("interval_pace_per_km", "")
        pace_str = f"{iv}/km" if iv else ""
    else:
        pace_str = ""

    parts = [p for p in [pace_str, zone] if p]
    return " | ".join(parts)


# VDOT lookup table (Jack Daniels, simplified) — used by estimate_vdot
# (vdot, easy_pace_s_per_km, threshold_pace_s_per_km)
_VDOT_TABLE: list[tuple[int, int, int]] = [
    (30, 450, 390),
    (33, 425, 368),
    (35, 405, 350),
    (38, 383, 332),
    (40, 370, 315),
    (43, 350, 300),
    (45, 340, 290),
    (48, 322, 275),
    (50, 315, 270),
    (53, 300, 258),
    (55, 295, 250),
    (58, 280, 238),
    (60, 275, 235),
    (65, 258, 220),
    (70, 242, 207),
]


# Strava says "Run"; the strava_activities table says "running" (see
# activity_mapper.SPORT_MAP). Filtering on one spelling silently excluded every
# activity read back from the table, dropping VDOT to its beginner floor.
_RUN_SPORT_TYPES: frozenset[str] = frozenset(
    {"run", "running", "trailrun", "virtualrun", "treadmillrun"}
)


def _is_run(sport_type: str | None) -> bool:
    key = "".join((sport_type or "").split()).replace("-", "").replace("_", "")
    return key.lower() in _RUN_SPORT_TYPES


# A run shorter than this cannot establish an aerobic pace -- a 1 km effort is
# a sprint, and reading its pace off an easy-pace table inflates the estimate.
_MIN_VDOT_DISTANCE_M = 3000.0
_VDOT_WINDOW_DAYS = 30
_BEGINNER_VDOT = 35.0


def qualifies_for_vdot(
    activity: StravaActivity,
    reference_date: date | None = None,
) -> bool:
    """Whether one activity may contribute to a VDOT estimate.

    Exposed so callers ask the same question the estimator asks; an inline copy
    of this rule in the view builder drifted from it within a single commit.
    """
    from datetime import date as _date

    ref = reference_date or _date.today()
    return (
        _is_run(activity.sport_type)
        and activity.date >= ref - timedelta(days=_VDOT_WINDOW_DAYS)
        and activity.distance_meters is not None
        and activity.distance_meters >= _MIN_VDOT_DISTANCE_M
        and activity.duration_seconds > 0
    )


def estimate_vdot(
    activities: list[StravaActivity],
    reference_date: date | None = None,
) -> float:
    """Estimate VDOT from recent runs. Returns 35.0 (beginner) when none qualify.

    Each qualifying run's average pace is looked up against the *easy* pace
    column, and the **median** across runs is taken.

    Median, not maximum. The previous version took the fastest run in the
    window, so a single threshold session -- whose average pace is nowhere near
    an easy pace -- set the number, and every prescribed pace for the block
    derived from it. In an 80/20 distribution the median run is an easy run,
    which is what the table is keyed on. It also means one hard day, or one GPS
    glitch, cannot move the estimate.

    This stays an estimate. A declared race time goes through Daniels' table
    instead and should replace it.
    """
    runs = [a for a in activities if qualifies_for_vdot(a, reference_date)]
    if not runs:
        return _BEGINNER_VDOT

    vdots: list[int] = []
    for a in runs:
        pace = a.duration_seconds / ((a.distance_meters or 1.0) / 1000)  # s/km
        row = min(_VDOT_TABLE, key=lambda r: abs(r[1] - pace))
        vdots.append(row[0])

    vdots.sort()
    middle = len(vdots) // 2
    if len(vdots) % 2:
        median = float(vdots[middle])
    else:
        # Round down on a tie: under-prescribing is the safer error.
        median = float(vdots[middle - 1])

    return median if median > 0 else _BEGINNER_VDOT


def compute_running_fatigue(activities: list[StravaActivity]) -> FatigueScore:
    """Compute FatigueScore from a pre-filtered list of running activities.

    Caller must pre-filter to the relevant time window (e.g., last 7 days).
    This function does NOT filter by date.
    """
    if not activities:
        return FatigueScore(
            local_muscular=0.0,
            cns_load=0.0,
            metabolic_cost=0.0,
            recovery_hours=0.0,
            affected_muscles=[],
        )

    total_km = sum((a.distance_meters or 0.0) / 1000.0 for a in activities)
    hiit_count = sum(1 for a in activities if _is_hiit(a))

    metabolic = (
        sum((a.duration_seconds / 60.0) * ((a.perceived_exertion or 5) / 10.0) for a in activities)
        / 10.0
    )

    if any(_is_hiit(a) for a in activities):
        recovery = 24.0
    elif any(
        a.perceived_exertion is not None and 6 <= a.perceived_exertion <= 7 for a in activities
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


def _resize_week(raw: list[tuple[str, int]], target: int) -> list[tuple[str, int]]:
    """Redistribute a week's minutes across exactly `target` sessions.

    Volume is preserved; only its shape changes. Quality sessions are kept
    ahead of easy ones when shrinking, because three runs must not silently
    become three easy runs -- that is a different training week, not a smaller
    one.
    """
    total = sum(minutes for _, minutes in raw)
    if total <= 0:
        return raw

    quality = [item for item in raw if "easy" not in item[0] and "long" not in item[0]]
    easy = [item for item in raw if item not in quality]
    ordered = quality + easy

    if target < len(ordered):
        kept = ordered[:target]
    else:
        kept = list(ordered)
        # Split the longest easy session repeatedly until the count is reached.
        while len(kept) < target:
            kept.sort(key=lambda item: item[1], reverse=True)
            label, minutes = kept.pop(0)
            half = max(1, minutes // 2)
            kept.extend([(label, half), (label, minutes - half)])

    share = total / len(kept)
    weights = [minutes for _, minutes in kept]
    weight_total = sum(weights) or len(kept)
    resized = [
        (label, max(15, round(total * (minutes / weight_total))))
        for (label, minutes) in kept
    ]
    # `share` is only used to keep short weeks from collapsing to the floor.
    if all(minutes == 15 for _, minutes in resized):
        resized = [(label, max(15, int(share))) for label, _ in kept]
    return resized


def generate_running_sessions(
    vdot: float,
    week_number: int,
    weeks_remaining: int,
    available_days: list[int],  # 0=Mon ... 6=Sun
    hours_budget: float,
    volume_modifier: float,
    tid_strategy: TIDStrategy,
    week_start: date,  # Monday of the planning week
    sessions_target: int | None = None,
    _paces: dict[str, Any] | None = None,  # injected in tests to avoid file I/O
) -> list[WorkoutSlot]:
    """Generate weekly running sessions as WorkoutSlots.

    Wave loading: week_number % 4 == 0 -> deload (60%). Otherwise 5% progressive
    overload per week in block. Taper (weeks_remaining <= 2) overrides to 50%.
    80/20 TID: 80% Z1, 20% quality. Quality selection by tid_strategy.
    Each WorkoutSlot.fatigue_score is zeroed (placeholder; aggregate computed separately).

    ``sessions_target`` is how many runs the athlete asked for. Without it the
    count is a byproduct of dividing the budget into 30-90 minute chunks, and
    the athlete's own answer -- "je vise 3 sorties" -- never reaches the plan.
    Given, it reshapes the same weekly volume into that many sessions rather
    than adding or removing training. Ignored when absent or non-positive, so
    every existing caller is unaffected.
    """
    if not available_days:
        return []

    # Lookup VDOT paces once (injected or from file)
    paces = _paces if _paces is not None else get_vdot_paces(vdot)

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

    # 3b. Reshape to the requested number of sessions, keeping total volume.
    if sessions_target is not None and sessions_target > 0 and raw:
        raw = _resize_week(raw, sessions_target)

    # 4. Assign days: longest sessions -> weekend (5-6) first
    raw_sorted = sorted(raw, key=lambda t: t[1], reverse=True)

    weekend = sorted(d for d in available_days if d >= 5)
    weekday = sorted(d for d in available_days if d < 5)
    if not weekend:
        last = max(available_days)
        day_pool = [last] + sorted(d for d in available_days if d != last)
    else:
        day_pool = weekend + weekday

    sessions_to_place = raw_sorted[: len(day_pool)]

    _z = FatigueScore(
        local_muscular=0.0,
        cns_load=0.0,
        metabolic_cost=0.0,
        recovery_hours=0.0,
        affected_muscles=[],
    )

    return [
        WorkoutSlot(
            date=week_start + timedelta(days=day_pool[i]),
            sport=Sport.RUNNING,
            workout_type=wtype,
            duration_min=dur,
            fatigue_score=_z,
            notes=_build_pace_note(wtype, paces),
        )
        for i, (wtype, dur) in enumerate(sessions_to_place)
    ]
