"""Cycle hormonal feminin — detection de phase, ajustements par phase, detection RED-S.

Reference : docs/resilio-v3-master.md — section 4 (cycle hormonal) et 6 (EA / RED-S)
Data      : data/hormonal_adjustments.json, data/ea_thresholds.json
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

CyclePhase = Literal["menstrual", "follicular", "ovulation", "luteal"]


# ---------------------------------------------------------------------------
# Phase detection
# ---------------------------------------------------------------------------


def compute_cycle_day(
    last_period_start: date,
    today: date,
    cycle_length: int = 28,
) -> int:
    """Return the 1-based cycle day, wrapping at cycle_length.

    Day 1 = last_period_start itself.
    """
    delta = (today - last_period_start).days
    return (delta % cycle_length) + 1


def detect_cycle_phase(cycle_day: int, cycle_length: int = 28) -> CyclePhase:
    """Map a cycle day to the corresponding hormonal phase.

    Boundaries (per docs/resilio-v3-master.md section 4.2):
    - Menstrual  : days 1-5
    - Follicular : days 6-13
    - Ovulation  : days 14-15
    - Luteal     : days 16 to cycle_length
    """
    if cycle_day <= 5:
        return "menstrual"
    if cycle_day <= 13:
        return "follicular"
    if cycle_day <= 15:
        return "ovulation"
    return "luteal"


# ---------------------------------------------------------------------------
# Lifting adjustments
# ---------------------------------------------------------------------------

_LIFTING: dict[str, dict[str, Any]] = {
    "menstrual": {
        "rpe_offset": -1,
        "no_1rm": True,
        "notes": (
            "Phase menstruelle — RPE cible reduit de 1 point, pas de 1RM attempts. "
            "Tolerance a la douleur reduite, recuperation ralentie."
        ),
    },
    "follicular": {
        "rpe_offset": 0,
        "no_1rm": False,
        "pr_week": True,
        "notes": (
            "Phase folliculaire — Phase optimale pour gains de force. "
            "Semaine ideale pour PR attempts et sessions lourdes."
        ),
    },
    "ovulation": {
        "rpe_offset": 0,
        "no_1rm": False,
        "ligament_risk_note": True,
        "notes": (
            "Phase ovulatoire — Force et puissance au maximum. "
            "Maximiser performance mais insister sur la technique : "
            "risque ligamentaire accru (laxite elevee)."
        ),
    },
    "luteal": {
        "rpe_offset": -1,
        "no_1rm": False,
        "notes": (
            "Phase luteale — Volume maintenu, intensite reduite progressivement. "
            "RPE cible -1 en fin de phase. Catabolisme musculaire augmente."
        ),
    },
}


def get_lifting_adjustments(phase: CyclePhase) -> dict[str, Any]:
    """Return lifting coaching adjustments for the given cycle phase.

    Keys guaranteed:
    - rpe_offset (int)  : RPE delta vs normal (0 = unchanged, -1 = one point lower)
    - no_1rm (bool)     : True if 1RM attempts should be avoided
    - notes (str)       : Human-readable coaching note
    Optional keys:
    - pr_week (bool)    : follicular only — ideal for PRs
    - ligament_risk_note (bool) : ovulation only — warn about ACL/ligament laxity
    """
    return dict[str, Any](_LIFTING[phase])


# ---------------------------------------------------------------------------
# Running adjustments
# ---------------------------------------------------------------------------

_RUNNING: dict[str, dict[str, Any]] = {
    "menstrual": {
        "replace_intervals_with_z2": True,
        "avoid_direction_changes": False,
        "increase_hydration": False,
        "avoid_heat": False,
        "notes": (
            "Phase menstruelle — Remplacer les fractionnes intensifs par Z2 "
            "si douleurs importantes. Fatigue percue augmentee."
        ),
    },
    "follicular": {
        "replace_intervals_with_z2": False,
        "avoid_direction_changes": False,
        "increase_hydration": False,
        "avoid_heat": False,
        "high_intensity_optimal": True,
        "notes": (
            "Phase folliculaire — Fractionnes a haute intensite : timing optimal. "
            "Recuperation la plus rapide du cycle."
        ),
    },
    "ovulation": {
        "replace_intervals_with_z2": False,
        "avoid_direction_changes": True,
        "increase_hydration": False,
        "avoid_heat": False,
        "notes": (
            "Phase ovulatoire — Eviter les changements de direction brusques "
            "et terrains instables : laxite ligamentaire elevee."
        ),
    },
    "luteal": {
        "replace_intervals_with_z2": False,
        "avoid_direction_changes": False,
        "increase_hydration": True,
        "avoid_heat": True,
        "notes": (
            "Phase luteale — Hydratation augmentee, eviter les seances dans la chaleur. "
            "Thermoregulation moins efficace (temperature basale +0.3-0.5 C)."
        ),
    },
}


def get_running_adjustments(phase: CyclePhase) -> dict[str, Any]:
    """Return running coaching adjustments for the given cycle phase.

    Keys guaranteed:
    - replace_intervals_with_z2 (bool)
    - avoid_direction_changes (bool)
    - increase_hydration (bool)
    - avoid_heat (bool)
    - notes (str)
    Optional keys:
    - high_intensity_optimal (bool) : follicular only
    """
    return dict[str, Any](_RUNNING[phase])


# ---------------------------------------------------------------------------
# Nutrition adjustments
# ---------------------------------------------------------------------------

_NUTRITION: dict[str, dict[str, Any]] = {
    "menstrual": {
        "protein_extra_g_per_kg": 0.0,
        "calories_extra": 0,
        "supplements": ["iron", "magnesium", "omega3"],
        "notes": (
            "Phase menstruelle — Augmenter fer (viande rouge, epinards), "
            "magnesium, omega-3. Prostaglandines elevees."
        ),
    },
    "follicular": {
        "protein_extra_g_per_kg": 0.0,
        "calories_extra": 0,
        "supplements": [],
        "notes": (
            "Phase folliculaire — Glucides moderes OK. "
            "Sensibilite insuline favorise le stockage glycogene."
        ),
    },
    "ovulation": {
        "protein_extra_g_per_kg": 0.0,
        "calories_extra": 0,
        "supplements": [],
        "notes": (
            "Phase ovulatoire — Maintenir hydratation optimale " "(retention d'eau possible)."
        ),
    },
    "luteal": {
        "protein_extra_g_per_kg": 0.2,
        "calories_extra": 200,
        "supplements": ["iron", "magnesium"],
        "notes": (
            "Phase luteale — Proteines +0.2 g/kg/jour (catabolisme accru), "
            "calories +200 kcal, fer et magnesium."
        ),
    },
}


def get_nutrition_adjustments(phase: CyclePhase) -> dict[str, Any]:
    """Return nutrition coaching adjustments for the given cycle phase.

    Keys guaranteed:
    - protein_extra_g_per_kg (float) : additional protein target
    - calories_extra (int)           : additional daily kcal target
    - supplements (list[str])        : recommended supplements
    - notes (str)
    """
    adj = dict[str, Any](_NUTRITION[phase])
    adj["supplements"] = list(adj["supplements"])  # return a copy
    return adj


# ---------------------------------------------------------------------------
# Energy Availability + RED-S detection
# ---------------------------------------------------------------------------

# Thresholds from data/ea_thresholds.json and docs section 6.2
_EA_THRESHOLDS: dict[str, dict[str, float]] = {
    "female": {"optimal": 45.0, "critical": 30.0},
    "male": {"optimal": 45.0, "critical": 25.0},
}


def ea_status(ea: float, sex: str) -> str:
    """Classify Energy Availability (kcal/kg FFM) as 'optimal', 'suboptimal', or 'critical'.

    Female: optimal >= 45, suboptimal [30, 45), critical < 30
    Male  : optimal >= 45, suboptimal [25, 45), critical < 25
    """
    thresholds = _EA_THRESHOLDS.get(sex, _EA_THRESHOLDS["female"])
    if ea >= thresholds["optimal"]:
        return "optimal"
    if ea >= thresholds["critical"]:
        return "suboptimal"
    return "critical"


def check_reds(
    ea_history: list[float],
    threshold: float,
    required_days: int = 3,
) -> bool:
    """Return True if the last `required_days` consecutive EA values are strictly below threshold.

    RED-S flag: 3 consecutive days EA < threshold (docs section 6.3).
    Returns False if history has fewer entries than required_days.
    """
    if len(ea_history) < required_days:
        return False
    window = ea_history[-required_days:]
    return all(ea < threshold for ea in window)
