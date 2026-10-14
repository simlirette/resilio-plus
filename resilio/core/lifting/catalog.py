"""
Exercise catalog — turns Hevy exercise templates into coaching facts:
landmark muscle group (for weekly volume), movement pattern, lower-body flag, SFR tier.

Nothing is guessed: a template with no counted muscle group stays uncounted, and an
exercise missing from the catalog is reported as unmapped by the analysis layer.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from resilio.schemas.lifting import CatalogEntry, ExerciseTemplate, MovementPattern

_HERE = Path(__file__).resolve().parent

# Hevy muscle group → volume-landmark group (None = tracked by Hevy but not counted here)
HEVY_TO_GROUP: dict[str, Optional[str]] = {
    "quadriceps": "quads",
    "hamstrings": "hamstrings",
    "glutes": "glutes",
    "abductors": "glutes",
    "calves": "calves",
    "chest": "chest",
    "lats": "back",
    "upper_back": "back",
    "shoulders": "shoulders",
    "biceps": "biceps",
    "triceps": "triceps",
    "abdominals": "core",
    "adductors": None,
    "lower_back": None,
    "traps": None,
    "forearms": None,
    "neck": None,
    "cardio": None,
    "full_body": None,
    "other": None,
}

LOWER_BODY_MUSCLES = {"quadriceps", "hamstrings", "glutes", "calves", "abductors", "adductors"}

# Ordered: first match wins (split squat must hit "lunge" before "squat").
_PATTERN_RULES: list[tuple[MovementPattern, tuple[str, ...]]] = [
    (MovementPattern.PLYO, ("jump", "hop", "bound", "throw", "slam", "plyo", "skater", "pogo")),
    (
        MovementPattern.CORE,
        (
            "plank",
            "crunch",
            "sit up",
            "sit-up",
            "leg raise",
            "pallof",
            "dead bug",
            "hollow",
            "russian twist",
            "ab wheel",
            "rollout",
            "v up",
        ),
    ),
    (
        MovementPattern.LUNGE,
        ("lunge", "split squat", "step up", "step-up", "step down", "step-down"),
    ),
    (
        MovementPattern.HINGE,
        (
            "deadlift",
            "rdl",
            "good morning",
            "hip thrust",
            "glute bridge",
            "kettlebell swing",
            "back extension",
            "hyperextension",
        ),
    ),
    (MovementPattern.SQUAT, ("squat", "leg press", "wall sit")),
    (
        MovementPattern.PULL,
        ("row", "pull up", "pull-up", "pullup", "pulldown", "chin up", "chin-up", "face pull"),
    ),
    (
        MovementPattern.PUSH,
        (
            "bench press",
            "chest press",
            "shoulder press",
            "overhead press",
            "push up",
            "push-up",
            "pushup",
            "dip",
            "incline press",
            "decline press",
            "military press",
            "arnold press",
        ),
    ),
    (MovementPattern.CARRY, ("carry", "farmer")),
]


_PATTERN_REGEX = [
    (pattern, re.compile(r"\b(?:" + "|".join(re.escape(k) for k in keys) + r")s?\b"))
    for pattern, keys in _PATTERN_RULES
]


def classify_pattern(title: str) -> str:
    """Whole-word keyword match ("narrow grip bench press" is not a row)."""
    t = title.lower()
    for pattern, rx in _PATTERN_REGEX:
        if rx.search(t):
            return pattern.value
    return MovementPattern.ISOLATION.value


def _norm(title: str) -> str:
    t = title.lower().replace("(db)", "(dumbbell)").replace("(bb)", "(barbell)")
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=1)
def _sfr_index() -> dict[str, int]:
    from resilio.core.config import get_repo_root

    path = get_repo_root() / ".bmad-core" / "data" / "exercise-database.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    index: dict[str, int] = {}
    for key, tier in (
        ("tier_1_high_sfr_low_cns", 1),
        ("tier_2_moderate_sfr_moderate_cns", 2),
        ("tier_3_low_sfr_high_cns_use_sparingly", 3),
    ):
        for name in data.get(key, []):
            index[_norm(name)] = tier
    return index


@lru_cache(maxsize=1)
def load_landmarks() -> dict[str, dict]:
    data = json.loads((_HERE / "volume_landmarks.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def catalog_entry(t: ExerciseTemplate) -> CatalogEntry:
    primary = HEVY_TO_GROUP.get(t.primary_muscle_group or "")
    secondary: list[str] = []
    for m in t.secondary_muscle_groups:
        g = HEVY_TO_GROUP.get(m)
        if g and g != primary and g not in secondary:
            secondary.append(g)
    return CatalogEntry(
        template_id=t.id,
        title=t.title,
        template_type=t.type,
        primary_group=primary,
        secondary_groups=secondary,
        pattern=MovementPattern(classify_pattern(t.title)),
        lower_body=(t.primary_muscle_group or "") in LOWER_BODY_MUSCLES,
        sfr_tier=_sfr_index().get(_norm(t.title)),
        equipment=t.equipment,
    )


def build_catalog(templates: dict[str, ExerciseTemplate]) -> dict[str, CatalogEntry]:
    return {tid: catalog_entry(t) for tid, t in templates.items()}
