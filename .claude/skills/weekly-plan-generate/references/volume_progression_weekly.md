# Volume Progression - Weekly Planning

Week-to-week volume progression decisions based on training response, adaptation, and risk assessment.

---

## Actual vs. Planned Baseline

> **Philosophy: CLI provides constraints, AI Coach decides.**
> `suggest-weekly-target` returns a context package: actual volumes, macro intent, safety ceilings, adherence pattern. `hard_ceiling_km` is a hard limit; `suggested_target_km` is an advisory anchor for illness/recovery cases. The AI Coach decides the target using all available data.

> **Why this matters**: The body adapts to actual training load, not scheduled load. When actual differs from planned, blindly using macro targets creates dangerous spikes (undershoot) or missed progression (overshoot).
>
> **Why two weeks?** A single week can be noisy — illness, travel, a catch-up surge. A 2:1 weighted average (N-1 counts double, N-2 counts once) damps outliers the same way ACWR uses chronic vs. acute windows.

### Command

```bash
resilio guardrails suggest-weekly-target \
  --actual-prev <N-1_KM> \
  --actual-prev2 <N-2_KM> \
  --macro-prev <MACRO_N-1_KM> \
  --macro-prev2 <MACRO_N-2_KM> \
  --macro-next <MACRO_N_KM> \
  --run-days <RUN_DAYS> \
  [--recovery-transition] \
  [--prev2-is-recovery]
```

`--macro-prev2` is optional but important for accurate `overshoot_pattern` detection in progressive plans: without it, `adherence_n2_pct` uses `macro_prev` as an approximation, which underestimates N-2 adherence when the plan is building week-over-week.

### Key Output Fields

| Field | What it is | How to use it |
|---|---|---|
| `hard_ceiling_km` | `max(10%, Pfitz)` from N-1 raw actual | **Absolute maximum — never exceed** |
| `actual_prev_km` | What athlete actually ran (N-1) | Your primary baseline for progression |
| `suggested_target_km` | `min(10%, Pfitz)` from weighted avg | Conservative anchor — use for illness/undershoot |
| `macro_next_km` | Macro plan's intent | Reference for structural progression |
| `overshoot_pattern` | N-1 AND N-2 both >10% above macro | Signals consistent overperformance |

### The Ceiling Design: Why `max()` for `hard_ceiling_km`

Pfitzinger's actual rule: **"10% OR 1.6km per session per week"** — these are alternatives, not cumulative requirements.

`hard_ceiling_km = max(actual × 1.10, actual + 1.6×run_days)`

This is automatically volume-tier aware — no explicit branching needed:
- **Crossover point**: `16 × run_days` km (64km for 4 days, 48km for 3 days)
- **Below crossover (low/medium volume)**: Pfitzinger wins — 1.6km/session guideline is more permissive, matching "absolute load matters at low volumes"
- **Above crossover (high volume)**: 10% wins — matches "cumulative load matters at high volumes"

Example with 4 run days:
| actual_prev | 10% ceiling | Pfitz ceiling | hard_ceiling (max) | rule |
|---|---|---|---|---|
| 18km | 19.8km | 24.4km | **24.4km** | Pfitz (+36% allowed) |
| 35km | 38.5km | 41.4km | **41.4km** | Pfitz (+18% allowed) |
| 50km | 55.0km | 56.4km | **56.4km** | Pfitz (+13% allowed) |
| 70km | 77.0km | 76.4km | **77.0km** | 10% (+10% allowed) |

The `suggested_target_km` (conservative formula path) still uses `min()` from the weighted average — that's the right anchor for illness recovery. The distinction is intentional:
- `safety_ceiling_km` / `suggested_target_km`: conservative path (min, from weighted avg)
- `hard_ceiling_km`: absolute maximum (max, from raw N-1)

### The Five Scenarios

| Scenario | N-1 | N-2 | macro_prev | macro_next | → AI target |
|---|---|---|---|---|---|
| Aligned | 35.3km | 36.1km | 36km | 40km | ~39–40km (macro delta preserved) |
| Overshoot (consistent) | 48.1km | 39.6km | 43km | 48km | ~51km (anchor to N-1 +6%, ceiling 52.9km) |
| Illness undershoot | 18km | 35km | 36km | 40km | ~26km (use suggested_target_km) |
| Week 2 (no N-2) | 28km | — | 30km | 33km | ~31km |
| Recovery transition | 30km | — | 28km | 38km | 38km (macro, hardcoded) |

**Formula trace — illness undershoot** (`UNDERSHOOT_CAPPED`):
```
effective_actual = (2×18 + 35) / 3 = 23.67km
planned_delta    = 40 - 36 = +4km
safety_ceiling   = min(23.67×1.10, 23.67+6.4) = min(26.03, 30.07) = 26.03km
suggested        = min(23.67+4, 26.03, macro_ceiling) = min(27.67, 26.03) = 26.0km
hard_ceiling     = max(18×1.10, 18+6.4) = max(19.8, 24.4) = 24.4km
```
Key insight: `suggested_target_km` (26.0km) > `hard_ceiling_km` (24.4km) — the outer ceiling is
tighter because it anchors to raw N-1 (18km), not the weighted average (23.67km).
**→ AI Coach uses `min(suggested, hard_ceiling)` = 24.4km.** The athlete's body last did 18km;
26km would exceed the outer ceiling.

**Formula trace — consistent overshoot** (`OVERSHOOT_ADJUSTED`, use AI judgment):
```
N-1 actual: 48.1km, N-2 actual: 39.6km, macro N-1: 43km, macro N: 48km, 4 run days
effective_actual = (2×48.1 + 39.6) / 3 = 45.27km
suggested        = min(45.27+5, 45.27×1.10) = min(50.27, 49.8) = 49.8km
hard_ceiling     = max(48.1×1.10, 48.1+6.4) = max(52.91, 54.5) = 54.5km
→ AI Coach: athlete already at 48.1, macro says 48. Check TSB/ACWR → choose ~51km (not 49.8)
```

### §Overshoot Scenarios — When `overshoot_pattern: true`

`overshoot_pattern: true` means N-1 AND N-2 both exceeded macro by >10%. Three possible situations:

**Scenario A — Ease back (fatigue accumulating)**
Signs: TSB ≤ -20, ACWR ≥ 1.3, readiness low, or TSB declining 3+ weeks.
Action: Hold near `actual_prev_km` or reduce slightly. "Consistency now protects the peak later."

**Scenario B — Continue at athlete's actual pace (adapting well)**
Signs: TSB -15 to -5, ACWR < 1.3, CTL growing steadily.
Action: Target `actual_prev_km + 3–8%`. Anchor to N-1 actual, not the formula's weighted-down average.

**Scenario C — Macro plan was too conservative (structural gap)**
Signs: 3+ consecutive weeks >10% above macro, TSB healthy, CTL growing, no injury flags.
Detect N-3: `resilio plan week-execution --week <N-3>` to confirm 3rd consecutive week.
Action: Apply 6–10% from `actual_prev_km`. Flag to main agent that macro needs upward revision.

### When NOT to use N-2

- N-2 was a planned recovery week (`is_recovery_week: true`) → pass `--prev2-is-recovery`
- N-2 doesn't exist (Week 2) → omit `--actual-prev2`; falls back to N-1 alone

### Relationship to Step 3 (`analyze-progression`)

- **Step 1.5**: AI Coach picks target within `hard_ceiling_km`, anchored to actual history
- **Step 3**: Validates chosen target against CTL capacity and Pfitzinger absolute-load guidelines

---

## Interpreting Progression Context (AI Coaching Judgment)

### Philosophy: CLI Provides Context, AI Coach Decides

`resilio guardrails analyze-progression` provides **rich context**, not pass/fail. You interpret using training methodology.

**Command**:
```bash
resilio guardrails analyze-progression --previous 15 --current 20 --ctl 27 --run-days 4 --age 32
```

**Returns**:
- Volume classification (low/medium/high)
- Traditional 10% rule (reference only)
- Absolute load analysis (Pfitzinger per-session guideline)
- CTL capacity context
- Risk factors (injury, age, large % increase)
- Protective factors (small absolute load, adequate capacity)
- Coaching considerations

### Volume Classification

**Low Volume (<25km)**:
- **Primary risk**: Absolute load per session
- **Flexibility**: Higher % increases OK if absolute load manageable
- **Key metric**: Per-session increase (<1.6km per Pfitzinger)
- **Decision**: Accept if within Pfitzinger guideline, even if % high

**Example**: 15→20km (+33%) acceptable because:
- Per-session increase 1.25km (within 1.6km guideline)
- Small absolute increase (5km total)
- Low volume means small absolute loads manageable

**Medium Volume (25-50km)**:
- **Primary risk**: Both absolute and cumulative load
- **Flexibility**: Moderate - balance % and absolute increases
- **Decision**: Consider both Pfitzinger guideline AND 10% rule

**High Volume (≥50km)**:
- **Primary risk**: Cumulative load
- **Flexibility**: Limited - adhere to 10% rule
- **Key concern**: Large absolute increases (>10km) significantly increase injury risk

**Example**: 60→75km (+25%) should be rejected because:
- Per-session increase 3.75km (exceeds 1.6km guideline)
- Large absolute increase (15km)
- High volume amplifies cumulative stress
- Recommend: 66km (10% increase)

### Risk vs. Protective Factors

**Weigh factors**:
- **Risk**: Recent injury, masters age, large % increase
- **Protective**: Low volume, small absolute load, adequate CTL capacity, within Pfitzinger guideline

**Decision rule**: Accept when protective factors outweigh risk factors.

**Example - Accept despite high %**:
```json
{
  "increase_pct": 33.3,
  "risk_factors": ["Large percentage increase"],
  "protective_factors": [
    "Low volume with small absolute increase",
    "Within Pfitzinger per-session guideline (1.25km < 1.6km)",
    "Target within CTL capacity (20km in 25-40km range)"
  ]
}
```
→ **ACCEPT**: 3 strong protective factors outweigh 1 risk factor.

**Example - Reject despite moderate %**:
```json
{
  "increase_pct": 15.0,
  "risk_factors": [
    "Recent injury (<90 days)",
    "Masters athlete (age 55)"
  ],
  "protective_factors": []
}
```
→ **MODIFY**: 2 moderate risks with no protective factors → be conservative.

### CTL Capacity

**Within capacity** (`target_within_capacity: true`): Strong protective factor, fitness supports volume.

**Outside capacity** (`target_within_capacity: false`): Warning flag (not automatic rejection).
- **Below**: Acceptable (conservative start or detraining)
- **Above**: Requires strong justification

**Example - Above capacity**:
```json
{
  "current_volume_km": 50.0,
  "ctl": 27.0,
  "ctl_based_capacity_km": [25, 40]
}
```
→ 50km exceeds 40km capacity limit (needs strong protective factors or adjustment).

### Decision Framework

1. Check volume classification (low/medium/high)
2. Identify primary risk (absolute vs. cumulative load)
3. Count protective vs. risk factors
4. Apply volume-specific rule:
   - **Low**: Accept if within Pfitzinger guideline
   - **Medium**: Balance both metrics
   - **High**: Be conservative, prioritize 10% rule
5. Consider athlete context (CTL, injury, age)
6. Provide clear rationale

**Example Decision - Accept**:
"Your 15→20km progression is 33%, exceeding the traditional 10% rule. However, at low volumes, absolute load per session matters more. Your per-session increase is 1.25km (within Pfitzinger's 1.6km guideline), and your CTL of 27 supports this volume. I'm accepting this progression."

**Example Decision - Modify**:
"Your 60→75km progression is too aggressive. The 15km absolute increase and 3.75km per-session increase both exceed safe guidelines. At 60km weekly volume, cumulative load stress is the primary risk. Reduce to 66km (10% increase)."

---

## The 10% Rule - Weekly Application

**Standard progression**: Increase weekly volume ≤10% per week.

**Example**:
- Week 1: 40 km
- Week 2: 44 km (+10%)
- Week 3: 48 km (+10%)
- Week 4: 34 km (recovery, 70%)
- Week 5: 52 km (+10% from week 3, NOT week 4)

**Command**:
```bash
resilio guardrails progression --previous 40 --current 48
```

**Recovery exception**: Every 4th week at 70%. Next buildup increases from pre-recovery baseline.

**Context factors that modify the 10% rule**:
1. **Recent illness**: Reduce to 5% or hold volume
2. **Poor adherence previous week**: Don't increase, investigate causes
3. **Elevated ACWR (>1.3)**: Reduce increase or hold volume
4. **Deeply negative TSB (<-20)**: Hold volume or reduce
5. **Low readiness (<50)**: Skip quality work, maintain easy volume

---

## Long Run Progression

### Caps
- **Duration**: ≤2.5 hours (injury prevention)
- **% of weekly volume**: ≤25-30%
- **Frequency**: Once per week (7 days recovery)

**Command**:
```bash
resilio guardrails long-run --duration 150 --weekly-volume 60 --pct-limit 30
```

### Buildup
- Increase 10-15 minutes every 2-3 weeks
- Recovery week: Reduce 20-30%
- Peak: 2-2.5 hours (race-dependent)

**Example (half marathon)**:
- Week 1: 90 min
- Week 3: 105 min (+15)
- Week 4: 75 min (recovery)
- Week 5: 120 min (+15 from week 3)
- Week 7: 135 min (+15)
- Week 10: 150 min (peak, hold)

---

## Adjustment Factors

### Illness Recovery
- **Acute illness (2-4 days)**: Hold volume 1 week, resume progression
- **Extended illness (5+ days)**: Reduce 20-30%, gradual return over 2 weeks
- **Return markers**: Resting HR normalized, readiness >70

### Poor Adherence
- **<70% completion**: Don't increase, investigate barriers
- **70-85% completion**: Hold volume, improve consistency
- **>85% completion**: Normal progression

### Elevated ACWR
- **1.3-1.5**: Caution - hold volume or minimal increase (+5%)
- **>1.5**: Danger - reduce volume 10-15%

### Deeply Negative TSB
- **-10 to -20**: Normal training fatigue, proceed
- **-20 to -30**: Accumulated fatigue, hold volume
- **<-30**: Overreaching, reduce volume or insert recovery week

---

## Quality Volume Limits (Daniels)

Hard running must be capped:

| Intensity | Daniels Limit | Example (50 km/week) |
|-----------|---------------|---------------------|
| T-pace    | ≤10% of weekly volume | ≤5 km |
| I-pace    | ≤8% of weekly volume  | ≤4 km |
| R-pace    | ≤5% of weekly volume  | ≤2.5 km |

**Command**:
```bash
resilio guardrails quality-volume --t-pace 6.0 --i-pace 4.0 --r-pace 2.0 --weekly-volume 50.0
```

**Why**: Excessive quality work → injury, even if total volume safe.

---

## Multi-Week Pattern Analysis

**Don't rely on single-week snapshot** - analyze 3-4 week trends:

### Consistent Building (healthy)
```
Week N-3: 30km, 90% adherence
Week N-2: 33km, 95% adherence
Week N-1: 36km, 90% adherence
→ Decision: Continue progression (39-40km)
```

### Yo-Yo Pattern (concerning)
```
Week N-3: 35km, 100% adherence
Week N-2: 22km, 65% adherence (illness)
Week N-1: 38km, 100% adherence
→ Decision: Week N-1 was "catch-up", not new baseline. Hold 38km or modest increase (40km)
```

### Declining Adherence (investigate)
```
Week N-3: 32km, 85% adherence
Week N-2: 30km, 70% adherence
Week N-1: 28km, 60% adherence
→ Decision: Don't increase. Identify barriers (life stress, fatigue, motivation)
```

### Cumulative Fatigue
```
Week N-3: TSB -12
Week N-2: TSB -18
Week N-1: TSB -22
→ Decision: TSB declining for 3 weeks = accumulated fatigue. Hold volume or insert recovery week.
```

**Commands for context**:
```bash
# Current week summary (planned vs completed)
resilio week

# Current metrics (multi-week aggregates)
resilio status  # CTL (42-day), ATL (7-day), TSB, ACWR
```

---

## Common Weekly Progression Mistakes

1. **Jumping volume**: 30 → 50 km in one week (+67%) → ACWR spike
2. **No recovery weeks**: 8+ weeks continuous buildup → overtraining
3. **Long run too long**: 40% of weekly volume → disproportionate fatigue
4. **Ignoring illness recovery**: Full volume immediately after illness
5. **Quality volume exceeded**: 12 km T-pace in 40 km week (30%, should be ≤10%)
6. **Single-week decisions**: Not analyzing 3-4 week trends
7. **Mechanical progression**: +10% every week regardless of adaptation signals

---

## Weekly Progression Commands

```bash
# Context-aware progression analysis
resilio guardrails analyze-progression --previous 15 --current 20 --ctl 27 --run-days 4

# Validate weekly progression
resilio guardrails progression --previous 40 --current 48

# Validate long run
resilio guardrails long-run --duration 135 --weekly-volume 55 --pct-limit 30

# Validate quality volume
resilio guardrails quality-volume --t-pace 5.0 --i-pace 4.0 --weekly-volume 50.0

# Current-week context + multi-week aggregates
resilio week
resilio status
```

---

## Deep Dive Resources

- [Advanced Marathoning](../../../docs/training_books/advanced_marathoning_pete_pfitzinger.md) - Pfitzinger volume progressions
- [Daniels' Running Formula](../../../docs/training_books/daniel_running_formula.md) - Quality volume limits
- [Guardrails Commands](../../../docs/coaching/cli/cli_guardrails.md) - Full CLI reference
