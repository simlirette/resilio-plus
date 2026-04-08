"""
Running Coach Prescriber — agents/running_coach/prescriber.py
Logique déterministe pure : TID, ACWR, volume, templates de séances.
Aucun appel LLM ici.
"""
from __future__ import annotations

from core.vdot import format_pace, get_vdot_paces  # noqa: F401

_TID_CONFIG: dict[str, dict] = {
    "base_building": {
        "model": "pyramidal",
        "session_types": ["easy_run", "tempo_run", "long_run"],
    },
    "build": {
        "model": "polarized",
        "session_types": ["easy_run", "interval_run", "long_run"],
    },
    "peak": {
        "model": "polarized",
        "session_types": ["easy_run", "interval_run", "long_run"],
    },
}

# Ordre de préférence pour l'assignation de jours
_DAY_ORDER_LONG = ["saturday", "sunday"]
_DAY_ORDER_QUALITY = ["wednesday", "thursday"]
_DAY_ORDER_EASY = ["tuesday", "monday", "thursday", "sunday"]


class RunningPrescriber:
    """Prescrit un plan de course hebdomadaire de façon déterministe."""

    def build_week_plan(self, view: dict) -> dict:
        """
        Point d'entrée unique. Retourne le plan complet sans coaching_notes.

        Args:
            view: Vue filtrée de l'AthleteState (retournée par get_agent_view).

        Returns:
            dict avec: agent, week, phase, tid_model, total_km_prescribed,
            acwr_running, sessions[].
        """
        running_profile = view["running_profile"]
        current_phase = view["current_phase"]
        fatigue = view["fatigue"]
        constraints = view["constraints"]
        available_days = view["available_days"]

        vdot: float = running_profile["vdot"]
        current_km: float = float(running_profile["weekly_km_current"])
        week: int = current_phase["mesocycle_week"]
        phase: str = current_phase["macrocycle"]
        acwr: float = float(fatigue.get("acwr_by_sport_running") or 0.0)
        injuries: list = constraints.get("injuries_history", [])
        has_shin_splints = any(i.get("type") == "shin_splints" for i in injuries)

        paces = get_vdot_paces(vdot)
        target_km = self._compute_target_km(current_km, week, has_shin_splints)
        session_types = self._select_session_types(phase, acwr, week)
        tid_config = _TID_CONFIG.get(phase, _TID_CONFIG["base_building"])
        sessions = self._build_sessions(
            session_types, paces, target_km, week, phase, available_days
        )
        total_km = sum(s["run_workout"]["estimated_distance_km"] for s in sessions)

        return {
            "agent": "running_coach",
            "week": week,
            "phase": phase,
            "tid_model": tid_config["model"],
            "total_km_prescribed": round(total_km, 1),
            "acwr_running": acwr if acwr > 0.0 else None,
            "sessions": sessions,
        }

    def _compute_target_km(
        self, current_km: float, week: int, has_shin_splints: bool
    ) -> float:
        """Calcule le volume cible en appliquant la règle du 10% et le deload."""
        if week % 4 == 0:
            return round(current_km * 0.75, 1)
        max_increase = 1.07 if has_shin_splints else 1.10
        return round(min(current_km * 1.05, current_km * max_increase), 1)

    def _select_session_types(
        self, phase: str, acwr: float, week: int
    ) -> list[str]:
        """Retourne la liste ordonnée de types de séances selon phase, ACWR, semaine."""
        if week % 4 == 0:
            return ["easy_run", "long_run"]

        config = _TID_CONFIG.get(phase, _TID_CONFIG["base_building"])
        session_types = list(config["session_types"])

        if acwr > 1.5:
            # Danger : tout en easy, garder le long run
            return [
                "easy_run" if t not in ("long_run",) else t for t in session_types
            ]

        if acwr > 1.3:
            # Caution : rétrograder l'intensité d'un cran
            session_types = [
                "tempo_run"
                if t == "interval_run"
                else "easy_run"
                if t == "tempo_run"
                else t
                for t in session_types
            ]

        return session_types

    def _build_sessions(
        self,
        session_types: list[str],
        paces: dict,
        target_km: float,
        week: int,
        phase: str,
        available_days: dict,
    ) -> list[dict]:
        """Construit les sessions au format Runna-compatible avec assignation de jours."""
        avail = {d: v for d, v in available_days.items() if v.get("available")}

        # Assignation des jours par type de séance
        day_map: dict[str, str] = {}
        used_days: set[str] = set()

        # Long run → week-end
        if "long_run" in session_types:
            for d in _DAY_ORDER_LONG:
                if d in avail and d not in used_days and avail[d].get("max_hours", 0) >= 1.5:
                    day_map["long_run"] = d
                    used_days.add(d)
                    break

        # Qualité (tempo / interval) → semaine
        for qt in ("tempo_run", "interval_run"):
            if qt in session_types:
                for d in _DAY_ORDER_QUALITY:
                    if d in avail and d not in used_days and avail[d].get("max_hours", 0) >= 1.0:
                        day_map[qt] = d
                        used_days.add(d)
                        break

        # Easy runs → jours restants
        easy_types = [t for t in session_types if t == "easy_run"]
        for idx in range(len(easy_types)):
            for d in _DAY_ORDER_EASY:
                if d in avail and d not in used_days:
                    day_map[f"easy_run_{idx}"] = d
                    used_days.add(d)
                    break

        # Distribution du volume
        has_long = "long_run" in session_types
        has_quality = any(t in session_types for t in ("tempo_run", "interval_run"))
        n_easy = sum(1 for t in session_types if t == "easy_run")

        long_km = round(target_km * 0.30, 1) if has_long else 0.0
        quality_km = round(target_km * 0.25, 1) if has_quality else 0.0
        easy_km_per = round(
            (target_km - long_km - quality_km) / max(n_easy, 1), 1
        )

        # Construction des sessions
        sessions: list[dict] = []
        easy_idx = 0
        for session_type in session_types:
            if session_type == "long_run":
                day = day_map.get("long_run", "saturday")
                sessions.append(self._make_long_run(paces, long_km, day, week, phase))
            elif session_type == "tempo_run":
                day = day_map.get("tempo_run", "wednesday")
                sessions.append(self._make_tempo_run(paces, quality_km, day, week, phase))
            elif session_type == "interval_run":
                day = day_map.get("interval_run", "wednesday")
                sessions.append(self._make_interval_run(paces, day, week, phase))
            elif session_type == "easy_run":
                day = day_map.get(f"easy_run_{easy_idx}", "tuesday")
                sessions.append(self._make_easy_run(paces, easy_km_per, day, week, phase))
                easy_idx += 1

        return sessions

    def _make_easy_run(
        self, paces: dict, km: float, day: str, week: int, phase: str
    ) -> dict:
        easy_fast = paces["easy_fast_sec_km"]
        recovery_pace = paces["easy_slow_sec_km"] + 20
        warmup_km = 0.5
        cooldown_km = 0.5
        run_km = max(round(km - warmup_km - cooldown_km, 1), 1.0)
        total_km = round(warmup_km + run_km + cooldown_km, 1)
        duration_min = int(total_km * easy_fast / 60)
        return {
            "run_workout": {
                "id": f"run_w{week}_{day}_easy",
                "name": "Easy Run",
                "type": "easy_run",
                "day": day,
                "week": week,
                "phase": phase,
                "estimated_duration_min": duration_min,
                "estimated_distance_km": total_km,
                "estimated_tss": round(total_km * 1.0, 1),
                "blocks": [
                    {
                        "type": "warmup",
                        "distance_km": warmup_km,
                        "pace_target": format_pace(recovery_pace),
                        "notes": "Jog très lent",
                    },
                    {
                        "type": "run",
                        "distance_km": run_km,
                        "pace_target": format_pace(easy_fast),
                        "pace_zone": "E-pace",
                    },
                    {
                        "type": "cooldown",
                        "distance_km": cooldown_km,
                        "pace_target": format_pace(recovery_pace),
                    },
                ],
                "sync_target": "garmin_structured_workout",
            }
        }

    def _make_tempo_run(
        self, paces: dict, total_km: float, day: str, week: int, phase: str
    ) -> dict:
        easy_slow = paces["easy_slow_sec_km"]
        threshold = paces["threshold_sec_km"]
        warmup_km = 2.0
        cooldown_km = 1.5
        threshold_km = max(round(total_km - warmup_km - cooldown_km, 1), 2.0)
        actual_total = round(warmup_km + threshold_km + cooldown_km, 1)
        duration_min = int(
            (warmup_km * easy_slow + threshold_km * threshold + cooldown_km * easy_slow) / 60
        )
        tss = round(threshold_km * 1.6 + (warmup_km + cooldown_km) * 1.0, 1)
        return {
            "run_workout": {
                "id": f"run_w{week}_{day}_tempo",
                "name": "Tempo Run",
                "type": "tempo_run",
                "day": day,
                "week": week,
                "phase": phase,
                "estimated_duration_min": duration_min,
                "estimated_distance_km": actual_total,
                "estimated_tss": tss,
                "blocks": [
                    {
                        "type": "warmup",
                        "distance_km": warmup_km,
                        "pace_target": format_pace(easy_slow),
                    },
                    {
                        "type": "tempo",
                        "distance_km": threshold_km,
                        "pace_target": format_pace(threshold),
                        "pace_zone": "T-pace",
                        "notes": "Confortablement difficile — quelques mots possibles",
                    },
                    {
                        "type": "cooldown",
                        "distance_km": cooldown_km,
                        "pace_target": format_pace(easy_slow),
                    },
                ],
                "sync_target": "garmin_structured_workout",
            }
        }

    def _make_interval_run(
        self, paces: dict, day: str, week: int, phase: str
    ) -> dict:
        easy_slow = paces["easy_slow_sec_km"]
        interval_pace = paces["interval_sec_km"]
        warmup_km = 2.0
        cooldown_km = 1.5
        n_reps = 5
        rep_km = 0.8
        interval_km = n_reps * rep_km
        total_km = round(warmup_km + interval_km + cooldown_km, 1)
        duration_min = int(
            (
                warmup_km * easy_slow
                + interval_km * interval_pace
                + n_reps * 180
                + cooldown_km * easy_slow
            )
            / 60
        )
        tss = round(n_reps * rep_km * 2.0 + (warmup_km + cooldown_km) * 1.0, 1)
        return {
            "run_workout": {
                "id": f"run_w{week}_{day}_interval",
                "name": "Interval Run",
                "type": "interval_run",
                "day": day,
                "week": week,
                "phase": phase,
                "estimated_duration_min": duration_min,
                "estimated_distance_km": total_km,
                "estimated_tss": tss,
                "blocks": [
                    {
                        "type": "warmup",
                        "distance_km": warmup_km,
                        "pace_target": format_pace(easy_slow),
                    },
                    {
                        "type": "strides",
                        "repetitions": 4,
                        "distance_m": 100,
                        "pace_target": format_pace(interval_pace),
                        "recovery_duration_sec": 60,
                        "recovery_type": "walk",
                    },
                    {
                        "type": "interval",
                        "repetitions": n_reps,
                        "distance_m": 800,
                        "pace_target": format_pace(interval_pace),
                        "pace_zone": "I-pace",
                        "recovery_duration_sec": 180,
                        "recovery_type": "jog",
                        "recovery_pace": format_pace(easy_slow),
                        "notes": "Arrêt si rep 4 > 5s plus lent que rep 1",
                    },
                    {
                        "type": "cooldown",
                        "distance_km": cooldown_km,
                        "pace_target": format_pace(easy_slow),
                    },
                ],
                "sync_target": "garmin_structured_workout",
            }
        }

    def _make_long_run(
        self, paces: dict, km: float, day: str, week: int, phase: str
    ) -> dict:
        easy_slow = paces["easy_slow_sec_km"]
        duration_min = int(km * easy_slow / 60)
        tss = round(km * 0.8, 1)
        return {
            "run_workout": {
                "id": f"run_w{week}_{day}_long",
                "name": "Long Run",
                "type": "long_run",
                "day": day,
                "week": week,
                "phase": phase,
                "estimated_duration_min": duration_min,
                "estimated_distance_km": km,
                "estimated_tss": tss,
                "blocks": [
                    {
                        "type": "long_run",
                        "distance_km": km,
                        "pace_target": format_pace(easy_slow),
                        "pace_zone": "E-pace (slow end)",
                        "notes": "Rythme conversationnel strict",
                    }
                ],
                "sync_target": "garmin_structured_workout",
            }
        }
