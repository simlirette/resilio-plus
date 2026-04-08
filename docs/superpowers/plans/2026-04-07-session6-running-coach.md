# Session 6 — Running Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the S5 stub RunningCoachAgent with a full VDOT-based prescriber and Anthropic LLM coaching_notes, exposed via `POST /api/v1/plan/running`.

**Architecture:** Three layers — `core/vdot.py` (VDOT table lookup + linear interpolation), `agents/running_coach/prescriber.py` (deterministic session builder: TID, ACWR adjustment, volume constraint), `agents/running_coach/agent.py` (orchestrates prescriber + Anthropic LLM for coaching_notes). API route at `api/v1/plan.py` mounted in `api/main.py`.

**Tech Stack:** Python 3.11, FastAPI 0.115, Pydantic v2, anthropic SDK 0.40.0, pytest + httpx (FastAPI TestClient).

**Spec:** `docs/superpowers/specs/2026-04-06-session6-running-coach-design.md`

**Baseline before starting:** Run `poetry run pytest tests/ -v` and confirm 71 tests pass.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `core/vdot.py` | VDOT lookup + linear interpolation + pace formatters |
| Create | `agents/running_coach/prescriber.py` | Deterministic session planning (TID, ACWR, volume) |
| Modify | `agents/running_coach/agent.py` | Replace S5 stub — orchestrate prescriber + Anthropic LLM |
| Create | `api/v1/plan.py` | `POST /plan/running` FastAPI route |
| Modify | `api/main.py` | Mount plan_router at `/api/v1/plan` |
| Create | `tests/test_vdot.py` | 5 tests for VDOT lookup + formatting |
| Create | `tests/test_running_prescriber.py` | 5 tests for prescriber logic |
| Create | `tests/test_running_agent.py` | 3 tests for agent with mocked Anthropic |
| Create | `tests/test_plan_route.py` | 3 tests for API route with mocked agent |
| Modify | `CLAUDE.md` | Mark S6 ✅ FAIT, update structure |

---

## Context for Implementers

**vdot_paces.json structure** (`data/vdot_paces.json`):
```json
{
  "table": {
    "38": {
      "easy_fast_sec_km": 378, "easy_slow_sec_km": 417, "marathon_sec_km": 342,
      "threshold_sec_km": 318, "interval_sec_km": 288, "repetition_sec_400m": 114
    },
    "39": {
      "easy_fast_sec_km": 372, "easy_slow_sec_km": 411, "marathon_sec_km": 338,
      "threshold_sec_km": 314, "interval_sec_km": 284, "repetition_sec_400m": 112
    }
  }
}
```
Keys are strings "20" through "85". Each entry has 6 numeric pace fields (all other fields like `easy_formatted` are ignored by our code).

**Running view fields** (from `get_agent_view(state, AgentType.running_coach)`):
```python
{
    "running_profile": {
        "vdot": 38.2,
        "weekly_km_current": 22.0,
        "max_long_run_km": 12.0,
        ...
    },
    "fatigue": {
        "acwr_by_sport_running": None,   # float | None
        ...
    },
    "current_phase": {
        "macrocycle": "base_building",   # "base_building" | "build" | "peak"
        "mesocycle_week": 3,
        ...
    },
    "constraints": {
        "injuries_history": [{"type": "shin_splints", ...}]
    },
    "available_days": {
        "monday":    {"available": True,  "max_hours": 1.5},
        "tuesday":   {"available": True,  "max_hours": 1.5},
        "wednesday": {"available": True,  "max_hours": 1.0},
        "thursday":  {"available": True,  "max_hours": 1.5},
        "friday":    {"available": False, "max_hours": 0},
        "saturday":  {"available": True,  "max_hours": 2.5},
        "sunday":    {"available": True,  "max_hours": 2.0},
    }
}
```

**Settings** (`core/config.py`):
- `settings.ANTHROPIC_API_KEY` → `str` (defaults to `""`)
- `settings.ANTHROPIC_MODEL` → `str` (defaults to `"claude-sonnet-4-6"`)

**Existing imports needed in tests** — `simon_pydantic_state` fixture is in `tests/conftest.py`.

---

## Task 1: core/vdot.py — VDOT Lookup and Pace Formatting

**Files:**
- Create: `core/vdot.py`
- Create: `tests/test_vdot.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_vdot.py` with this exact content:

```python
"""Tests pour core/vdot.py — lookup VDOT + formatters de pace."""


def test_vdot_exact_lookup():
    """VDOT 38 (entier) → threshold_sec_km = 318 (valeur confirmée table)."""
    from core.vdot import get_vdot_paces

    paces = get_vdot_paces(38.0)
    assert paces["threshold_sec_km"] == 318.0


def test_vdot_interpolation():
    """VDOT 38.5 → threshold interpolé entre 38 (318) et 39 (314)."""
    from core.vdot import get_vdot_paces

    paces = get_vdot_paces(38.5)
    assert paces["threshold_sec_km"] == 316.0  # 318 + 0.5*(314-318)


def test_vdot_clamp_low():
    """VDOT 10 → clampé à VDOT 20 (threshold_sec_km = 498)."""
    from core.vdot import get_vdot_paces

    paces = get_vdot_paces(10.0)
    assert paces["threshold_sec_km"] == 498.0


def test_vdot_clamp_high():
    """VDOT 100 → clampé à VDOT 85 (threshold_sec_km = 164)."""
    from core.vdot import get_vdot_paces

    paces = get_vdot_paces(100.0)
    assert paces["threshold_sec_km"] == 164.0


def test_format_pace():
    """318 sec/km → '5:18/km'."""
    from core.vdot import format_pace

    assert format_pace(318) == "5:18/km"


def test_format_pace_400m():
    """114 sec/400m → '1:54/400m'."""
    from core.vdot import format_pace_400m

    assert format_pace_400m(114) == "1:54/400m"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/test_vdot.py -v
```

Expected: 6 failures with `ModuleNotFoundError: No module named 'core.vdot'`

- [ ] **Step 3: Implement core/vdot.py**

Create `core/vdot.py` with this exact content:

```python
"""
VDOT Training Paces — core/vdot.py
Lookup linéaire dans data/vdot_paces.json avec interpolation fractionnaire.
"""
from __future__ import annotations

import json
from pathlib import Path

_TABLE: dict[str, dict] = {}
_PACE_KEYS = [
    "easy_fast_sec_km",
    "easy_slow_sec_km",
    "marathon_sec_km",
    "threshold_sec_km",
    "interval_sec_km",
    "repetition_sec_400m",
]


def _load_table() -> dict[str, dict]:
    global _TABLE
    if not _TABLE:
        path = Path(__file__).parent.parent / "data" / "vdot_paces.json"
        _TABLE = json.loads(path.read_text())["table"]
    return _TABLE


def get_vdot_paces(vdot: float) -> dict:
    """
    Retourne les 6 allures pour un VDOT donné (interpolation linéaire entre entiers).

    Args:
        vdot: VDOT de l'athlète (ex: 38.2). Clampé dans [20.0, 85.0].

    Returns:
        dict avec clés: easy_fast_sec_km, easy_slow_sec_km, marathon_sec_km,
        threshold_sec_km, interval_sec_km, repetition_sec_400m.
        Toutes les valeurs en secondes (float).
    """
    table = _load_table()
    vdot = max(20.0, min(85.0, float(vdot)))
    low = int(vdot)
    frac = vdot - low

    low_paces = table[str(low)]
    high_paces = table.get(str(low + 1), low_paces)

    return {k: low_paces[k] + frac * (high_paces[k] - low_paces[k]) for k in _PACE_KEYS}


def format_pace(sec_per_km: float) -> str:
    """Convertit secondes/km en 'M:SS/km'."""
    total = int(round(sec_per_km))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}/km"


def format_pace_400m(sec_per_400m: float) -> str:
    """Convertit secondes/400m en 'M:SS/400m'."""
    total = int(round(sec_per_400m))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}/400m"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/test_vdot.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add core/vdot.py tests/test_vdot.py
git commit -m "feat: add core/vdot.py — VDOT lookup + linear interpolation + pace formatters"
```

---

## Task 2: agents/running_coach/prescriber.py — RunningPrescriber

**Files:**
- Create: `agents/running_coach/prescriber.py`
- Create: `tests/test_running_prescriber.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_running_prescriber.py` with this exact content:

```python
"""Tests pour agents/running_coach/prescriber.py — logique déterministe."""


def test_select_sessions_base_building():
    """Phase base_building, ACWR safe → sessions pyramidales standard."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._select_session_types("base_building", 1.0, 3)
    assert result == ["easy_run", "tempo_run", "long_run"]


def test_acwr_danger_drops_to_easy():
    """ACWR > 1.5 (danger) → uniquement easy_run et long_run (pas de qualité)."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._select_session_types("base_building", 1.6, 3)
    assert "tempo_run" not in result
    assert "interval_run" not in result
    assert "easy_run" in result


def test_acwr_caution_downgrades_intensity():
    """ACWR 1.4 (caution) en phase build → interval_run rétrogradé en tempo_run."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._select_session_types("build", 1.4, 3)
    assert "interval_run" not in result
    assert "tempo_run" in result


def test_volume_cap_10_percent():
    """Semaine normale sans shin_splints → progression 5%, dans la limite 10%."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._compute_target_km(22.0, 3, False)
    assert result == 23.1  # 22.0 * 1.05
    assert result <= 22.0 * 1.10  # Dans la limite 10%


def test_deload_week():
    """Semaine 4 (deload) → volume × 0.75."""
    from agents.running_coach.prescriber import RunningPrescriber

    p = RunningPrescriber()
    result = p._compute_target_km(22.0, 4, False)
    assert result == 16.5  # 22.0 * 0.75


def test_build_week_plan_returns_required_fields(simon_pydantic_state):
    """build_week_plan() retourne tous les champs requis du format de sortie."""
    from agents.running_coach.prescriber import RunningPrescriber
    from models.views import AgentType, get_agent_view

    p = RunningPrescriber()
    view = get_agent_view(simon_pydantic_state, AgentType.running_coach)
    plan = p.build_week_plan(view)

    assert plan["agent"] == "running_coach"
    assert "week" in plan
    assert "phase" in plan
    assert "tid_model" in plan
    assert "total_km_prescribed" in plan
    assert "sessions" in plan
    assert isinstance(plan["sessions"], list)
    assert len(plan["sessions"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/test_running_prescriber.py -v
```

Expected: 6 failures with `ModuleNotFoundError: No module named 'agents.running_coach.prescriber'`

- [ ] **Step 3: Implement agents/running_coach/prescriber.py**

Create `agents/running_coach/prescriber.py` with this exact content:

```python
"""
Running Coach Prescriber — agents/running_coach/prescriber.py
Logique déterministe pure : TID, ACWR, volume, templates de séances.
Aucun appel LLM ici.
"""
from __future__ import annotations

from core.vdot import format_pace, format_pace_400m, get_vdot_paces

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
            (warmup_km * easy_slow + interval_km * interval_pace + n_reps * 180 + cooldown_km * easy_slow) / 60
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/test_running_prescriber.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Verify existing tests still pass**

```bash
poetry run pytest tests/ -v --ignore=tests/test_running_agent.py --ignore=tests/test_plan_route.py
```

Expected: 77 passed (71 original + 6 new).

- [ ] **Step 6: Commit**

```bash
git add agents/running_coach/prescriber.py tests/test_running_prescriber.py
git commit -m "feat: add RunningPrescriber — TID, ACWR adjustment, volume constraint, session templates"
```

---

## Task 3: agents/running_coach/agent.py — Replace Stub with LLM Agent

**Files:**
- Modify: `agents/running_coach/agent.py` (full replacement)
- Create: `tests/test_running_agent.py`

**Important:** The Anthropic client is always mocked in tests — no real API calls. `settings.ANTHROPIC_API_KEY` defaults to `""`, which is fine since the client is patched before `RunningCoachAgent()` is instantiated.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_running_agent.py` with this exact content:

```python
"""
Tests pour agents/running_coach/agent.py — orchestration prescriber + LLM.
Anthropic est toujours mocké — aucun appel API réel.
"""
from unittest.mock import MagicMock, patch


def _make_mock_message(text: str) -> MagicMock:
    """Crée un faux message Anthropic avec le texte donné."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=text)]
    return mock_message


def test_prescribe_mocked_llm(simon_pydantic_state):
    """Agent avec LLM mocké → retourne dict avec 'sessions' et 'coaching_notes'."""
    from agents.running_coach.agent import RunningCoachAgent

    mock_msg = _make_mock_message(
        "- Maintenir la cadence à 170 pas/min.\n- Hydratation avant la séance tempo."
    )

    with patch("agents.running_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        agent = RunningCoachAgent()
        plan = agent.run(simon_pydantic_state)

    assert isinstance(plan, dict)
    assert "sessions" in plan
    assert len(plan["sessions"]) > 0
    assert "coaching_notes" in plan
    assert isinstance(plan["coaching_notes"], list)


def test_output_schema_valid(simon_pydantic_state):
    """Chaque session du plan a run_workout.id, .blocks, et .sync_target."""
    from agents.running_coach.agent import RunningCoachAgent

    mock_msg = _make_mock_message("- Note 1.\n- Note 2.")

    with patch("agents.running_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        agent = RunningCoachAgent()
        plan = agent.run(simon_pydantic_state)

    for session in plan["sessions"]:
        rw = session["run_workout"]
        assert "id" in rw, f"Session manque 'id': {rw}"
        assert "blocks" in rw, f"Session manque 'blocks': {rw}"
        assert "sync_target" in rw, f"Session manque 'sync_target': {rw}"
        assert rw["sync_target"] == "garmin_structured_workout"


def test_coaching_notes_merged(simon_pydantic_state):
    """Les coaching_notes du LLM sont parsées et incluses dans le plan."""
    from agents.running_coach.agent import RunningCoachAgent

    mock_msg = _make_mock_message(
        "- Maintenir la cadence.\n- Hydratation requise.\n- Éviter les collines en deload."
    )

    with patch("agents.running_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        agent = RunningCoachAgent()
        plan = agent.run(simon_pydantic_state)

    notes = plan["coaching_notes"]
    assert isinstance(notes, list)
    assert len(notes) >= 1
    # Les tirets de Markdown ont été retirés du parsing
    assert all(not note.startswith("-") for note in notes)


def test_llm_error_returns_empty_notes(simon_pydantic_state):
    """Si le LLM lève une exception, coaching_notes = [] (plan toujours retourné)."""
    from agents.running_coach.agent import RunningCoachAgent

    with patch("agents.running_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API overloaded")
        mock_cls.return_value = mock_client

        agent = RunningCoachAgent()
        plan = agent.run(simon_pydantic_state)

    assert "sessions" in plan
    assert plan["coaching_notes"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/test_running_agent.py -v
```

Expected: 4 failures — `RunningCoachAgent` exists but doesn't have `RunningPrescriber` or Anthropic yet.

- [ ] **Step 3: Replace agents/running_coach/agent.py**

Replace the entire content of `agents/running_coach/agent.py` with:

```python
"""
Running Coach Agent — agents/running_coach/agent.py
Orchestre RunningPrescriber (déterministe) + Anthropic LLM (coaching_notes).
S6 : remplace le stub S5.
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.running_coach.prescriber import RunningPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "running_coach_system_prompt.md").read_text()


class RunningCoachAgent(BaseAgent):
    """Running Coach — prescription VDOT + notes qualitatives via LLM."""

    agent_type = AgentType.running_coach

    def __init__(self) -> None:
        self._prescriber = RunningPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        plan = self._prescriber.build_week_plan(view)
        plan["coaching_notes"] = self._get_coaching_notes(view, plan)
        return plan

    def _get_coaching_notes(self, view: dict, plan: dict) -> list[str]:
        """Appel LLM Anthropic pour les coaching notes qualitatives. Fallback = []."""
        user_content = (
            f"Génère 3-5 coaching_notes techniques CONCISES pour ce plan de course :\n"
            f"{json.dumps(plan, ensure_ascii=False, indent=2)}\n\n"
            f"Contexte athlète :\n{json.dumps(view, ensure_ascii=False, indent=2)}"
        )
        try:
            message = self._client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=512,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            text = message.content[0].text
            lines = [line.strip().lstrip("-•*").strip() for line in text.split("\n") if line.strip()]
            return [line for line in lines if line][:5]
        except Exception:
            return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/test_running_agent.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Verify existing test_base_agent.py still passes**

```bash
poetry run pytest tests/test_base_agent.py -v
```

Expected: 3 passed. Note: `test_running_coach_run_returns_plan` will now fail if RunningCoachAgent tries to instantiate the Anthropic client — if it does, patch anthropic in that test is needed. Check the output. If the test fails because `RunningCoachAgent()` raises an error (e.g., API key validation), you need to mock `anthropic.Anthropic` in `test_base_agent.py` as well.

If `test_running_coach_run_returns_plan` fails, update `tests/test_base_agent.py` to mock the Anthropic client:

```python
def test_running_coach_run_returns_plan(simon_pydantic_state):
    """RunningCoachAgent.run() retourne un dict avec 'sessions'."""
    from unittest.mock import MagicMock, patch
    from agents.running_coach.agent import RunningCoachAgent

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="- Note test.")]

    with patch("agents.running_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        agent = RunningCoachAgent()
        plan = agent.run(simon_pydantic_state)

    assert isinstance(plan, dict)
    assert "sessions" in plan
    assert len(plan["sessions"]) > 0
    assert plan["agent"] == "running_coach"
```

- [ ] **Step 6: Run full test suite to verify no regressions**

```bash
poetry run pytest tests/ -v --ignore=tests/test_plan_route.py
```

Expected: 81 passed (71 + 6 prescriber + 4 agent) or 80 if test_base_agent needed updating.

- [ ] **Step 7: Commit**

```bash
git add agents/running_coach/agent.py tests/test_running_agent.py tests/test_base_agent.py
git commit -m "feat: replace S5 stub — RunningCoachAgent now uses RunningPrescriber + Anthropic LLM"
```

---

## Task 4: api/v1/plan.py + api/main.py — POST /plan/running Route

**Files:**
- Create: `api/v1/plan.py`
- Modify: `api/main.py`
- Create: `tests/test_plan_route.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plan_route.py` with this exact content:

```python
"""
Tests pour POST /api/v1/plan/running.
RunningCoachAgent toujours mocké — aucun appel prescriber ni LLM réel.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


_MOCK_PLAN = {
    "agent": "running_coach",
    "week": 3,
    "phase": "base_building",
    "tid_model": "pyramidal",
    "total_km_prescribed": 23.1,
    "acwr_running": None,
    "coaching_notes": ["Note de test."],
    "sessions": [],
}


def test_post_running_plan_returns_200(simon_pydantic_state):
    """POST /api/v1/plan/running avec payload valide → 200 + plan JSON."""
    from api.main import app

    client = TestClient(app)

    with patch("api.v1.plan.RunningCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = _MOCK_PLAN
        mock_cls.return_value = mock_agent

        response = client.post(
            "/api/v1/plan/running",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "running_coach"
    assert "sessions" in data


def test_post_running_plan_invalid_body():
    """POST avec athlete_state invalide → 422 Unprocessable Entity."""
    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/plan/running",
        json={"athlete_state": {"invalid_field": "bad_data"}},
    )

    assert response.status_code == 422


def test_post_running_plan_agent_receives_state(simon_pydantic_state):
    """Le body transmis à RunningCoachAgent.run() est bien un AthleteState valide."""
    from api.main import app
    from models.athlete_state import AthleteState

    client = TestClient(app)
    received_states: list = []

    def capture_run(state):
        received_states.append(state)
        return _MOCK_PLAN

    with patch("api.v1.plan.RunningCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.side_effect = capture_run
        mock_cls.return_value = mock_agent

        client.post(
            "/api/v1/plan/running",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert len(received_states) == 1
    assert isinstance(received_states[0], AthleteState)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/test_plan_route.py -v
```

Expected: 3 failures with `ImportError` or `404` (route doesn't exist yet).

- [ ] **Step 3: Create api/v1/plan.py**

Create `api/v1/plan.py` with this exact content:

```python
"""
Plan routes — api/v1/plan.py
POST /plan/running : génère un plan de course hebdomadaire Runna/Garmin-compatible.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.running_coach.agent import RunningCoachAgent
from models.athlete_state import AthleteState

router = APIRouter()


class RunningPlanRequest(BaseModel):
    athlete_state: dict


@router.post("/running")
def generate_running_plan(body: RunningPlanRequest) -> dict:
    """
    Génère un plan de course hebdomadaire Runna/Garmin-compatible.

    Body: {"athlete_state": <AthleteState as dict>}
    Returns: plan dict avec sessions[], coaching_notes[], métadonnées phase/TID.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    agent = RunningCoachAgent()
    return agent.run(state)
```

- [ ] **Step 4: Modify api/main.py to mount plan_router**

The current content of `api/main.py` is:

```python
"""
FastAPI application stub — Resilio+
S11 complétera : auth JWT, middleware CORS, autres routers.
"""

from fastapi import FastAPI

from api.v1.apple_health import router as apple_health_router
from api.v1.connectors import router as connectors_router
from api.v1.files import router as files_router
from api.v1.food import router as food_router

app = FastAPI(title="Resilio+", version="0.1.0")

app.include_router(
    connectors_router,
    prefix="/api/v1/connectors",
    tags=["connectors"],
)
app.include_router(
    apple_health_router,
    prefix="/api/v1/connectors",
    tags=["apple-health"],
)
app.include_router(
    files_router,
    prefix="/api/v1/connectors",
    tags=["files"],
)
app.include_router(
    food_router,
    prefix="/api/v1/connectors",
    tags=["food"],
)
```

Replace it with (add plan_router import and mount):

```python
"""
FastAPI application stub — Resilio+
S11 complétera : auth JWT, middleware CORS, autres routers.
"""

from fastapi import FastAPI

from api.v1.apple_health import router as apple_health_router
from api.v1.connectors import router as connectors_router
from api.v1.files import router as files_router
from api.v1.food import router as food_router
from api.v1.plan import router as plan_router

app = FastAPI(title="Resilio+", version="0.1.0")

app.include_router(
    connectors_router,
    prefix="/api/v1/connectors",
    tags=["connectors"],
)
app.include_router(
    apple_health_router,
    prefix="/api/v1/connectors",
    tags=["apple-health"],
)
app.include_router(
    files_router,
    prefix="/api/v1/connectors",
    tags=["files"],
)
app.include_router(
    food_router,
    prefix="/api/v1/connectors",
    tags=["food"],
)
app.include_router(
    plan_router,
    prefix="/api/v1/plan",
    tags=["plan"],
)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
poetry run pytest tests/test_plan_route.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Run full test suite**

```bash
poetry run pytest tests/ -v
```

Expected: 87 passed (71 original + 6 vdot + 6 prescriber + 4 agent + 3 plan + any test_base_agent changes). If count differs, check which tests were added vs modified.

Also verify ruff passes:

```bash
poetry run ruff check .
```

Expected: no output (no errors).

- [ ] **Step 7: Commit**

```bash
git add api/v1/plan.py api/main.py tests/test_plan_route.py
git commit -m "feat: add POST /api/v1/plan/running — Runna/Garmin-compatible weekly plan endpoint"
```

---

## Task 5: CLAUDE.md Update and Push

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md**

In `CLAUDE.md`, make the following changes:

**In the session table**, change S6 from `⬜ À FAIRE` to `✅ FAIT`:
```
| **S6** | Running Coach | VDOT + zones + output format Runna/Garmin | ✅ FAIT |
```

**In the STRUCTURE DU REPO section**, add the new files under `agents/running_coach/`:
```
│   ├── running_coach/
│   │   ├── __init__.py                ← ✅ S5
│   │   ├── agent.py                   ← ✅ S6 — RunningCoachAgent (prescriber + LLM)
│   │   ├── prescriber.py              ← ✅ S6 — RunningPrescriber (déterministe)
│   │   └── running_coach_system_prompt.md ← ✅ Existant
```

**Add `core/vdot.py`** under the `core/` section:
```
├── core/
│   ├── config.py                      ← ✅ S1 — Pydantic v2 SettingsConfigDict + validator
│   ├── acwr.py                        ← ✅ S5 — compute_ewma_acwr + acwr_zone
│   └── vdot.py                        ← ✅ S6 — get_vdot_paces() + format_pace()
```

**Add new API and test files** in their sections:
```
│   └── v1/
│       ├── connectors.py             ← ✅ S3
│       ├── apple_health.py           ← ✅ S4
│       ├── files.py                  ← ✅ S4
│       ├── food.py                   ← ✅ S4
│       └── plan.py                   ← ✅ S6 — POST /plan/running
```

```
├── tests/
│   ├── conftest.py                    ← ✅ S5
│   ├── test_config.py                 ← ✅ S1
│   ├── test_exercise_database.py      ← ✅ S1
│   ├── test_acwr.py                   ← ✅ S5
│   ├── test_athlete_state.py          ← ✅ S5
│   ├── test_base_agent.py             ← ✅ S5/S6
│   ├── test_head_coach_graph.py       ← ✅ S5
│   ├── test_vdot.py                   ← ✅ S6 — 6 tests VDOT lookup + formatters
│   ├── test_running_prescriber.py     ← ✅ S6 — 6 tests prescriber logic
│   ├── test_running_agent.py          ← ✅ S6 — 4 tests agent + mocked LLM
│   └── test_plan_route.py             ← ✅ S6 — 3 tests API route
```

Also update the test count comment if any: **87 tests total** (or the actual count from Step 6 of Task 4).

- [ ] **Step 2: Commit CLAUDE.md**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md — mark S6 ✅ FAIT, add new files to structure"
```

- [ ] **Step 3: Push to origin/master**

```bash
git push origin master
```

Expected: push succeeds, all 87 tests pass on the pushed branch.

- [ ] **Step 4: Final verification**

```bash
poetry run pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected output ends with something like:
```
========================= 87 passed in X.XXs =========================
```
