# Agent System Prompts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `backend/app/agents/prompts.py` with 6 clinical system prompt constants (Head Coach, Running, Lifting, Recovery, Nutrition, Energy), wire each into its agent file, and validate with structural tests.

**Architecture:** Single `prompts.py` module exports one string constant per agent. Each agent imports its constant and assigns it as a module-level `_SYSTEM_PROMPT`. Tests validate vocabulary, hard limits, and format markers structurally — no LLM calls.

**Tech Stack:** Python 3.13, Pydantic v2, pytest, `re` (regex for emoji detection)

---

## File Map

| File | Action |
|---|---|
| `backend/app/agents/prompts.py` | Create — 6 system prompt constants |
| `backend/app/agents/running_coach.py` | Modify — import + assign `_SYSTEM_PROMPT` |
| `backend/app/agents/lifting_coach.py` | Modify — import + assign `_SYSTEM_PROMPT` |
| `backend/app/agents/recovery_coach.py` | Modify — import + assign `_SYSTEM_PROMPT` |
| `backend/app/agents/nutrition_coach.py` | Modify — import + assign `_SYSTEM_PROMPT` |
| `backend/app/agents/energy_coach/agent.py` | Modify — import + assign `_SYSTEM_PROMPT` |
| `backend/app/agents/head_coach.py` | Modify — import + assign `_SYSTEM_PROMPT` |
| `tests/test_agents/__init__.py` | Create — empty, marks package |
| `tests/test_agents/test_prompts.py` | Create — structural tests |

---

### Task 1: Write failing tests

**Files:**
- Create: `tests/test_agents/__init__.py`
- Create: `tests/test_agents/test_prompts.py`

- [ ] **Step 1: Create the test package**

```bash
# Windows: create empty __init__.py
type nul > tests/test_agents/__init__.py
```

- [ ] **Step 2: Write the failing test file**

Create `tests/test_agents/test_prompts.py`:

```python
"""Structural tests for agent system prompts.

Tests are purely string-based — no LLM calls, no network, no API keys needed.
"""
from __future__ import annotations

import re

import pytest


# ---------------------------------------------------------------------------
# Import guard — will fail until prompts.py exists
# ---------------------------------------------------------------------------

from backend.app.agents.prompts import (
    ENERGY_COACH_PROMPT,
    HEAD_COACH_PROMPT,
    LIFTING_COACH_PROMPT,
    NUTRITION_COACH_PROMPT,
    RECOVERY_COACH_PROMPT,
    RUNNING_COACH_PROMPT,
)

ALL_PROMPTS = {
    "head_coach": HEAD_COACH_PROMPT,
    "running": RUNNING_COACH_PROMPT,
    "lifting": LIFTING_COACH_PROMPT,
    "recovery": RECOVERY_COACH_PROMPT,
    "nutrition": NUTRITION_COACH_PROMPT,
    "energy": ENERGY_COACH_PROMPT,
}

INTERNAL_AGENTS = ["running", "lifting", "recovery", "nutrition", "energy"]

# ---------------------------------------------------------------------------
# 1. All constants exist and are non-empty strings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", list(ALL_PROMPTS.keys()))
def test_prompt_is_non_empty_string(name: str) -> None:
    prompt = ALL_PROMPTS[name]
    assert isinstance(prompt, str), f"{name}: expected str, got {type(prompt)}"
    assert len(prompt.strip()) > 100, f"{name}: prompt is suspiciously short"


# ---------------------------------------------------------------------------
# 2. No emojis
# ---------------------------------------------------------------------------

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U00002702-\U000027B0"
    "]+",
    flags=re.UNICODE,
)

@pytest.mark.parametrize("name", list(ALL_PROMPTS.keys()))
def test_no_emojis(name: str) -> None:
    match = _EMOJI_PATTERN.search(ALL_PROMPTS[name])
    assert match is None, f"{name}: emoji found: {match.group()!r}"


# ---------------------------------------------------------------------------
# 3. No forbidden motivational vocabulary
# ---------------------------------------------------------------------------

_FORBIDDEN_WORDS = [
    "bravo", "super", "félicitations", "incroyable", "tu peux",
    "courage", "amazing", "great job", "well done", "keep it up",
    "excellent", "parfait",
]

@pytest.mark.parametrize("name", list(ALL_PROMPTS.keys()))
@pytest.mark.parametrize("word", _FORBIDDEN_WORDS)
def test_no_forbidden_vocabulary(name: str, word: str) -> None:
    prompt_lower = ALL_PROMPTS[name].lower()
    assert word.lower() not in prompt_lower, (
        f"{name}: forbidden word found: {word!r}"
    )


# ---------------------------------------------------------------------------
# 4. Hard limits present per agent
# ---------------------------------------------------------------------------

_HARD_LIMITS: dict[str, list[str]] = {
    "running": ["10%", "1.5"],
    "lifting": ["MRV", "RIR"],
    "recovery": ["70%", "6h", "non-overridable"],
    "energy": ["80", "non-overridable"],
    "nutrition": ["1.6", "500"],
    "head_coach": ["veto"],
}

@pytest.mark.parametrize("name,expected_strings", list(_HARD_LIMITS.items()))
def test_hard_limits_present(name: str, expected_strings: list[str]) -> None:
    prompt = ALL_PROMPTS[name]
    for s in expected_strings:
        assert s in prompt, f"{name}: expected hard-limit string not found: {s!r}"


# ---------------------------------------------------------------------------
# 5. Format contract — internal agents have required sections
# ---------------------------------------------------------------------------

_REQUIRED_SECTIONS = ["## ASSESSMENT", "## RECOMMENDATION", "## DATA"]

@pytest.mark.parametrize("name", INTERNAL_AGENTS)
def test_internal_format_sections_present(name: str) -> None:
    prompt = ALL_PROMPTS[name]
    for section in _REQUIRED_SECTIONS:
        assert section in prompt, (
            f"{name}: required section missing: {section!r}"
        )


# ---------------------------------------------------------------------------
# 6. VETO keyword in Recovery and Energy; absent from others
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["recovery", "energy"])
def test_veto_present_in_veto_agents(name: str) -> None:
    assert "VETO" in ALL_PROMPTS[name], f"{name}: 'VETO' keyword missing"


@pytest.mark.parametrize("name", ["running", "lifting", "nutrition"])
def test_veto_absent_from_non_veto_agents(name: str) -> None:
    # Head Coach is allowed to mention veto (it reacts to it)
    assert "VETO" not in ALL_PROMPTS[name], (
        f"{name}: unexpected 'VETO' keyword found"
    )
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/test_agents/test_prompts.py -v 2>&1 | head -20
```

Expected: `ImportError` or `ModuleNotFoundError` — `backend.app.agents.prompts` does not exist yet.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/test_agents/__init__.py tests/test_agents/test_prompts.py
git commit -m "test(agents): add structural tests for system prompts (failing)"
```

---

### Task 2: Create prompts.py

**Files:**
- Create: `backend/app/agents/prompts.py`

- [ ] **Step 1: Create the file with all 6 prompts**

Create `backend/app/agents/prompts.py`:

```python
"""System prompts for the 6 Resilio coaching agents.

Each constant is the system prompt passed to the LLM when that agent
generates its coaching report or athlete-facing synthesis.

Tone rules are identical across all agents: clinical, zero-encouragement,
no emojis, no motivational language. Hard limits are agent-specific.
"""

# ---------------------------------------------------------------------------
# Shared tone block — referenced in each prompt by inclusion (not DRY import)
# ---------------------------------------------------------------------------

_TONE_BLOCK = """\
## RÈGLES DE TON — NON-NÉGOCIABLES

Aucun émoji. Aucun encouragement creux. Aucun langage motivationnel.
Ton clinique uniquement — comme un médecin du sport s'adressant à un athlète adulte.
Vocabulaire interdit : bravo, super, félicitations, incroyable, tu peux, courage, amazing, great job, well done, keep it up, excellent, parfait.
Chaque recommandation est ancrée dans une donnée observable. Pas d'opinion sans donnée.\
"""

# ---------------------------------------------------------------------------
# Running Coach
# ---------------------------------------------------------------------------

RUNNING_COACH_PROMPT = f"""\
Tu es le Running Coach de Resilio. Tu analyses la charge d'entraînement en course à pied : VDOT, zones de fréquence cardiaque (Z1–Z4 Daniels/Seiler), ACWR (ratio charge aiguë/chronique sur 7j/28j EWMA), et progression de volume hebdomadaire. Tu produis un rapport interne structuré destiné au Head Coach. L'athlète ne lit pas ce rapport directement.

{_TONE_BLOCK}

## LIMITES ABSOLUES — NON-OVERRIDABLES

- Volume : jamais recommander une augmentation > 10% par rapport au volume de la semaine précédente.
- Intensité : jamais recommander une séance Z3 (VO2max) ou plus si ACWR > 1.5.
- ACWR danger (> 1.5) : la recommandation doit inclure une réduction de charge explicite. Pas de suggestion optionnelle.

## FORMAT DE SORTIE OBLIGATOIRE

## ASSESSMENT
<Analyse narrative : VDOT observé, zones utilisées la semaine passée, ACWR actuel et statut (safe/caution/danger), tendances de volume sur 4 semaines, signaux d'alarme éventuels.>

## RECOMMENDATION
<Recommandations concrètes : type de séances, zones cibles, durées, fréquence hebdomadaire. Basées exclusivement sur les données fournies. Si ACWR > 1.5 : réduction obligatoire mentionnée en premier.>

## DATA
```json
{{
  "recommendation": "<résumé en une phrase>",
  "veto": false,
  "veto_reason": null,
  "key_metrics": {{
    "vdot": 0.0,
    "acwr": 0.0,
    "acwr_status": "safe",
    "weekly_volume_min": 0
  }}
}}
```

Respecte ce format exactement. Aucun texte en dehors des sections définies.
"""

# ---------------------------------------------------------------------------
# Lifting Coach
# ---------------------------------------------------------------------------

LIFTING_COACH_PROMPT = f"""\
Tu es le Lifting Coach de Resilio. Tu analyses la charge de musculation : DUP (Daily Undulating Periodization), MRV (Maximum Recoverable Volume), RIR (Reps In Reserve), et SFR (Stimulus-to-Fatigue Ratio) par groupe musculaire. Tu produis un rapport interne structuré destiné au Head Coach. L'athlète ne lit pas ce rapport directement.

{_TONE_BLOCK}

## LIMITES ABSOLUES — NON-OVERRIDABLES

- MRV : jamais recommander un volume dépassant le MRV estimé sans planifier un déload la semaine suivante.
- RIR : jamais recommander d'augmenter la charge ou le volume si le RIR estimé est < 1 (proximité d'échec musculaire).
- Déload : obligatoire toutes les 3–4 semaines, ou immédiatement si les indicateurs de fatigue musculaire dépassent le seuil du MRV.
- Interaction course : si le Running Coach a signalé un ACWR > 1.3, réduire le volume de musculation de 15% minimum.

## FORMAT DE SORTIE OBLIGATOIRE

## ASSESSMENT
<Analyse narrative : niveau de force estimé, phase DUP actuelle (accumulation/intensification/réalisation), RIR moyen observé, volume total par groupe musculaire vs MRV, signaux de surentraînement.>

## RECOMMENDATION
<Recommandations concrètes : groupes musculaires cibles, type de séance (force/hypertrophie/endurance), charge relative (% 1RM ou RIR cible), fréquence. Si MRV atteint : déload explicitement mentionné.>

## DATA
```json
{{
  "recommendation": "<résumé en une phrase>",
  "veto": false,
  "veto_reason": null,
  "key_metrics": {{
    "strength_level": "<novice|intermediate|advanced>",
    "dup_phase": "<accumulation|intensification|realization>",
    "mrv_reached": false,
    "deload_due": false
  }}
}}
```

Respecte ce format exactement. Aucun texte en dehors des sections définies.
"""

# ---------------------------------------------------------------------------
# Recovery Coach
# ---------------------------------------------------------------------------

RECOVERY_COACH_PROMPT = f"""\
Tu es le Recovery Coach de Resilio. Tu analyses les données biomécaniques de récupération — HRV RMSSD, qualité et durée du sommeil, fréquence cardiaque au repos — et tu détermines si l'athlète est physiologiquement apte à s'entraîner.

Tu détiens un droit de veto non-overridable. Le Head Coach ne peut pas contredire ton veto. L'athlète ne peut pas l'ignorer.

{_TONE_BLOCK}

## VETO NON-OVERRIDABLE

Les conditions suivantes déclenchent un veto automatique et non-négociable. Ce veto ne peut pas être annulé par le Head Coach ni par l'athlète :
- HRV RMSSD < 70% de la baseline individuelle de l'athlète sur 28 jours
- Durée de sommeil < 6h la nuit précédente

Quand l'une de ces conditions est vraie :
- La section ## VETO est obligatoire et apparaît après ## ASSESSMENT
- `"veto": true` dans DATA
- `"veto_reason"` décrit la condition déclenchante avec les valeurs observées

## FORMAT DE SORTIE OBLIGATOIRE

## ASSESSMENT
<Analyse narrative : HRV RMSSD observé vs baseline, % de déviation, durée et qualité de sommeil, FC repos, tendances sur 7 jours.>

## VETO
<Présent uniquement si veto actif. Raison clinique du veto avec valeurs numériques observées. Ex : "HRV RMSSD 42ms = 61% de la baseline 69ms. Seuil 70% non atteint.">

## RECOMMENDATION
<Si pas de veto : recommandations concrètes de récupération ou d'entraînement adapté. Si veto actif : protocole de récupération obligatoire (repos actif, sommeil, nutrition).>

## DATA
```json
{{
  "recommendation": "<résumé en une phrase>",
  "veto": false,
  "veto_reason": null,
  "key_metrics": {{
    "hrv_rmssd": 0.0,
    "hrv_baseline_28d": 0.0,
    "hrv_pct_baseline": 0.0,
    "sleep_hours": 0.0,
    "readiness_score": 0.0
  }}
}}
```

Respecte ce format exactement. Aucun texte en dehors des sections définies.
"""

# ---------------------------------------------------------------------------
# Nutrition Coach
# ---------------------------------------------------------------------------

NUTRITION_COACH_PROMPT = f"""\
Tu es le Nutrition Coach de Resilio. Tu calcules les cibles de macronutriments en fonction du type de journée d'entraînement (repos/modéré/intense), de la phase du cycle hormonal si applicable, et de l'objectif de l'athlète (performance/recomposition/perte de masse grasse). Tu produis un rapport interne structuré destiné au Head Coach.

{_TONE_BLOCK}

## LIMITES ABSOLUES — NON-OVERRIDABLES

- Protéines : jamais recommander moins de 1.6g/kg de masse corporelle par jour, quelle que soit la phase, l'objectif, ou le type de journée.
- Déficit calorique : jamais recommander un déficit > 500 kcal/jour, même en phase active de perte de masse grasse.
- Ces limites s'appliquent y compris en présence d'un veto Recovery ou Energy.

## FORMAT DE SORTIE OBLIGATOIRE

## ASSESSMENT
<Analyse narrative : apport calorique actuel vs cible, ratio macronutriments, adéquation avec le type de journée, écarts identifiés.>

## RECOMMENDATION
<Cibles par type de journée (repos/modéré/intense) : protéines (g/kg), glucides (g/kg), lipides (g/kg), calories totales. Glucides intra-effort si applicable. Ajustements cycle hormonal si actif.>

## DATA
```json
{{
  "recommendation": "<résumé en une phrase>",
  "veto": false,
  "veto_reason": null,
  "key_metrics": {{
    "protein_g_per_kg": 0.0,
    "caloric_deficit": 0,
    "day_type": "<rest|moderate|intense>",
    "cycle_phase_active": false
  }}
}}
```

Respecte ce format exactement. Aucun texte en dehors des sections définies.
"""

# ---------------------------------------------------------------------------
# Energy Coach
# ---------------------------------------------------------------------------

ENERGY_COACH_PROMPT = f"""\
Tu es le Energy Coach de Resilio. Tu modélises la charge de vie totale — cognitive, professionnelle, hormonale, allostatic — et tu produis un EnergySnapshot quotidien. Tu ne prescris jamais de workouts. Ton output sert de signal d'alerte au Head Coach et au Recovery Coach.

Tu détiens un droit de veto non-overridable sur toute charge d'entraînement supplémentaire.

{_TONE_BLOCK}

## VETO NON-OVERRIDABLE

Les conditions suivantes déclenchent un veto automatique et non-négociable. Ce veto ne peut pas être annulé par le Head Coach ni par l'athlète :
- Score allostatique > 80 (sur 100)
- Niveau d'énergie auto-déclaré < 2 (sur 10)

Quand l'une de ces conditions est vraie :
- La section ## VETO est obligatoire
- `"veto": true` dans DATA
- `"veto_reason"` décrit la condition déclenchante avec les valeurs observées

## FORMAT DE SORTIE OBLIGATOIRE

## ASSESSMENT
<Analyse narrative : score allostatique, niveau d'énergie déclaré, charge cognitive estimée, disponibilité énergétique (EA), signaux de RED-S si pertinents, tendances sur 7 jours.>

## VETO
<Présent uniquement si veto actif. Condition déclenchante avec valeurs numériques. Ex : "Score allostatique 84/100. Seuil 80 dépassé.">

## RECOMMENDATION
<Si pas de veto : recommandations sur la charge de vie (sommeil, gestion du stress, nutrition énergétique). Si veto actif : protocole de décharge obligatoire.>

## DATA
```json
{{
  "recommendation": "<résumé en une phrase>",
  "veto": false,
  "veto_reason": null,
  "key_metrics": {{
    "allostatic_score": 0.0,
    "energy_level": 0,
    "cognitive_load": "<low|moderate|high>",
    "ea_status": "<optimal|low|risk>",
    "reds_risk": false
  }}
}}
```

Respecte ce format exactement. Aucun texte en dehors des sections définies.
"""

# ---------------------------------------------------------------------------
# Head Coach
# ---------------------------------------------------------------------------

HEAD_COACH_PROMPT = f"""\
Tu es le Head Coach de Resilio. Tu reçois les rapports des 5 agents spécialistes (Running, Lifting, Recovery, Energy, Nutrition) et tu produis le message final destiné à l'athlète. Tu synthétises. Tu ne génères pas de nouvelles analyses. Tu ne répètes pas les données brutes.

{_TONE_BLOCK}

## RÈGLES DE PRIORITÉ — NON-OVERRIDABLES

1. Veto actif (Recovery ou Energy) : tu communiques la restriction en premier, sans la minimiser, sans proposer de contournement, sans nuancer. Un veto est un veto.
2. ACWR > 1.5 (Running Coach) : réduction de charge obligatoire dans ton message. Pas de suggestion optionnelle.
3. Conflit Running vs Lifting : tu tranches selon les objectifs de l'athlète. Si veto actif, récupération prime sur performance.
4. Tu ne génères jamais de motivation vide. Interdit : "tu vas y arriver", "chaque pas compte", "reste focus", "tu peux le faire", tout langage d'encouragement non ancré dans des données.

## FORMAT DE SORTIE

Message concis (3–5 phrases par section), factuel, structuré. Si un veto est actif, il apparaît en premier paragraphe. Structure libre — pas de JSON requis en output final.

Exemple de structure :
- Situation actuelle (1–2 phrases : données clés de la semaine)
- Décision d'entraînement (2–3 phrases : ce que l'athlète fait cette semaine et pourquoi)
- Nutrition (1–2 phrases si pertinent)
- Point de vigilance (1 phrase si signaux d'alarme)
"""
```

- [ ] **Step 2: Run the tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/test_agents/test_prompts.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Run full test suite to check no regression**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: Same passing count as before + new tests passing.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/prompts.py
git commit -m "feat(agents): add system prompts module with 6 clinical coaching prompts"
```

---

### Task 3: Wire prompt into RunningCoach

**Files:**
- Modify: `backend/app/agents/running_coach.py`

- [ ] **Step 1: Take backup**

```bash
cp backend/app/agents/running_coach.py backend/app/agents/running_coach.py.backup
```

- [ ] **Step 2: Add import and module-level constant**

Open `backend/app/agents/running_coach.py`. After the existing imports block (after line `from ..schemas.athlete import Sport`), add:

```python
from .prompts import RUNNING_COACH_PROMPT

_SYSTEM_PROMPT = RUNNING_COACH_PROMPT
```

The file header becomes:

```python
from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.hormonal import get_running_adjustments
from ..core.periodization import get_current_phase
from ..core.readiness import compute_readiness
from ..core.running_logic import (
    compute_running_fatigue, estimate_vdot, generate_running_sessions,
)
from ..schemas.athlete import Sport
from .prompts import RUNNING_COACH_PROMPT

_SYSTEM_PROMPT = RUNNING_COACH_PROMPT
```

- [ ] **Step 3: Run full test suite**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: same count, all passing.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/running_coach.py
git commit -m "feat(agents): wire RUNNING_COACH_PROMPT into RunningCoach"
```

---

### Task 4: Wire prompt into LiftingCoach

**Files:**
- Modify: `backend/app/agents/lifting_coach.py`

- [ ] **Step 1: Take backup**

```bash
cp backend/app/agents/lifting_coach.py backend/app/agents/lifting_coach.py.backup
```

- [ ] **Step 2: Add import and constant**

After `from ..schemas.athlete import Sport`, add:

```python
from .prompts import LIFTING_COACH_PROMPT

_SYSTEM_PROMPT = LIFTING_COACH_PROMPT
```

Full header:

```python
from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.hormonal import get_lifting_adjustments
from ..core.lifting_logic import (
    compute_lifting_fatigue, estimate_strength_level, generate_lifting_sessions,
)
from ..core.periodization import get_current_phase
from ..core.readiness import compute_readiness
from ..schemas.athlete import Sport
from .prompts import LIFTING_COACH_PROMPT

_SYSTEM_PROMPT = LIFTING_COACH_PROMPT
```

- [ ] **Step 3: Run full test suite**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: all passing.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/lifting_coach.py
git commit -m "feat(agents): wire LIFTING_COACH_PROMPT into LiftingCoach"
```

---

### Task 5: Wire prompt into RecoveryCoach

**Files:**
- Modify: `backend/app/agents/recovery_coach.py`

- [ ] **Step 1: Take backup**

```bash
cp backend/app/agents/recovery_coach.py backend/app/agents/recovery_coach.py.backup
```

- [ ] **Step 2: Add import and constant**

After `from ..schemas.plan import WorkoutSlot`, add:

```python
from .prompts import RECOVERY_COACH_PROMPT

_SYSTEM_PROMPT = RECOVERY_COACH_PROMPT
```

Full header:

```python
from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.recovery_logic import compute_recovery_status
from ..schemas.athlete import Sport
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot
from .prompts import RECOVERY_COACH_PROMPT

_SYSTEM_PROMPT = RECOVERY_COACH_PROMPT

_LOW_READINESS_THRESHOLD = 0.7
```

- [ ] **Step 3: Run full test suite**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: all passing.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/recovery_coach.py
git commit -m "feat(agents): wire RECOVERY_COACH_PROMPT into RecoveryCoach"
```

---

### Task 6: Wire prompt into NutritionCoach

**Files:**
- Modify: `backend/app/agents/nutrition_coach.py`

- [ ] **Step 1: Take backup**

```bash
cp backend/app/agents/nutrition_coach.py backend/app/agents/nutrition_coach.py.backup
```

- [ ] **Step 2: Add import and constant**

After `from ..schemas.fatigue import FatigueScore`, add:

```python
from .prompts import NUTRITION_COACH_PROMPT

_SYSTEM_PROMPT = NUTRITION_COACH_PROMPT
```

Full header:

```python
from __future__ import annotations

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.hormonal import get_nutrition_adjustments
from ..core.nutrition_logic import compute_nutrition_directives
from ..schemas.fatigue import FatigueScore
from .prompts import NUTRITION_COACH_PROMPT

_SYSTEM_PROMPT = NUTRITION_COACH_PROMPT
```

- [ ] **Step 3: Run full test suite**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: all passing.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/nutrition_coach.py
git commit -m "feat(agents): wire NUTRITION_COACH_PROMPT into NutritionCoach"
```

---

### Task 7: Wire prompt into EnergyCoach

**Files:**
- Modify: `backend/app/agents/energy_coach/agent.py`

- [ ] **Step 1: Take backup**

```bash
cp backend/app/agents/energy_coach/agent.py backend/app/agents/energy_coach/agent.py.backup
```

- [ ] **Step 2: Add import and constant**

After `from ...models.athlete_state import EnergyCheckIn, EnergySnapshot, StressLevel, WorkIntensity`, add:

```python
from ..prompts import ENERGY_COACH_PROMPT

_SYSTEM_PROMPT = ENERGY_COACH_PROMPT
```

- [ ] **Step 3: Run full test suite**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: all passing.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/energy_coach/agent.py
git commit -m "feat(agents): wire ENERGY_COACH_PROMPT into EnergyCoach"
```

---

### Task 8: Wire prompt into HeadCoach

**Files:**
- Modify: `backend/app/agents/head_coach.py`

- [ ] **Step 1: Take backup**

```bash
cp backend/app/agents/head_coach.py backend/app/agents/head_coach.py.backup
```

- [ ] **Step 2: Add import and constant**

After the existing imports block (after `from ..schemas.plan import WorkoutSlot`), add:

```python
from .prompts import HEAD_COACH_PROMPT

_SYSTEM_PROMPT = HEAD_COACH_PROMPT
```

Full header:

```python
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.goal_analysis import analyze_goals
from ..core.acwr import ACWRResult, ACWRStatus, compute_acwr
from ..core.conflict import Conflict, ConflictSeverity, detect_conflicts
from ..core.fatigue import GlobalFatigue, aggregate_fatigue
from ..core.periodization import PeriodizationPhase, get_current_phase
from ..schemas.plan import WorkoutSlot
from .prompts import HEAD_COACH_PROMPT

_SYSTEM_PROMPT = HEAD_COACH_PROMPT
```

- [ ] **Step 3: Run full test suite**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q 2>&1 | tail -5
```

Expected: all passing.

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/head_coach.py
git commit -m "feat(agents): wire HEAD_COACH_PROMPT into HeadCoach"
```

---

### Task 9: Final verification

**Files:** None modified

- [ ] **Step 1: Run full test suite**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -v 2>&1 | tail -20
```

Expected: ≥1847 tests passing + new prompt tests. Zero failures.

- [ ] **Step 2: Verify prompt tests specifically**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/test_agents/test_prompts.py -v
```

Expected: All 6 constant tests + emoji tests + vocabulary tests + hard limits tests + format tests + veto tests passing.

- [ ] **Step 3: Confirm backups exist**

```bash
ls backend/app/agents/*.backup backend/app/agents/energy_coach/*.backup
```

Expected: 6 `.backup` files present.

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git status
```

If clean: done. If uncommitted changes: commit with `git add -A && git commit -m "chore(agents): final cleanup after prompt wiring"`.
