# Training Book Extraction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract 5 running books into structured, agent-actionable markdown files under `docs/backend/books/`, then produce a cross-book INDEX.md.

**Architecture:** Each source `docs/training_books/*.md` → 1 extract `docs/backend/books/*-extract.md` with 6 standardized sections (Concepts, Formulas, Reference Tables, Prescriptive Rules IF/THEN, Contraindications, Source References). One atomic commit per book. INDEX produced last.

**Tech Stack:** Markdown only. No Python, no tests, no migrations. No changes to `docs/training_books/` (read-only).

---

## File Map

| File | Action | Source |
|---|---|---|
| `docs/backend/books/daniels-running-formula-extract.md` | Create | `docs/training_books/daniel_running_formula.md` |
| `docs/backend/books/pfitzinger-advanced-marathoning-extract.md` | Create | `docs/training_books/advanced_marathoning_pete_pfitzinger.md` |
| `docs/backend/books/pfitzinger-faster-road-racing-extract.md` | Create | `docs/training_books/faster_road_racing_pete_pfitzinger.md` |
| `docs/backend/books/fitzgerald-8020-extract.md` | Create | `docs/training_books/80_20_matt_fitzgerald.md` |
| `docs/backend/books/pierce-first-extract.md` | Create | `docs/training_books/run_less_run_faster_bill_pierce.md` |
| `docs/backend/books/INDEX.md` | Create | All 5 extracts above |

---

## Standard Template (every extract file)

```markdown
# [Titre complet] — Agent Extract

**Source:** [auteur, titre, éditeur, année, édition]
**Domain:** Running — [sous-domaine]
**Agent cible:** Running Coach (principalement); Head Coach (règles de sécurité)

---

## 1. Concepts fondamentaux
- [bullet concis par concept — pas de paraphrase]

## 2. Formules et calculs
| Formule | Inputs | Output | Notes |
|---|---|---|---|

## 3. Tables de référence
| Zone/Seuil | Valeur | Unité | Condition |
|---|---|---|---|

## 4. Règles prescriptives
- IF [condition observable] THEN [action prescrite] `[ref: §X / Table Y]`

## 5. Contre-indications et cas limites
- [situations où la règle générale ne s'applique pas]

## 6. Références sources
| Concept | Référence livre |
|---|---|
```

**Section 4 rules (non-negotiable):**
- Form: `IF X THEN Y` — no hedging, no "may", no "consider", no "typically"
- Every rule ends with `[ref: §X]` or `[ref: Table Y]` bracketed source
- Rules that cannot be expressed as IF/THEN go in section 1
- Conflicting rules across books → keep verbatim; conflicts flagged in INDEX

---

## Task 1: Daniels' Running Formula

**Files:**
- Read: `docs/training_books/daniel_running_formula.md`
- Create: `docs/backend/books/daniels-running-formula-extract.md`

- [ ] **Step 1: Read source file**

  ```
  Read: docs/training_books/daniel_running_formula.md (267 lines)
  ```

  Key sections to extract: §0 Core Philosophy, §2 Vocabulary (VDOT + 5 paces), §3 Decision Rules (IF/THEN), §4 Workout Constructors (guardrails = formulas), §5 Phase structure.

- [ ] **Step 2: Create extract file**

  Create `docs/backend/books/daniels-running-formula-extract.md` with the standard template filled as follows:

  **Section 1 — Concepts fondamentaux** (derive from §0 + §2):
  - VDOT = pseudo-VO2max index derived from recent race performance; governs all training paces
  - 5 training intensities: E (Easy), M (Marathon), T (Threshold), I (Interval), R (Repetition)
  - Train at current fitness, not goal fitness — VDOT based on last race ≤4-6 weeks
  - Phase structure: 4 phases (I=Foundation/E+L, II=Repetition/R, III=Interval/I, IV=Threshold/T)
  - Hard/Easy: quality sessions require recovery days; never 2 consecutive hard days without compensation
  - Volume progressed conservatively: hold new stress level 3-4 weeks before increasing
  - Rest = training: recovery, sleep, nutrition are non-negotiable inputs
  - 10% mileage cap per week, never exceeded

  **Section 2 — Formules et calculs** (derive from §2 guardrails + §3):

  | Formule | Inputs | Output | Notes |
  |---|---|---|---|
  | VDOT lookup | race_distance, race_time | VDOT (integer) | Table 5.1 |
  | Training paces | VDOT | E_pace, M_pace, T_pace, I_pace, R_pace | Table 5.2 |
  | 6-Second Rule | R_pace | I_pace = R_pace − 6s/400m; T_pace = I_pace − 6s/400m | For VDOT > 50; use 7-8s for VDOT 40-50 `[§2]` |
  | T-pace volume cap | weekly_mileage | max_T_volume = weekly_mileage × 10% | Single continuous T run also capped by this `[§2 T-Pace]` |
  | I-pace volume cap | weekly_mileage | max_I_volume = min(10 km, weekly_mileage × 8%) | Per session `[§2 I-Pace]` |
  | R-pace volume cap | weekly_mileage | max_R_volume = min(8 km, weekly_mileage × 5%) | Per session `[§2 R-Pace]` |
  | Long run cap | weekly_mileage | max_long = min(weekly_mileage × 25-30%, 150 min) | 150 min = practical cap `[§2 L-Pace]` |
  | VDOT break — short | pre_break_VDOT, break_days | adjusted_VDOT = pre_break_VDOT × 0.93-0.99 | For 6-28 days off `[Table 9.2]` |
  | VDOT break — long | pre_break_VDOT, cross_trained | adjusted_VDOT = pre_break_VDOT × 0.80-0.92 | For >8 weeks off `[Table 9.2]` |

  **Section 3 — Tables de référence** (derive from §2 definitions):

  | Zone/Seuil | Valeur | Unité | Condition |
  |---|---|---|---|
  | E-pace HR | conversational | — | No HR cap specified; effort = sustainable conversation |
  | T-pace HR | comfortably hard | — | "controlled, steady-state effort" `[§2 T-Pace]` |
  | I-pace duration (min work bout) | 3 | min | per repetition `[§2 I-Pace]` |
  | I-pace duration (max work bout) | 5 | min | per repetition `[§2 I-Pace]` |
  | R-pace duration (max work bout) | 2 | min | per repetition `[§2 R-Pace]` |
  | I-pace recovery | ≥ work bout duration | min | equal or slightly less `[§2 I-Pace]` |
  | R-pace recovery | 2-3× work bout duration | min | near-full recovery `[§2 R-Pace]` |
  | Phase length (ideal) | 6 | weeks | compress if total season < 24 weeks `[§5]` |
  | VDOT update window | 3-4 | weeks | minimum between updates `[§3]` |
  | Phase I (Foundation) | E + L + strides | — | No quality sessions `[§5]` |
  | Phase II (Repetition) | R-pace primary | — | Speed/economy focus `[§5]` |
  | Phase III (Interval) | I-pace primary | — | VO2max focus `[§5]` |
  | Phase IV (Threshold) | T-pace primary | — | Sharpening; mix T+R for short-distance `[§5]` |

  **Section 4 — Règles prescriptives** (derive from §3 Decision Rules — already IF/THEN, extract verbatim then reformat strictly):

  Include all rules from §3 "Pace Selection Logic", "Progression Logic", "Workout Substitution", "Scaling & Return-to-Running". Convert any rules not in strict IF/THEN form. Examples:
  - `IF runner provides recent race time THEN lookup VDOT in Table 5.1 THEN derive all paces from Table 5.2 [ref: §3]`
  - `IF runner has no recent race time AND has recent mile time THEN set R_pace = mile_race_pace THEN apply 6-Second Rule to derive I_pace and T_pace [ref: §3]`
  - `IF total T-pace volume in session > weekly_mileage × 10% THEN reduce T volume to cap [ref: §2 T-Pace]`
  - `IF break_duration ≤ 5 days THEN resume at 100% of previous load and VDOT [ref: §3]`
  - `IF break_duration is 6-28 days THEN reduce load to 50% for first half of return period THEN 75% for second half THEN adjust VDOT per Table 9.2 [ref: §3]`
  - All rules from §3 — keep verbatim, add `[ref: §3]` on each.

  **Section 5 — Contre-indications et cas limites** (derive from §1 Red Flags + §3):
  - Do not set VDOT from goal race time — current fitness only
  - Do not update VDOT more than once every 3-4 weeks even after new race
  - Do not run I-pace work bouts > 5 min — purpose changes above this threshold
  - Do not run R-pace work bouts > 2 min — purpose changes; form degrades
  - Do not train when sick or injured — enforce pause, no exceptions `[§0, §1]`
  - Phase III (I-pace) can be skipped for short seasons (<9 weeks); go I→IV directly `[§5]`
  - Altitude (≥7,000 ft): R-pace unchanged but recovery increased; I + T pace by effort not pace `[§3]`

  **Section 6 — Références sources**:

  | Concept | Référence livre |
  |---|---|
  | VDOT lookup table | Table 5.1 |
  | Training pace table | Table 5.2 |
  | Novice pace table | Table 5.3 |
  | Break duration / VDOT decay | Table 9.2 |
  | I-pace: faster ≠ better | Figure 4.3 |
  | Phase structure | §5 Week/Season Structure |
  | Decision rules (all) | §3 Decision Rules |

- [ ] **Step 3: Verify**

  Checklist before committing:
  - [ ] All 6 sections present and non-empty
  - [ ] Section 2: every row has Formule, Inputs, Output, Notes columns
  - [ ] Section 3: every row has Zone/Seuil, Valeur, Unité, Condition columns
  - [ ] Section 4: every rule starts with `IF` — zero narrative sentences
  - [ ] Section 4: every rule ends with `[ref: ...]`
  - [ ] Section 5: no soft language ("may", "could", "consider")

- [ ] **Step 4: Commit**

  ```bash
  git add docs/backend/books/daniels-running-formula-extract.md
  git commit -m "docs(books): extract Daniels' Running Formula — 6-section agent-actionable format"
  ```

---

## Task 2: Pfitzinger — Advanced Marathoning

**Files:**
- Read: `docs/training_books/advanced_marathoning_pete_pfitzinger.md`
- Create: `docs/backend/books/pfitzinger-advanced-marathoning-extract.md`

- [ ] **Step 1: Read source file**

  ```
  Read: docs/training_books/advanced_marathoning_pete_pfitzinger.md (270 lines)
  ```

  Key sections: §2 Vocabulary (7 workout types), §3 Decision Rules, §4 Workout Constructors, §5 Taper principles.

- [ ] **Step 2: Create extract file**

  Create `docs/backend/books/pfitzinger-advanced-marathoning-extract.md`.

  **Section 1 — Concepts fondamentaux**:
  - Physiological hierarchy for marathon: LT > running economy > VO2max (in priority order for training emphasis)
  - Periodization: 4 mesocycles (Base/Endurance → Peak Mileage/LT → Pre-Taper/Race-Specific → Taper)
  - Hard/Easy or Back-to-Back Hard then 2+ easy days — both valid; back-to-back useful near race weeks
  - Adaptation occurs during recovery, not during workout — recovery days are non-negotiable
  - Maximum long run: 22 miles (35 km) regardless of plan — law of diminishing returns above this
  - Taper = 3-week mandatory protocol with specific volume reductions while maintaining intensity
  - Tune-up races: 10-day block for 15K-25K (4-6 day mini-taper + race + recovery)
  - Weekly mileage increase: ≤10% per week OR ≤1 mile/session/week (whichever is less)

  **Section 2 — Formules et calculs**:

  | Formule | Inputs | Output | Notes |
  |---|---|---|---|
  | LT pace | current_15K_to_HM_race_pace | LT_pace | Equivalent to 82-91% MHR `[§2]` |
  | VO2max pace | current_5K_race_pace | VO2_pace | 93-95% MHR `[§2]` |
  | Long run pace | goal_marathon_pace | LR_pace = marathon_pace × 1.10-1.20 | 74-84% MHR `[§2]` |
  | General aerobic pace | goal_marathon_pace | GA_pace = marathon_pace × 1.15-1.25 | 70-81% MHR `[§2]` |
  | VO2max total volume cap | — | max = min(10,000 m, per session) | Exceeding → excessive fatigue `[§2]` |
  | Interval recovery | interval_time | recovery = 0.50-0.90 × interval_time | Slow jog `[§2 VO2max]` |
  | Taper week 1 | peak_mileage | taper_w1 = peak_mileage × 0.75-0.80 | 3 weeks before race `[§5]` |
  | Taper week 2 | peak_mileage | taper_w2 = peak_mileage × 0.60 | 2 weeks before race `[§5]` |
  | Taper week 3 (race week) | peak_mileage | taper_w3 = peak_mileage × 0.40 | 6 days before race `[§5]` |
  | Weekly mileage increase | current_weekly, runs_per_week | max_increase = min(current_weekly × 0.10, runs_per_week × 1 mi) | `[§3]` |
  | Cross-training substitute (cycling) | running_duration | cycling_duration = running_duration × 1.50 | `[§3]` |
  | Water running HR offset | land_target_HR | water_target_HR = land_target_HR × 0.90 | `[§3]` |
  | Tune-up race block | — | total = 4-6 days taper + race + recovery | For 15K-25K `[§5]` |

  **Section 3 — Tables de référence**:

  | Zone/Seuil | Valeur | Unité | Condition |
  |---|---|---|---|
  | LT HR | 82-91 | % MHR | OR 77-88% HRR `[§2]` |
  | LT HR (HRR) | 77-88 | % HRR | `[§2]` |
  | VO2max HR | 93-95 | % MHR | OR 91-94% HRR `[§2]` |
  | VO2max HR (HRR) | 91-94 | % HRR | `[§2]` |
  | Marathon-pace HR | 79-88 | % MHR | OR 73-84% HRR `[§2]` |
  | Long run HR | 74-84 | % MHR | OR 65-78% HRR `[§2]` |
  | General aerobic HR | 70-81 | % MHR | OR 62-75% HRR `[§2]` |
  | Recovery HR | < 76 | % MHR | OR < 70% HRR `[§2]` |
  | Max long run distance | 22 | miles / 35 km | Hard ceiling `[§2]` |
  | LT tempo duration | 20-40 | min | 7 miles max `[§2]` |
  | VO2max interval duration | 2-6 | min | Per rep (600m-1600m equiv.) `[§2]` |
  | Ferritin red flag | < 25 | ng/ml | Prompt physician consult `[§1]` |
  | Taper duration | 3 | weeks | Non-negotiable for marathon `[§5]` |
  | Strides duration | 80-120 | meters | Per repetition `[§2]` |

  **Section 4 — Règles prescriptives** (derive from §3 verbatim, reformat to strict IF/THEN):
  - `IF workout_type = 'VO2max' THEN pace = current_5K_race_pace [ref: §3]`
  - `IF workout_type = 'Lactate Threshold' THEN pace = current_15K_to_HM_race_pace [ref: §3]`
  - `IF workout_type = 'Long Run' THEN pace = goal_marathon_pace × 1.10-1.20 [ref: §3]`
  - `IF workout_type = 'General Aerobic' THEN pace = goal_marathon_pace × 1.15-1.25 [ref: §3]`
  - `IF workout_type = 'Recovery' THEN HR < 76% MHR [ref: §3]`
  - `IF increasing weekly mileage THEN limit increase to min(current × 10%, runs_per_week × 1 mi) [ref: §3]`
  - `IF increasing mileage THEN increase 1 week THEN hold 2-3 weeks before next increase [ref: §3]`
  - `IF in base-building phase THEN exclude VO2max intervals [ref: §3]`
  - `IF missed_training < 10 days THEN resume schedule at current week [ref: §3]`
  - `IF missed_training is 10-20 days AND marathon < 8 weeks away THEN advise goal revision [ref: §3]`
  - `IF missed_training > 20 days THEN advise goal revision regardless of time remaining [ref: §3]`
  - All cross-training substitution rules from §3
  - All taper rules from §5

  **Section 5 — Contre-indications et cas limites**:
  - Ferritin < 25 ng/ml → pause hard training, consult physician before resuming `[§1]`
  - Illness with systemic symptoms or fever → pause hard training (immune suppression 12-72h post-intense exercise) `[§1]`
  - Limping or worsening pain during run → stop immediately `[§1]`
  - VO2max intervals: frequency overuse detracts from marathon-specific LT + long run work `[§2]`
  - LT runs > 40 min / 7 mi → purpose degrades; no additional benefit `[§2]`
  - Long run > 22 mi → dramatically increased recovery cost for minimal added benefit `[§2]`
  - Water running target HR ~10% lower than land running equivalent effort `[§3]`

  **Section 6 — Références sources**:

  | Concept | Référence livre |
  |---|---|
  | HR zones per workout type | §2 Canonical Vocabulary |
  | Mileage progression rules | §3 Training Progression |
  | Missed training rules | §3 Scaling for Missed Training |
  | Taper volume reduction | §5 Tapering Principles |
  | Tune-up race block | §5 Incorporating Tune-Up Races |
  | Ferritin red flag | §1 Red Flags |

- [ ] **Step 3: Verify** (same checklist as Task 1)

- [ ] **Step 4: Commit**

  ```bash
  git add docs/backend/books/pfitzinger-advanced-marathoning-extract.md
  git commit -m "docs(books): extract Pfitzinger Advanced Marathoning — 6-section agent-actionable format"
  ```

---

## Task 3: Pfitzinger — Faster Road Racing (5K–Half Marathon)

**Files:**
- Read: `docs/training_books/faster_road_racing_pete_pfitzinger.md`
- Create: `docs/backend/books/pfitzinger-faster-road-racing-extract.md`

- [ ] **Step 1: Read source file**

  ```
  Read: docs/training_books/faster_road_racing_pete_pfitzinger.md (334 lines)
  ```

  Key sections: §2 Vocabulary (9 workout types), §3 Decision Rules (including masters age brackets), §4 Workout Constructors (5 types), §5 Taper + planning.

- [ ] **Step 2: Create extract file**

  Create `docs/backend/books/pfitzinger-faster-road-racing-extract.md`.

  **Section 1 — Concepts fondamentaux**:
  - Target distances: 5K, 8K, 10K, 15K, half marathon
  - LT improvement is the single best predictor of race performance for 8K–HM
  - Polarized training: hard days must be hard, easy days must be truly easy — no gray zone
  - Two-phase structure: Base (aerobic foundation) → Race-Specific (targeted quality)
  - Masters runners (40+) require extra recovery days after every hard session
  - Speed work = strides (15-25s) and power hills (8-15s) — short enough for maximal power
  - Supplementary training (strength 2-3×/week, plyometrics ≤2×/week) = injury prevention
  - Static stretching only when muscles are warm (post-run), 20-40s per stretch

  **Section 2 — Formules et calculs**:

  | Formule | Inputs | Output | Notes |
  |---|---|---|---|
  | Long run pace | current_10K_pace | LR_pace = 10K_pace × 1.20-1.33 | OR HM pace × 1.17-1.29 `[§2]` |
  | VO2max pace | — | current_3K_to_5K_race_pace | 95-100% VO2max `[§2]` |
  | LT pace | — | pace_sustainable_for_60min_race | HR 82-91% MHR or 77-88% HRR `[§2]` |
  | LT interval recovery | work_interval_duration | recovery = work_interval × 0.20-0.40 | Slow jog `[§2]` |
  | VO2max interval recovery | interval_duration | recovery = interval_duration × 0.50-0.90 | Slow jog `[§2]` |
  | Cross-training substitute (cycling) | running_duration | cycling = running_duration × 1.50-1.75 | `[§2]` |
  | Cross-training substitute (water/elliptical) | running_duration | duration ≈ running_duration | Same duration `[§2]` |
  | Stride duration | — | 15-25 | sec | `[§2]` |
  | Power hill duration | — | 8-15 | sec | Maximal intensity `[§2]` |
  | Weekly mileage increase cap | current_weekly | max_increase = current_weekly × 1.10 | `[§3]` |
  | Warm-up pre-race | — | ~45 min total | Finish ~5 min before start `[§2 Warm-Up]` |

  **Section 3 — Tables de référence**:

  | Zone/Seuil | Valeur | Unité | Condition |
  |---|---|---|---|
  | LT HR | 82-91 | % MHR | OR 77-88% HRR `[§2]` |
  | VO2max HR | 95-100 | % VO2max | ~93-95% MHR `[§2]` |
  | Long run HR | 74-84 | % MHR | OR 65-78% HRR `[§2]` |
  | General aerobic HR | 70-81 | % MHR | OR 62-75% HRR `[§2]` |
  | VO2max interval duration (min) | 2 | min | Minimum per rep `[§2]` |
  | VO2max interval duration (max) | 6 | min | Maximum per rep `[§2]` |
  | Masters 36-45: extra rest after VO2max | +1 | day | `[§3]` |
  | Masters 46-55: extra rest after VO2max | +2 | days | `[§3]` |
  | Masters 56-65: extra rest after VO2max | +2-3 | days | `[§3]` |
  | Masters 46-55: extra rest after Tempo/LR | +1 | day | `[§3]` |
  | Recovery after race (40-49, 5K) | ≥5 | days | Before next hard workout `[§3]` |
  | Recovery after race (50-59, 8K-10K) | ≥7 | days | `[§3]` |
  | Recovery after race (60-69, 15K-HM) | ≥10 | days | `[§3]` |
  | Masters taper extension | several | days | e.g., 17-day taper for goal race `[§5]` |
  | Strength training frequency | 2-3 | ×/week | `[§2]` |
  | Plyometrics frequency | ≤2 | ×/week | `[§2]` |
  | Strength timing | ≥24-36h | before hard run | `[§2]` |
  | Static stretch duration | 20-40 | sec | Only post-run `[§2]` |

  **Section 4 — Règles prescriptives** (derive from §3 verbatim):
  - All pace selection rules from §3
  - All masters age-bracket rules from §3 (exact values)
  - All workout substitution rules from §3
  - `IF illness_symptoms = 'below the chest' THEN stop training until recovered [ref: §3]`
  - `IF illness_symptoms = 'above the chest only' (e.g., runny nose) THEN proceed with caution; consider recovery run or rest day [ref: §3]`
  - `IF weather_is_hot_and_humid AND workout_type IN (VO2max, LT) THEN postpone or cancel workout [ref: §3]`
  - `IF runner_is_master THEN add extra recovery days per age bracket table before next hard session [ref: §3]`
  - `IF increasing_mileage THEN max_weekly_increase = current × 10%; hold new level ≥1 week before next increase [ref: §3]`
  - `IF increasing_mileage THEN reduce intensity (avoid VO2max work) during mileage build phase [ref: §3]`

  **Section 5 — Contre-indications et cas limites**:
  - Pain at injury site during run → stop immediately, do not modify and continue `[§1]`
  - VO2max intervals: if interval < 2 min, stimulus for VO2max is insufficient `[§2]`
  - VO2max intervals: if interval > 6 min, shifts to LT stimulus, not VO2max `[§2]`
  - LT intervals: if recovery > 40% of work bout, stimulus becomes discontinuous and less effective `[§2]`
  - Plyometrics: avoid when fatigued; rest ≥1 min between sets `[§2]`
  - Static stretching: never before run (reduces muscle strength temporarily) `[§2]`
  - Dynamic stretching should take ≤5 min pre-run `[§2]`

  **Section 6 — Références sources**:

  | Concept | Référence livre |
  |---|---|
  | HR zones per workout | §2 Canonical Vocabulary |
  | Masters recovery rules | §3 Scaling for Special Populations |
  | Pace selection rules | §3 Pace Selection Logic |
  | Illness decision rules | §3 Workout Substitution |
  | Taper masters extension | §5 Tapering Principles |

- [ ] **Step 3: Verify** (same checklist as Task 1)

- [ ] **Step 4: Commit**

  ```bash
  git add docs/backend/books/pfitzinger-faster-road-racing-extract.md
  git commit -m "docs(books): extract Pfitzinger Faster Road Racing — 6-section agent-actionable format"
  ```

---

## Task 4: Fitzgerald — 80/20 Running

**Files:**
- Read: `docs/training_books/80_20_matt_fitzgerald.md`
- Create: `docs/backend/books/fitzgerald-8020-extract.md`

- [ ] **Step 1: Read source file**

  ```
  Read: docs/training_books/80_20_matt_fitzgerald.md (212 lines)
  ```

  Key sections: §0 Core Philosophy, §2 Vocabulary (Low/Moderate/High intensity + LT + Cross-Training), §3 Decision Rules, §4 Workout Constructors (9 types), §5 Week/Season phases.

- [ ] **Step 2: Create extract file**

  Create `docs/backend/books/fitzgerald-8020-extract.md`.

  **Section 1 — Concepts fondamentaux**:
  - Foundational rule: 80% of total weekly training time at low intensity; 20% at moderate + high combined
  - Polarized training: easy must be easy, hard must be hard — moderate intensity is the enemy (the "rut")
  - Low intensity enables high volume; high volume = aerobic base + neurological optimization (running economy)
  - "Brain fitness": tolerance for suffering is a trainable attribute, developed by high-volume low-intensity work
  - Lactate Threshold (LT) = physiological anchor; LTHR determined by 30-min TT (avg HR final 10 min)
  - 5 intensity zones: Z1-Z2 = low, Z3 = moderate, Z4-Z5 = high
  - Quality sessions: max 2 per week; advanced athletes may occasionally do 3
  - Minimum 3 runs/week must be running (cross-training does not replace all)
  - Phase structure: Base (85-90% low) → Peak (80/20 or up to 77/23) → Taper (volume reduction)

  **Section 2 — Formules et calculs**:

  | Formule | Inputs | Output | Notes |
  |---|---|---|---|
  | LTHR field test | 30-min TT effort | LTHR = avg HR over final 10 min of TT | Primary method `[§2 LT]` |
  | Zone boundaries | LTHR | Z1-Z5 HR ranges | Use McMillan-equivalent tool for pace zones `[§3]` |
  | TID target | total_weekly_time | low_intensity_time ≥ weekly_time × 0.80 | Time-based, not distance `[§0]` |
  | Quality cap | — | quality_sessions ≤ 2/week (3 for advanced) | `[§5]` |
  | Post-race recovery week 1 | — | no structured runs; light activity only | `[§3]` |
  | Post-race recovery week 2 | — | 3-4 short low-intensity runs only | `[§3]` |
  | Return from break (>2 weeks) | planned_volume | first_week_volume = planned_volume × 0.50 | `[§3]` |

  **Section 3 — Tables de référence**:

  | Zone/Seuil | Valeur | Unité | Condition |
  |---|---|---|---|
  | Low intensity ceiling | Zone 2 top | — | ≤ ventilatory threshold `[§2]` |
  | Low intensity (Z1) RPE | ≤ 2 | / 10 | Recovery runs `[§4]` |
  | Low intensity (Z2) RPE | ≤ 4 | / 10 | Foundation + long runs `[§4]` |
  | Moderate intensity (Z3) | above VT, below LT | — | Tempo, cruise intervals `[§2]` |
  | High intensity (Z4) | above LT | — | Long intervals `[§2]` |
  | High intensity (Z5) | maximal | — | Short intervals `[§2]` |
  | Low intensity weekly target | ≥ 80 | % of weekly time | Time-based `[§0]` |
  | Base phase low intensity | 85-90 | % of weekly time | `[§5]` |
  | Peak phase low intensity | 77-80 | % of weekly time | `[§5]` |
  | Quality sessions per week | ≤ 2 (3 advanced) | per week | `[§5]` |
  | Min runs/week | ≥ 3 | runs | Cross-training cannot replace all `[§2]` |
  | Hill effort duration | 15-25 | sec/rep | Zone 4-5 `[§4 Hill Rep]` |

  **Section 4 — Règles prescriptives** (derive from §3 Decision Rules verbatim):
  - `IF valid_recent_race_time provided THEN calculate personalized pace zones via LTHR/McMillan model [ref: §3]`
  - `IF intensity_metric = HR AND workout_duration < 2 min THEN use RPE instead; HR lags too much [ref: §3]`
  - `IF terrain is hilly THEN use RPE or HR as intensity guide; not pace [ref: §3]`
  - `IF runner reports excessive_soreness OR unusual_fatigue OR minor_pain THEN substitute planned run with cross-training of equal duration and intended intensity [ref: §3]`
  - `IF runner reports mild fatigue (poor sleep, life stress) AND no pain AND no excessive soreness THEN proceed at lower end of prescribed zone [ref: §3]`
  - `IF return_from_break > 2 weeks THEN reduce planned volume by ≥50% for first week THEN build gradually; ignore formal plan until consistent base re-established [ref: §3]`
  - `IF runner is highly injury-prone THEN substitute 2-3 planned weekly runs with non-impact cardio [ref: §3]`
  - `IF runner completes goal race THEN enforce post-race protocol: week 1 no structured runs; week 2 3-4 short low-intensity runs only [ref: §3]`
  - `IF runner completes a training phase THEN advance to next phase; do not skip or reorder phases [ref: §3]`
  - All LTHR-based zone rules from §3

  **Section 5 — Contre-indications et cas limites**:
  - Stagnation + most runs feel "lousy" = diagnostic signal of moderate-intensity rut → enforce strict low-intensity discipline immediately `[§0]`
  - Cross-training does not fully replicate neuromuscular/biomechanical demands of running → ≥3 runs/week minimum `[§2]`
  - High-intensity sessions > 2/week → diminishing returns, overtraining, injury risk `[§2]`
  - Z4-Z5 Hill reps: use RPE not pace (gradient invalidates pace as intensity proxy) `[§4]`
  - LTHR field test: if effort too easy or too hard, zone calculations are invalid → retest `[§2]`

  **Section 6 — Références sources**:

  | Concept | Référence livre |
  |---|---|
  | TID 80/20 rule | §0 Core Philosophy |
  | LTHR field test method | §2 Lactate Threshold |
  | Zone boundaries | §2 Lactate Threshold + §3 |
  | RPE for short intervals / hills | §3 Pace/Intensity Selection |
  | Post-race recovery protocol | §3 Plan Advancement Logic |
  | Phase TID percentages | §5 Week/Season Structure |

- [ ] **Step 3: Verify** (same checklist as Task 1)

- [ ] **Step 4: Commit**

  ```bash
  git add docs/backend/books/fitzgerald-8020-extract.md
  git commit -m "docs(books): extract Fitzgerald 80/20 Running — 6-section agent-actionable format"
  ```

---

## Task 5: Pierce — Run Less Run Faster (FIRST)

**Files:**
- Read: `docs/training_books/run_less_run_faster_bill_pierce.md`
- Create: `docs/backend/books/pierce-first-extract.md`

- [ ] **Step 1: Read source file**

  ```
  Read: docs/training_books/run_less_run_faster_bill_pierce.md (193 lines)
  ```

  Key sections: §0 Core tenets, §2 Vocabulary (3 key runs + XT), §3 Decision Rules, §4 Constructors, §5 Week/season structure.

- [ ] **Step 2: Create extract file**

  Create `docs/backend/books/pierce-first-extract.md`.

  **Section 1 — Concepts fondamentaux**:
  - FIRST structure: "3plus2" — 3 key runs/week + 2 cross-training sessions; no optional easy runs
  - Every run = "Training with Purpose" — no junk miles; each key run has specific pace + distance
  - 3 key run types: Track Repeats (speed/VO2max), Tempo Run (LT), Long Run (endurance)
  - Cross-training: non-weight-bearing only (cycling, swimming, rowing) — not elliptical, not additional running
  - All paces derived from recent 5K time via program's official pace tables
  - Long runs are faster than other programs' long runs — challenge pacing, not conversational
  - Required mileage base before starting: 15 mi/week (5K/10K); 25 mi/week (marathon)
  - Year structured as two seasons: spring (5K/10K for speed) + fall (HM/marathon for endurance)
  - Taper: skip all cross-training in race week; reduce all 3 key runs per final week schedule

  **Section 2 — Formules et calculs**:

  | Formule | Inputs | Output | Notes |
  |---|---|---|---|
  | All training paces | recent_5K_time | KR1_pace (repeats), KR2_pace (tempo), KR3_pace (long) | Via program's official pace tables `[§2]` |
  | Long run pace | goal_marathon_pace | LR_pace = marathon_pace + 15-45 sec/mi | Offset decreases as race approaches `[§2]` |
  | Tempo distance (5K/10K plan) | — | 3-5 | miles | Per session `[§2]` |
  | Tempo distance (marathon plan) | — | 8-10 | miles | Per session `[§2]` |
  | Required base (5K/10K) | — | ≥15 mi/week × 3 months | Before starting plan `[§3]` |
  | Required base (marathon) | — | ≥25 mi/week | Before starting plan `[§3]` |
  | Max long run (marathon) | — | 20 | miles | Hard ceiling `[§2]` |
  | Post-marathon recovery week 1 | — | no running | `[§3]` |
  | Post-marathon recovery week 2 | — | easy runs only | `[§3]` |
  | Post-marathon recovery week 3 | — | ≤ 90% effort | Before full resumption `[§3]` |
  | Post-HM week 1 | — | full rest day + substitute KR1/KR2 with easy runs | `[§3]` |
  | Post-HM week 2 | — | long run = half normal distance at easy pace | `[§3]` |
  | Pace adherence flag | — | flag if repeat > 2-3 sec/400m faster than prescribed | `[§4]` |

  **Section 3 — Tables de référence**:

  | Zone/Seuil | Valeur | Unité | Condition |
  |---|---|---|---|
  | Key runs per week | 3 | runs | Non-negotiable `[§0]` |
  | Cross-training per week | 2 | sessions | Non-weight-bearing `[§0]` |
  | Rest days per week | 1-2 | days | Day 5 + optional Day 7 `[§5]` |
  | Track Repeats: pace deviation flag | > 2-3 | sec/400m | Faster than prescribed → flag `[§4]` |
  | Tempo segment (5K/10K) | 3-5 | miles | Per workout `[§2]` |
  | Tempo segment (marathon) | 8-10 | miles | Per workout `[§2]` |
  | Max long run | 20 | miles | Marathon plans `[§2]` |
  | Standard plan length | 12-16 | weeks | By goal distance `[§5]` |
  | Required base (5K/10K) | 15 | mi/week × 3 months | Pre-plan prerequisite `[§3]` |
  | Required base (marathon) | 25 | mi/week | Pre-plan prerequisite `[§3]` |
  | Medical clearance age trigger | > 40 | years | Always `[§1]` |

  **Section 4 — Règles prescriptives** (derive from §3 verbatim):
  - `IF runner provides valid recent 5K time THEN set all KR paces using program's official pace tables [ref: §3]`
  - `IF all 3 key runs completed at prescribed paces without overtraining signs THEN advance to next week's plan [ref: §3]`
  - `IF all key workouts consistently feel easy THEN recommend faster reference 5K (new race or realistic estimate) to recalibrate all paces [ref: §3]`
  - `IF runner lacks required mileage base THEN do not start FIRST plan; prescribe 3-month base-building phase first [ref: §3]`
  - `IF goal_race_course is hilly THEN incorporate hills into Tempo and Long runs; maintain constant effort not constant pace [ref: §3]`
  - `IF minor injury reported (non-debilitating) THEN reduce distance and pace of next key run [ref: §3]`
  - `IF injury symptom persists or worsens THEN reduce run frequency AND substitute with non-weight-bearing cross-training [ref: §3]`
  - `IF workout must be missed THEN prioritize completing 3 key runs over cross-training sessions; do not double up to "make up" [ref: §3]`
  - `IF returning from marathon THEN enforce 3-week recovery: week 1 no running, week 2 easy only, week 3 ≤90% [ref: §3]`
  - `IF returning from half marathon THEN enforce 2-week recovery: week 1 rest + sub KR1/KR2 with easy; week 2 half-distance long run at easy pace [ref: §3]`

  **Section 5 — Contre-indications et cas limites**:
  - Runner over 40 → mandatory physician clearance before starting program `[§1]`
  - Elliptical and stair climber are weight-bearing → NOT valid cross-training substitutes `[§2]`
  - Yoga, P90X etc. improve strength/flexibility but do NOT replace core aerobic XT sessions `[§2]`
  - Cross-training at low intensity when "tempo" effort is prescribed → insufficient training stimulus `[§2]`
  - Running 3 key runs at faster than prescribed pace → defeats purpose; VO2max gains plateau; fatigue accumulates `[§0]`
  - Heat-related symptoms (disorientation, muscle spasms, cessation of sweating) → stop immediately, seek shade, hydrate `[§1]`
  - Trying to "bank" time on long runs (running faster than target) → compromises taper and race-day execution `[§2]`

  **Section 6 — Références sources**:

  | Concept | Référence livre |
  |---|---|
  | 3plus2 program structure | §0 Core Tenets |
  | Pace tables (all key runs) | §2 Canonical Vocabulary + §4 Constructors |
  | Required mileage base | §3 Scaling & Onboarding |
  | Post-race recovery protocols | §3 Scaling & Onboarding |
  | Weekly schedule template | §5 Standard Weekly Layout |
  | Taper rules | §5 Tapering Principles |

- [ ] **Step 3: Verify** (same checklist as Task 1)

- [ ] **Step 4: Commit**

  ```bash
  git add docs/backend/books/pierce-first-extract.md
  git commit -m "docs(books): extract Pierce Run Less Run Faster (FIRST) — 6-section agent-actionable format"
  ```

---

## Task 6: INDEX.md

**Files:**
- Read: all 5 `docs/backend/books/*-extract.md` files
- Create: `docs/backend/books/INDEX.md`

- [ ] **Step 1: Read all 5 extract files**

  ```
  Read all 5 files created in Tasks 1-5.
  ```

- [ ] **Step 2: Create INDEX.md**

  Create `docs/backend/books/INDEX.md` with 3 sections:

  **Section 1 — Coverage matrix**

  Concepts in rows, books in columns (✅ = covered, — = not covered, ⚠️ = conflicts with another book). Include all major concepts:
  - VDOT / race-based pace zones
  - 80/20 TID
  - Polarized training
  - Training phases (number and type)
  - LT pace definition
  - VO2max interval specs
  - Long run caps (distance/time)
  - Taper protocol (weeks, reductions)
  - Masters-specific adjustments
  - Return from break rules
  - Post-race recovery
  - Mileage progression cap (10% rule)
  - Required mileage base
  - Illness rules
  - Ferritin red flag
  - Cross-training substitution ratios
  - HR zones by workout

  Flag conflicts explicitly (⚠️) — e.g., long run pace differs between Daniels/Pfitzinger/Pierce.

  **Section 2 — JSON integration candidates**

  Table: concept, file path to update, example value, source book.

  Key candidates for `.bmad-core/data/running-zones.json` (already exists):
  - Pfitzinger Advanced HR zones: `{ "LT": {"hr_pct_max": [82, 91], "hr_pct_hrr": [77, 88]} ... }`
  - Pfitzinger Faster HR zones (same as above + masters recovery table)
  - 80/20 zone definitions: Z1-Z5 from LTHR

  Candidates for new JSON `docs/backend/books/running-formulas.json` (proposed):
  - VDOT volume caps (Daniels)
  - Masters recovery extra days table (Pfitzinger Faster)
  - Post-race recovery protocols (80/20 + FIRST)

  **Section 3 — Agent prompt candidates**

  Table: rule text, agent (Running Coach / Head Coach), source book.

  Key candidates for `backend/app/agents/prompts.py`:

  | Rule | Agent | Source |
  |---|---|---|
  | `IF sick THEN pause training` | Head Coach (veto rule) | All books |
  | `IF ferritin < 25 ng/ml THEN pause hard training` | Recovery Coach + Head Coach | Pfitzinger Advanced |
  | `IF pain worsens during run THEN stop` | Head Coach (veto rule) | Pfitzinger Faster |
  | `IF VDOT derived from goal pace not current race THEN override with current race pace` | Running Coach | Daniels |
  | `IF break > 8 weeks THEN VDOT × 0.80-0.92` | Running Coach | Daniels |
  | Masters age-bracket extra recovery days | Running Coach | Pfitzinger Faster |
  | 80% low intensity weekly TID target | Running Coach | Fitzgerald |
  | Post-race recovery protocol (week 1/2) | Running Coach + Recovery Coach | Fitzgerald + FIRST |

- [ ] **Step 3: Verify INDEX**

  Checklist:
  - [ ] Every extract file is referenced in the coverage matrix
  - [ ] All ⚠️ conflicts are explained (not just flagged)
  - [ ] JSON candidates include the specific key path in the target file
  - [ ] Prompt candidates reference the exact agent and section of `prompts.py`
  - [ ] INDEX contains no duplicate content from extract files — pointers only

- [ ] **Step 4: Commit**

  ```bash
  git add docs/backend/books/INDEX.md
  git commit -m "docs(books): add INDEX.md — coverage matrix, JSON candidates, agent prompt candidates"
  ```

---

## Self-Review

**Spec coverage check:**
- ✅ 5 books → 5 extract files
- ✅ Standard 6-section format with exact columns per section
- ✅ Section 4: strict IF/THEN format with `[ref: ...]` required
- ✅ Citations via table/section name (not page numbers — source files have none)
- ✅ Post-extraction: JSON candidates + agent prompt candidates in INDEX
- ✅ INDEX.md with coverage matrix
- ✅ Atomic commit per book
- ✅ `docs/training_books/` files untouched

**Placeholder scan:** No TBD, no "implement later", no "fill in" present.

**Content consistency:** Section column headers identical across all 5 tasks. `[ref: §X]` format consistent.
