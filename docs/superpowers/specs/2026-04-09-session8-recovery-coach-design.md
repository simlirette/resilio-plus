# Session 8 — Recovery Coach Design Spec

## Goal

Implémenter le Recovery Coach complet : calcul déterministe du Readiness Score (5 facteurs pondérés), verdict gate keeper (vert/jaune/rouge), détection du surentraînement, enrichissement LLM des notes, et route API `POST /api/v1/plan/recovery`.

---

## Architecture

Le Recovery Coach suit le même pattern que le Running Coach (S6) et le Lifting Coach (S7) :

```
POST /api/v1/plan/recovery
        ↓
RecoveryCoachAgent.run(state)          ← BaseAgent
        ↓
get_agent_view(state, recovery_coach)  ← _recovery_view (views.py)
        ↓
RecoveryCoachAgent.prescribe(view)
        ↓
RecoveryPrescriber.evaluate(view)      ← calcul déterministe
        +
_get_coaching_notes(view, verdict)     ← LLM Anthropic
        ↓
verdict dict (Hevy-style JSON)
```

Le prescriber est **pur et déterministe** — pas d'appels réseau, pas d'état. L'agent ajoute les notes LLM en couche séparée.

---

## Schema Changes

### `models/schemas.py` — `FatigueState`

Ajouter un champ optionnel pour la FC repos mesurée aujourd'hui (nécessaire pour le facteur FC Repos) :

```python
class FatigueState(BaseModel):
    # ... champs existants ...
    hr_rest_today: int | None = None   # ← NOUVEAU
```

La baseline FC repos vient de `profile.resting_hr` (AthleteProfile, déjà existant).

### `models/views.py` — `_recovery_view`

Exposer `resting_hr` (baseline FC repos) depuis le profil :

```python
def _recovery_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg", "resting_hr"}  # + resting_hr
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

---

## `agents/recovery_coach/prescriber.py` — RecoveryPrescriber

### Interface publique

```python
class RecoveryPrescriber:
    def evaluate(self, view: dict) -> dict:
        """
        Calcule le Readiness Score et émet le verdict gate keeper.

        Args:
            view: vue filtrée Recovery Coach (fatigue, identity, current_phase, …)

        Returns:
            {
              "agent": "recovery_coach",
              "readiness_score": float,        # 0-100
              "color": "green"|"yellow"|"red",
              "factors": {
                "hrv_score": float,
                "sleep_score": float,
                "acwr_score": float,
                "hr_rest_score": float,
                "subjective_score": float,
              },
              "modification_params": {
                "intensity_reduction_pct": int,
                "tier_max": int,
                "volume_reduction_pct": int,
              },
              "overtraining_alert": bool,
              "notes": "",   # chaîne vide — remplie par l'agent LLM
            }
        """
```

### Calcul des 5 facteurs

#### 1. HRV Score (poids : 0.30)

Source : `fatigue.hrv_rmssd_today` vs `fatigue.hrv_rmssd_baseline`.

| Condition | Score |
|-----------|-------|
| `today >= baseline` | 100 |
| `85% <= today < baseline` | 75 |
| `70% <= today < 85% baseline` | 50 |
| `today < 70% baseline` | 25 |
| `today` ou `baseline` est `None` | **50** (fallback neutre) |

#### 2. Sleep Score (poids : 0.25)

Source : `fatigue.sleep_hours_last_night` + `fatigue.sleep_quality_subjective`.

| Condition | Score |
|-----------|-------|
| hours >= 8 ET quality >= 8 | 100 |
| 7 <= hours < 8 ET quality >= 7 | 80 |
| 6 <= hours < 7 OU quality in [5, 6] | 50 |
| hours < 6 OU quality < 5 | 20 |
| `hours` ou `quality` est `None` | **50** (fallback neutre) |

Règle de priorité : si les deux conditions d'une ligne sont requises (ET), les deux doivent être vraies pour le score. Si une seule condition suffit (OU), prendre le pire des deux. Évaluer les lignes de haut en bas, retenir la première qui correspond.

#### 3. ACWR Score (poids : 0.25)

Source : `fatigue.acwr` (ACWR global).

| Condition | Score |
|-----------|-------|
| `0.8 <= acwr <= 1.3` | 100 |
| `0.7 <= acwr < 0.8` OU `1.3 < acwr <= 1.4` | 70 |
| `acwr < 0.7` OU `1.4 < acwr <= 1.5` | 40 |
| `acwr > 1.5` | 0 |
| `acwr` est `None` | **70** (fallback prudent) |

#### 4. HR Rest Score (poids : 0.10)

Source : `fatigue.hr_rest_today` vs `identity.resting_hr` (baseline).

| Condition | Score |
|-----------|-------|
| `today <= baseline` | 100 |
| `baseline < today <= baseline + 3` | 70 |
| `baseline + 4 <= today <= baseline + 6` | 40 |
| `today > baseline + 6` | 10 |
| `hr_rest_today` ou `resting_hr` est `None` | **100** (neutre — pas de pénalité sans données) |

#### 5. Subjective Fatigue Score (poids : 0.10)

Source : `fatigue.fatigue_subjective` (échelle 1-10).

| Condition | Score |
|-----------|-------|
| 1 <= value <= 3 | 100 |
| 4 <= value <= 5 | 70 |
| 6 <= value <= 7 | 40 |
| 8 <= value <= 10 | 10 |
| `fatigue_subjective` est `None` | **70** (fallback neutre) |

### Readiness Score final

```
readiness_score = round(
    0.30 * hrv_score
  + 0.25 * sleep_score
  + 0.25 * acwr_score
  + 0.10 * hr_rest_score
  + 0.10 * subjective_score,
  1
)
```

### Verdict par seuil

| Readiness Score | Color | modification_params |
|-----------------|-------|---------------------|
| >= 75 | `"green"` | `{intensity_reduction_pct: 0, tier_max: 3, volume_reduction_pct: 0}` |
| 50–74 | `"yellow"` | `{intensity_reduction_pct: 15, tier_max: 1, volume_reduction_pct: 0}` |
| < 50 | `"red"` | `{intensity_reduction_pct: 100, tier_max: 0, volume_reduction_pct: 100}` |

### Détection surentraînement

`overtraining_alert = True` si au moins une condition est vraie :
1. `acwr > 1.5`
2. `hrv_rmssd_today` is not None AND `hrv_rmssd_baseline` is not None AND `hrv_rmssd_today < 0.70 * hrv_rmssd_baseline`

(Les signaux multi-jours consécutifs nécessitent un pipeline d'historique — hors scope S8, YAGNI.)

---

## `agents/recovery_coach/agent.py` — RecoveryCoachAgent

```python
class RecoveryCoachAgent(BaseAgent):
    agent_type = AgentType.recovery_coach

    def __init__(self) -> None:
        self._prescriber = RecoveryPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        verdict = self._prescriber.evaluate(view)
        verdict["notes"] = self._get_coaching_notes(view, verdict)
        return verdict

    def _get_coaching_notes(self, view: dict, verdict: dict) -> str:
        """
        Appel LLM : génère une note factuelle biométrique (≤ 2 phrases).
        Retourne "" en cas d'échec.
        Style attendu : "HRV RMSSD 45ms (-27% vs baseline 62ms). FC repos +7 bpm. Verdict : ROUGE."
        """
```

Le prompt LLM inclut : score, couleur, valeurs brutes des 5 facteurs, overtraining_alert.
La réponse est tronquée à 500 caractères si nécessaire.
En cas d'exception, `notes = ""` (silencieux).

La clé de retour est `"notes"` (string, pas list[str]) — le Recovery Coach émet un constat biométrique unique, pas une liste de prescriptions.

---

## `api/v1/plan.py` — POST /recovery

Même pattern que `/running` et `/lifting` :

```python
class RecoveryPlanRequest(BaseModel):
    athlete_state: dict

@router.post("/recovery")
def generate_recovery_plan(body: RecoveryPlanRequest) -> dict:
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return RecoveryCoachAgent().run(state)
```

---

## Tests

### `tests/test_recovery_prescriber.py` — 6 tests

```python
def test_green_verdict_healthy_athlete():
    """Tous facteurs optimaux → readiness >= 75, color = "green"."""

def test_yellow_verdict_moderate_fatigue():
    """ACWR 1.35, HRV -20% vs baseline → 50 <= score < 75, color = "yellow",
    modification_params.intensity_reduction_pct == 15."""

def test_red_verdict_critical_fatigue():
    """ACWR 1.61, HRV -39%, sommeil 5h, fatigue_subjective 8
    → score < 50, color = "red", modification_params.tier_max == 0."""

def test_overtraining_alert_acwr():
    """acwr = 1.55 → overtraining_alert is True."""

def test_overtraining_alert_hrv():
    """hrv_rmssd_today = 40, hrv_rmssd_baseline = 62 (ratio 0.645 < 0.70)
    → overtraining_alert is True."""

def test_fallback_when_data_missing():
    """hrv_rmssd_today=None, sleep_hours=None, hr_rest_today=None,
    fatigue_subjective=None, acwr=None → evaluate() ne crash pas,
    readiness_score est calculé (fallbacks actifs), color est valide."""
```

### `tests/test_recovery_agent.py` — 4 tests

```python
def test_agent_returns_readiness_score(simon_pydantic_state):
    """RecoveryCoachAgent.run() retourne un dict avec "readiness_score"."""

def test_agent_returns_valid_color(simon_pydantic_state):
    """color in ["green", "yellow", "red"]."""

def test_agent_appends_notes(simon_pydantic_state):
    """Avec LLM mocké → "notes" est une str (peut être vide)."""

def test_agent_handles_llm_failure(simon_pydantic_state):
    """LLM lève une exception → notes = "", pas de crash."""
```

### `tests/test_plan_route.py` — 3 tests additionnels

```python
def test_post_recovery_plan_returns_200(simon_pydantic_state): ...
def test_post_recovery_plan_invalid_body(): ...
def test_post_recovery_plan_agent_receives_state(simon_pydantic_state): ...
```

---

## Fichiers — Résumé

| Fichier | Action |
|---------|--------|
| `models/schemas.py` | Modifier — ajouter `hr_rest_today: int \| None = None` à `FatigueState` |
| `models/views.py` | Modifier — ajouter `"resting_hr"` à l'include set de `_recovery_view` |
| `agents/recovery_coach/__init__.py` | Créer (vide) |
| `agents/recovery_coach/prescriber.py` | Créer — `RecoveryPrescriber` |
| `agents/recovery_coach/agent.py` | Créer — `RecoveryCoachAgent` |
| `api/v1/plan.py` | Modifier — `POST /recovery` |
| `tests/test_recovery_prescriber.py` | Créer — 6 tests |
| `tests/test_recovery_agent.py` | Créer — 4 tests |
| `tests/test_plan_route.py` | Modifier — 3 tests recovery route |
| `CLAUDE.md` | Modifier — S8 ✅ FAIT en fin de session |

---

## Invariants post-S8

- Tous les tests existants continuent de passer (107 → ~120 tests)
- `ruff check` propre
- `FatigueState.hr_rest_today` est optionnel — pas de breaking change sur les fixtures existantes
- Le Recovery Coach ne produit PAS de `sessions[]` — il produit un verdict (`readiness_score`, `color`, `factors`, `modification_params`, `overtraining_alert`, `notes`)
