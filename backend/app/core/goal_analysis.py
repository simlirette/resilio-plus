from __future__ import annotations

from datetime import date

from ..schemas.athlete import AthleteProfile, Sport

# Keyword → sport weight multiplier
_KEYWORD_WEIGHTS: list[tuple[list[str], Sport, float]] = [
    (["marathon", "5k", "10k", "trail", "course", "running", "run"], Sport.RUNNING, 2.0),
    (["ftp", "vélo", "velo", "biking", "gravel", "cycling", "triathlon"], Sport.BIKING, 2.0),
    (["force", "squat", "hypertrophie", "musculation", "lifting", "deadlift"], Sport.LIFTING, 2.0),
    (["natation", "swimming", "nager", "open water", "swim"], Sport.SWIMMING, 2.0),
]

_NEAR_RACE_WEEKS = 12  # boost if race within this many weeks


def analyze_goals(athlete: AthleteProfile) -> dict[Sport, float]:
    """Interpret athlete goals and return hourly budget per sport.

    Returns dict with exactly the sports in athlete.sports.
    Guarantee: sum(values) == athlete.hours_per_week (within float precision).
    Floor: each active sport receives at least 0.33h (20 min).
    """
    active_sports = list(athlete.sports)
    if not active_sports:
        return {}

    if len(active_sports) == 1:
        return {active_sports[0]: athlete.hours_per_week}

    # 1. Base weights: each sport starts at 1.0
    weights: dict[Sport, float] = {s: 1.0 for s in active_sports}

    # 2. Apply keyword boosts from goals
    goals_lower = " ".join(athlete.goals).lower()
    for keywords, sport, multiplier in _KEYWORD_WEIGHTS:
        if sport not in weights:
            continue
        if any(kw in goals_lower for kw in keywords):
            weights[sport] *= multiplier

    # 3. Near-race boost: if race within _NEAR_RACE_WEEKS, boost detected sport × 1.5
    if athlete.target_race_date:
        weeks_remaining = (athlete.target_race_date - date.today()).days // 7
        if 0 < weeks_remaining <= _NEAR_RACE_WEEKS:
            for keywords, sport, _ in _KEYWORD_WEIGHTS:
                if sport in weights and any(kw in goals_lower for kw in keywords):
                    weights[sport] *= 1.5

    # 4. Normalize to hours_per_week with floor
    floor_h = 0.33  # 20 min minimum per active sport
    total_floor = floor_h * len(active_sports)
    distributable = max(0.0, athlete.hours_per_week - total_floor)

    total_weight = sum(weights.values())
    budgets: dict[Sport, float] = {}
    for sport in active_sports:
        budgets[sport] = floor_h + distributable * (weights[sport] / total_weight)

    # 5. Correct floating-point drift — assign remainder to heaviest sport
    diff = athlete.hours_per_week - sum(budgets.values())
    if abs(diff) > 1e-9:
        heaviest = max(budgets, key=lambda s: budgets[s])
        budgets[heaviest] += diff

    return budgets
