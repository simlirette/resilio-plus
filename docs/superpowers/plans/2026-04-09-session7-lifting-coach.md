# S7 — Lifting Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a full `LiftingCoachAgent` with DUP periodization, MEV/MRV hybrid enforcement, and Hevy-compatible output format.

**Architecture:** A deterministic `LiftingPrescriber` handles all DUP logic and session construction; `LiftingCoachAgent` orchestrates it and appends LLM-generated coaching notes exactly like `RunningCoachAgent`. The `/plan/lifting` route is added to the existing `api/v1/plan.py` file.

**Tech Stack:** Python 3.11, FastAPI, Anthropic SDK (`anthropic`), Pydantic v2, pytest, Poetry

---

## File Map

| File | Action |
|------|--------|
| `data/exercise_database.json` | Expand 23 → 75 exercises |
| `agents/lifting_coach/prescriber.py` | Create — deterministic LiftingPrescriber |
| `agents/lifting_coach/agent.py` | Replace S5 stub |
| `api/v1/plan.py` | Add POST /lifting route |
| `tests/test_exercise_database.py` | Add 4 new tests |
| `tests/test_lifting_prescriber.py` | Create — 6 tests |
| `tests/test_lifting_agent.py` | Create — 4 tests |
| `tests/test_plan_route.py` | Add 3 new tests |
| `CLAUDE.md` | Mark S7 done, update counts |

---

## Context for Implementers

- **Poetry path on Windows:** `/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe`
- **Run tests:** `poetry run pytest tests/ -v`
- **Run linter:** `poetry run ruff check .`
- **Current test count:** 90 (S1–S6). Target after S7: ~107.
- **Athlète de test "Simon":** `simon_agent_view_lifting` fixture in `tests/conftest.py` gives the lifting coach view dict. `simon_pydantic_state` is the full `AthleteState` Pydantic model.
- **System prompt file:** `agents/lifting_coach/system_prompt.md.txt` (note: `.txt` extension — file already exists).
- **Volume landmarks:** `data/volume_landmarks.json` — landmark muscle keys (`back_lats`, `shoulders_lateral`) differ from exercise DB muscle names (`back`, `shoulders`). The prescriber uses `_MUSCLE_ALIAS` to bridge this.
- **MRV rule:** quadriceps `mrv_hybrid` = 12 for `base_building` (multiplier 1.0). All lower body muscles have phase multipliers applied.
- **Pattern:** Follow `agents/running_coach/agent.py` exactly (prescriber → LLM → merge).

---

## Task 1: Expand exercise_database.json to 75 exercises

**Files:**
- Modify: `data/exercise_database.json`
- Modify: `tests/test_exercise_database.py`

### Step 1.1 — Write the 4 failing tests

Add to end of `tests/test_exercise_database.py`:

```python
# Alias mapping for test_all_muscles_covered
_LANDMARK_TO_DB_MUSCLE = {
    "back_lats": "back",
    "shoulders_lateral": "shoulders",
    "quadriceps": "quadriceps",
    "hamstrings": "hamstrings",
    "glutes": "glutes",
    "calves": "calves",
    "chest": "chest",
    "biceps": "biceps",
    "triceps": "triceps",
    "core": "core",
    "hip_external_rotators": "hip_external_rotators",
}


def test_exercise_db_has_75_exercises():
    """DB doit avoir >= 75 exercices après expansion S7."""
    db = load_db()
    assert len(db) >= 75, f"Expected >= 75 exercises, got {len(db)}"


def test_all_exercises_have_hevy_id():
    """Chaque exercice doit avoir hevy_exercise_id (peut être vide string mais doit exister)."""
    db = load_db()
    for ex in db:
        assert "hevy_exercise_id" in ex, f"Missing hevy_exercise_id: {ex['name']}"


def test_tier1_sfr_above_7():
    """Tous les exercices Tier 1 doivent avoir sfr_score >= 7."""
    db = load_db()
    for ex in db:
        if ex["tier"] == 1:
            assert ex["sfr_score"] >= 7, (
                f"Tier 1 exercise '{ex['name']}' has sfr_score {ex['sfr_score']} < 7"
            )


def test_all_muscles_covered():
    """Au moins 1 exercice par muscle group des volume_landmarks."""
    import json as _json
    from pathlib import Path as _Path

    landmarks_path = _Path(__file__).parent.parent / "data" / "volume_landmarks.json"
    with open(landmarks_path, encoding="utf-8") as f:
        landmarks = _json.load(f)

    db = load_db()
    db_muscles = {ex["muscle_primary"] for ex in db}

    for landmark_muscle in landmarks["muscles"]:
        db_muscle = _LANDMARK_TO_DB_MUSCLE.get(landmark_muscle, landmark_muscle)
        assert db_muscle in db_muscles, (
            f"No exercise in DB for landmark muscle '{landmark_muscle}' (maps to '{db_muscle}')"
        )
```

- [ ] **Step 1.2 — Run tests to verify they fail**

```
poetry run pytest tests/test_exercise_database.py::test_exercise_db_has_75_exercises tests/test_exercise_database.py::test_tier1_sfr_above_7 tests/test_exercise_database.py::test_all_muscles_covered -v
```

Expected: 3 FAIL (only 23 exercises, no hip_external_rotators in DB)

- [ ] **Step 1.3 — Expand data/exercise_database.json**

Replace `data/exercise_database.json` with the full 75-exercise version below. The first 23 entries are unchanged from the current file. Add the 52 new entries after the last existing entry (before the closing `]`).

**New exercises to append (52 entries):**

```json
  ,
  {
    "exercise_id": "MACHINE-CHEST-PRESS-001",
    "name": "Machine Chest Press",
    "tier": 1,
    "muscle_primary": "chest",
    "muscle_secondary": ["shoulders", "triceps"],
    "equipment": ["machines"],
    "movement_pattern": "horizontal_push",
    "sfr_score": 9,
    "form_cues_fr": [
      "Siège réglé pour alignement prise / épaules",
      "Poussée horizontale explosive, retour contrôlé 2s"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "PEC-DECK-001",
    "name": "Pec Deck",
    "tier": 1,
    "muscle_primary": "chest",
    "muscle_secondary": [],
    "equipment": ["machines"],
    "movement_pattern": "isolation_fly",
    "sfr_score": 9,
    "form_cues_fr": [
      "Étirement complet en position ouverte",
      "Contraction au centre — pause 1s"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DB-BENCH-PRESS-001",
    "name": "Dumbbell Bench Press",
    "tier": 2,
    "muscle_primary": "chest",
    "muscle_secondary": ["shoulders", "triceps"],
    "equipment": ["dumbbells", "bench"],
    "movement_pattern": "horizontal_push",
    "sfr_score": 7,
    "form_cues_fr": [
      "Haltères dans l'axe des nipples",
      "Étirement pectoral complet en bas"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "BARBELL-INCLINE-PRESS-001",
    "name": "Barbell Incline Press",
    "tier": 3,
    "muscle_primary": "chest",
    "muscle_secondary": ["shoulders", "triceps"],
    "equipment": ["barbell", "bench"],
    "movement_pattern": "horizontal_push",
    "sfr_score": 6,
    "form_cues_fr": [
      "Banc à 30° max — protège les épaules",
      "Barre descend vers le haut de la poitrine"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DB-FLY-FLAT-001",
    "name": "Dumbbell Fly (Flat)",
    "tier": 1,
    "muscle_primary": "chest",
    "muscle_secondary": [],
    "equipment": ["dumbbells", "bench"],
    "movement_pattern": "isolation_fly",
    "sfr_score": 9,
    "form_cues_fr": [
      "Légère flexion coudes fixe (15°)",
      "Étirement maximum — ne pas dépasser le plan du banc"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "MACHINE-ROW-001",
    "name": "Machine Row",
    "tier": 1,
    "muscle_primary": "back",
    "muscle_secondary": ["biceps"],
    "equipment": ["machines"],
    "movement_pattern": "horizontal_pull",
    "sfr_score": 9,
    "form_cues_fr": [
      "Tire vers le bas du sternum",
      "Pause 1s en contraction maximale"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DB-ROW-001",
    "name": "Dumbbell Row",
    "tier": 2,
    "muscle_primary": "back",
    "muscle_secondary": ["biceps", "rear_delts"],
    "equipment": ["dumbbells"],
    "movement_pattern": "horizontal_pull",
    "sfr_score": 7,
    "form_cues_fr": [
      "Genou et main sur banc — dos plat",
      "Tire coude vers le plafond"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CHEST-SUPPORTED-ROW-001",
    "name": "Chest-Supported Row",
    "tier": 2,
    "muscle_primary": "back",
    "muscle_secondary": ["biceps", "rear_delts"],
    "equipment": ["dumbbells", "bench"],
    "movement_pattern": "horizontal_pull",
    "sfr_score": 7,
    "form_cues_fr": [
      "Poitrine contre banc incliné — élimine la triche",
      "Omoplates serrées en fin de mouvement"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "T-BAR-ROW-001",
    "name": "T-Bar Row",
    "tier": 3,
    "muscle_primary": "back",
    "muscle_secondary": ["biceps", "forearms"],
    "equipment": ["barbell"],
    "movement_pattern": "horizontal_pull",
    "sfr_score": 6,
    "form_cues_fr": [
      "Buste à 45°, dos plat tout au long",
      "Prise neutre — tire vers le nombril"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DB-LATERAL-RAISE-001",
    "name": "DB Lateral Raise",
    "tier": 2,
    "muscle_primary": "shoulders",
    "muscle_secondary": [],
    "equipment": ["dumbbells"],
    "movement_pattern": "isolation_raise",
    "sfr_score": 7,
    "form_cues_fr": [
      "Légère flexion du coude (15°)",
      "Monte jusqu'à parallèle — pas plus"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DB-OVERHEAD-PRESS-001",
    "name": "DB Overhead Press",
    "tier": 2,
    "muscle_primary": "shoulders",
    "muscle_secondary": ["triceps"],
    "equipment": ["dumbbells"],
    "movement_pattern": "vertical_push",
    "sfr_score": 7,
    "form_cues_fr": [
      "Descends haltères jusqu'à hauteur d'oreilles",
      "Extension complète sans bloquer les coudes"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "BARBELL-OHP-001",
    "name": "Barbell Overhead Press",
    "tier": 3,
    "muscle_primary": "shoulders",
    "muscle_secondary": ["triceps", "core"],
    "equipment": ["barbell"],
    "movement_pattern": "vertical_push",
    "sfr_score": 6,
    "form_cues_fr": [
      "Gainage abdominal strict — éviter extension lombaire",
      "Tête en arrière à la montée, pas de balancement"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "MACHINE-SHOULDER-PRESS-001",
    "name": "Machine Shoulder Press",
    "tier": 1,
    "muscle_primary": "shoulders",
    "muscle_secondary": ["triceps"],
    "equipment": ["machines"],
    "movement_pattern": "vertical_push",
    "sfr_score": 9,
    "form_cues_fr": [
      "Siège réglé — coudes à 90° en bas",
      "Pression régulière, retour contrôlé"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "REVERSE-FLY-MACHINE-001",
    "name": "Reverse Fly Machine",
    "tier": 1,
    "muscle_primary": "shoulders",
    "muscle_secondary": ["rear_delts"],
    "equipment": ["machines"],
    "movement_pattern": "isolation_fly",
    "sfr_score": 9,
    "form_cues_fr": [
      "Bras tendus — coudes légèrement fléchis",
      "Pince les omoplates en fin de mouvement"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "MACHINE-PREACHER-CURL-001",
    "name": "Machine Preacher Curl",
    "tier": 1,
    "muscle_primary": "biceps",
    "muscle_secondary": [],
    "equipment": ["machines"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 9,
    "form_cues_fr": [
      "Étirement complet en bas — ne pas verrouiller",
      "Contraction maximale en haut, pause 1s"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CABLE-CURL-001",
    "name": "Cable Curl",
    "tier": 1,
    "muscle_primary": "biceps",
    "muscle_secondary": [],
    "equipment": ["cables"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 9,
    "form_cues_fr": [
      "Tension constante grâce au câble",
      "Coudes fixes au corps"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "BARBELL-CURL-001",
    "name": "Barbell Curl",
    "tier": 2,
    "muscle_primary": "biceps",
    "muscle_secondary": ["forearms"],
    "equipment": ["barbell"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 7,
    "form_cues_fr": [
      "Coudes fixes — pas d'élan",
      "Descente complète et contrôlée 2s"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DB-HAMMER-CURL-001",
    "name": "DB Hammer Curl",
    "tier": 2,
    "muscle_primary": "biceps",
    "muscle_secondary": ["brachialis", "forearms"],
    "equipment": ["dumbbells"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 7,
    "form_cues_fr": [
      "Prise neutre (pouce en haut)",
      "Coudes fixes au corps tout au long"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "BAYESIAN-CABLE-CURL-001",
    "name": "Bayesian Cable Curl",
    "tier": 1,
    "muscle_primary": "biceps",
    "muscle_secondary": [],
    "equipment": ["cables"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 9,
    "form_cues_fr": [
      "Cable derrière le corps — maximise l'étirement du chef long",
      "Coude légèrement en arrière de la hanche"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "EZ-BAR-CURL-001",
    "name": "EZ Bar Curl",
    "tier": 2,
    "muscle_primary": "biceps",
    "muscle_secondary": ["forearms"],
    "equipment": ["barbell"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 7,
    "form_cues_fr": [
      "Prise semi-supine — réduit le stress au poignet",
      "Amplitude complète, descente contrôlée"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DB-SKULL-CRUSHER-001",
    "name": "DB Skull Crusher",
    "tier": 2,
    "muscle_primary": "triceps",
    "muscle_secondary": [],
    "equipment": ["dumbbells", "bench"],
    "movement_pattern": "isolation_extension",
    "sfr_score": 7,
    "form_cues_fr": [
      "Haltères descendent vers les tempes (pas vers le front)",
      "Coudes pointent vers le plafond — fixes"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CLOSE-GRIP-BP-001",
    "name": "Close-Grip Bench Press",
    "tier": 3,
    "muscle_primary": "triceps",
    "muscle_secondary": ["chest", "shoulders"],
    "equipment": ["barbell", "bench"],
    "movement_pattern": "horizontal_push",
    "sfr_score": 6,
    "form_cues_fr": [
      "Prise légèrement plus étroite que les épaules",
      "Descend vers le bas du sternum"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "MACHINE-TRICEP-DIP-001",
    "name": "Machine Tricep Dip",
    "tier": 1,
    "muscle_primary": "triceps",
    "muscle_secondary": [],
    "equipment": ["machines"],
    "movement_pattern": "isolation_extension",
    "sfr_score": 9,
    "form_cues_fr": [
      "Corps vertical — focus triceps",
      "Extension complète en bas"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "ROPE-PUSHDOWN-001",
    "name": "Rope Tricep Pushdown",
    "tier": 1,
    "muscle_primary": "triceps",
    "muscle_secondary": [],
    "equipment": ["cables"],
    "movement_pattern": "isolation_extension",
    "sfr_score": 9,
    "form_cues_fr": [
      "Écarter la corde en bas — maximise la contraction",
      "Coudes fixes au corps"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "LEG-EXTENSION-001",
    "name": "Leg Extension",
    "tier": 1,
    "muscle_primary": "quadriceps",
    "muscle_secondary": [],
    "equipment": ["machines"],
    "movement_pattern": "isolation_extension",
    "sfr_score": 9,
    "form_cues_fr": [
      "Extension complète — pause 1s en haut",
      "Descente contrôlée 2s"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "WALKING-LUNGES-001",
    "name": "Walking Lunges",
    "tier": 2,
    "muscle_primary": "quadriceps",
    "muscle_secondary": ["glutes", "hamstrings"],
    "equipment": ["dumbbells"],
    "movement_pattern": "lunge",
    "sfr_score": 7,
    "form_cues_fr": [
      "Pas large, genou avant au-dessus du pied",
      "Torse vertical tout au long"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "BARBELL-FRONT-SQUAT-001",
    "name": "Barbell Front Squat",
    "tier": 3,
    "muscle_primary": "quadriceps",
    "muscle_secondary": ["glutes", "core"],
    "equipment": ["barbell"],
    "movement_pattern": "squat",
    "sfr_score": 5,
    "form_cues_fr": [
      "Barre sur les épaules — coudes hauts",
      "Descente verticale — charge CNS très élevée"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "GOBLET-SQUAT-001",
    "name": "Goblet Squat",
    "tier": 2,
    "muscle_primary": "quadriceps",
    "muscle_secondary": ["glutes", "core"],
    "equipment": ["dumbbells"],
    "movement_pattern": "squat",
    "sfr_score": 8,
    "form_cues_fr": [
      "Haltère tenu contre la poitrine",
      "Descente profonde — coudes poussent les genoux vers l'extérieur"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "LYING-LEG-CURL-001",
    "name": "Lying Leg Curl",
    "tier": 1,
    "muscle_primary": "hamstrings",
    "muscle_secondary": [],
    "equipment": ["machines"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 9,
    "form_cues_fr": [
      "Hanches plaquées contre la machine",
      "Contraction maximale en haut, étirement complet en bas"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "NORDIC-CURL-001",
    "name": "Nordic Curl",
    "tier": 2,
    "muscle_primary": "hamstrings",
    "muscle_secondary": ["glutes"],
    "equipment": ["machines", "bench"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 7,
    "form_cues_fr": [
      "Descente contrôlée au maximum — utiliser les mains pour remonter si nécessaire",
      "Excellent pour prévention des ischio-jambiers chez les coureurs"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "RDL-BARBELL-001",
    "name": "Romanian Deadlift (Barbell)",
    "tier": 3,
    "muscle_primary": "hamstrings",
    "muscle_secondary": ["glutes", "lower_back"],
    "equipment": ["barbell"],
    "movement_pattern": "hinge",
    "sfr_score": 6,
    "form_cues_fr": [
      "Barre près du corps — jambes légèrement fléchies",
      "Dos plat — arrêt dès que dos arrondit"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "SUMO-DEADLIFT-001",
    "name": "Sumo Deadlift",
    "tier": 3,
    "muscle_primary": "hamstrings",
    "muscle_secondary": ["glutes", "quadriceps", "back"],
    "equipment": ["barbell"],
    "movement_pattern": "hinge",
    "sfr_score": 6,
    "form_cues_fr": [
      "Écartement large — orteils à 45°",
      "Pousse le sol, tirelles la barre verticalement"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "HIP-THRUST-MACHINE-001",
    "name": "Hip Thrust (Machine)",
    "tier": 1,
    "muscle_primary": "glutes",
    "muscle_secondary": ["hamstrings"],
    "equipment": ["machines"],
    "movement_pattern": "isolation_push",
    "sfr_score": 9,
    "form_cues_fr": [
      "Extension complète des hanches en haut",
      "Contraction maximale des fessiers — pause 1s"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "HIP-THRUST-BARBELL-001",
    "name": "Hip Thrust (Barbell)",
    "tier": 2,
    "muscle_primary": "glutes",
    "muscle_secondary": ["hamstrings"],
    "equipment": ["barbell", "bench"],
    "movement_pattern": "isolation_push",
    "sfr_score": 7,
    "form_cues_fr": [
      "Barre sur les hanches, serviette pour confort",
      "Extension complète — pas d'hyperextension lombaire"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CABLE-KICKBACK-001",
    "name": "Cable Kickback",
    "tier": 1,
    "muscle_primary": "glutes",
    "muscle_secondary": ["hamstrings"],
    "equipment": ["cables"],
    "movement_pattern": "isolation_push",
    "sfr_score": 9,
    "form_cues_fr": [
      "Extension de hanche — pas de rotation du torse",
      "Contraction à l'apex — pause 1s"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "ABDUCTOR-MACHINE-001",
    "name": "Abductor Machine",
    "tier": 1,
    "muscle_primary": "glutes",
    "muscle_secondary": ["hip_external_rotators"],
    "equipment": ["machines"],
    "movement_pattern": "isolation_raise",
    "sfr_score": 9,
    "form_cues_fr": [
      "Pousse vers l'extérieur — amplitude complète",
      "Retour contrôlé — ne pas laisser peser"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "STEP-UP-001",
    "name": "Step-Up",
    "tier": 2,
    "muscle_primary": "glutes",
    "muscle_secondary": ["quadriceps", "hamstrings"],
    "equipment": ["dumbbells", "bench"],
    "movement_pattern": "lunge",
    "sfr_score": 7,
    "form_cues_fr": [
      "Pied entier sur le banc",
      "Pousse sur le talon du pied avant"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CABLE-PULL-THROUGH-001",
    "name": "Cable Pull-Through",
    "tier": 1,
    "muscle_primary": "glutes",
    "muscle_secondary": ["hamstrings"],
    "equipment": ["cables"],
    "movement_pattern": "hinge",
    "sfr_score": 8,
    "form_cues_fr": [
      "Cable entre les jambes — extension de hanche explosive",
      "Peu de fatigue CNS — idéal pour accumulation volume"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "SEATED-CALF-RAISE-001",
    "name": "Seated Calf Raise",
    "tier": 1,
    "muscle_primary": "calves",
    "muscle_secondary": [],
    "equipment": ["machines"],
    "movement_pattern": "isolation_raise",
    "sfr_score": 9,
    "form_cues_fr": [
      "Cible le soléaire (chef profond)",
      "Étirement complet en bas — pause 1s en haut"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CALF-PRESS-LEG-PRESS-001",
    "name": "Calf Press (Leg Press)",
    "tier": 1,
    "muscle_primary": "calves",
    "muscle_secondary": [],
    "equipment": ["machines"],
    "movement_pattern": "isolation_raise",
    "sfr_score": 9,
    "form_cues_fr": [
      "Orteils au bord de la plateforme",
      "Amplitude maximale — étirement complet en bas"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "STANDING-CALF-RAISE-DB-001",
    "name": "Standing Calf Raise (Dumbbell)",
    "tier": 2,
    "muscle_primary": "calves",
    "muscle_secondary": [],
    "equipment": ["dumbbells"],
    "movement_pattern": "isolation_raise",
    "sfr_score": 7,
    "form_cues_fr": [
      "Orteils sur step pour amplitude maximale",
      "Montée explosive, descente contrôlée 3s"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "STANDING-CALF-RAISE-BB-001",
    "name": "Standing Calf Raise (Barbell)",
    "tier": 3,
    "muscle_primary": "calves",
    "muscle_secondary": [],
    "equipment": ["barbell"],
    "movement_pattern": "isolation_raise",
    "sfr_score": 5,
    "form_cues_fr": [
      "Barre sur les trapèzes",
      "Étirement complet en bas — amplitude >90°"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CABLE-CRUNCH-001",
    "name": "Cable Crunch",
    "tier": 2,
    "muscle_primary": "core",
    "muscle_secondary": [],
    "equipment": ["cables"],
    "movement_pattern": "core",
    "sfr_score": 7,
    "form_cues_fr": [
      "Flexion du tronc — ne pas tirer avec le cou",
      "Contraction maximale en bas"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "HANGING-LEG-RAISE-001",
    "name": "Hanging Leg Raise",
    "tier": 2,
    "muscle_primary": "core",
    "muscle_secondary": ["hip_flexors"],
    "equipment": ["pull_up_bar"],
    "movement_pattern": "core",
    "sfr_score": 7,
    "form_cues_fr": [
      "Pas de balancement — initier avec le bas du ventre",
      "Descente contrôlée"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DEAD-BUG-001",
    "name": "Dead Bug",
    "tier": 1,
    "muscle_primary": "core",
    "muscle_secondary": [],
    "equipment": [],
    "movement_pattern": "core",
    "sfr_score": 9,
    "form_cues_fr": [
      "Bas du dos plaqué au sol en permanence",
      "Extension bras / jambe opposés simultanément"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "PALLOF-PRESS-001",
    "name": "Pallof Press",
    "tier": 1,
    "muscle_primary": "core",
    "muscle_secondary": ["shoulders"],
    "equipment": ["cables"],
    "movement_pattern": "core",
    "sfr_score": 9,
    "form_cues_fr": [
      "Anti-rotation — résiste à la traction latérale",
      "Extension bras lente, retour contrôlé"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "PLANK-001",
    "name": "Plank",
    "tier": 1,
    "muscle_primary": "core",
    "muscle_secondary": ["shoulders"],
    "equipment": [],
    "movement_pattern": "core",
    "sfr_score": 8,
    "form_cues_fr": [
      "Corps en ligne droite — hanches ni hautes ni basses",
      "Temps de tenue progressif semaine après semaine"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "SIDE-PLANK-001",
    "name": "Side Plank",
    "tier": 1,
    "muscle_primary": "core",
    "muscle_secondary": ["hip_external_rotators"],
    "equipment": [],
    "movement_pattern": "core",
    "sfr_score": 8,
    "form_cues_fr": [
      "Hanche haute — ne pas laisser tomber",
      "Renforce l'abduction et la stabilité latérale"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CLAMSHELL-001",
    "name": "Clamshell",
    "tier": 1,
    "muscle_primary": "hip_external_rotators",
    "muscle_secondary": ["glutes"],
    "equipment": [],
    "movement_pattern": "prevention",
    "sfr_score": 9,
    "form_cues_fr": [
      "Sur le côté, hanches empilées",
      "Ouvre les genoux comme une palourde — amplitude maximale"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "SIDE-LYING-ABDUCTION-001",
    "name": "Side-lying Hip Abduction",
    "tier": 1,
    "muscle_primary": "hip_external_rotators",
    "muscle_secondary": ["glutes"],
    "equipment": [],
    "movement_pattern": "prevention",
    "sfr_score": 9,
    "form_cues_fr": [
      "Jambe tendue, légère rotation externe",
      "Monte jusqu'à 45° — contraction au sommet"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "BANDED-HIP-EXT-ROT-001",
    "name": "Banded Hip External Rotation",
    "tier": 1,
    "muscle_primary": "hip_external_rotators",
    "muscle_secondary": ["glutes"],
    "equipment": ["resistance_band"],
    "movement_pattern": "prevention",
    "sfr_score": 9,
    "form_cues_fr": [
      "Élastique autour des genoux",
      "Pousse les genoux vers l'extérieur contre la résistance"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "REAR-DELT-FLY-MACHINE-001",
    "name": "Rear Delt Fly Machine",
    "tier": 1,
    "muscle_primary": "shoulders",
    "muscle_secondary": ["rear_delts"],
    "equipment": ["machines"],
    "movement_pattern": "isolation_fly",
    "sfr_score": 9,
    "form_cues_fr": [
      "Bras tendus — ouverture derrière le plan du corps",
      "Pince les omoplates en fin de mouvement"
    ],
    "hevy_exercise_id": ""
  }
```

- [ ] **Step 1.4 — Run tests to verify they pass**

```
poetry run pytest tests/test_exercise_database.py -v
```

Expected: all 12 tests PASS (8 existing + 4 new)

- [ ] **Step 1.5 — Lint**

```
poetry run ruff check .
```

Expected: no errors

- [ ] **Step 1.6 — Commit**

```bash
git add data/exercise_database.json tests/test_exercise_database.py
git commit -m "feat: expand exercise_database.json 23 → 75 exercises (S7)"
```

---

## Task 2: LiftingPrescriber — deterministic DUP prescription

**Files:**
- Create: `agents/lifting_coach/prescriber.py`
- Create: `tests/test_lifting_prescriber.py`

### Step 2.1 — Write the 6 failing tests

Create `tests/test_lifting_prescriber.py`:

```python
"""
Tests pour agents/lifting_coach/prescriber.py — DUP, MRV, Hevy format.
Aucun appel LLM ici — prescripteur 100% déterministe.
"""


def test_select_session_types_3x_week():
    """3 sessions/semaine → ['upper_a', 'lower', 'upper_b']."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    p = LiftingPrescriber()
    result = p._get_session_types(sessions_per_week=3, week=1)
    assert result == ["upper_a", "lower", "upper_b"]


def test_dup_base_building_upper_a(simon_agent_view_lifting):
    """Phase base_building, Upper A → 3 séries normales, reps <= 12, RPE 8."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    plan = LiftingPrescriber().build_week_plan(simon_agent_view_lifting)
    upper_a_sessions = [
        s for s in plan["sessions"] if s["hevy_workout"]["type"] == "upper_a"
    ]
    assert len(upper_a_sessions) >= 1, "Aucune session upper_a trouvée"
    for ex in upper_a_sessions[0]["hevy_workout"]["exercises"]:
        normal_sets = [s for s in ex["sets"] if s["type"] == "normal"]
        assert len(normal_sets) == 3, (
            f"Expected 3 normal sets for {ex['name']}, got {len(normal_sets)}"
        )
        for s in normal_sets:
            assert s["rpe"] == 8, f"Expected RPE 8, got {s['rpe']} for {ex['name']}"
            assert s["reps"] <= 12, f"Expected reps <= 12, got {s['reps']}"


def test_cns_blocks_tier3(simon_agent_view_lifting):
    """cns_load_7day_avg > 65 → aucun exercice Tier 3 dans le plan."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    view = dict(simon_agent_view_lifting)
    view["fatigue"] = {**view["fatigue"], "cns_load_7day_avg": 70}
    plan = LiftingPrescriber().build_week_plan(view)

    for session in plan["sessions"]:
        for ex in session["hevy_workout"]["exercises"]:
            assert ex["tier"] != 3, (
                f"Tier 3 exercice '{ex['name']}' trouvé malgré CNS overload (70 > 65)"
            )


def test_mrv_hybrid_enforced(simon_agent_view_lifting):
    """Volume total quadriceps sur la semaine <= mrv_hybrid (12 en base_building)."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    plan = LiftingPrescriber().build_week_plan(simon_agent_view_lifting)
    total_quad_sets = 0
    for session in plan["sessions"]:
        for ex in session["hevy_workout"]["exercises"]:
            if ex["muscle_primary"] == "quadriceps":
                total_quad_sets += sum(
                    1 for s in ex["sets"] if s["type"] == "normal"
                )
    # base_building: mrv_hybrid = 12, lower_body_mrv_multiplier = 1.0 → MRV = 12
    assert total_quad_sets <= 12, (
        f"Total quad sets {total_quad_sets} exceeds mrv_hybrid 12"
    )


def test_deload_reduces_volume(simon_agent_view_lifting):
    """Semaine de deload (week % 4 == 0) → total_sets <= 65% de la semaine normale."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    p = LiftingPrescriber()
    normal_plan = p.build_week_plan(simon_agent_view_lifting)

    deload_view = {
        **simon_agent_view_lifting,
        "current_phase": {**simon_agent_view_lifting["current_phase"], "mesocycle_week": 4},
    }
    deload_plan = p.build_week_plan(deload_view)

    def count_normal_sets(plan: dict) -> int:
        return sum(
            1
            for session in plan["sessions"]
            for ex in session["hevy_workout"]["exercises"]
            for s in ex["sets"]
            if s["type"] == "normal"
        )

    normal_sets = count_normal_sets(normal_plan)
    deload_sets = count_normal_sets(deload_plan)
    assert deload_sets <= normal_sets * 0.65, (
        f"Deload sets {deload_sets} > 65% of normal sets {normal_sets}"
    )


def test_build_week_plan_hevy_format(simon_agent_view_lifting):
    """Chaque session a hevy_workout.id, .exercises[], .exercises[].sets[], weight_kg=null."""
    from agents.lifting_coach.prescriber import LiftingPrescriber

    plan = LiftingPrescriber().build_week_plan(simon_agent_view_lifting)
    assert "sessions" in plan
    assert len(plan["sessions"]) >= 1

    for session in plan["sessions"]:
        assert "hevy_workout" in session
        hw = session["hevy_workout"]
        assert "id" in hw, "hevy_workout missing 'id'"
        assert "exercises" in hw, "hevy_workout missing 'exercises'"
        assert len(hw["exercises"]) >= 1

        for ex in hw["exercises"]:
            assert "sets" in ex, f"Exercise '{ex.get('name')}' missing 'sets'"
            assert len(ex["sets"]) >= 1
            for s in ex["sets"]:
                assert "weight_kg" in s
                assert s["weight_kg"] is None, (
                    f"weight_kg should be null (auto-regulation), got {s['weight_kg']}"
                )
```

- [ ] **Step 2.2 — Run tests to verify they fail**

```
poetry run pytest tests/test_lifting_prescriber.py -v
```

Expected: all 6 FAIL with `ImportError: cannot import name 'LiftingPrescriber'`

- [ ] **Step 2.3 — Implement agents/lifting_coach/prescriber.py**

Create `agents/lifting_coach/prescriber.py` with the full content below:

```python
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

# Alias: volume_landmarks key → exercise DB muscle_primary
_MUSCLE_ALIAS: dict[str, str] = {
    "back_lats": "back",
    "shoulders_lateral": "shoulders",
}

_LOWER_MUSCLES = {"quadriceps", "hamstrings", "glutes", "calves"}

# DUP configuration: phase → session_type → {focus, n_sets, rep_min, rep_max, rpe, rir, rest_sec}
_DUP_CONFIG: dict[str, dict[str, dict]] = {
    "base_building": {
        "upper_a": {"focus": "hypertrophy", "n_sets": 3, "rep_min": 10, "rep_max": 12, "rpe": 8, "rir": 2, "rest_sec": 120},
        "upper_b": {"focus": "strength",    "n_sets": 4, "rep_min": 6,  "rep_max": 8,  "rpe": 8, "rir": 2, "rest_sec": 210},
        "lower":   {"focus": "mixed",       "n_sets": 3, "rep_min": 10, "rep_max": 12, "rpe": 7, "rir": 2, "rest_sec": 120},
    },
    "build": {
        "upper_a": {"focus": "strength",    "n_sets": 4, "rep_min": 5,  "rep_max": 7,  "rpe": 8, "rir": 1, "rest_sec": 210},
        "upper_b": {"focus": "power",       "n_sets": 5, "rep_min": 3,  "rep_max": 5,  "rpe": 8, "rir": 2, "rest_sec": 240},
        "lower":   {"focus": "hypertrophy", "n_sets": 3, "rep_min": 10, "rep_max": 12, "rpe": 8, "rir": 2, "rest_sec": 120},
    },
    "peak": {
        "upper_a": {"focus": "maintenance", "n_sets": 2, "rep_min": 8, "rep_max": 10, "rpe": 7, "rir": 3, "rest_sec": 90},
        "upper_b": {"focus": "maintenance", "n_sets": 2, "rep_min": 8, "rep_max": 10, "rpe": 7, "rir": 3, "rest_sec": 90},
        "lower":   {"focus": "maintenance", "n_sets": 2, "rep_min": 8, "rep_max": 10, "rpe": 7, "rir": 3, "rest_sec": 90},
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
# preferred_tier = None → pick best available by SFR
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
        ("quadriceps",          2,    True),
        ("quadriceps",          1,    False),
        ("hamstrings",          1,    False),
        ("hamstrings",          2,    True),
        ("glutes",              1,    False),
        ("calves",              1,    False),
        ("hip_external_rotators", 1,  False),
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
        landmark_key = _MUSCLE_ALIAS.get(muscle, muscle)
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

        effective_allow_tier3 = allow_tier3 and not acwr_caution and not acwr_danger and not is_deload

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
                    "Double progression : garder même poids jusqu'à haut de la plage RIR 2, puis +2.5kg"
                )
            else:
                progression_note = (
                    "Progression par répétitions : ajouter 1-2 reps/semaine jusqu'à limite haute de la plage"
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
```

- [ ] **Step 2.4 — Run tests to verify they pass**

```
poetry run pytest tests/test_lifting_prescriber.py -v
```

Expected: all 6 PASS

- [ ] **Step 2.5 — Run full test suite (must not break existing tests)**

```
poetry run pytest tests/ -v
```

Expected: 96 PASS (90 existing + 6 new)

- [ ] **Step 2.6 — Lint**

```
poetry run ruff check .
```

Expected: no errors

- [ ] **Step 2.7 — Commit**

```bash
git add agents/lifting_coach/prescriber.py tests/test_lifting_prescriber.py
git commit -m "feat: implement LiftingPrescriber — DUP, MRV hybrid, Hevy format (S7)"
```

---

## Task 3: LiftingCoachAgent — replace stub with LLM coaching_notes

**Files:**
- Modify: `agents/lifting_coach/agent.py`
- Create: `tests/test_lifting_agent.py`

### Step 3.1 — Write the 4 failing tests

Create `tests/test_lifting_agent.py`:

```python
"""
Tests pour agents/lifting_coach/agent.py — orchestration prescriber + LLM.
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
    from agents.lifting_coach.agent import LiftingCoachAgent

    mock_msg = _make_mock_message("- Note technique 1.\n- Note technique 2.")

    with patch("agents.lifting_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        agent = LiftingCoachAgent()
        plan = agent.run(simon_pydantic_state)

    assert isinstance(plan, dict)
    assert "sessions" in plan
    assert len(plan["sessions"]) > 0
    assert "coaching_notes" in plan
    assert isinstance(plan["coaching_notes"], list)


def test_output_schema_valid(simon_pydantic_state):
    """Chaque session a hevy_workout.id, .exercises, et .exercises[].sets."""
    from agents.lifting_coach.agent import LiftingCoachAgent

    mock_msg = _make_mock_message("- Note.")

    with patch("agents.lifting_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        plan = LiftingCoachAgent().run(simon_pydantic_state)

    for session in plan["sessions"]:
        hw = session["hevy_workout"]
        assert "id" in hw, f"Session manque 'id': {hw}"
        assert "exercises" in hw, f"Session manque 'exercises': {hw}"
        for ex in hw["exercises"]:
            assert "sets" in ex, f"Exercise manque 'sets': {ex}"


def test_coaching_notes_merged(simon_pydantic_state):
    """Les coaching_notes du LLM sont parsées (sans tirets) et incluses dans le plan."""
    from agents.lifting_coach.agent import LiftingCoachAgent

    mock_msg = _make_mock_message(
        "- Réduire le volume quadriceps.\n- Prioriser le RIR 2 sur le développé.\n- Core activé."
    )

    with patch("agents.lifting_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        plan = LiftingCoachAgent().run(simon_pydantic_state)

    notes = plan["coaching_notes"]
    assert isinstance(notes, list)
    assert len(notes) >= 1
    assert all(not note.startswith("-") for note in notes), (
        "Les tirets Markdown doivent être retirés du parsing"
    )


def test_llm_error_returns_empty_notes(simon_pydantic_state):
    """Si le LLM lève une exception, coaching_notes = [] (plan toujours retourné)."""
    from agents.lifting_coach.agent import LiftingCoachAgent

    with patch("agents.lifting_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API overloaded")
        mock_cls.return_value = mock_client

        plan = LiftingCoachAgent().run(simon_pydantic_state)

    assert "sessions" in plan
    assert plan["coaching_notes"] == []
```

- [ ] **Step 3.2 — Run tests to verify they fail**

```
poetry run pytest tests/test_lifting_agent.py -v
```

Expected: 4 FAIL — the stub `agent.py` returns wrong schema (no `hevy_workout`, no `coaching_notes`)

- [ ] **Step 3.3 — Replace agents/lifting_coach/agent.py**

Replace the full contents of `agents/lifting_coach/agent.py`:

```python
"""
Lifting Coach Agent — agents/lifting_coach/agent.py
Orchestre LiftingPrescriber (déterministe) + Anthropic LLM (coaching_notes).
S7 : remplace le stub S5.
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.lifting_coach.prescriber import LiftingPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md.txt").read_text()


class LiftingCoachAgent(BaseAgent):
    """Lifting Coach — prescription DUP + notes qualitatives via LLM."""

    agent_type = AgentType.lifting_coach

    def __init__(self) -> None:
        self._prescriber = LiftingPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        plan = self._prescriber.build_week_plan(view)
        plan["coaching_notes"] = self._get_coaching_notes(view, plan)
        return plan

    def _get_coaching_notes(self, view: dict, plan: dict) -> list[str]:
        """Appel LLM Anthropic pour notes qualitatives. Fallback = [] si exception."""
        user_content = (
            f"Génère 3-5 coaching_notes techniques CONCISES pour ce plan de musculation :\n"
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
            lines = [
                line.strip().lstrip("-•*").strip()
                for line in text.split("\n")
                if line.strip()
            ]
            return [line for line in lines if line][:5]
        except Exception:
            return []
```

- [ ] **Step 3.4 — Run tests to verify they pass**

```
poetry run pytest tests/test_lifting_agent.py -v
```

Expected: all 4 PASS

- [ ] **Step 3.5 — Run full test suite**

```
poetry run pytest tests/ -v
```

Expected: 100 PASS (96 + 4 new)

- [ ] **Step 3.6 — Lint**

```
poetry run ruff check .
```

Expected: no errors

- [ ] **Step 3.7 — Commit**

```bash
git add agents/lifting_coach/agent.py tests/test_lifting_agent.py
git commit -m "feat: implement LiftingCoachAgent — replace S5 stub with DUP + LLM (S7)"
```

---

## Task 4: POST /api/v1/plan/lifting route

**Files:**
- Modify: `api/v1/plan.py`
- Modify: `tests/test_plan_route.py`

### Step 4.1 — Write the 3 failing tests

Add to end of `tests/test_plan_route.py`:

```python
_MOCK_LIFTING_PLAN = {
    "agent": "lifting_coach",
    "week": 3,
    "phase": "base_building",
    "dup_model": "DUP 3-way (Hypertrophie / Force / Mixte)",
    "cns_tier3_allowed": True,
    "coaching_notes": ["Note de test."],
    "sessions": [],
}


def test_post_lifting_plan_returns_200(simon_pydantic_state):
    """POST /api/v1/plan/lifting avec payload valide → 200 + plan JSON."""
    from api.main import app

    client = TestClient(app)

    with patch("api.v1.plan.LiftingCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = _MOCK_LIFTING_PLAN
        mock_cls.return_value = mock_agent

        response = client.post(
            "/api/v1/plan/lifting",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "lifting_coach"
    assert "sessions" in data


def test_post_lifting_plan_invalid_body():
    """POST avec athlete_state invalide → 422 Unprocessable Entity."""
    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/plan/lifting",
        json={"athlete_state": {"invalid_field": "bad_data"}},
    )

    assert response.status_code == 422


def test_post_lifting_plan_agent_receives_state(simon_pydantic_state):
    """Le body transmis à LiftingCoachAgent.run() est bien un AthleteState valide."""
    from api.main import app
    from models.athlete_state import AthleteState

    client = TestClient(app)
    received_states: list = []

    def capture_run(state):
        received_states.append(state)
        return _MOCK_LIFTING_PLAN

    with patch("api.v1.plan.LiftingCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.side_effect = capture_run
        mock_cls.return_value = mock_agent

        client.post(
            "/api/v1/plan/lifting",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert len(received_states) == 1
    assert isinstance(received_states[0], AthleteState)
```

- [ ] **Step 4.2 — Run tests to verify they fail**

```
poetry run pytest tests/test_plan_route.py::test_post_lifting_plan_returns_200 tests/test_plan_route.py::test_post_lifting_plan_invalid_body tests/test_plan_route.py::test_post_lifting_plan_agent_receives_state -v
```

Expected: 3 FAIL with 404 (route not found)

- [ ] **Step 4.3 — Modify api/v1/plan.py**

Replace the full contents of `api/v1/plan.py`:

```python
"""
Plan routes — api/v1/plan.py
POST /plan/running : plan de course hebdomadaire Runna/Garmin-compatible.
POST /plan/lifting : plan de musculation hebdomadaire Hevy-compatible.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.lifting_coach.agent import LiftingCoachAgent
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
```

- [ ] **Step 4.4 — Run tests to verify they pass**

```
poetry run pytest tests/test_plan_route.py -v
```

Expected: all 6 PASS (3 existing + 3 new)

- [ ] **Step 4.5 — Run full test suite**

```
poetry run pytest tests/ -v
```

Expected: 103 PASS (100 + 3 new)

- [ ] **Step 4.6 — Lint**

```
poetry run ruff check .
```

Expected: no errors

- [ ] **Step 4.7 — Commit**

```bash
git add api/v1/plan.py tests/test_plan_route.py
git commit -m "feat: add POST /api/v1/plan/lifting route (S7)"
```

---

## Task 5: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 5.1 — Update session status table**

In `CLAUDE.md`, find the session table row for S7 and mark it done:

Old:
```
| **S7** | Lifting Coach | Exercise DB complet (400+) + Volume Landmarks + output format Hevy | ⬜ À FAIRE |
```

New:
```
| **S7** | Lifting Coach | Exercise DB ~75 + DUP/MRV + LiftingPrescriber + output format Hevy | ✅ FAIT |
```

- [ ] **Step 5.2 — Update repo structure section**

In the `agents/lifting_coach/` block, update from:
```
│   ├── lifting_coach/
│   │   ├── __init__.py                ← ✅ S5
│   │   ├── agent.py                   ← ✅ S5 — LiftingCoachAgent stub
│   │   └── system_prompt.md           ← ✅ Existant
```

To:
```
│   ├── lifting_coach/
│   │   ├── __init__.py                ← ✅ S5
│   │   ├── agent.py                   ← ✅ S7 — LiftingCoachAgent (prescriber + LLM)
│   │   ├── prescriber.py              ← ✅ S7 — LiftingPrescriber (déterministe)
│   │   └── system_prompt.md.txt       ← ✅ Existant
```

- [ ] **Step 5.3 — Update test files list**

Add the 2 new test files to the tests section:
```
│   ├── test_lifting_prescriber.py     ← ✅ S7 — 6 tests prescriber logic
│   └── test_lifting_agent.py          ← ✅ S7 — 4 tests agent + mocked LLM
```

Update the total count comment at bottom: `# (~103 tests total)`

- [ ] **Step 5.4 — Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md — mark S7 done, 103 tests"
```

---

## Task 6: Push and verify

- [ ] **Step 6.1 — Final test run**

```
poetry run pytest tests/ -v --tb=short
```

Expected: 103 PASS, 0 FAIL

- [ ] **Step 6.2 — Final lint**

```
poetry run ruff check .
```

Expected: no errors

- [ ] **Step 6.3 — Push to origin**

```bash
git push origin master
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ Exercise DB 23 → ~75 exercises (spec said ~80, test checks >= 75)
- ✅ LiftingPrescriber: DUP 3-way, MEV/MRV hybrid, CNS tier restriction, deload, ACWR adjustment
- ✅ LiftingCoachAgent: replaces stub, LLM coaching_notes, fallback = []
- ✅ POST /plan/lifting route with 422 validation
- ✅ 17 new tests (4+6+4+3)

**Type consistency:**
- `LiftingPrescriber._get_session_types(sessions_per_week: int, week: int) -> list[str]` used in Task 2 tests ✅
- `LiftingPrescriber.build_week_plan(view: dict) -> dict` used throughout ✅
- `session["hevy_workout"]["exercises"][i]["sets"][j]["weight_kg"]` always `None` ✅
- `patch("agents.lifting_coach.agent.anthropic.Anthropic")` matches import in agent.py ✅

**Equipment note:** Exercises with `equipment: []` (Dead Bug, Plank, Side Plank, Clamshell, Side-lying Hip Abduction) are bodyweight and available regardless of the athlete's equipment list. The `_select_exercise` method handles this with `if not ex["equipment"]: return True`.
