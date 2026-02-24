# Quality Progression Framework — Weekly Plan Generation

> **Purpose**: Decision framework for designing quality sessions with longitudinal
> awareness. Consulted during Step 2b and Step 6 of the weekly-plan-generate workflow.

---

## Table of Contents

1. [Quality Micro-Progression Model](#1-quality-micro-progression-model)
2. [Phase-by-Phase Quality Types](#2-phase-by-phase-quality-types)
3. [Quality Type Rotation Table](#3-quality-type-rotation-table)
4. [Long Run Progression Tracking](#4-long-run-progression-tracking)
5. [Cross-Week Boundary Quality Check](#5-cross-week-boundary-quality-check)
6. [Execution Quality → Progression Gate](#6-execution-quality--progression-gate)

---

## 1. Quality Micro-Progression Model

Every quality stimulus follows a **3–4 week mini-cycle** before stepping up
(Daniels / Pfitzinger consensus):

| Week in cycle | Pattern | Example (Tempo) |
|---|---|---|
| Week 1 (Introduction) | Lower volume of new stimulus | 15 min continuous threshold |
| Week 2 (Consolidation) | Same or +5 min | 20 min continuous threshold |
| Week 3 (Progression) | +rep or cruise variant | 3 × 7 min @ T-pace w/ 1 min rest |
| Week 4 (Recovery) | Drop to 70% volume, maintain paces | 12 min threshold (recovery week) |

After recovery, restart from a **higher plateau**:
- Next cycle: 20 min → 25 min → cruise 3×8 min

**Key rule**: Do not step up quality before the athlete has consolidated at the current
level. Two consecutive clean sessions at the same stimulus = safe to progress.

**Critical constraint — one stressor per week** (Daniels / Pfitzinger consensus):
When weekly volume increases significantly (>10%), keep quality session duration flat.
Increasing BOTH volume and quality in the same week stacks two stressors simultaneously —
a known overreaching risk. The Quality Progression Summary must check *which variable
moved last week* to decide which to advance this week:

- Volume increased last week → quality can progress this week (if execution was CLEAN)
- Quality progressed last week → volume can increase this week (if ACWR allows)
- NEITHER progressed last week → genuine stagnation; progress quality OR note reason

Example: Week 3 tempo 15 min, Week 4 recovery, Week 5 volume +30% + tempo 15 min is
**CORRECT** (Pfitzinger: "add miles to easy runs first, not to tempo"). Week 6 volume
flat + tempo 15 min is the actual stagnation to flag and correct.

---

## 2. Phase-by-Phase Quality Types

### Base phase (weeks 1–3)
- **Primary quality**: Strides (neuromuscular only) then first tempo introduction (late base)
- **Rotation**: N/A — single quality type allowed; no intervals yet
- **Intensity**: Strides at R-pace (short, controlled, not full speed); tempo at T-pace

### Build phase (weeks 4–6)
- **Primary quality**: Threshold/Tempo (lactate clearance is the key stimulus)
- **Progression options** within a "tempo" macro hint:
  1. Continuous tempo block (15 → 20 → 25 min progression)
  2. Cruise intervals (3×5 min → 3×7 min → 4×7 min) — same T-pace, fragmented
  3. For marathon focus: Tempo within long run (M-pace segments embedded)
- **When to rotate**: After 2 consecutive continuous tempo weeks → offer cruise interval
  variant next (same lactate stimulus, different fatigue profile, breaks monotony)
- **Intervals (I-pace / VO2max)**: Not primary in build for marathon; use sparingly if
  Week 6 hints include `intervals` type — introduce conservatively (3×1000m)

### Peak phase (week 7)
- **Primary quality**: Race-pace (M-pace segments within long run + standalone M-pace run)
- This is NOT threshold/tempo — it's specificity training
- Pattern: Long run with 8–10 km M-pace block + optional standalone M-pace run

### Taper phase (weeks 8–9)
- **Primary quality**: Shortened tempo (maintain sharpness, reduce fatigue)
- Week 8: 60–70% of peak quality duration (e.g., if Week 6 was 25 min → Week 8 is 15 min)
- Week 9 (race week): Strides only (4–6 × 20 sec acceleration)

### Recovery weeks
- **Quality**: None required. If macro hints allow quality, reduce to 50% of previous
  hard-week volume at the same pace — do not introduce new stimulus.

---

## 3. Quality Type Rotation Table

For build phase, marathon focus:

| Consecutive weeks same type | Action |
|---|---|
| 1 week continuous tempo | Continue with progression (+5 min) |
| 2 weeks continuous tempo | Consider cruise intervals as variation |
| 3 weeks same structure | Rotate type if macro hints allow; if not, vary rep/duration |
| Recovery week between hard weeks | Reset cycle; re-introduce at same or slightly higher level |

**Rotation is a coaching tool, not a rule.** If the athlete is progressing cleanly and
macro hints specify "tempo", cruise intervals are the natural variation — not a deviation.

---

## 4. Long Run Progression Tracking

Explicit **duration-based progression** (NOT just volume %, which the macro plan handles):

```
Rule: Long run duration +10–15 min every 2–3 hard weeks
      (not every week; the 1 hard / 1 easy pattern = progress every 2 weeks)

Check: Read last 2 long runs from plan data.
  - If last LR was X min and prior hard-week LR was also X min → progress to X+10 min
  - If last LR came after a recovery week → use pre-recovery LR as baseline
```

### Priority: target_km overrides duration rule

If `workout_structure_hints.long_run.target_km` is set → use it directly.
The macro plan already validated this step; document the jump and monitor execution.

When only `pct_range` is set → compute candidate distances, then pick one that satisfies
the "+10–15 min" duration rule. If the % envelope forces a bigger jump → document the
exception and apply extra conservatism on pace (stricter HR cap, lower RPE target).

### Long run execution quality signals
- **HR drift** across long run laps: HR creep >10 bpm at constant pace = fatigue signal
- **Positive fade**: Pace slows >8 sec/km in final 30% = athlete was at the edge
- **Embedded quality segments**: If LR had M-pace sections, check execution of those laps

---

## 5. Cross-Week Boundary Quality Check

Before placing Monday quality sessions: check if last week ended Sunday with RPE ≥ 6.

**Concrete rule**:
> If last week's final workout had `target_rpe ≥ 6`, no quality on the following Monday.
> Earliest next quality = Tuesday (48h minimum).

**Why this matters**: Long runs often fall on Sunday at RPE 6–7. A Monday tempo
12 hours later is a quality session on top of un-recovered aerobic stress.

Check: `resilio plan week --week <N-1>` → look at last workout's `target_rpe`.

---

## 6. Execution Quality → Progression Gate

Retrieve and interpret actual execution before progressing quality load.

### Four execution states

| State | Criteria | Progression Action |
|---|---|---|
| CLEAN | Pace within range, HR stable, full duration completed | PROGRESS — safe to add 5 min / 1 rep / next phase |
| STRUGGLED | Pace above ceiling, HR spiked, or session cut short | MAINTAIN — same structure, investigate cause |
| EASY | Pace well under floor, HR consistently low | PROGRESS aggressively OR flag VDOT recalibration |
| MISSED | No matching activity found on that date | Do NOT progress; re-introduce at same or lower level |

### Lap data signals (from `resilio activity laps <id>` or `resilio plan week-execution --week N`)

- **Positive fade**: Pace slows 5–10+ sec/km in final 30% of quality block → athlete
  was at the edge; MAINTAIN rather than PROGRESS even if pace was "in range"
- **HR creep**: HR rises >10 bpm across laps at constant pace → underlying fatigue;
  caution flag even if pace looks clean
- **Perfect consistency**: Lap splits within 5 sec/km, HR steady → CLEAN; safe to progress

### VDOT recalibration trigger

If 2+ consecutive quality sessions are EASY (athlete consistently runs 10+ sec/km faster
than T-pace target without elevated HR), flag VDOT for upward recalibration before the
next quality session.

> Do NOT increase T-pace without a formal VDOT update. Always use
> `resilio vdot paces --vdot <N>` with the recalibrated value.

### Missed session policy

A missed quality session is NOT a recovery week.

- Athlete is fresh (TSB > 0, ACWR < 1.1): re-introduce at same level as the missed session
- Athlete is tired despite missing quality (ACWR still elevated from volume): easy week first; investigate cause before adding any quality

### No prior execution data

If all prior quality sessions have `execution: null` (still `status: scheduled`, not yet run):
- Classify as "no execution data yet"
- Design based on macro plan structure only
- Apply conservative rules (introduction-level, not progression)

---

## Cross-References

> **Path note**: Sibling reference files below are relative to this file's directory
> (`references/`). Docs paths are relative to the skill root
> (`.claude/skills/weekly-plan-generate/`).

- Daniels pace zones: `pace_zones.md`
- Volume guardrails: `guardrails_weekly.md`
- Multi-sport load interaction: `multi_sport_weekly.md`
- Methodology source: `../../../docs/coaching/methodology.md`
- Training book summaries: `../../../docs/training_books/daniel_running_formula.md`,
  `../../../docs/training_books/advanced_marathoning_pete_pfitzinger.md`
