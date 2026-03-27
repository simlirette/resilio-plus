# Phase 3 Sessions 6–7 — Specialist Agents Design Spec

## Overview

Build two specialist coaching agents — **RunningCoach** and **LiftingCoach** — that implement the full `BaseAgent` interface and produce deterministic, periodization-aware weekly training recommendations for a hybrid athlete.

**Goal:** Each agent ingests `AgentContext` (athlete profile + connector data + macro phase context), computes sport-specific fatigue and readiness, and returns a `AgentRecommendation` with properly typed `WorkoutSlot` sessions, a `FatigueScore`, a `weekly_load` float, and a `readiness_modifier` derived from HRV/sleep data.

**Architecture:** Approach C — `core/` modules hold stateless business logic (testable without a full AgentContext); `agents/` classes are thin wrappers that orchestrate core calls and return `AgentRecommendation`. Shared readiness computation lives in `core/readiness.py`.

---

## §1. AgentContext Enrichment

`agents/base.py` gains two optional fields with defaults (no breaking change to existing tests):

```python
@dataclass
class AgentContext:
    athlete: AthleteProfile
    date_range: tuple[date, date]
    phase: str                              # MacroPhase value string
    strava_activities: list[StravaActivity] = field(default_factory=list)
    hevy_workouts: list[HevyWorkout] = field(default_factory=list)
    terra_health: list[TerraHealthData] = field(default_factory=list)
    fatsecret_days: list[FatSecretDay] = field(default_factory=list)
    week_number: int = 1                    # 1-based absolute week number in the plan
    weeks_remaining: int = 0               # weeks until target_race_date (0 = race week, negative = post-race)
```

**Semantics:**
- `week_number` increments each time `HeadCoach.build_week()` is called in a multi-week plan. The caller is responsible for incrementing it.
- `weeks_remaining` is computed from `get_current_phase(athlete.target_race_date, today).weeks_remaining` and passed by the caller.
- Existing tests use defaults `week_number=1, weeks_remaining=0` — no changes needed.

---

## §2. core/readiness.py

Shared module computing `readiness_modifier: float` in `[0.5, 1.5]` from HRV and sleep data.

### Signature

```python
def compute_readiness(
    terra_data: list[TerraHealthData],
    hrv_baseline: float | None = None,
) -> float
```

### Algorithm

**Step 1 — HRV delta (hrv_delta):**
- Filter `terra_data` to last 7 entries (most recent first by date).
- Compute `hrv_7d_mean = mean(entry.hrv_rmssd for entry in last_7 if entry.hrv_rmssd is not None)`.
- If `hrv_baseline` is None and fewer than 4 valid entries exist → use `hrv_7d_mean` itself as baseline (cold start: delta = 0, no bonus/penalty).
- If `hrv_baseline` is None and ≥ 4 entries → use the mean of all available entries as baseline.
- Compute `hrv_ratio = hrv_7d_mean / hrv_baseline`:
  - `hrv_ratio ≥ 1.0` → `hrv_delta = +0.10`
  - `0.80 ≤ hrv_ratio < 1.0` → `hrv_delta = 0.0`
  - `0.60 ≤ hrv_ratio < 0.80` → `hrv_delta = -0.15`
  - `hrv_ratio < 0.60` → `hrv_delta = -0.30`
- If no valid HRV data → `hrv_delta = 0.0`

**Step 2 — Sleep delta (sleep_delta):**
- Use `TerraHealthData` fields: `sleep_duration_hours` and `sleep_score`.
- Compute `sleep_hours_mean = mean(e.sleep_duration_hours for e in last_7 if e.sleep_duration_hours is not None)`.
- Compute `sleep_score_mean = mean(e.sleep_score for e in last_7 if e.sleep_score is not None)`.
- If `sleep_hours_mean ≥ 7.0` AND `sleep_score_mean ≥ 70` → `sleep_delta = 0.0`
- Elif `sleep_hours_mean < 6.0` OR `sleep_score_mean < 50` → `sleep_delta = -0.20`
- Else → `sleep_delta = -0.10`
- If no sleep data (both fields None for all entries) → `sleep_delta = 0.0`

**Step 3 — Final modifier:**
```python
modifier = 1.0 + hrv_delta + sleep_delta
return max(0.5, min(1.5, modifier))
```

**Empty input:** `compute_readiness([])` returns `1.0`.

---

## §3. core/running_logic.py

Stateless module for running-specific computations.

### 3.1 VDOT Estimation

```python
def estimate_vdot(activities: list[StravaActivity]) -> float
```

- Filter activities to last 30 days, sport_type == "Run", distance ≥ 1000m.
- For each activity with `distance_meters` and `duration_seconds`:
  - Compute `pace_per_km = duration_seconds / (distance_meters / 1000)`
  - Map to VDOT using a static lookup table (Jack Daniels, simplified: 15 entries covering VDOT 30–70).
- Return the maximum VDOT found (best recent effort).
- No valid activities → return `35.0` (beginner fallback).

**Static VDOT table (complete — 15 entries, pace in seconds/km for lookup):**

| VDOT | Easy pace (s/km) | Threshold pace (s/km) |
|------|------------------|-----------------------|
| 30   | 450              | 390                   |
| 33   | 425              | 368                   |
| 35   | 405              | 350                   |
| 38   | 383              | 332                   |
| 40   | 370              | 315                   |
| 43   | 350              | 300                   |
| 45   | 340              | 290                   |
| 48   | 322              | 275                   |
| 50   | 315              | 270                   |
| 53   | 300              | 258                   |
| 55   | 295              | 250                   |
| 58   | 280              | 238                   |
| 60   | 275              | 235                   |
| 65   | 258              | 220                   |
| 70   | 242              | 207                   |

Lookup: find the row where `pace_per_km_seconds` is closest to `duration_seconds / (distance_meters / 1000)`. Return that row's VDOT value.

### 3.2 Running Fatigue

```python
def compute_running_fatigue(activities: list[StravaActivity]) -> FatigueScore
```

**Input contract:** `activities` must be pre-filtered to the relevant week by the caller (e.g., the 7 days before `date_range[0]`). This function does not filter by date internally.

From the provided activities:
- `local_muscular = min(100, total_distance_km * 3.0)`
- `cns_load = min(100, count_hiit_sessions * 20)` — HIIT = perceived_exertion ≥ 8 OR duration < 30min with high HR
- `metabolic_cost = min(100, sum(duration_min * rpe_normalized) / 10)` where `rpe_normalized = perceived_exertion / 10`
- `recovery_hours`:
  - Max HIIT session → 24h
  - Max tempo session (RPE 6–7) → 12h
  - Only Z1 sessions → 6h
  - No sessions → 0h
- `affected_muscles = ["quads", "calves", "hamstrings"]`
- No activities → return all-zero `FatigueScore` with empty muscles.

### 3.3 Session Generation

```python
def generate_running_sessions(
    vdot: float,
    week_number: int,
    weeks_remaining: int,
    available_days: list[int],
    hours_budget: float,
    volume_modifier: float,
    tid_strategy: TIDStrategy,
) -> list[WorkoutSlot]
```

**Volume budget:**
- `base_minutes = hours_budget * 60 * volume_modifier`
- Wave loading — deload check **must come first**:
  - `if week_number % 4 == 0` → `weekly_minutes = base_minutes * 0.6` (deload week)
  - `else` → `weekly_minutes = base_minutes * (1.0 + 0.05 * ((week_number % 4) - 1))` — 5% progressive overload per week in block (week 1: ×1.0, week 2: ×1.05, week 3: ×1.10)
- Tapering override (applied after wave loading): `if weeks_remaining ≤ 2` → `weekly_minutes = base_minutes * 0.5`

**80/20 TID distribution:**
- Easy Z1 volume: 80% of `weekly_minutes`
- Quality volume: 20% of `weekly_minutes`

**Quality session selection by TID strategy:**

| Strategy | Quality sessions |
|---|---|
| `PYRAMIDAL` | Tempo Z2 (threshold) + short hill repeats |
| `MIXED` | Tempo Z2 + 1 VO2max Z3 session |
| `POLARIZED` | VO2max Z3 only (avoids Z2 "grey zone") |

**Tapering override (`weeks_remaining ≤ 2`):**
- Only Z1 easy + 1 short activation session (20min Z3, one strides set)

**Session types generated:**

| workout_type | duration_min | Zone | Notes |
|---|---|---|---|
| `easy_z1` | 45–90 | Z1 | Main volume carrier |
| `long_run_z1` | 90–120 | Z1 | Only if hours_budget ≥ 6h |
| `tempo_z2` | 40–60 | Z2 | Warm-up + threshold + cool-down |
| `vo2max_z3` | 45 | Z3 | 8×3min intervals with recovery |
| `activation_z3` | 20 | Z3 | Pre-race activation only |

**Day assignment:** sessions distributed across `available_days`, longest sessions on weekend days (index 5–6) when possible.

**intensity_weight for weekly_load calculation:** Z1=1.0, Z2=1.5, Z3=2.0, Z4=2.5

---

## §4. core/lifting_logic.py

Stateless module for lifting-specific computations.

### 4.1 Strength Level Estimation

```python
class StrengthLevel(str, Enum):
    BEGINNER     = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED     = "advanced"

def estimate_strength_level(workouts: list[HevyWorkout]) -> StrengthLevel
```

From workouts in last 30 days:
- `sessions_per_week = len(workouts) / 4.3`
- `mean_rpe = mean(set.rpe for workout in workouts for exercise in workout.exercises for set in exercise.sets if set.rpe is not None)`
- `BEGINNER`: sessions_per_week < 2 OR mean_rpe < 6 OR no data
- `INTERMEDIATE`: 2 ≤ sessions_per_week < 3 AND 6 ≤ mean_rpe ≤ 8
- `ADVANCED`: sessions_per_week ≥ 3 AND mean_rpe > 8

### 4.2 Lifting Fatigue

```python
def compute_lifting_fatigue(workouts: list[HevyWorkout]) -> FatigueScore
```

From workouts in target week:
- `total_sets = sum(len(exercise.sets) for workout in workouts for exercise in workout.exercises)`
- `local_muscular = min(100, total_sets * 3)`
- `tier3_sessions = count of workouts containing any Tier 3 exercise` (from exercise-database.json)
- `cns_load = min(100, tier3_sessions * 25)`
- `metabolic_cost = min(100, total_sets * total_reps_mean / 50)` where `total_reps_mean` = mean reps across all sets
- `recovery_hours`:
  - Contains squat or deadlift → 48h
  - Upper body only → 24h
  - Light/endurance only → 12h
- `affected_muscles` = union of muscles targeted. Use a static lookup dict (authored in `lifting_logic.py`) mapping exercise name keywords to muscle groups from `volume-landmarks.json` keys (e.g., "squat" → ["quads", "glutes"], "bench" → ["chest", "triceps"], "row" → ["back", "biceps"], "deadlift" → ["hamstrings", "glutes", "back"]). This lookup is not derivable from existing JSON files alone — it must be written by hand.
- No workouts → all-zero FatigueScore.

### 4.3 Session Generation

```python
def generate_lifting_sessions(
    strength_level: StrengthLevel,
    phase: str,                 # MacroPhase value string — used for exercise tier selection
    week_number: int,
    weeks_remaining: int,
    available_days: list[int],
    hours_budget: float,
    volume_modifier: float,
    running_load_ratio: float,
) -> list[WorkoutSlot]
```

**DUP rotation** (`week_number % 3`):
- `0` → Hypertrophy priority (3–4 sets × 8–12 reps, RPE 7–8)
- `1` → Strength priority (4–5 sets × 3–5 reps, RPE 8–9)
- `2` → Muscular endurance priority (2–3 sets × 15–20 reps, RPE 6–7)

**Hybrid volume reduction:**
- `running_load_ratio = running_minutes / total_minutes` (passed from RunningCoach weekly_load)
- If `running_load_ratio > 0.5`: apply `hybrid_reduction` from `volume-landmarks.json` to lower body muscles
- Effective lower body volume: `max(MEV, MRV * (1 - hybrid_reduction))`
- Upper body: unaffected

**Exercise tier selection by phase:**
- `GENERAL_PREP` / deload week → Tier 1 only (machines, low CNS cost)
- `SPECIFIC_PREP` → Tier 1–2
- `PRE_COMPETITION` → Tier 1–2, avoid Tier 3
- `TRANSITION` → Tier 2–3 acceptable

**Wave loading:** same as running — `week_number % 4 == 0` → volume × 0.6

**Session types generated:**

| workout_type | duration_min | Focus | Muscles |
|---|---|---|---|
| `upper_hypertrophy` | 60 | Chest/back/shoulders, Tier 1–2 | chest, back, shoulders |
| `lower_strength` | 60 | Quads/hamstrings (reduced if running high) | quads, hamstrings, glutes |
| `full_body_endurance` | 45 | Core + light compound movements | core, quads, back |
| `upper_strength` | 75 | Heavy press/pull, Tier 2–3 if GENERAL_PREP | chest, back, shoulders, triceps, biceps |
| `arms_hypertrophy` | 60 | Biceps/triceps/forearms, Tier 1–2 | biceps, triceps |

**`arms_hypertrophy` inclusion rule:** generated only when `week_number % 3 == 0` (hypertrophy DUP priority week) AND `len(available_days) ≥ 4` (enough days to add a dedicated arms session without crowding lower/upper sessions).

**Sessions per week:** 2–4 depending on `available_days` length and `hours_budget`.

**weekly_load calculation:** `sum(total_sets_per_session * mean_rpe_target)`, normalized to float.

---

## §5. agents/running_coach.py

Thin wrapper around core modules.

```python
class RunningCoach(BaseAgent):
    name = "running"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        # 1. Filter Strava activities to last 7 days before date_range start
        activities = [a for a in context.strava_activities
                      if a.date >= context.date_range[0] - timedelta(days=7)
                      and a.date < context.date_range[0]]

        # 2. Estimate VDOT (use athlete.vdot if set, else estimate from history)
        vdot = context.athlete.vdot or estimate_vdot(context.strava_activities)

        # 3. Readiness modifier from Terra data
        readiness_modifier = compute_readiness(context.terra_health)

        # 4. Fatigue from last week
        fatigue_score = compute_running_fatigue(activities)

        # 5. Get periodization phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 6. Generate sessions
        # Budget: 60% running / 40% lifting by default; reversed if primary_sport == LIFTING
        run_ratio = 0.4 if context.athlete.primary_sport == Sport.LIFTING else 0.6
        sessions = generate_running_sessions(
            vdot=vdot,
            week_number=context.week_number,
            weeks_remaining=context.weeks_remaining,
            available_days=context.athlete.available_days,
            hours_budget=context.athlete.hours_per_week * run_ratio,
            volume_modifier=phase.volume_modifier,
            tid_strategy=phase.tid_recommendation,
        )

        # 7. Compute weekly_load
        _INTENSITY = {"easy_z1": 1.0, "long_run_z1": 1.0, "tempo_z2": 1.5,
                      "vo2max_z3": 2.0, "activation_z3": 2.0}
        weekly_load = sum(
            s.duration_min * _INTENSITY.get(s.workout_type, 1.0)
            for s in sessions
        )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=f"VDOT {vdot:.0f} | Phase: {phase.phase.value} | "
                  f"Weeks remaining: {context.weeks_remaining}",
        )
```

---

## §6. agents/lifting_coach.py

```python
class LiftingCoach(BaseAgent):
    name = "lifting"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        # 1. Filter Hevy workouts to last 7 days before date_range start
        workouts = [w for w in context.hevy_workouts
                    if w.date >= context.date_range[0] - timedelta(days=7)
                    and w.date < context.date_range[0]]

        # 2. Estimate strength level
        strength_level = estimate_strength_level(context.hevy_workouts)

        # 3. Readiness modifier
        readiness_modifier = compute_readiness(context.terra_health)

        # 4. Fatigue
        fatigue_score = compute_lifting_fatigue(workouts)

        # 5. Get periodization phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 6. Compute running_load_ratio from context
        # Approximate: running uses 60% of hours_budget; total = hours_budget
        running_load_ratio = 0.6  # default; refined when HeadCoach passes load info

        # 7. Generate sessions
        # Budget: 40% lifting / 60% running by default; reversed if primary_sport == LIFTING
        lift_ratio = 0.6 if context.athlete.primary_sport == Sport.LIFTING else 0.4
        sessions = generate_lifting_sessions(
            strength_level=strength_level,
            phase=phase.phase.value,
            week_number=context.week_number,
            weeks_remaining=context.weeks_remaining,
            available_days=context.athlete.available_days,
            hours_budget=context.athlete.hours_per_week * lift_ratio,
            volume_modifier=phase.volume_modifier,
            running_load_ratio=running_load_ratio,
        )

        # 8. Compute weekly_load = sum(duration_min * intensity_weight per session)
        # Intensity weights for lifting: strength=2.0, hypertrophy=1.5, endurance=1.0, arms=1.0
        _LIFT_INTENSITY = {
            "upper_strength": 2.0, "lower_strength": 2.0,
            "upper_hypertrophy": 1.5, "arms_hypertrophy": 1.0,
            "full_body_endurance": 1.0,
        }
        weekly_load = sum(
            s.duration_min * _LIFT_INTENSITY.get(s.workout_type, 1.0)
            for s in sessions
        )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=f"Level: {strength_level.value} | Phase: {phase.phase.value} | "
                  f"DUP block: {context.week_number % 3}",
        )
```

---

## §7. Testing Strategy

### File map

```
backend/app/core/readiness.py
backend/app/core/running_logic.py
backend/app/core/lifting_logic.py
backend/app/agents/running_coach.py
backend/app/agents/lifting_coach.py

tests/backend/core/test_readiness.py           6 tests
tests/backend/core/test_running_logic.py      12 tests
tests/backend/core/test_lifting_logic.py      12 tests
tests/backend/agents/test_running_coach.py     8 tests
tests/backend/agents/test_lifting_coach.py     8 tests
```

**Total: ~46 new tests**

### test_readiness.py (6 tests)
- `test_empty_data_returns_1_0` — no Terra data → 1.0
- `test_good_hrv_good_sleep_returns_bonus` — HRV ≥ baseline, sleep ≥ 7h/70 → 1.1
- `test_low_hrv_reduces_modifier` — HRV < 60% baseline → modifier ≤ 0.7
- `test_poor_sleep_reduces_modifier` — sleep < 6h → penalty applied
- `test_combined_low_hrv_and_poor_sleep_clamped` — sum of penalties → clamped to 0.5
- `test_no_hrv_baseline_uses_mean` — cold start: no penalty, returns 1.0

### test_running_logic.py (12 tests)
- `test_estimate_vdot_no_activities_returns_default` — empty → 35.0
- `test_estimate_vdot_from_recent_activity` — known pace → expected VDOT
- `test_fatigue_empty_activities_returns_zeros`
- `test_fatigue_hiit_increases_cns_load`
- `test_fatigue_long_distance_increases_local_muscular`
- `test_generate_sessions_respects_80_20_ratio` — Z1 volume ≥ 80% of total
- `test_generate_sessions_deload_week_reduces_volume` — week_number % 4 == 0 → 60%
- `test_generate_sessions_tapering_near_race` — weeks_remaining ≤ 2 → only Z1 + activation
- `test_generate_sessions_pyramidal_includes_tempo`
- `test_generate_sessions_polarized_avoids_z2`
- `test_generate_sessions_no_long_run_below_6h_budget`
- `test_generate_sessions_intensity_weights_compute_load`

### test_lifting_logic.py (12 tests)
- `test_estimate_strength_level_no_data_returns_beginner`
- `test_estimate_strength_level_advanced`
- `test_fatigue_empty_workouts_returns_zeros`
- `test_fatigue_tier3_increases_cns_load`
- `test_fatigue_squat_sets_recovery_48h`
- `test_generate_sessions_dup_rotation_week_0_hypertrophy`
- `test_generate_sessions_dup_rotation_week_1_strength`
- `test_generate_sessions_dup_rotation_week_2_endurance`
- `test_generate_sessions_hybrid_reduction_applied_when_running_high`
- `test_generate_sessions_deload_week_reduces_volume`
- `test_generate_sessions_arms_hypertrophy_included`
- `test_generate_sessions_tier1_only_in_general_prep`

### test_running_coach.py (8 tests)
- `test_analyze_returns_agent_recommendation`
- `test_analyze_name_is_running`
- `test_analyze_readiness_modifier_propagated_from_terra`
- `test_analyze_sessions_are_workout_slots`
- `test_analyze_weekly_load_positive`
- `test_analyze_cold_start_no_strava_data`
- `test_analyze_week_number_affects_volume` — week 4 (deload) < week 3
- `test_analyze_near_race_only_z1_sessions`

### test_lifting_coach.py (8 tests)
- `test_analyze_returns_agent_recommendation`
- `test_analyze_name_is_lifting`
- `test_analyze_readiness_modifier_propagated_from_terra`
- `test_analyze_sessions_are_workout_slots`
- `test_analyze_weekly_load_positive`
- `test_analyze_cold_start_no_hevy_data`
- `test_analyze_week_number_affects_dup_rotation`
- `test_analyze_running_load_ratio_reduces_lower_body_volume`

---

## §8. Key Constraints & Edge Cases

1. **Cold start (no historical data):** all agents return valid `AgentRecommendation` with default VDOT=35, StrengthLevel=BEGINNER, readiness_modifier=1.0, and plausible sessions.
2. **`readiness_modifier` bounds:** always in `[0.5, 1.5]` — enforced by `compute_readiness()` clamp AND `AgentRecommendation.__post_init__`.
3. **`weekly_load` must be > 0** when sessions are generated; 0.0 only when no sessions produced.
4. **`WorkoutSlot.duration_min > 0`** — all generated sessions must have at least 1 minute.
5. **No LLM calls** — all logic is deterministic Python. No external API calls in agents.
6. **Sport enum:** sessions use `Sport.RUNNING` or `Sport.LIFTING` (not swimming/biking).
7. **Budget split:** RunningCoach takes 60% of `hours_per_week`, LiftingCoach 40%. If athlete's `primary_sport` is LIFTING, reverse the split.
8. **`week_number` starts at 1.** Callers must not pass 0.
