# Knowledge JSONs Enrichment — V3-N2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich all 9 knowledge JSON files using book extractions as primary source and external science as secondary, raising total rules from 111 to ~175–185 with full source provenance.

**Architecture:** Each JSON file in `docs/knowledge/` is processed independently: backup → add rules → validate with existing 90 parametrized tests → commit. No schema changes. No code changes. Tier 1 (running, book-rich) first, Tier 2 (book-indirect) second, Tier 3 (science-only) last.

**Tech Stack:** JSON, pytest, jsonschema. Test file: `tests/backend/test_knowledge_jsons.py` (90 parametrized tests, schema compliance only).

**pytest command (Windows):**
```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

---

## Task 1: Baseline verification + git sync

**Files:**
- Read: `tests/backend/test_knowledge_jsons.py`

- [ ] **Step 1: Pull latest**

```bash
git pull --rebase origin main
```

Expected: fast-forward or already up to date.

- [ ] **Step 2: Verify baseline tests pass**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed` — all 10 test types × 9 files. If any fail, stop and investigate before proceeding.

---

## Task 2: Enrich `running_coach_tid_rules.json` (Tier 1 — book-rich)

**Files:**
- Modify: `docs/knowledge/running_coach_tid_rules.json`

**Context:** Currently 20 rules, all 5 books already in `source_books`. Adding 9 rules covering M-pace zone, Daniels phase structure, FIRST model, Pfitz-FRR specifics, adverse weather substitution, Pfitz-FRR taper, and two return-from-break protocols. Target: 29 rules.

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/running_coach_tid_rules.json docs/knowledge/running_coach_tid_rules.json.backup
```

- [ ] **Step 2: Add rules — append to `extracted_rules` array**

Open `docs/knowledge/running_coach_tid_rules.json`. Before the final `]` of `extracted_rules`, add a comma after the last rule, then append:

```json
    {
      "rule_name": "Marathon pace (M-pace) zone",
      "category": "Pace Zones",
      "condition": "If scheduling a marathon-pace run or goal marathon-pace segment within a long run",
      "action": "Run at current goal marathon pace; embed M-pace in long runs or as standalone medium-long runs; effort is controlled and sustainable for 26.2 miles",
      "formula_or_value": "M-pace: 75-84% vVO2max; 75-84% HRmax; volume embedded in long run = unlimited; standalone M-pace run capped at 29% of weekly mileage",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula, 3rd ed., §2 M-Pace",
      "applies_to": ["running"]
    },
    {
      "rule_name": "4-phase training structure — Daniels model",
      "category": "Periodization",
      "condition": "When structuring a seasonal training plan for a runner",
      "action": "Apply Daniels 4-phase structure: Phase I (Foundation/E+L), Phase II (Repetition/R), Phase III (Interval/I), Phase IV (Threshold/T); compress proportionally if season <24 weeks",
      "formula_or_value": "Phase I: E-pace + Long runs; Phase II: R-pace reps (economy); Phase III: I-pace intervals (VO2max); Phase IV: T-pace tempo (threshold); ideal duration: 6 weeks/phase; season <24 weeks: compress each phase to 4 weeks",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula, 3rd ed., §5 Training Plans",
      "applies_to": ["running"]
    },
    {
      "rule_name": "FIRST 3-run-only model — structural constraint",
      "category": "Session Structure",
      "condition": "If athlete is following a FIRST (Run Less, Run Faster) training model",
      "action": "Prescribe exactly 3 key runs per week: Track Repeats (TR, Z4-5), Tempo Run (TMP, Z3), Long Run (LR, Z1-2); mandate 2 non-weight-bearing cross-training sessions per week; adding a 4th run defeats the model",
      "formula_or_value": "TR: 5K pace or faster (Z4-5, 1 session); TMP: 10K-HM pace (Z3, 1 session); LR: goal MP+45-90s/mile (Z1-2, 1 session); XT: 2×/week non-weight-bearing (cycling, swimming, elliptical excluded); 4th run = model violation",
      "priority": "high",
      "confidence": "strong",
      "source": "Pierce, Murr & Moss, Run Less Run Faster (FIRST program)",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Pfitz-FRR VO2max repetitions — 5K/10K specificity",
      "category": "Session Structure",
      "condition": "If athlete is on a 5K or 10K plan and scheduling a VO2max-targeted interval session",
      "action": "Prescribe 600m-1 mile repeats at 5K race pace with full recovery intervals; use only during 5K/10K-specific plan weeks, not marathon prep",
      "formula_or_value": "Rep distance: 600m-1 mile at 5K race pace; recovery: full jog equal duration; reps: 4-6; total VO2max volume: 4-6 km per session; not applicable in marathon or >10K blocks",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Latter, Faster Road Racing",
      "applies_to": ["running"]
    },
    {
      "rule_name": "General Aerobic (GA) run — Pfitz-Adv definition",
      "category": "Pace Zones",
      "condition": "When scheduling a medium-effort aerobic run that is not a recovery run and not a quality session",
      "action": "Assign General Aerobic pace: MP+15-25% slower than goal marathon pace; fills the majority of non-quality weekly mileage; never slower than E-pace",
      "formula_or_value": "GA pace: marathon_pace × 1.15 to marathon_pace × 1.25; HR: approximately 73-84% HRmax; typical run duration: 60-110 min",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Douglas, Advanced Marathoning",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Adverse weather — quality session substitution",
      "category": "Session Structure",
      "condition": "If a quality session (T/I/R-pace) is scheduled and weather is adverse (high wind, ice, extreme heat)",
      "action": "Swap the quality day with a scheduled E-day; perform the quality session when weather improves; acceptable substitutes: fartlek or hard hill repeats to achieve similar physiological stimulus",
      "formula_or_value": "Option A: swap Q-day with E-day in same week; Option B: substitute fartlek (unstructured) or hill repeats (same CV stimulus without pace precision required); pace targets secondary to physiological effort",
      "priority": "medium",
      "confidence": "strong",
      "source": "Daniels' Running Formula, 3rd ed., §3 Workout Substitution Logic",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Pfitz-FRR taper structure — sub-marathon distances",
      "category": "Taper",
      "condition": "If athlete is tapering for a 5K, 10K, or half-marathon",
      "action": "Apply distance-specific taper: shorter taper for 5K, longer for half-marathon; reduce volume progressively while maintaining intensity",
      "formula_or_value": "5K taper: 1-2 weeks; Week-1: -20-25%, Week-2 (race week): -35-40%; 10K taper: 2 weeks; Week-1: -20-25%, Week-2: -35-40%; HM taper: 2-3 weeks; Week-1: -20-25%, Week-2: -35-40%, Week-3: -50-60%; intensity sessions maintained throughout",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Latter, Faster Road Racing",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Return from break — Pfitz protocol (>20 days)",
      "category": "Return to Training",
      "condition": "If athlete returns after a break of more than 20 days",
      "action": "Skip all missed sessions entirely; revise goal race time downward; do not attempt to make up lost volume; resume with easy weeks and reassess fitness before setting new goals",
      "formula_or_value": "Break >20 days: zero makeup sessions; weeks 1-2: Z1-Z2 only at 50-60% of pre-break volume; revise goal race time; reassess pace targets after 3-4 weeks of resumed training",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Douglas, Advanced Marathoning",
      "applies_to": ["running"]
    },
    {
      "rule_name": "80/20 return from break (>2 weeks)",
      "category": "Return to Training",
      "condition": "If an athlete following the 80/20 model returns after a break of more than 2 weeks",
      "action": "First week back at 50% of pre-break volume; maintain 80/20 TID from the first session back; reduce volume, not intensity distribution",
      "formula_or_value": "Break >2 weeks: week 1 = 50% volume, full 80/20 TID; week 2 = 70% volume; week 3 = 85%; week 4 = full volume if no adverse HRV or fatigue signals",
      "priority": "medium",
      "confidence": "strong",
      "source": "Fitzgerald, 80/20 Running",
      "applies_to": ["running"]
    }
```

Also update `last_updated` to `"2026-04-14"`.

- [ ] **Step 3: Validate JSON is well-formed**

```bash
python -c "import json; json.load(open('docs/knowledge/running_coach_tid_rules.json'))" && echo OK
```

Expected: `OK`

- [ ] **Step 4: Run tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 5: Commit**

```bash
git add docs/knowledge/running_coach_tid_rules.json docs/knowledge/running_coach_tid_rules.json.backup
git commit -m "feat(knowledge): enrich running_coach_tid — M-pace, phases, FIRST, Pfitz-FRR taper, return protocols"
```

---

## Task 3: Enrich `head_coach_acwr_rules.json` (Tier 2 — book-indirect)

**Files:**
- Modify: `docs/knowledge/head_coach_acwr_rules.json`

**Context:** Currently 10 rules, `source_books: []`. Adding training monotony, strain composite, post-marathon recovery block, back-to-back advanced rule, session variety, compound HRV+ACWR flag, and single-session spike cap. Also updating envelope `source_books`. Target: 17 rules.

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/head_coach_acwr_rules.json docs/knowledge/head_coach_acwr_rules.json.backup
```

- [ ] **Step 2: Update `source_books` envelope and `last_updated`**

Change:
```json
"source_books": [],
"last_updated": "2026-04-13",
```
To:
```json
"source_books": ["daniels-running-formula", "pfitzinger-advanced-marathoning"],
"last_updated": "2026-04-14",
```

- [ ] **Step 3: Add rules — append to `extracted_rules` array**

Before the final `]` of `extracted_rules`, add a comma after the last existing rule, then append:

```json
    {
      "rule_name": "Training monotony index — Foster protocol",
      "category": "Load Calculation",
      "condition": "When computing weekly training load quality for any athlete",
      "action": "Calculate training monotony; monotony >2.0 indicates dangerous daily load uniformity and elevated illness/injury risk; prescribe session variety to reduce monotony",
      "formula_or_value": "monotony = weekly_avg_daily_load / StdDev(daily_loads); monotony >2.0: elevated illness/injury risk; ideal: 1.0-1.5 (varied sessions)",
      "priority": "high",
      "confidence": "strong",
      "source": "Foster 1998 training monotony and strain; session RPE method",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Training strain composite — weekly load × monotony",
      "category": "Load Calculation",
      "condition": "When evaluating overall weekly training stress and illness/injury risk",
      "action": "Compute training strain as the product of weekly total load and monotony; strain >6000 arbitrary units signals high illness risk; alert Head Coach",
      "formula_or_value": "strain = weekly_total_load × monotony; strain >6000: high illness/injury risk flag; strain >8000: mandatory load reduction",
      "priority": "high",
      "confidence": "strong",
      "source": "Foster 1998; Impellizzeri et al. 2004 session-RPE training monitoring",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Post-marathon mandatory recovery block",
      "category": "Load Management",
      "condition": "After an athlete completes a marathon or ultra-endurance event (>3h)",
      "action": "Enforce mandatory recovery block before resuming quality training; do not allow ACWR to increase during this block",
      "formula_or_value": "Post-marathon: 1 week complete rest (no structured training) + 1 week Z1-only easy (ACWR floor ≤0.5) + 1 week transition (Z1-Z2, ACWR ≤0.8) before any quality sessions",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Douglas, Advanced Marathoning; post-marathon recovery consensus",
      "applies_to": ["running"]
    },
    {
      "rule_name": "Back-to-back hard days — advanced athlete exception",
      "category": "Load Management",
      "condition": "If athlete is advanced (>60 mi/week or >10h training/week) and weekly structure demands consecutive hard days",
      "action": "Permit back-to-back hard days maximum 1 occurrence per month; must be followed by 2 mandatory easy days; never two back-to-back hard weeks",
      "formula_or_value": "Back-to-back hard days: max 1×/month, advanced athletes only (>60 mi/wk or >10h/wk); mandatory: 2 easy days after; ACWR must be <1.3 before attempting",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Pfitzinger & Douglas, Advanced Marathoning; concurrent training tolerance research",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "Session variety for monotony prevention",
      "category": "Load Management",
      "condition": "If the same session type (same zone, same duration) is repeated more than 3 consecutive days",
      "action": "Prescribe a different session type or intensity zone; identical daily sessions inflate monotony index above safe threshold",
      "formula_or_value": "Identical session type >3 consecutive days: flag monotony risk; solution: vary zone (Z1→Z2), duration (short→long), or modality (run→bike); daily load variance target: StdDev ≥ 30% of daily mean",
      "priority": "medium",
      "confidence": "strong",
      "source": "Daniels' Running Formula §2 variety principle; Foster 1998 monotony model",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "ACWR + HRV compound danger flag",
      "category": "Load Management",
      "condition": "If athlete's ACWR is >1.3 AND morning RMSSD is <15ms on the same day",
      "action": "Apply compound danger flag: mandatory load reduction; no hard or threshold sessions; injury and illness risk substantially elevated beyond either signal alone",
      "formula_or_value": "ACWR >1.3 + RMSSD <15ms: compound danger flag; mandatory: replace all Z3+ sessions with Z1 only; reassess both signals next morning before any load increase",
      "priority": "high",
      "confidence": "strong",
      "source": "Gabbett 2016 ACWR injury model; Plews et al. 2013 HRV readiness; combined load-readiness research",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Single-session load spike cap",
      "category": "Load Management",
      "condition": "When planning any individual training session",
      "action": "Cap any single session's load at 1.5× the athlete's 7-day average daily load; even if the weekly total is within the 10% cap, a single spike elevates acute injury risk",
      "formula_or_value": "Single session load ≤ EWMA_7d_daily_load × 1.5; if planned session exceeds this: split into two sessions or reduce volume",
      "priority": "high",
      "confidence": "moderate",
      "source": "Hulin et al. 2014 single-session spike and injury risk; Gabbett 2016",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    }
```

- [ ] **Step 4: Validate JSON**

```bash
python -c "import json; json.load(open('docs/knowledge/head_coach_acwr_rules.json'))" && echo OK
```

Expected: `OK`

- [ ] **Step 5: Run tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 6: Commit**

```bash
git add docs/knowledge/head_coach_acwr_rules.json docs/knowledge/head_coach_acwr_rules.json.backup
git commit -m "feat(knowledge): enrich head_coach_acwr — monotony, strain, compound flag, recovery block"
```

---

## Task 4: Enrich `head_coach_interference_rules.json` (Tier 2 — book-indirect)

**Files:**
- Modify: `docs/knowledge/head_coach_interference_rules.json`

**Context:** Currently 10 rules. `session order`, `6h gap`, `AMPK/mTOR`, and `frequency` rules already exist — do NOT duplicate. Adding: FIRST XT buffer, Pfitz strength-before-long-run specifics, block periodization, taper strength protocol, intra-day double session default. Target: 15 rules. Update `source_books` envelope.

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/head_coach_interference_rules.json docs/knowledge/head_coach_interference_rules.json.backup
```

- [ ] **Step 2: Update `source_books` envelope and `last_updated`**

Change:
```json
"source_books": [],
"last_updated": "2026-04-13",
```
To:
```json
"source_books": ["pfitzinger-advanced-marathoning", "pierce-first"],
"last_updated": "2026-04-14",
```

- [ ] **Step 3: Add rules — append to `extracted_rules` array**

Before the final `]` of `extracted_rules`, add a comma after the last existing rule, then append:

```json
    {
      "rule_name": "FIRST cross-training as interference buffer",
      "category": "Session Scheduling",
      "condition": "If a hybrid athlete needs active recovery on a high-stress week without adding CNS or mechanical load",
      "action": "Prescribe FIRST-style non-weight-bearing cross-training (cycling, swimming) as interference-free active recovery; preserves aerobic load without adding musculoskeletal stress",
      "formula_or_value": "Non-weight-bearing XT: cycling or pool running; CNS load ≈ 0; mechanical stress ≈ 0; aerobic load maintained; use on days where running interference with strength is a concern",
      "priority": "medium",
      "confidence": "strong",
      "source": "Pierce, Murr & Moss, Run Less Run Faster (FIRST); cross-training interference research",
      "applies_to": ["running", "cycling", "lifting"]
    },
    {
      "rule_name": "Strength before long run — Pfitz sequencing",
      "category": "Session Scheduling",
      "condition": "If a heavy lower-body strength session and a long run are scheduled within 24 hours of each other",
      "action": "Always perform the strength session before the long run, not after; residual fatigue from a long run degrades strength quality more than the reverse",
      "formula_or_value": "Order: Strength → (rest ≥6h or next morning) → Long Run; reverse order (Long Run → Strength) reduces peak force output by 15-25% in the strength session",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Douglas, Advanced Marathoning; concurrent training sequencing meta-analysis",
      "applies_to": ["running", "lifting"]
    },
    {
      "rule_name": "Block periodization for interference reduction",
      "category": "Periodization",
      "condition": "When designing an annual training plan for a hybrid endurance-strength athlete",
      "action": "Consider alternating 4-week strength-emphasis blocks and 4-week endurance-emphasis blocks rather than concurrent year-round programming; reduces chronic interference vs simultaneous high loads",
      "formula_or_value": "Strength block: 3-4 sessions/week at MAV-MRV; endurance at MEV; Endurance block: 4-6 sessions/week at peak volume; strength at MEV (maintenance); transition week: 1 deload between blocks",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Issurin 2010 block periodization theory; concurrent training interference meta-analysis",
      "applies_to": ["running", "cycling", "lifting"]
    },
    {
      "rule_name": "Taper period strength protocol",
      "category": "Session Scheduling",
      "condition": "During the taper phase (final 2-3 weeks before A-race)",
      "action": "Reduce strength training to MEV (maintenance); maintain intensity, reduce volume by 40-60%; avoid DOMS-inducing sessions within 7 days of A-race",
      "formula_or_value": "Taper strength: MEV sets/week (8-10 sets/muscle group); load unchanged; volume cut 40-60%; no novel exercises; no eccentric-heavy work (Nordic curls, tempo squats) within 7 days of race",
      "priority": "high",
      "confidence": "strong",
      "source": "Concurrent training taper consensus; Pfitzinger & Douglas, Advanced Marathoning (taper principles applied to strength)",
      "applies_to": ["running", "cycling", "lifting"]
    },
    {
      "rule_name": "Double session same-day default ordering",
      "category": "Session Scheduling",
      "condition": "If two training sessions are scheduled on the same day with any combination of modalities",
      "action": "Follow fixed priority ordering based on goal; default for hybrid athletes: endurance AM + strength PM is acceptable, but strength AM + quality run PM is not",
      "formula_or_value": "Priority A (strength-primary): Strength AM → Endurance PM (if endurance is aerobic/Z1-Z2); Priority B (endurance-primary): Easy run AM → Strength PM; NEVER: Hard endurance (Z3+) AM → Strength PM same day",
      "priority": "high",
      "confidence": "strong",
      "source": "Coffey & Hawley 2017; concurrent training sequencing research consensus",
      "applies_to": ["running", "cycling", "lifting"]
    }
```

- [ ] **Step 4: Validate JSON**

```bash
python -c "import json; json.load(open('docs/knowledge/head_coach_interference_rules.json'))" && echo OK
```

Expected: `OK`

- [ ] **Step 5: Run tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 6: Commit**

```bash
git add docs/knowledge/head_coach_interference_rules.json docs/knowledge/head_coach_interference_rules.json.backup
git commit -m "feat(knowledge): enrich head_coach_interference — FIRST XT, Pfitz sequencing, block periodization, taper"
```

---

## Task 5: Enrich `nutrition_coach_fueling_rules.json` (Tier 2 — book-indirect)

**Files:**
- Modify: `docs/knowledge/nutrition_coach_fueling_rules.json`

**Context:** Currently 12 rules, `source_books: []`. Adding race-week carb loading (Pfitz), electrolytes/sodium, pre-long-run fueling (Pfitz), caffeine ergogenic, protein + post-long-run, altitude adjustment. Target: 18 rules. Update `source_books`.

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/nutrition_coach_fueling_rules.json docs/knowledge/nutrition_coach_fueling_rules.json.backup
```

- [ ] **Step 2: Update `source_books` envelope and `last_updated`**

Change:
```json
"source_books": [],
"last_updated": "2026-04-13",
```
To:
```json
"source_books": ["pfitzinger-advanced-marathoning"],
"last_updated": "2026-04-14",
```

- [ ] **Step 3: Add rules — append to `extracted_rules` array**

Before the final `]` of `extracted_rules`, add a comma after the last rule, then append:

```json
    {
      "rule_name": "Race-week carbohydrate loading — Pfitz protocol",
      "category": "Pre-Race Nutrition",
      "condition": "In the 48 hours before a marathon or endurance event lasting >90 minutes",
      "action": "Load carbohydrates to maximize muscle glycogen; use only familiar foods; do not introduce new foods race week",
      "formula_or_value": "Carb loading: 8-12 g/kg/day for 48h pre-race; reduce fiber and fat intake; increase simple carbohydrates; familiar foods only; no dietary experiments race week",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Douglas, Advanced Marathoning Ch.9; Burke et al. 2011 carbohydrate loading",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "Electrolytes and sodium — intra-race protocol",
      "category": "Intra-Workout Nutrition",
      "condition": "During endurance efforts lasting more than 90 minutes",
      "action": "Supplement with sodium to prevent hyponatremia; combine with fluid intake at each aid station",
      "formula_or_value": "Sodium: 500-700 mg/hour for efforts >90 min; combine with 400-600 ml fluid/hour; sweat rate adjustment: high sweat rate (>1L/h) → upper bound 700mg; sodium sources: salt tabs, electrolyte drinks, pretzels",
      "priority": "high",
      "confidence": "strong",
      "source": "ACSM Position Stand 2007 (Sawka et al.); sodium and hyponatremia prevention research",
      "applies_to": ["running", "cycling", "swimming"]
    },
    {
      "rule_name": "Pre-long-run fueling — Pfitz protocol",
      "category": "Pre-Workout Nutrition",
      "condition": "Before any long run session exceeding 90 minutes",
      "action": "Consume carbohydrate-rich meal 2-3 hours before; practice this protocol in all long training runs to gut-train for race day",
      "formula_or_value": "2-3h before long run: 1-4 g/kg carbohydrates + moderate protein; low fat, low fiber; consistent execution in training = race-day gut adaptation; same foods and timing as planned race-day protocol",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Douglas, Advanced Marathoning Ch.9; Burke et al. 2011 pre-exercise nutrition",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "Caffeine — pre-race ergogenic protocol",
      "category": "Ergogenic Aids",
      "condition": "If athlete wants to use caffeine for race performance enhancement",
      "action": "Use 3-6 mg/kg body weight 30-60 min before event; trial in training first; avoid if caffeine-naïve; skip day-before caffeine to amplify race-day effect",
      "formula_or_value": "Dose: 3-6 mg/kg body weight; timing: 30-60 min pre-event; performance benefit: ~3% improvement in endurance time-trial; naïve use → higher GI risk; caffeine abstinence 24h before race amplifies effect",
      "priority": "medium",
      "confidence": "strong",
      "source": "Spriet 2014 caffeine and endurance; IOC consensus statement; Jeukendrup & Gleeson 2019",
      "applies_to": ["running", "cycling", "swimming"]
    },
    {
      "rule_name": "Post-long-run protein addition for recovery",
      "category": "Post-Workout Nutrition",
      "condition": "After a long run exceeding 90 minutes or any high-volume training day",
      "action": "Add protein to the post-run recovery meal alongside carbohydrates to accelerate both glycogen resynthesis and muscle repair",
      "formula_or_value": "Post-long-run: 0.3-0.4 g/kg protein + 1.2 g/kg carbohydrate within 30-45 min; protein source: whey, dairy, or plant-based complete protein; synergistic effect vs carbs-only on glycogen synthesis rate",
      "priority": "high",
      "confidence": "strong",
      "source": "Ivy et al. 1988; Berardi et al. 2006 protein+carb vs carb-only recovery; Burke et al. 2011",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Altitude nutrition adjustment",
      "category": "Environmental Nutrition",
      "condition": "If athlete trains or races at altitude ≥2000m (6,500 ft)",
      "action": "Increase daily carbohydrate intake by 10-15% above sea-level targets; emphasize iron-rich foods to support hematological adaptation",
      "formula_or_value": "Altitude ≥2000m: carb intake +10-15% vs sea-level target; iron-rich foods daily (red meat, leafy greens, legumes); vitamin C with iron sources to enhance absorption; monitor ferritin levels every 4 weeks at altitude",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Mazzeo 2008 altitude physiology; Daniels' Running Formula §3 altitude section; altitude nutrition consensus",
      "applies_to": ["running", "cycling"]
    }
```

- [ ] **Step 4: Validate JSON**

```bash
python -c "import json; json.load(open('docs/knowledge/nutrition_coach_fueling_rules.json'))" && echo OK
```

Expected: `OK`

- [ ] **Step 5: Run tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 6: Commit**

```bash
git add docs/knowledge/nutrition_coach_fueling_rules.json docs/knowledge/nutrition_coach_fueling_rules.json.backup
git commit -m "feat(knowledge): enrich nutrition_coach_fueling — race-week carbs, sodium, caffeine, altitude"
```

---

## Task 6: Enrich `recovery_coach_sleep_cns_rules.json` (Tier 2 — book-indirect)

**Files:**
- Modify: `docs/knowledge/recovery_coach_sleep_cns_rules.json`

**Context:** Currently 11 rules, `source_books: []`. Adding Pfitz "rest is training" principle, post-marathon sleep debt, Daniels CNS consolidation rule, RPE inflation from sleep deprivation, screen cutoff, napping timing. Target: 17 rules. Update `source_books`.

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/recovery_coach_sleep_cns_rules.json docs/knowledge/recovery_coach_sleep_cns_rules.json.backup
```

- [ ] **Step 2: Update `source_books` envelope and `last_updated`**

Change:
```json
"source_books": [],
"last_updated": "2026-04-13",
```
To:
```json
"source_books": ["pfitzinger-advanced-marathoning", "daniels-running-formula"],
"last_updated": "2026-04-14",
```

- [ ] **Step 3: Add rules — append to `extracted_rules` array**

Before the final `]` of `extracted_rules`, add a comma after the last rule, then append:

```json
    {
      "rule_name": "Pfitz 'rest is training' — prioritize recovery over forced sessions",
      "category": "Recovery Philosophy",
      "condition": "When an athlete shows poor recovery signals (low HRV, high fatigue, poor sleep) before a scheduled hard session",
      "action": "Replace the planned hard session with rest or easy movement; recovery is the adaptation stimulus, not the session itself; unscheduled rest > forced hard session",
      "formula_or_value": "If ≥2 of: RMSSD <15ms, sleep <6h, subjective fatigue ≥4/5, RPE inflation >2: replace hard session with Z1 ≤45 min or full rest; adaptation occurs during recovery, not during the session",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Douglas, Advanced Marathoning (rest as training); Daniels' Running Formula §2 rest principle",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Post-marathon elevated sleep need",
      "category": "Sleep",
      "condition": "In the 1-2 weeks following a marathon or endurance event >3 hours",
      "action": "Prescribe elevated sleep target; expect athlete to need more sleep than their normal baseline due to systemic inflammation and muscle repair",
      "formula_or_value": "Post-marathon weeks 1-2: target 9-10h sleep/night (vs normal 8h target); elevated sleep need driven by systemic inflammation; do not penalize 'laziness' — it is appropriate physiological response",
      "priority": "high",
      "confidence": "strong",
      "source": "Pfitzinger & Douglas, Advanced Marathoning; post-marathon recovery physiology research",
      "applies_to": ["running", "cycling"]
    },
    {
      "rule_name": "Daniels 3-4 week hold — CNS consolidation principle",
      "category": "CNS Recovery",
      "condition": "When deciding whether to increase training load after a period of consistent training",
      "action": "Hold training volume at current level for 3-4 weeks before increasing; this is CNS and musculoskeletal consolidation, not just muscular adaptation",
      "formula_or_value": "Volume hold: 3-4 weeks at consistent level before increasing; rationale: neuromuscular, tendon, and bone adaptations lag muscular adaptations by 2-4 weeks; premature increase = injury risk",
      "priority": "high",
      "confidence": "strong",
      "source": "Daniels' Running Formula §2 Volume Progression; bone and tendon adaptation research",
      "applies_to": ["running", "cycling", "lifting"]
    },
    {
      "rule_name": "Sleep deprivation — RPE inflation and session adjustment",
      "category": "Sleep",
      "condition": "If athlete slept <6 hours the night before a planned session",
      "action": "Reduce session intensity targets downward by 10-15%; do not cancel but adjust; perceived exertion is artificially elevated due to sleep deprivation",
      "formula_or_value": "Sleep <6h: RPE inflated by +1 to +2 vs normal; pace/power target reduction: 5-10%; cancel only if sleep <5h + high subjective fatigue ≥4/5; adjusted session > no session for adaptation signal",
      "priority": "high",
      "confidence": "strong",
      "source": "Fullagar et al. 2015 sleep and athletic performance; Skein et al. 2011 sleep and sport performance",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Screen and blue-light cutoff for sleep quality",
      "category": "Sleep",
      "condition": "When advising an athlete on sleep hygiene practices",
      "action": "Prescribe screen/blue-light avoidance 60-90 minutes before planned bedtime; blue light suppresses melatonin onset",
      "formula_or_value": "Screen cutoff: 60-90 min before bedtime; blue light (wavelength 460-480 nm) suppresses melatonin by 50-60%; alternatives: blue-light blocking glasses (partial effect), dim red/warm lighting",
      "priority": "medium",
      "confidence": "strong",
      "source": "Chang et al. 2015 blue-light and melatonin; Harvard chronobiology lab sleep hygiene research",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Napping — timing and duration protocol",
      "category": "Sleep",
      "condition": "When prescribing naps to supplement nocturnal sleep or for performance recovery",
      "action": "Use power naps (10-20 min) or full-cycle naps (90 min); avoid the 20-90 min sleep inertia zone; schedule before 3pm to minimize circadian disruption",
      "formula_or_value": "Power nap: 10-20 min — REM and light sleep; cognitive boost, no inertia; Full-cycle nap: 90 min — complete sleep cycle; maximal restoration but requires >30 min wake-up; AVOID: 21-89 min naps → deep NREM onset = strong sleep inertia; all naps: before 3pm",
      "priority": "medium",
      "confidence": "strong",
      "source": "Mednick et al. 2002 nap optimization; sleep architecture research; Waterhouse et al. 2007",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    }
```

- [ ] **Step 4: Validate JSON**

```bash
python -c "import json; json.load(open('docs/knowledge/recovery_coach_sleep_cns_rules.json'))" && echo OK
```

Expected: `OK`

- [ ] **Step 5: Run tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 6: Commit**

```bash
git add docs/knowledge/recovery_coach_sleep_cns_rules.json docs/knowledge/recovery_coach_sleep_cns_rules.json.backup
git commit -m "feat(knowledge): enrich recovery_coach_sleep_cns — Pfitz rest principle, post-marathon sleep, RPE inflation"
```

---

## Task 7: Enrich `recovery_coach_hrv_rules.json` (Tier 3 — science-only)

**Files:**
- Modify: `docs/knowledge/recovery_coach_hrv_rules.json`

**Context:** Currently 11 rules, `source_books: []` (stays `[]` — no book content for HRV). Adding orthostatic test, HRV-guided periodization, female athlete correction, ln-RMSSD clarification, dehydration effect, nocturnal vs morning HRV. Target: 17 rules.

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/recovery_coach_hrv_rules.json docs/knowledge/recovery_coach_hrv_rules.json.backup
```

- [ ] **Step 2: Update `last_updated` only**

Change `"last_updated": "2026-04-13"` to `"last_updated": "2026-04-14"`. Leave `source_books: []` unchanged.

- [ ] **Step 3: Add rules — append to `extracted_rules` array**

Before the final `]` of `extracted_rules`, add a comma after the last rule, then append:

```json
    {
      "rule_name": "Orthostatic HRV test — sympathetic elevation flag",
      "category": "Measurement Protocol",
      "condition": "When absolute RMSSD value is ambiguous (e.g., athlete with naturally low or high baseline)",
      "action": "Perform orthostatic HRV test: measure RMSSD supine 2 min then standing 2 min; HR increase >15 bpm indicates elevated sympathetic tone and reduced readiness",
      "formula_or_value": "Orthostatic delta: supine_HR vs standing_HR; delta >15 bpm = sympathetic elevation flag = reduce session intensity by 15%; delta >25 bpm = rest day; normal orthostatic response: 10-15 bpm increase",
      "priority": "medium",
      "confidence": "strong",
      "source": "Kiviniemi et al. 2010 orthostatic HRV; autonomic nervous system assessment research",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "HRV-guided periodization outperforms fixed programming",
      "category": "Training Application",
      "condition": "When choosing between a fixed pre-planned training schedule and an HRV-guided adaptive schedule",
      "action": "Prefer HRV-guided daily load adjustment; HRV-guided periodization produces superior VO2max and endurance gains vs same-volume fixed programming",
      "formula_or_value": "HRV-guided rule: if RMSSD within ±8% of 7-day baseline → execute planned session; if RMSSD >8% above baseline → upgrade session intensity; if RMSSD >8% below baseline → reduce; VO2max improvement: ~9% greater than fixed programming over 4 weeks",
      "priority": "high",
      "confidence": "strong",
      "source": "Kiviniemi et al. 2010 HRV-guided periodization; Flatt et al. 2017 HRV-guided training in athletes",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Female athlete HRV — menstrual phase baseline correction",
      "category": "Measurement Protocol",
      "condition": "When interpreting HRV trends for female athletes",
      "action": "Account for menstrual cycle phase when evaluating RMSSD deviations; luteal phase naturally lowers RMSSD; compare vs phase-matched 28-day baseline, not absolute rolling average",
      "formula_or_value": "Follicular phase (days 1-14): higher RMSSD baseline; luteal phase (days 15-28): lower RMSSD by 5-12%; correction: flag deviations vs phase-specific sub-average, not overall 28-day mean; 28-day rolling baseline still valid as long-term trend",
      "priority": "high",
      "confidence": "moderate",
      "source": "Baird et al. 2018 menstrual cycle and HRV; female athlete physiology research",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "ln-RMSSD vs raw RMSSD — metric selection",
      "category": "Measurement Protocol",
      "condition": "When selecting the HRV metric for monitoring or reporting",
      "action": "Use raw RMSSD for intra-athlete longitudinal monitoring (most apps report this); use ln-RMSSD for cross-athlete population comparisons or research; both are valid for within-athlete trending",
      "formula_or_value": "ln-RMSSD = natural log of RMSSD (ms); preferred for population normalization; raw RMSSD: acceptable for personal longitudinal tracking; HRV4Training and most apps report raw RMSSD — this is sufficient",
      "priority": "low",
      "confidence": "strong",
      "source": "Plews et al. 2013 HRV metrics review; Buchheit 2014 HRV monitoring review",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Dehydration effect on HRV measurement",
      "category": "Measurement Protocol",
      "condition": "When interpreting a low HRV reading on a hot day, after travel, or after alcohol consumption",
      "action": "Flag HRV outlier as potentially dehydration-related; ensure consistent hydration before morning measurement; do not make training decisions solely on anomalous readings",
      "formula_or_value": "Dehydration >2% body weight: RMSSD reduction measurable; heat/travel/alcohol: similar dehydration-adjacent effects; morning measurement protocol: drink 200-300ml water upon waking, measure after 10 min rest",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Buchheit et al. 2010 dehydration and HRV; Esco & Flatt 2014 HRV confounders",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    },
    {
      "rule_name": "Nocturnal HRV superior to morning HRV",
      "category": "Measurement Protocol",
      "condition": "If athlete uses a wearable device that provides nocturnal or overnight HRV data",
      "action": "Prefer nocturnal HRV as the primary readiness signal over morning spot-measurement; nocturnal HRV averages multiple sleep cycles and is more robust",
      "formula_or_value": "Nocturnal RMSSD (during sleep): 2-4× higher absolute values vs morning; better signal-to-noise; use nocturnal RMSSD as primary signal if available; morning measurement: valid backup when no overnight data",
      "priority": "medium",
      "confidence": "strong",
      "source": "Flatt & Esco 2016 nocturnal vs morning HRV; wearable HRV validation research",
      "applies_to": ["running", "cycling", "swimming", "lifting"]
    }
```

- [ ] **Step 4: Validate JSON**

```bash
python -c "import json; json.load(open('docs/knowledge/recovery_coach_hrv_rules.json'))" && echo OK
```

Expected: `OK`

- [ ] **Step 5: Run tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 6: Commit**

```bash
git add docs/knowledge/recovery_coach_hrv_rules.json docs/knowledge/recovery_coach_hrv_rules.json.backup
git commit -m "feat(knowledge): enrich recovery_coach_hrv — orthostatic test, guided periodization, female baseline, nocturnal"
```

---

## Task 8: Enrich `lifting_coach_volume_rules.json` (Tier 3 — science-only)

**Files:**
- Modify: `docs/knowledge/lifting_coach_volume_rules.json`

**Context:** Currently 12 rules, `source_books: []` (stays `[]`). Adding frequency effect, deload timing, compound lifts priority, double progression method, exercise selection for hybrid athletes. Target: 17 rules.

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/lifting_coach_volume_rules.json docs/knowledge/lifting_coach_volume_rules.json.backup
```

- [ ] **Step 2: Update `last_updated`**

Change `"last_updated": "2026-04-13"` to `"last_updated": "2026-04-14"`.

- [ ] **Step 3: Add rules — append to `extracted_rules` array**

Before the final `]` of `extracted_rules`, add a comma after the last rule, then append:

```json
    {
      "rule_name": "Frequency — 2×/week per muscle group superior to 1×/week",
      "category": "Volume Programming",
      "condition": "When determining how frequently to train each muscle group per week",
      "action": "Distribute the same weekly volume across at least 2 sessions per muscle group; 2× frequency produces superior hypertrophy vs 1× at equal total weekly sets",
      "formula_or_value": "2×/week vs 1×/week at equal volume: effect size g ≈ 0.37 favor of 2×; minimum 2 sessions/week for any primary muscle group; 3×/week marginally better than 2× for advanced lifters at MAV",
      "priority": "high",
      "confidence": "strong",
      "source": "Schoenfeld et al. 2016 meta-analysis: weekly frequency and hypertrophy; Ralston et al. 2017",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Deload week protocol for strength blocks",
      "category": "Volume Programming",
      "condition": "After 4-6 consecutive weeks of accumulation at MAV-MRV loads",
      "action": "Schedule a 1-week deload: reduce volume to MEV, maintain load (weight on bar); full unloading is not required; performance rebounds within 1-2 weeks post-deload",
      "formula_or_value": "Deload every 4-6 weeks; sets: MEV (8-10/muscle group); load: unchanged (same weights); frequency: can drop to 2×/week; 1 week duration; after deload: resume at pre-deload volume",
      "priority": "high",
      "confidence": "strong",
      "source": "Israetel et al. Scientific Principles of Hypertrophy Training; Issurin 2010 deload research",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Compound lifts priority for hybrid athletes",
      "category": "Exercise Selection",
      "condition": "When designing a resistance training program for an athlete who also performs endurance training",
      "action": "Prioritize compound multi-joint exercises; they produce greater hypertrophy and strength per unit of training time vs isolation work, with lower overall volume and less interference",
      "formula_or_value": "Priority order: Squat, deadlift, bench press, overhead press, row, pull-up/chin-up; isolation work (curls, extensions, flyes): supplement only; compound:isolation ratio ≥ 3:1 for hybrid athletes",
      "priority": "high",
      "confidence": "strong",
      "source": "Resistance training meta-analysis: compound vs isolation for strength and hypertrophy; concurrent training interference research",
      "applies_to": ["lifting", "running", "cycling"]
    },
    {
      "rule_name": "Double progression method for load management",
      "category": "Progression",
      "condition": "When deciding how and when to increase load on an exercise",
      "action": "Use double progression: increase reps within target range first; then increase load by minimum increment and reset reps to lower bound; more systematic than pure RPE-based progression",
      "formula_or_value": "Example: target 3×8-12; start at 3×8; when 3×12 achieved at RPE ≤7: add 2.5kg (upper body) or 5kg (lower body) and reset to 3×8; repeat; do NOT increase load before hitting rep ceiling",
      "priority": "high",
      "confidence": "strong",
      "source": "Progressive overload methodology; Helms et al. 2016 systematic progression guidelines",
      "applies_to": ["lifting"]
    },
    {
      "rule_name": "Exercise selection — DOMS risk for hybrid athletes",
      "category": "Exercise Selection",
      "condition": "When selecting lower-body exercises for an athlete with key endurance sessions within 48-72 hours",
      "action": "Avoid high-eccentric-load exercises within 72 hours of a key running or cycling session; high DOMS risk exercises impair endurance performance more than low-eccentric alternatives",
      "formula_or_value": "High DOMS risk (avoid ≥72h before key endurance): Nordic curls, tempo squats, Bulgarian split squats, Romanian deadlifts, step-downs; Low DOMS risk (safe 24-48h before): leg press, goblet squat, sled push; use low-DOMS alternatives during race build phase",
      "priority": "high",
      "confidence": "strong",
      "source": "Eccentric exercise and DOMS research; Twist & Eston 2005; concurrent training interference meta-analysis",
      "applies_to": ["lifting", "running", "cycling"]
    }
```

- [ ] **Step 4: Validate JSON**

```bash
python -c "import json; json.load(open('docs/knowledge/lifting_coach_volume_rules.json'))" && echo OK
```

Expected: `OK`

- [ ] **Step 5: Run tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 6: Commit**

```bash
git add docs/knowledge/lifting_coach_volume_rules.json docs/knowledge/lifting_coach_volume_rules.json.backup
git commit -m "feat(knowledge): enrich lifting_coach_volume — frequency, deload, compound priority, double progression, DOMS"
```

---

## Task 9: Enrich `biking_coach_power_rules.json` (Tier 3 — science-only)

**Files:**
- Modify: `docs/knowledge/biking_coach_power_rules.json`

**Context:** Currently 15 rules. NOTE: FTP test protocol (20-min × 0.95 + ramp × 0.75) ALREADY EXISTS in rule 1 — do NOT duplicate. Adding: weekly TSS load thresholds, Coggan Zone 7, and cycling-specific taper TSB targeting. Target: 18 rules.

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/biking_coach_power_rules.json docs/knowledge/biking_coach_power_rules.json.backup
```

- [ ] **Step 2: Update `last_updated`**

Change `"last_updated": "2026-04-13"` to `"last_updated": "2026-04-14"`.

- [ ] **Step 3: Add rules — append to `extracted_rules` array**

Before the final `]` of `extracted_rules`, add a comma after the last rule, then append:

```json
    {
      "rule_name": "Weekly TSS load thresholds by training phase",
      "category": "Load Monitoring",
      "condition": "When evaluating whether a cyclist's weekly training load is appropriate for their current phase",
      "action": "Compare weekly TSS to phase-appropriate thresholds; flag deviations above danger zone regardless of ACWR",
      "formula_or_value": "Weekly TSS thresholds: <300 TSS/wk: minimal aerobic stimulus (base restoration or taper); 300-450: moderate load (base building); 450-600: high training stress (build phase); 600-800: very high (peak phase, short duration only); >800 for >2 consecutive weeks: OTS risk flag",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter; Allen & Coggan CTL/ATL model thresholds",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Coggan Zone 7 — neuromuscular power",
      "category": "Training Zones",
      "condition": "If scheduling neuromuscular power sprints or maximal sprint efforts",
      "action": "Target >150% FTP for sprint efforts; these cannot be quantified by HR (too short for HR response); track as peak power in watts only; separate accounting from aerobic TSS",
      "formula_or_value": ">150% FTP; duration: <30 seconds; HR response: not valid (lag too long); training dose measured in sprint count and peak watts, not TSS; TSS contribution: minimal (<5 TSS per sprint session despite high peak stress)",
      "priority": "medium",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter; neuromuscular sprint physiology",
      "applies_to": ["cycling"]
    },
    {
      "rule_name": "Race-day TSB targeting — A-event peak form",
      "category": "Load Monitoring",
      "condition": "When planning taper strategy for a target cycling event",
      "action": "Target TSB in the +5 to +25 range on race day; below this range indicates accumulated fatigue; above indicates detraining; plan taper to arrive in this window",
      "formula_or_value": "A-race TSB target: +5 to +25; taper approach: reduce ATL (cut volume 40-60%) while maintaining CTL (keep some intensity); TSB = CTL − ATL; track daily; final 3 days: no new training load stimulus",
      "priority": "high",
      "confidence": "strong",
      "source": "Coggan & Allen, Training and Racing with a Power Meter; performance form modeling research",
      "applies_to": ["cycling"]
    }
```

- [ ] **Step 4: Validate JSON**

```bash
python -c "import json; json.load(open('docs/knowledge/biking_coach_power_rules.json'))" && echo OK
```

Expected: `OK`

- [ ] **Step 5: Run tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 6: Commit**

```bash
git add docs/knowledge/biking_coach_power_rules.json docs/knowledge/biking_coach_power_rules.json.backup
git commit -m "feat(knowledge): enrich biking_coach_power — TSS thresholds, Zone 7 neuromuscular, TSB race targeting"
```

---

## Task 10: Enrich `swimming_coach_biomechanics_rules.json` (Tier 3 — science-only)

**Files:**
- Modify: `docs/knowledge/swimming_coach_biomechanics_rules.json`

**Context:** Currently 10 rules, `source_books: []` (stays `[]`). Adding: CSS worked example, SWOLF stroke-rate tradeoff, CSS lactate threshold sets, flip turn/dolphin kick, open-water time adjustment, bilateral breathing prescription. Target: 16 rules.

- [ ] **Step 1: Backup**

```bash
cp docs/knowledge/swimming_coach_biomechanics_rules.json docs/knowledge/swimming_coach_biomechanics_rules.json.backup
```

- [ ] **Step 2: Update `last_updated`**

Change `"last_updated": "2026-04-13"` to `"last_updated": "2026-04-14"`.

- [ ] **Step 3: Add rules — append to `extracted_rules` array**

Before the final `]` of `extracted_rules`, add a comma after the last rule, then append:

```json
    {
      "rule_name": "CSS derivation worked example",
      "category": "Pace Prescription",
      "condition": "When calculating CSS from 400m and 200m time trial results",
      "action": "Apply the CSS formula with athlete's actual times; convert result from m/s to 100m pace for practical use",
      "formula_or_value": "CSS (m/s) = (400 - 200) / (T400_seconds - T200_seconds); example: T400=360s, T200=160s → CSS = 200/200 = 1.0 m/s = 100s/100m = 1:40/100m; CSS pace = (100 / CSS_ms) seconds per 100m",
      "priority": "high",
      "confidence": "strong",
      "source": "Wakayoshi et al. 1992; CSS worked example standard practice",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "Stroke rate vs distance-per-stroke — efficiency tradeoff",
      "category": "Technique Prescription",
      "condition": "When optimizing stroke efficiency via SWOLF monitoring",
      "action": "For distance events: optimize for fewer strokes per length (higher DPS, lower SWOLF); for sprint events: higher stroke rate is appropriate; SWOLF target is event-specific",
      "formula_or_value": "SWOLF = stroke_count + split_seconds; distance freestyle (1500m+): target SWOLF ≤38 (elite); recreational: ≤48; sprint (50-100m): accept higher stroke rate, SWOLF less meaningful; improve SWOLF by +1 unit/month as realistic progress target",
      "priority": "medium",
      "confidence": "strong",
      "source": "Toussaint & Hollander 1994; competitive swimming technique research; SWOLF monitoring standards",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "CSS threshold sets for aerobic development",
      "category": "Session Structure",
      "condition": "When scheduling the key aerobic development swim set for the week",
      "action": "Prescribe CSS ±3s/100m threshold sets; this is the swim lactate threshold zone; primary aerobic development stimulus",
      "formula_or_value": "CSS threshold set: 6-10 × 100m at CSS pace (±3s/100m); rest interval: 15-20s; total volume: 600-1000m at CSS; can substitute with 4-6 × 200m at CSS ±5s/100m; limit to ≤15% of weekly swim volume",
      "priority": "high",
      "confidence": "strong",
      "source": "Wakayoshi 1992; Pyne et al. 2001 CSS training guidelines",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "Flip turn and underwater dolphin kick",
      "category": "Technique Prescription",
      "condition": "When coaching pool swimming technique for competitive improvement",
      "action": "Train underwater dolphin kick off each wall; up to 15m breakout is faster than surface swimming for most trained swimmers; include in all training sets",
      "formula_or_value": "Underwater kick distance: up to 15m off each wall; dolphin kick velocity: 0.1-0.2 m/s faster than surface freestyle at same effort; train breakouts as a dedicated drill weekly; race legal maximum: 15m from wall",
      "priority": "medium",
      "confidence": "strong",
      "source": "Competitive swimming biomechanics consensus; wall-push velocity research",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "Open water vs pool time adjustment",
      "category": "Pace Prescription",
      "condition": "When translating pool CSS pace targets to open water racing pace expectations",
      "action": "Add 5-8% to pool CSS-derived time for equivalent open water effort; adjust pace targets accordingly; wetsuit partially offsets but does not eliminate the difference",
      "formula_or_value": "Open water time = pool time × 1.05 to 1.08; reasons: no walls, sighting time, navigation deviation, varying currents; wetsuit: reduces penalty to ~+2-4% over pool; CSS threshold sessions remain pool-based",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Open water vs pool performance research; triathlon swim split analysis",
      "applies_to": ["swimming"]
    },
    {
      "rule_name": "Bilateral breathing — aerobic vs high-intensity prescription",
      "category": "Technique Prescription",
      "condition": "When prescribing breathing pattern for training sessions",
      "action": "Mandate bilateral breathing (every 3 strokes) during aerobic sessions; permit every-2-stroke breathing during high-intensity intervals; bilateral breathing improves stroke symmetry and balance",
      "formula_or_value": "Aerobic sessions (Z1-Z2): every 3 strokes (bilateral); threshold sessions (CSS ±3s): every 3 strokes; VO2max intervals (Z4): every 2 strokes permitted; race/sprint: every 2 strokes; bilateral training: reduces stroke asymmetry by ~15% over 8 weeks",
      "priority": "medium",
      "confidence": "moderate",
      "source": "Competitive swimming coaching consensus; stroke symmetry and breathing research",
      "applies_to": ["swimming"]
    }
```

- [ ] **Step 4: Validate JSON**

```bash
python -c "import json; json.load(open('docs/knowledge/swimming_coach_biomechanics_rules.json'))" && echo OK
```

Expected: `OK`

- [ ] **Step 5: Run tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 6: Commit**

```bash
git add docs/knowledge/swimming_coach_biomechanics_rules.json docs/knowledge/swimming_coach_biomechanics_rules.json.backup
git commit -m "feat(knowledge): enrich swimming_coach_biomechanics — CSS example, SWOLF, threshold sets, dolphin kick, open water"
```

---

## Task 11: Update `KNOWLEDGE-JSONS.md` + cleanup backups

**Files:**
- Modify: `docs/backend/KNOWLEDGE-JSONS.md`
- Delete: all `*.json.backup` files in `docs/knowledge/`

**Context:** Update the coverage table with new rule counts and dates. Remove .backup files.

- [ ] **Step 1: Update coverage table in `docs/backend/KNOWLEDGE-JSONS.md`**

Replace the Coverage Table section with:

```markdown
| File | Agent | Rules | Last Updated | Source Books | Key Formulas |
|---|---|---|---|---|---|
| `biking_coach_power_rules.json` | Biking Coach | 18 | 2026-04-14 | Coggan & Allen | FTP×0.95; CTL=EWMA42; ATL=EWMA7; TSB=CTL-ATL; TSS thresholds 300/450/600/800; Z1-Z7 %FTP |
| `head_coach_acwr_rules.json` | Head Coach | 17 | 2026-04-14 | Daniels, Pfitz-Adv | ACWR=EWMA7/EWMA28; safe 0.8-1.3; monotony=avg/SD; strain=load×monotony; compound HRV+ACWR flag |
| `head_coach_interference_rules.json` | Head Coach | 15 | 2026-04-14 | Pfitz-Adv, FIRST | Strength→Endurance order; 6h gap; AMPK/mTOR 0-6h; FIRST XT buffer; block periodization |
| `lifting_coach_volume_rules.json` | Lifting Coach | 17 | 2026-04-14 | — | MEV 8-10 sets/wk; MAV 15-20; MRV 25+; DUP 3/8/15; 2×/week frequency; double progression |
| `nutrition_coach_fueling_rules.json` | Nutrition Coach | 18 | 2026-04-14 | Pfitz-Adv | 1.6-2.2g protein/kg; 3-12g carbs/kg; 30-90g carbs/h; sodium 500-700mg/h; caffeine 3-6mg/kg |
| `recovery_coach_hrv_rules.json` | Recovery Coach | 17 | 2026-04-14 | — | RMSSD: >20ms=OK; 15-20ms=reduce 15%; <15ms×2=rest; <10ms=veto; nocturnal HRV preferred |
| `recovery_coach_sleep_cns_rules.json` | Recovery Coach | 17 | 2026-04-14 | Pfitz-Adv, Daniels | 8-9h target; <6h=modify+10-15% RPE inflation; CNS 48-72h; rest=training principle |
| `running_coach_tid_rules.json` | Running Coach | 29 | 2026-04-14 | All 5 books | VDOT→paces; 80/20 TID; 10% cap; 4 phases; M-pace 75-84% vVO2max; FIRST 3-run model |
| `swimming_coach_biomechanics_rules.json` | Swimming Coach | 16 | 2026-04-14 | — | CSS=(D400-D200)/(T400-T200); SWOLF=strokes+seconds; Z1-Z4; CSS threshold 6-10×100m |
```

- [ ] **Step 2: Run final full test suite**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/test_knowledge_jsons.py -v
```

Expected: `90 passed`

- [ ] **Step 3: Remove backup files**

```bash
rm docs/knowledge/*.backup
```

- [ ] **Step 4: Commit cleanup**

```bash
git add docs/backend/KNOWLEDGE-JSONS.md
git add -u docs/knowledge/
git commit -m "docs(knowledge): update KNOWLEDGE-JSONS.md rule counts + remove backups — V3-N2 complete"
```

---

## Summary

| Task | File | Rules Added | Source |
|---|---|---|---|
| 2 | `running_coach_tid_rules` | +9 (20→29) | 5 books |
| 3 | `head_coach_acwr_rules` | +7 (10→17) | Daniels+Pfitz+science |
| 4 | `head_coach_interference_rules` | +5 (10→15) | Pfitz+FIRST+science |
| 5 | `nutrition_coach_fueling_rules` | +6 (12→18) | Pfitz+science |
| 6 | `recovery_coach_sleep_cns_rules` | +6 (11→17) | Pfitz+Daniels+science |
| 7 | `recovery_coach_hrv_rules` | +6 (11→17) | Science only |
| 8 | `lifting_coach_volume_rules` | +5 (12→17) | Science only |
| 9 | `biking_coach_power_rules` | +3 (15→18) | Science only |
| 10 | `swimming_coach_biomechanics_rules` | +6 (10→16) | Science only |
| **Total** | | **+53 (111→164)** | |
