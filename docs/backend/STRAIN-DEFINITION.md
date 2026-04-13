# Strain Index — Architectural Decision Record

**Date:** 2026-04-13
**Status:** Implemented
**Module:** `backend/app/core/strain.py`
**Model:** `MuscleStrainScore` in `backend/app/models/athlete_state.py`

---

## Definition

Strain is a per-muscle-group fatigue index (0–100) representing how hard a muscle
group has been worked in the past 7 days relative to its chronic baseline (28 days).

**Score interpretation:**
- 0–69%: Green — normal or underloaded
- 70–84%: Orange — elevated load, monitor
- 85–100%: Red — near peak load, recovery recommended

---

## Formula

### Score

```
score[m] = min(100, EWMA_7d[m] / EWMA_28d[m] × 100)
```

When `EWMA_28d[m] == 0` (no history): `score[m] = 0.0`

Both EWMAs are computed over the full 28-day daily load array. λ controls the
effective window, not array slicing.

EWMA constants:
- λ_7d = 2 / (7 + 1) = 0.25
- λ_28d = 2 / (28 + 1) ≈ 0.069

### Cardio load (Strava)

```
IF = perceived_exertion / 10
base_au = (duration_seconds / 3600) × IF² × 100
muscle_au[m] = base_au × SPORT_MUSCLE_MAP[sport_type][m]
```

Consistent with TSS-equivalent formula in `methodology.md`
(Coggan/TrainingPeaks, normalized so 1h at threshold = 100 AU).

### Lifting load (Hevy)

```
set_load = weight_kg × reps × (rpe / 10)
muscle_au[m] += set_load × EXERCISE_MUSCLE_MAP[exercise][m]
```

RPE fallback cascade (when `set.rpe` is None):
1. Mean RPE of other sets in same exercise
2. RPE 7 (default for a logged session)

Bodyweight exercises (weight_kg = 0) use a floor of 1.0 kg to preserve
relative load contributions.

### Muscle groups (10 axes)

`quads`, `posterior_chain`, `glutes`, `calves`, `chest`,
`upper_pull`, `shoulders`, `triceps`, `biceps`, `core`

---

## Scientific basis

**Cardio formula:** TSS-equivalent (Coggan, 1997) extended to muscle group
recruitment via sport-specific coefficients. Normalized intensity factor (IF)
derived from RPE (session-RPE method, Impellizzeri et al. 2004).

**Lifting formula:** Volume load (weight × reps) weighted by relative intensity
(RPE/10). Aligns with Zourdos et al. (2016) modified RPE scale for strength
training and the Gillingham total tonnage model.

**EWMA windows:** Matches existing ACWR implementation (`core/acwr.py`).
Acute 7d / Chronic 28d is the Gabbett (2016) recommendation for load spike
detection, applied per muscle group.

---

## Alternatives considered

**A — sRPE × duration (global):** Simpler but ignores mechanical load
specificity. A 1h deadlift session and a 1h easy run would have the same
posterior_chain score. Rejected.

**C — Banister Impulse-Response:** Scientifically superior for calibrated
athletes with dense data. Requires individual fitting (τ₁, τ₂, k₁, k₂).
Deferred to V2 when longitudinal data is available.

---

## Known limitations

1. `EXERCISE_MUSCLE_MAP` covers ~30 exercises. Unmapped exercises default to
   `core: 0.3`. Extend the map as new exercises appear in athlete data.
2. Normalization uses EWMA_28d as current chronic baseline. True individual max
   requires storing historical EWMA peaks. Deferred to V2.
3. Swim coefficients are estimates — electromyography data for swimming is
   limited in the literature.
4. Perceived exertion (RPE) is subjective. Connector data quality affects
   score accuracy.
