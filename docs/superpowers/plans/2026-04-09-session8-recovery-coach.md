# Session 8 — Recovery Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implémenter le Recovery Coach complet — RecoveryPrescriber (5 facteurs pondérés, verdict vert/jaune/rouge, détection surentraînement), RecoveryCoachAgent (LLM notes), route POST /api/v1/plan/recovery.

**Architecture:** Même pattern que Running Coach (S6) et Lifting Coach (S7) : prescriber déterministe + agent LLM en couche séparée. Deux changements de schéma mineurs (FatigueState.hr_rest_today + _recovery_view expose resting_hr). Le Recovery Coach ne produit pas de sessions[] — il produit un verdict biométrique structuré.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, Anthropic SDK (claude-sonnet-4-6), pytest, ruff, Poetry.

---

## Contexte projet

```
resilio-plus/
├── models/schemas.py           ← FatigueState à modifier (ajouter hr_rest_today)
├── models/views.py             ← _recovery_view à modifier (exposer resting_hr)
├── agents/
│   ├── base_agent.py           ← BaseAgent ABC — prescribe(view) + run(state)
│   └── recovery_coach/
│       ├── recovery_coach_system_prompt.md  ← Existant — formule complète
│       ├── __init__.py         ← À créer
│       ├── prescriber.py       ← À créer — RecoveryPrescriber
│       └── agent.py            ← À créer — RecoveryCoachAgent
├── api/v1/plan.py              ← À modifier — POST /recovery
└── tests/
    ├── conftest.py             ← simon_pydantic_state fixture existante
    ├── test_recovery_prescriber.py  ← À créer
    ├── test_recovery_agent.py       ← À créer
    └── test_plan_route.py           ← À modifier (3 tests recovery)
```

**Commande de test :** `poetry run pytest tests/ -v`
**Path Poetry sur Windows :** `/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe`

---

## Task 1 : Schema changes — FatigueState + _recovery_view

**Files:**
- Modify: `models/schemas.py` (FatigueState — ajouter hr_rest_today)
- Modify: `models/views.py` (_recovery_view — exposer resting_hr)
- Test: `tests/test_recovery_prescriber.py` (deux tests de schéma)

---

- [ ] **Step 1.1 : Écrire les deux tests qui échouent**

Créer `tests/test_recovery_prescriber.py` :

```python
"""Tests pour RecoveryPrescriber — S8."""


def test_fatigue_state_accepts_hr_rest_today():
    """FatigueState accepte le champ hr_rest_today optionnel."""
    from models.schemas import FatigueState

    state = FatigueState(hr_rest_today=65)
    assert state.hr_rest_today == 65


def test_recovery_view_includes_resting_hr(simon_pydantic_state):
    """_recovery_view expose resting_hr (baseline FC repos) dans identity."""
    from models.views import AgentType, get_agent_view

    view = get_agent_view(simon_pydantic_state, AgentType.recovery_coach)
    assert "resting_hr" in view["identity"]
```

- [ ] **Step 1.2 : Vérifier que les tests échouent**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_recovery_prescriber.py::test_fatigue_state_accepts_hr_rest_today tests/test_recovery_prescriber.py::test_recovery_view_includes_resting_hr -v
```

Attendu :
- `test_fatigue_state_accepts_hr_rest_today` : FAIL — AttributeError (hr_rest_today not in FatigueState)
- `test_recovery_view_includes_resting_hr` : FAIL — AssertionError (resting_hr absent)

- [ ] **Step 1.3 : Ajouter `hr_rest_today` à FatigueState dans `models/schemas.py`**

Trouver la classe FatigueState (lignes ~168-181). Ajouter après `fatigue_subjective` :

```python
class FatigueState(BaseModel):
    acwr: float | None = None
    acwr_trend: str | None = None
    acwr_by_sport: ACWRBySport = Field(default_factory=ACWRBySport)
    weekly_fatigue_score: float | None = None
    fatigue_by_muscle: dict[str, float] = {}
    cns_load_7day_avg: float | None = None
    recovery_score_today: float | None = None
    hrv_rmssd_today: float | None = None
    hrv_rmssd_baseline: float | None = None
    sleep_hours_last_night: float | None = None
    sleep_quality_subjective: int | None = None
    fatigue_subjective: int | None = None
    hr_rest_today: int | None = None
```

- [ ] **Step 1.4 : Ajouter `resting_hr` à `_recovery_view` dans `models/views.py`**

Trouver `_recovery_view` (lignes ~127-139). Changer l'include set :

```python
def _recovery_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg", "resting_hr"}
        ),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "fatigue": state.fatigue.model_dump(),
        "weekly_volumes": state.weekly_volumes.model_dump(),
        "compliance": state.compliance.model_dump(),
        "current_phase": state.current_phase.model_dump(),
    }
```

- [ ] **Step 1.5 : Vérifier que les 2 tests passent + aucune régression**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_recovery_prescriber.py::test_fatigue_state_accepts_hr_rest_today tests/test_recovery_prescriber.py::test_recovery_view_includes_resting_hr tests/ -v 2>&1 | tail -20
```

Attendu : 2 nouveaux tests PASS, 107 anciens tests PASS.

- [ ] **Step 1.6 : Commit**

```bash
git add models/schemas.py models/views.py tests/test_recovery_prescriber.py
git commit -m "feat: add hr_rest_today to FatigueState, expose resting_hr in recovery view (S8)"
```

---

## Task 2 : RecoveryPrescriber — calcul déterministe du Readiness Score

**Files:**
- Create: `agents/recovery_coach/prescriber.py`
- Test: `tests/test_recovery_prescriber.py` (6 tests au total)

---

- [ ] **Step 2.1 : Ajouter les 6 tests dans `tests/test_recovery_prescriber.py`**

Ajouter après les 2 tests existants :

```python
# ─────────────────────────────────────────────────────────────
# Helper — construit une vue Recovery Coach de test
# ─────────────────────────────────────────────────────────────

def _make_view(
    hrv_today=None,
    hrv_baseline=None,
    sleep_hours=None,
    sleep_quality=None,
    acwr=None,
    hr_rest_today=None,
    resting_hr=None,
    fatigue_subjective=None,
):
    return {
        "identity": {
            "first_name": "Simon",
            "age": 32,
            "sex": "M",
            "weight_kg": 78.5,
            "resting_hr": resting_hr,
        },
        "constraints": {"injuries_history": []},
        "fatigue": {
            "acwr": acwr,
            "acwr_trend": None,
            "acwr_by_sport": {
                "running": None,
                "lifting": None,
                "biking": None,
                "swimming": None,
            },
            "weekly_fatigue_score": None,
            "fatigue_by_muscle": {},
            "cns_load_7day_avg": None,
            "recovery_score_today": None,
            "hrv_rmssd_today": hrv_today,
            "hrv_rmssd_baseline": hrv_baseline,
            "sleep_hours_last_night": sleep_hours,
            "sleep_quality_subjective": sleep_quality,
            "fatigue_subjective": fatigue_subjective,
            "hr_rest_today": hr_rest_today,
        },
        "weekly_volumes": {
            "running_km": 22.0,
            "lifting_sessions": 3,
            "swimming_km": 0.0,
            "biking_km": 0.0,
            "total_training_hours": 6.5,
        },
        "compliance": {
            "last_4_weeks_completion_rate": 0.88,
            "missed_sessions_this_week": [],
            "nutrition_adherence_7day": 0.75,
        },
        "current_phase": {
            "macrocycle": "base_building",
            "mesocycle_week": 3,
            "mesocycle_length": 4,
            "next_deload": None,
            "target_event": None,
            "target_event_date": None,
        },
    }


# ─────────────────────────────────────────────────────────────
# Tests prescriber
# ─────────────────────────────────────────────────────────────

def test_green_verdict_healthy_athlete():
    """Tous facteurs optimaux → readiness >= 75, color = 'green'."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view(
        hrv_today=65,
        hrv_baseline=62,      # today > baseline → hrv_score 100
        sleep_hours=8.5,
        sleep_quality=9,       # >=8h + quality>=8 → sleep_score 100
        acwr=1.1,              # 0.8-1.3 → acwr_score 100
        hr_rest_today=57,
        resting_hr=58,         # today <= baseline → hr_rest_score 100
        fatigue_subjective=2,  # 1-3 → subjective_score 100
    )
    result = RecoveryPrescriber().evaluate(view)

    assert result["color"] == "green"
    assert result["readiness_score"] >= 75
    assert result["modification_params"]["intensity_reduction_pct"] == 0
    assert result["modification_params"]["tier_max"] == 3


def test_yellow_verdict_moderate_fatigue():
    """Facteurs modérés → 50 <= score < 75, color = 'yellow',
    modification_params.intensity_reduction_pct == 15."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view(
        hrv_today=50,
        hrv_baseline=62,       # 50/62=0.806 → in [0.70, 0.85) → hrv_score 50
        sleep_hours=7.0,
        sleep_quality=7,       # 7h + quality>=7 → sleep_score 80
        acwr=1.35,             # 1.3 < acwr <= 1.4 → acwr_score 70
        hr_rest_today=60,
        resting_hr=58,         # diff=2 → hr_rest_score 70
        fatigue_subjective=5,  # 4-5 → subjective_score 70
    )
    # Expected: 0.30*50 + 0.25*80 + 0.25*70 + 0.10*70 + 0.10*70 = 66.5
    result = RecoveryPrescriber().evaluate(view)

    assert result["color"] == "yellow"
    assert 50 <= result["readiness_score"] < 75
    assert result["modification_params"]["intensity_reduction_pct"] == 15
    assert result["modification_params"]["tier_max"] == 1


def test_red_verdict_critical_fatigue():
    """ACWR 1.61, HRV -39%, sommeil 5h, fatigue_subjective 8
    → score < 50, color = 'red', tier_max == 0."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view(
        hrv_today=38,
        hrv_baseline=62,       # 38/62=0.613 < 0.70 → hrv_score 25
        sleep_hours=5.1,
        sleep_quality=4,       # <6h AND quality<5 → sleep_score 20
        acwr=1.61,             # >1.5 → acwr_score 0
        hr_rest_today=67,
        resting_hr=58,         # diff=9 > 6 → hr_rest_score 10
        fatigue_subjective=8,  # 8-10 → subjective_score 10
    )
    # Expected: 0.30*25 + 0.25*20 + 0.25*0 + 0.10*10 + 0.10*10 = 14.5
    result = RecoveryPrescriber().evaluate(view)

    assert result["color"] == "red"
    assert result["readiness_score"] < 50
    assert result["modification_params"]["tier_max"] == 0
    assert result["modification_params"]["volume_reduction_pct"] == 100


def test_overtraining_alert_triggered_by_acwr():
    """acwr > 1.5 → overtraining_alert is True."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view(acwr=1.55)
    result = RecoveryPrescriber().evaluate(view)
    assert result["overtraining_alert"] is True


def test_overtraining_alert_triggered_by_hrv():
    """hrv_today/baseline < 0.70 → overtraining_alert is True."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    # 40/62 = 0.645 < 0.70
    view = _make_view(hrv_today=40, hrv_baseline=62)
    result = RecoveryPrescriber().evaluate(view)
    assert result["overtraining_alert"] is True


def test_fallback_when_all_data_missing():
    """Tous les champs fatigue à None → evaluate() ne crash pas,
    readiness_score est calculé avec les fallbacks, color est valide."""
    from agents.recovery_coach.prescriber import RecoveryPrescriber

    view = _make_view()  # tous None
    result = RecoveryPrescriber().evaluate(view)

    assert result["readiness_score"] >= 0
    assert result["color"] in ("green", "yellow", "red")
    assert "factors" in result
    assert "overtraining_alert" in result
```

- [ ] **Step 2.2 : Vérifier que les 6 nouveaux tests échouent**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_recovery_prescriber.py -v 2>&1 | tail -20
```

Attendu : 2 anciens PASS, 6 nouveaux FAIL — ImportError (prescriber inexistant).

- [ ] **Step 2.3 : Créer `agents/recovery_coach/prescriber.py`**

```python
"""
RecoveryPrescriber — calcul déterministe du Readiness Score.

Formule complète définie dans recovery_coach_system_prompt.md.
Aucun appel réseau — pur calcul, entièrement testable hors LLM.
"""


class RecoveryPrescriber:
    """Calcule le Readiness Score (0–100) à partir de 5 facteurs biométriques pondérés."""

    _HRV_W = 0.30
    _SLEEP_W = 0.25
    _ACWR_W = 0.25
    _HR_W = 0.10
    _SUBJ_W = 0.10

    def evaluate(self, view: dict) -> dict:
        """
        Calcule le Readiness Score et émet le verdict gate keeper.

        Args:
            view: vue filtrée Recovery Coach (retournée par _recovery_view).

        Returns:
            {
              "agent": "recovery_coach",
              "readiness_score": float (0-100),
              "color": "green" | "yellow" | "red",
              "factors": {hrv_score, sleep_score, acwr_score, hr_rest_score, subjective_score},
              "modification_params": {intensity_reduction_pct, tier_max, volume_reduction_pct},
              "overtraining_alert": bool,
              "notes": "",   # rempli par RecoveryCoachAgent
            }
        """
        fatigue = view.get("fatigue", {})
        identity = view.get("identity", {})

        hrv_score = self._hrv_score(
            fatigue.get("hrv_rmssd_today"),
            fatigue.get("hrv_rmssd_baseline"),
        )
        sleep_score = self._sleep_score(
            fatigue.get("sleep_hours_last_night"),
            fatigue.get("sleep_quality_subjective"),
        )
        acwr_score = self._acwr_score(fatigue.get("acwr"))
        hr_rest_score = self._hr_rest_score(
            fatigue.get("hr_rest_today"),
            identity.get("resting_hr"),
        )
        subjective_score = self._subjective_score(fatigue.get("fatigue_subjective"))

        readiness_score = round(
            self._HRV_W * hrv_score
            + self._SLEEP_W * sleep_score
            + self._ACWR_W * acwr_score
            + self._HR_W * hr_rest_score
            + self._SUBJ_W * subjective_score,
            1,
        )

        color = self._color(readiness_score)

        return {
            "agent": "recovery_coach",
            "readiness_score": readiness_score,
            "color": color,
            "factors": {
                "hrv_score": hrv_score,
                "sleep_score": sleep_score,
                "acwr_score": acwr_score,
                "hr_rest_score": hr_rest_score,
                "subjective_score": subjective_score,
            },
            "modification_params": self._modification_params(color),
            "overtraining_alert": self._overtraining_alert(
                fatigue.get("acwr"),
                fatigue.get("hrv_rmssd_today"),
                fatigue.get("hrv_rmssd_baseline"),
            ),
            "notes": "",
        }

    # ── Facteurs ────────────────────────────────────────────────────────────

    def _hrv_score(self, today: float | None, baseline: float | None) -> float:
        """HRV Score (30%) — RMSSD aujourd'hui vs baseline 7 jours."""
        if today is None or baseline is None or baseline == 0:
            return 50.0
        ratio = today / baseline
        if ratio >= 1.0:
            return 100.0
        if ratio >= 0.85:
            return 75.0
        if ratio >= 0.70:
            return 50.0
        return 25.0

    def _sleep_score(self, hours: float | None, quality: int | None) -> float:
        """Sleep Score (25%) — durée + qualité subjective (1-10)."""
        if hours is None or quality is None:
            return 50.0
        if hours >= 8 and quality >= 8:
            return 100.0
        if hours >= 7 and quality >= 7:
            return 80.0
        # 6-7h OU qualité 5-6 : évaluation top-down, premier match
        if (6 <= hours < 7) or (5 <= quality <= 6):
            return 50.0
        return 20.0

    def _acwr_score(self, acwr: float | None) -> float:
        """ACWR Score (25%) — ratio charge aiguë / chronique global."""
        if acwr is None:
            return 70.0
        if 0.8 <= acwr <= 1.3:
            return 100.0
        if (0.7 <= acwr < 0.8) or (1.3 < acwr <= 1.4):
            return 70.0
        if acwr > 1.5:
            return 0.0
        # acwr < 0.7 OU 1.4 < acwr <= 1.5
        return 40.0

    def _hr_rest_score(self, today: int | None, baseline: int | None) -> float:
        """HR Rest Score (10%) — FC repos aujourd'hui vs baseline profil."""
        if today is None or baseline is None:
            return 100.0  # neutre — pas de pénalité sans données
        diff = today - baseline
        if diff <= 0:
            return 100.0
        if diff <= 3:
            return 70.0
        if diff <= 6:
            return 40.0
        return 10.0

    def _subjective_score(self, value: int | None) -> float:
        """Subjective Fatigue Score (10%) — échelle 1-10."""
        if value is None:
            return 70.0
        if value <= 3:
            return 100.0
        if value <= 5:
            return 70.0
        if value <= 7:
            return 40.0
        return 10.0

    # ── Verdict ─────────────────────────────────────────────────────────────

    def _color(self, score: float) -> str:
        if score >= 75:
            return "green"
        if score >= 50:
            return "yellow"
        return "red"

    def _modification_params(self, color: str) -> dict:
        if color == "green":
            return {"intensity_reduction_pct": 0, "tier_max": 3, "volume_reduction_pct": 0}
        if color == "yellow":
            return {"intensity_reduction_pct": 15, "tier_max": 1, "volume_reduction_pct": 0}
        return {"intensity_reduction_pct": 100, "tier_max": 0, "volume_reduction_pct": 100}

    def _overtraining_alert(
        self,
        acwr: float | None,
        hrv_today: float | None,
        hrv_baseline: float | None,
    ) -> bool:
        """Détecte signaux de surentraînement point-in-time (sans historique multi-jours)."""
        if acwr is not None and acwr > 1.5:
            return True
        if (
            hrv_today is not None
            and hrv_baseline is not None
            and hrv_baseline > 0
            and hrv_today / hrv_baseline < 0.70
        ):
            return True
        return False
```

- [ ] **Step 2.4 : Vérifier que tous les tests passent**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_recovery_prescriber.py -v
```

Attendu : 8/8 PASS.

- [ ] **Step 2.5 : Vérifier aucune régression**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/ -q 2>&1 | tail -5
```

Attendu : 109 passed.

- [ ] **Step 2.6 : Commit**

```bash
git add agents/recovery_coach/prescriber.py tests/test_recovery_prescriber.py
git commit -m "feat: implement RecoveryPrescriber — 5-factor readiness score (S8)"
```

---

## Task 3 : RecoveryCoachAgent — LLM coaching notes

**Files:**
- Create: `agents/recovery_coach/__init__.py`
- Create: `agents/recovery_coach/agent.py`
- Create: `tests/test_recovery_agent.py`

---

- [ ] **Step 3.1 : Créer `tests/test_recovery_agent.py`**

```python
"""Tests pour RecoveryCoachAgent — S8."""
from unittest.mock import MagicMock, patch


def test_agent_returns_readiness_score(simon_pydantic_state):
    """RecoveryCoachAgent.run() retourne un dict avec 'readiness_score'."""
    from agents.recovery_coach.agent import RecoveryCoachAgent

    with patch("agents.recovery_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="HRV normal. Verdict : VERT.")
        ]
        mock_cls.return_value = mock_client

        agent = RecoveryCoachAgent()
        result = agent.run(simon_pydantic_state)

    assert "readiness_score" in result
    assert isinstance(result["readiness_score"], (int, float))


def test_agent_returns_valid_color(simon_pydantic_state):
    """La couleur retournée est bien parmi les valeurs attendues."""
    from agents.recovery_coach.agent import RecoveryCoachAgent

    with patch("agents.recovery_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value.content = [
            MagicMock(text="Verdict : VERT.")
        ]
        agent = RecoveryCoachAgent()
        result = agent.run(simon_pydantic_state)

    assert result["color"] in ("green", "yellow", "red")


def test_agent_appends_notes(simon_pydantic_state):
    """Avec LLM mocké, 'notes' est une str (peut être vide ou non)."""
    from agents.recovery_coach.agent import RecoveryCoachAgent

    with patch("agents.recovery_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="HRV RMSSD à 58ms (baseline). FC repos normale. Verdict : VERT.")
        ]
        mock_cls.return_value = mock_client

        agent = RecoveryCoachAgent()
        result = agent.run(simon_pydantic_state)

    assert isinstance(result.get("notes"), str)


def test_agent_handles_llm_failure(simon_pydantic_state):
    """Si le LLM lève une exception, notes = '' et pas de crash."""
    from agents.recovery_coach.agent import RecoveryCoachAgent

    with patch("agents.recovery_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.side_effect = RuntimeError("API down")

        agent = RecoveryCoachAgent()
        result = agent.run(simon_pydantic_state)

    assert result["notes"] == ""
    assert "readiness_score" in result  # le verdict déterministe est toujours présent
```

- [ ] **Step 3.2 : Vérifier que les 4 tests échouent**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_recovery_agent.py -v 2>&1 | tail -10
```

Attendu : 4 FAIL — ImportError (agent inexistant).

- [ ] **Step 3.3 : Créer `agents/recovery_coach/__init__.py`**

```python
```

(Fichier vide — rend le dossier importable comme package Python.)

- [ ] **Step 3.4 : Créer `agents/recovery_coach/agent.py`**

```python
"""
RecoveryCoachAgent — portier biométrique de Resilio+.

Enchaîne RecoveryPrescriber (calcul déterministe) + appel LLM Anthropic
pour générer une note factuelle biométrique (≤ 2 phrases).
"""
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.recovery_coach.prescriber import RecoveryPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "recovery_coach_system_prompt.md").read_text(
    encoding="utf-8"
)


class RecoveryCoachAgent(BaseAgent):
    """Agent Recovery Coach — calcule le Readiness Score et génère un constat biométrique."""

    agent_type = AgentType.recovery_coach

    def __init__(self) -> None:
        self._prescriber = RecoveryPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        """
        Évalue la capacité physiologique de l'athlète.

        Retourne un verdict structuré (pas de sessions[]) :
        readiness_score, color, factors, modification_params, overtraining_alert, notes.
        """
        verdict = self._prescriber.evaluate(view)
        verdict["notes"] = self._get_coaching_notes(view, verdict)
        return verdict

    def _get_coaching_notes(self, view: dict, verdict: dict) -> str:
        """
        Génère un constat biométrique factuel via LLM (≤ 2 phrases, style clinique).

        Retourne "" en cas d'échec LLM.
        """
        fatigue = view.get("fatigue", {})
        factors = verdict["factors"]

        user_content = (
            f"Readiness Score : {verdict['readiness_score']}/100 → {verdict['color'].upper()}.\n"
            f"HRV RMSSD : {fatigue.get('hrv_rmssd_today')} ms "
            f"(baseline {fatigue.get('hrv_rmssd_baseline')} ms) → score {factors['hrv_score']}/100.\n"
            f"Sommeil : {fatigue.get('sleep_hours_last_night')}h, "
            f"qualité {fatigue.get('sleep_quality_subjective')}/10 → score {factors['sleep_score']}/100.\n"
            f"ACWR global : {fatigue.get('acwr')} → score {factors['acwr_score']}/100.\n"
            f"FC repos : {fatigue.get('hr_rest_today')} bpm → score {factors['hr_rest_score']}/100.\n"
            f"Fatigue subjective : {fatigue.get('fatigue_subjective')}/10 → score {factors['subjective_score']}/100.\n"
            f"Surentraînement détecté : {verdict['overtraining_alert']}.\n"
            "Génère un constat biométrique en 1-2 phrases. Factuel. Chiffré. Zéro encouragement."
        )

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=150,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text.strip()
            return raw[:500]  # tronquer si nécessaire
        except Exception:
            return ""
```

- [ ] **Step 3.5 : Vérifier que les 4 tests passent**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_recovery_agent.py -v
```

Attendu : 4/4 PASS.

- [ ] **Step 3.6 : Vérifier aucune régression (total ~113 tests)**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/ -q 2>&1 | tail -5
```

Attendu : 113 passed.

- [ ] **Step 3.7 : Commit**

```bash
git add agents/recovery_coach/__init__.py agents/recovery_coach/agent.py tests/test_recovery_agent.py
git commit -m "feat: implement RecoveryCoachAgent — LLM biometric notes (S8)"
```

---

## Task 4 : POST /api/v1/plan/recovery — route API

**Files:**
- Modify: `api/v1/plan.py` (ajouter POST /recovery)
- Modify: `tests/test_plan_route.py` (ajouter 3 tests recovery)

---

- [ ] **Step 4.1 : Ajouter les 3 tests dans `tests/test_plan_route.py`**

Ajouter à la fin du fichier, après les tests lifting :

```python
_MOCK_RECOVERY_VERDICT = {
    "agent": "recovery_coach",
    "readiness_score": 68.0,
    "color": "yellow",
    "factors": {
        "hrv_score": 50.0,
        "sleep_score": 80.0,
        "acwr_score": 70.0,
        "hr_rest_score": 70.0,
        "subjective_score": 70.0,
    },
    "modification_params": {
        "intensity_reduction_pct": 15,
        "tier_max": 1,
        "volume_reduction_pct": 0,
    },
    "overtraining_alert": False,
    "notes": "Note de test.",
}


def test_post_recovery_plan_returns_200(simon_pydantic_state):
    """POST /api/v1/plan/recovery avec payload valide → 200 + verdict JSON."""
    from api.main import app

    client = TestClient(app)

    with patch("api.v1.plan.RecoveryCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = _MOCK_RECOVERY_VERDICT
        mock_cls.return_value = mock_agent

        response = client.post(
            "/api/v1/plan/recovery",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "recovery_coach"
    assert "readiness_score" in data


def test_post_recovery_plan_invalid_body():
    """POST avec athlete_state invalide → 422 Unprocessable Entity."""
    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/plan/recovery",
        json={"athlete_state": {"invalid_field": "bad_data"}},
    )

    assert response.status_code == 422


def test_post_recovery_plan_agent_receives_state(simon_pydantic_state):
    """Le body transmis à RecoveryCoachAgent.run() est bien un AthleteState valide."""
    from api.main import app
    from models.athlete_state import AthleteState

    client = TestClient(app)
    received_states: list = []

    def capture_run(state):
        received_states.append(state)
        return _MOCK_RECOVERY_VERDICT

    with patch("api.v1.plan.RecoveryCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.side_effect = capture_run
        mock_cls.return_value = mock_agent

        client.post(
            "/api/v1/plan/recovery",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert len(received_states) == 1
    assert isinstance(received_states[0], AthleteState)
```

- [ ] **Step 4.2 : Vérifier que les 3 nouveaux tests échouent**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_plan_route.py::test_post_recovery_plan_returns_200 tests/test_plan_route.py::test_post_recovery_plan_invalid_body tests/test_plan_route.py::test_post_recovery_plan_agent_receives_state -v 2>&1 | tail -10
```

Attendu : 3 FAIL — 404 (route inexistante).

- [ ] **Step 4.3 : Ajouter le code dans `api/v1/plan.py`**

Ajouter à la fin du fichier, après le bloc lifting :

```python
from agents.recovery_coach.agent import RecoveryCoachAgent


class RecoveryPlanRequest(BaseModel):
    athlete_state: dict


@router.post("/recovery")
def generate_recovery_plan(body: RecoveryPlanRequest) -> dict:
    """
    Évalue la capacité physiologique de l'athlète — verdict gate keeper.

    Body: {"athlete_state": <AthleteState as dict>}
    Returns: verdict dict avec readiness_score, color, factors, modification_params,
             overtraining_alert, notes.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    agent = RecoveryCoachAgent()
    return agent.run(state)
```

Note : l'import `RecoveryCoachAgent` doit être ajouté en tête de fichier avec les autres imports. Le fichier complet après modification :

```python
"""
Plan routes — api/v1/plan.py
POST /plan/running : plan de course hebdomadaire Runna/Garmin-compatible.
POST /plan/lifting : plan de musculation hebdomadaire Hevy-compatible.
POST /plan/recovery : verdict gate keeper — readiness score + modification params.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.lifting_coach.agent import LiftingCoachAgent
from agents.recovery_coach.agent import RecoveryCoachAgent
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
        raise HTTPException(status_code=422, detail=str(e)) from e

    agent = RunningCoachAgent()
    return agent.run(state)


class LiftingPlanRequest(BaseModel):
    athlete_state: dict


@router.post("/lifting")
def generate_lifting_plan(body: LiftingPlanRequest) -> dict:
    """
    Génère un plan de musculation hebdomadaire Hevy-compatible.

    Body: {"athlete_state": <AthleteState as dict>}
    Returns: plan dict avec sessions[].hevy_workout, coaching_notes[], métadonnées DUP.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    agent = LiftingCoachAgent()
    return agent.run(state)


class RecoveryPlanRequest(BaseModel):
    athlete_state: dict


@router.post("/recovery")
def generate_recovery_plan(body: RecoveryPlanRequest) -> dict:
    """
    Évalue la capacité physiologique de l'athlète — verdict gate keeper.

    Body: {"athlete_state": <AthleteState as dict>}
    Returns: verdict dict avec readiness_score, color, factors, modification_params,
             overtraining_alert, notes.
    """
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    agent = RecoveryCoachAgent()
    return agent.run(state)
```

- [ ] **Step 4.4 : Vérifier que tous les tests plan_route passent**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_plan_route.py -v
```

Attendu : 9/9 PASS (3 running + 3 lifting + 3 recovery).

- [ ] **Step 4.5 : Vérifier aucune régression**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/ -q 2>&1 | tail -5
```

Attendu : ~120 passed.

- [ ] **Step 4.6 : Lint**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run ruff check agents/recovery_coach/ api/v1/plan.py tests/test_recovery_prescriber.py tests/test_recovery_agent.py tests/test_plan_route.py
```

Attendu : aucun message (clean).

- [ ] **Step 4.7 : Commit**

```bash
git add api/v1/plan.py tests/test_plan_route.py
git commit -m "feat: add POST /api/v1/plan/recovery route (S8)"
```

---

## Task 5 : Update CLAUDE.md — S8 ✅ FAIT

**Files:**
- Modify: `CLAUDE.md`

---

- [ ] **Step 5.1 : Marquer S8 comme terminé dans la table des sessions**

Trouver :
```
| **S8** | Recovery Coach | Readiness score + gate keeper + HRV pipeline | ⬜ À FAIRE |
```

Remplacer par :
```
| **S8** | Recovery Coach | Readiness score (5 facteurs) + gate keeper + RecoveryCoachAgent | ✅ FAIT |
```

- [ ] **Step 5.2 : Mettre à jour la structure du repo — section agents/recovery_coach/**

Trouver :
```
│   ├── recovery_coach/system_prompt.md  ← ✅ Existant
```

Remplacer par :
```
│   ├── recovery_coach/
│   │   ├── __init__.py                ← ✅ S8
│   │   ├── agent.py                   ← ✅ S8 — RecoveryCoachAgent (prescriber + LLM notes)
│   │   ├── prescriber.py              ← ✅ S8 — RecoveryPrescriber (5 facteurs, gate keeper)
│   │   └── recovery_coach_system_prompt.md ← ✅ Existant
```

- [ ] **Step 5.3 : Mettre à jour la liste des tests**

Trouver :
```
│   ├── test_lifting_prescriber.py     ← ✅ S7 — 6 tests LiftingPrescriber
│   └── test_lifting_agent.py          ← ✅ S7 — 4 tests LiftingCoachAgent (107 tests total)
```

Remplacer par :
```
│   ├── test_lifting_prescriber.py     ← ✅ S7 — 6 tests LiftingPrescriber
│   ├── test_lifting_agent.py          ← ✅ S7 — 4 tests LiftingCoachAgent
│   ├── test_recovery_prescriber.py    ← ✅ S8 — 8 tests RecoveryPrescriber
│   └── test_recovery_agent.py         ← ✅ S8 — 4 tests RecoveryCoachAgent (~120 tests total)
```

- [ ] **Step 5.4 : Lancer la suite complète une dernière fois**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/ -q 2>&1 | tail -5
```

Attendu : ~120 passed, 0 failed.

- [ ] **Step 5.5 : Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md — S8 Recovery Coach complete"
```

---

## Invariants post-S8

- `FatigueState.hr_rest_today` est optionnel (None par défaut) — aucune fixture existante ne casse
- Le Recovery Coach ne produit PAS de `sessions[]` — son contrat de retour est un verdict biométrique
- Tous les fallbacks (hrv=None, sleep=None, etc.) retournent un score valide sans exception
- `ruff check` propre
- ~120 tests, 0 échecs
