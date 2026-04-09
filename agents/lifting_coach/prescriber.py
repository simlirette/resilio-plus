"""
Lifting Coach Prescriber — agents/lifting_coach/prescriber.py
Logique déterministe pure : DUP, MEV/MRV hybride, templates de séances Hevy.
Aucun appel LLM ici.
"""
from __future__ import annotations

import json
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "exercise_database.json"
_LANDMARKS_PATH = Path(__file__).parent.parent.parent / "data" / "volume_landmarks.json"

# Maps exercise DB muscle_primary → volume_landmarks muscles key
_MUSCLE_TO_LANDMARK: dict[str, str] = {
    "back": "back_lats",
    "shoulders": "shoulders_lateral",
}

_LOWER_MUSCLES = {"quadriceps", "hamstrings", "glutes", "calves"}

# DUP configuration: phase → session_type → set prescription
_DUP_CONFIG: dict[str, dict[str, dict]] = {
    "base_building": {
        "upper_a": {
            "focus": "hypertrophy", "n_sets": 3, "rep_min": 10,
            "rep_max": 12, "rpe": 8, "rir": 2, "rest_sec": 120,
        },
        "upper_b": {
            "focus": "strength", "n_sets": 4, "rep_min": 6,
            "rep_max": 8, "rpe": 8, "rir": 2, "rest_sec": 210,
        },
        "lower": {
            "focus": "mixed", "n_sets": 3, "rep_min": 10,
            "rep_max": 12, "rpe": 7, "rir": 2, "rest_sec": 120,
        },
    },
    "build": {
        "upper_a": {
            "focus": "strength", "n_sets": 4, "rep_min": 5,
            "rep_max": 7, "rpe": 8, "rir": 1, "rest_sec": 210,
        },
        "upper_b": {
            "focus": "power", "n_sets": 5, "rep_min": 3,
            "rep_max": 5, "rpe": 8, "rir": 2, "rest_sec": 240,
        },
        "lower": {
            "focus": "hypertrophy", "n_sets": 3, "rep_min": 10,
            "rep_max": 12, "rpe": 8, "rir": 2, "rest_sec": 120,
        },
    },
    "peak": {
        "upper_a": {
            "focus": "maintenance", "n_sets": 2, "rep_min": 8,
            "rep_max": 10, "rpe": 7, "rir": 3, "rest_sec": 90,
        },
        "upper_b": {
            "focus": "maintenance", "n_sets": 2, "rep_min": 8,
            "rep_max": 10, "rpe": 7, "rir": 3, "rest_sec": 90,
        },
        "lower": {
            "focus": "maintenance", "n_sets": 2, "rep_min": 8,
            "rep_max": 10, "rpe": 7, "rir": 3, "rest_sec": 90,
        },
    },
}

_SESSION_TITLES: dict[str, dict[str, str]] = {
    "upper_a": {
        "hypertrophy": "Upper A — Hypertrophie",
        "strength":    "Upper A — Force",
        "maintenance": "Upper A — Maintenance",
    },
    "upper_b": {
        "strength":    "Upper B — Force",
        "power":       "Upper B — Puissance",
        "maintenance": "Upper B — Maintenance",
    },
    "lower": {
        "mixed":       "Lower — Mixte",
        "hypertrophy": "Lower — Hypertrophie",
        "maintenance": "Lower — Maintenance",
    },
}

_DUP_LABELS: dict[str, str] = {
    "base_building": "DUP 3-way (Hypertrophie / Force / Mixte)",
    "build":         "DUP 3-way (Force / Puissance / Hypertrophie)",
    "peak":          "DUP Maintenance",
}

# Session muscle slots: (muscle, preferred_tier, needs_warmup)
_SESSION_SLOTS: dict[str, list[tuple[str, int | None, bool]]] = {
    "upper_a": [
        ("chest",     3,    True),
        ("chest",     1,    False),
        ("back",      3,    True),
        ("back",      1,    False),
        ("shoulders", 1,    False),
        ("shoulders", 1,    False),
        ("biceps",    1,    False),
        ("triceps",   1,    False),
    ],
    "upper_b": [
        ("chest",     3,    True),
        ("chest",     2,    True),
        ("back",      3,    True),
        ("back",      2,    False),
        ("shoulders", 2,    False),
        ("biceps",    2,    False),
        ("triceps",   2,    False),
    ],
    "lower": [
        ("quadriceps",            2,    True),
        ("quadriceps",            1,    False),
        ("hamstrings",            1,    False),
        ("hamstrings",            2,    True),
        ("glutes",                1,    False),
        ("calves",                1,    False),
        ("hip_external_rotators", 1,    False),
    ],
}

_DAY_ORDER_UPPER = ["monday", "tuesday", "thursday", "saturday"]
_DAY_ORDER_LOWER = ["wednesday", "thursday", "saturday", "sunday"]


class LiftingPrescriber:
    """Prescrit un plan de musculation hebdomadaire de façon déterministe."""

    def __init__(
        self,
        exercise_db_path: Path | None = None,
        landmarks_path: Path | None = None,
    ) -> None:
        self._db_path = exercise_db_path or _DB_PATH
        self._landmarks_path = landmarks_path or _LANDMARKS_PATH
        self._db_cache: list[dict] | None = None
        self._landmarks_cache: dict | None = None

    def _load_db(self) -> list[dict]:
        if self._db_cache is None:
            with open(self._db_path, encoding="utf-8") as f:
                self._db_cache = json.load(f)
        return self._db_cache

    def _load_landmarks(self) -> dict:
        if self._landmarks_cache is None:
            with open(self._landmarks_path, encoding="utf-8") as f:
                self._landmarks_cache = json.load(f)
        return self._landmarks_cache

    def build_week_plan(self, view: dict) -> dict:
        """Point d'entrée unique. Retourne plan complet sans coaching_notes."""
        lifting_profile = view["lifting_profile"]
        current_phase = view["current_phase"]
        fatigue = view["fatigue"]
        equipment: list[str] = view.get("equipment", {}).get("gym_equipment", [])
        available_days: dict = view["available_days"]

        phase: str = current_phase["macrocycle"]
        week: int = current_phase["mesocycle_week"]
        sessions_per_week: int = int(lifting_profile.get("sessions_per_week", 3))
        acwr: float = float(fatigue.get("acwr_by_sport_lifting") or 0.0)
        cns_load: float = float(fatigue.get("cns_load_7day_avg") or 0.0)

        is_deload = (week % 4 == 0)
        allow_tier3 = (
            cns_load <= 65
            and phase not in ("peak", "taper")
            and acwr <= 1.3
        )

        session_types = self._get_session_types(sessions_per_week, week)
        day_map = self._assign_days(session_types, available_days)
        dup_cfg_map = _DUP_CONFIG.get(phase, _DUP_CONFIG["peak"])

        weekly_volume: dict[str, int] = {}
        sessions: list[dict] = []

        for stype in session_types:
            day = day_map.get(stype, "monday")
            dup_cfg = dup_cfg_map[stype]
            session = self._build_session(
                session_type=stype,
                phase=phase,
                week=week,
                day=day,
                equipment=equipment,
                allow_tier3=allow_tier3,
                is_deload=is_deload,
                acwr=acwr,
                dup_cfg=dup_cfg,
                weekly_volume=weekly_volume,
            )
            sessions.append({"hevy_workout": session})

        return {
            "agent": "lifting_coach",
            "week": week,
            "phase": phase,
            "dup_model": _DUP_LABELS.get(phase, "DUP Maintenance"),
            "cns_tier3_allowed": allow_tier3,
            "sessions": sessions,
        }

    def _get_session_types(self, sessions_per_week: int, week: int) -> list[str]:
        """Returns ordered list of session types for the week."""
        if week % 4 == 0:
            return ["upper_a", "lower"]
        if sessions_per_week >= 3:
            return ["upper_a", "lower", "upper_b"]
        if sessions_per_week == 2:
            return ["upper_a", "lower"]
        return ["upper_a"]

    def _get_mrv_hybrid(self, muscle: str, phase: str) -> int:
        """Returns MRV hybrid for a muscle adjusted for the current phase."""
        landmarks = self._load_landmarks()
        # Translate exercise DB muscle name to volume_landmarks key
        landmark_key = _MUSCLE_TO_LANDMARK.get(muscle, muscle)
        muscle_data = landmarks["muscles"].get(landmark_key, {})
        base_mrv: int = muscle_data.get("mrv_hybrid", 999)
        if muscle in _LOWER_MUSCLES:
            phase_adj = landmarks["phase_adjustments"].get(phase, {})
            multiplier: float = phase_adj.get("lower_body_mrv_multiplier", 1.0)
            return max(int(base_mrv * multiplier), 2)
        return base_mrv

    def _assign_days(
        self, session_types: list[str], available_days: dict
    ) -> dict[str, str]:
        """Maps session types to days of the week."""
        avail = {d: v for d, v in available_days.items() if v.get("available")}
        day_map: dict[str, str] = {}
        used: set[str] = set()

        if "lower" in session_types:
            for d in _DAY_ORDER_LOWER:
                if d in avail and d not in used and avail[d].get("max_hours", 0) >= 1.0:
                    day_map["lower"] = d
                    used.add(d)
                    break

        if "upper_a" in session_types:
            for d in _DAY_ORDER_UPPER:
                if d in avail and d not in used:
                    day_map["upper_a"] = d
                    used.add(d)
                    break

        if "upper_b" in session_types:
            for d in _DAY_ORDER_UPPER:
                if d in avail and d not in used:
                    day_map["upper_b"] = d
                    used.add(d)
                    break

        return day_map

    def _select_exercise(
        self,
        muscle: str,
        equipment: list[str],
        allow_tier3: bool,
        exclude: set[str],
        prefer_tier: int | None = None,
    ) -> dict | None:
        """Selects best exercise by SFR, respecting tier and equipment constraints."""
        db = self._load_db()

        def passes_equipment(ex: dict) -> bool:
            if not ex["equipment"]:
                return True  # bodyweight — always available
            return any(eq in equipment for eq in ex["equipment"])

        def make_candidates(pt: int | None) -> list[dict]:
            return [
                ex for ex in db
                if ex["muscle_primary"] == muscle
                and passes_equipment(ex)
                and ex["exercise_id"] not in exclude
                and (allow_tier3 or ex["tier"] != 3)
                and (pt is None or ex["tier"] == pt)
            ]

        candidates = make_candidates(prefer_tier)
        if not candidates and prefer_tier is not None:
            candidates = make_candidates(None)
        if not candidates:
            return None
        return max(candidates, key=lambda x: x["sfr_score"])

    def _make_sets(
        self,
        n_sets: int,
        rep_max: int,
        rpe: int,
        rir: int,
        has_warmup: bool,
        acwr_danger: bool,
        is_deload: bool,
        is_hip_ext_rotators: bool = False,
    ) -> list[dict]:
        """Builds set list for one exercise in Hevy format."""
        effective_n = 2 if is_hip_ext_rotators else n_sets
        effective_rpe = rpe
        effective_rir = rir

        if acwr_danger:
            effective_n = 2
            effective_rpe = min(rpe, 7)
            effective_rir = max(rir, 2)
        if is_deload:
            effective_n = max(int(effective_n * 0.6), 1)
            effective_rpe = min(effective_rpe, 7)

        sets: list[dict] = []
        if has_warmup and not is_deload and not acwr_danger:
            sets.append({
                "set_number": 1,
                "type": "warmup",
                "weight_kg": None,
                "reps": rep_max,
                "rpe": None,
                "rir": None,
            })
        for _ in range(effective_n):
            sets.append({
                "set_number": len(sets) + 1,
                "type": "normal",
                "weight_kg": None,
                "reps": rep_max,
                "rpe": effective_rpe,
                "rir": effective_rir,
            })
        return sets

    def _build_session(
        self,
        session_type: str,
        phase: str,
        week: int,
        day: str,
        equipment: list[str],
        allow_tier3: bool,
        is_deload: bool,
        acwr: float,
        dup_cfg: dict,
        weekly_volume: dict[str, int],
    ) -> dict:
        """Builds one Hevy-compatible session dict."""
        acwr_danger = acwr > 1.5
        acwr_caution = 1.3 < acwr <= 1.5

        effective_allow_tier3 = (
            allow_tier3 and not acwr_caution and not acwr_danger and not is_deload
        )

        n_sets: int = dup_cfg["n_sets"]
        if acwr_caution:
            n_sets = max(n_sets - 1, 2)

        rep_max: int = dup_cfg["rep_max"]
        rpe: int = dup_cfg["rpe"]
        rir: int = dup_cfg["rir"]
        rest_sec: int = dup_cfg["rest_sec"]
        focus: str = dup_cfg["focus"]

        if is_deload:
            rpe = min(rpe, 7)
            rest_sec = 60

        title = _SESSION_TITLES.get(session_type, {}).get(focus, f"{session_type} — {focus}")
        if is_deload:
            title += " (Deload)"

        slots = list(_SESSION_SLOTS[session_type])
        if is_deload or acwr_danger:
            slots = [(m, 1, w) for m, _, w in slots]

        exercises: list[dict] = []
        used_ids: set[str] = set()
        est_duration = 0

        for muscle, prefer_tier, needs_warmup in slots:
            mrv = self._get_mrv_hybrid(muscle, phase)
            current_vol = weekly_volume.get(muscle, 0)
            is_hip_ext = muscle == "hip_external_rotators"

            if not is_hip_ext and current_vol >= mrv:
                continue

            ex = self._select_exercise(
                muscle=muscle,
                equipment=equipment,
                allow_tier3=effective_allow_tier3,
                exclude=used_ids,
                prefer_tier=prefer_tier if not (acwr_danger or is_deload) else 1,
            )
            if ex is None:
                continue

            sets_remaining = mrv - current_vol
            effective_n = 2 if is_hip_ext else min(n_sets, sets_remaining)

            sets = self._make_sets(
                n_sets=effective_n,
                rep_max=rep_max,
                rpe=rpe,
                rir=rir,
                has_warmup=needs_warmup and ex["tier"] >= 2,
                acwr_danger=acwr_danger,
                is_deload=is_deload,
                is_hip_ext_rotators=is_hip_ext,
            )

            normal_count = sum(1 for s in sets if s["type"] == "normal")
            weekly_volume[muscle] = current_vol + normal_count

            if ex["tier"] >= 2:
                progression_note = (
                    "Double progression : garder même poids jusqu'à haut"
                    " de la plage RIR 2, puis +2.5kg"
                )
            else:
                progression_note = (
                    "Progression par répétitions : ajouter 1-2 reps/semaine"
                    " jusqu'à limite haute de la plage"
                )

            rest_for_ex = 30 if is_hip_ext else rest_sec
            exercises.append({
                "exercise_id": ex["exercise_id"],
                "name": ex["name"],
                "muscle_primary": ex["muscle_primary"],
                "tier": ex["tier"],
                "sets": sets,
                "rest_seconds": rest_for_ex,
                "progression_note": progression_note,
            })
            used_ids.add(ex["exercise_id"])
            est_duration += len(sets) * max(rest_for_ex // 60, 1) + 1

        return {
            "id": f"lift_w{week}_{day}_{session_type}",
            "title": title,
            "type": session_type,
            "day": day,
            "week": week,
            "phase": phase,
            "estimated_duration_min": max(est_duration, 30),
            "dup_focus": focus,
            "exercises": exercises,
        }
