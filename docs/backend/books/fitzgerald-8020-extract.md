# 80/20 Running — Agent Extract

**Source:** Matt Fitzgerald, 80/20 Running, New American Library, 2014
**Domain:** Running — Training intensity distribution (TID), polarized model, 80/20 rule
**Agent cible:** Running Coach (principalement); Head Coach (règles de sécurité)

---

## 1. Concepts fondamentaux

- The 80/20 rule: approximately 80% of total weekly training TIME (not distance, not sessions) at low intensity; remaining 20% at moderate-to-high intensity
- "Low intensity" = Zones 1-2 in Fitzgerald's 5-zone model (below VT1 / first ventilatory threshold); the 80% is a MINIMUM, not an exact target
- "High intensity" = Zones 4-5 (above VT2 / second ventilatory threshold)
- Zone 3 ("gray zone" / moderate intensity) is permitted only for Tempo runs, Cruise Intervals, and Fast Finish workouts; must remain under 5% of weekly training time — not counted in either the 80% or the 20% — it generates fatigue comparable to high-intensity work without delivering equivalent adaptation benefit
- Polarized training model: the majority of training at low intensity, a minority at high intensity, and very little in the "moderate" gray zone — contrasts with threshold-dominant models (e.g., heavy T-pace emphasis)
- Training intensity distribution (TID) must be measured and tracked by TIME, not by distance or number of sessions
- The "moderate-intensity rut": the single most common and destructive training error — easy runs performed too fast, generating fatigue that prevents quality high-intensity work and failing to maximize aerobic development
- Low-intensity running is highly repeatable, enabling the volume required to build a deep aerobic base, drive neurological self-optimization of running economy, and develop brain fitness (mental fatigue resistance)
- High-intensity work (Zones 4-5) boosts VO2max, top-end speed, and cardiovascular power; limited by recovery cost
- Zone 3 (Moderate) develops lactate threshold endurance; appropriate only for Tempo Runs, Cruise Intervals, and Fast Finish Runs — not for daily runs
- Lactate Threshold Heart Rate (LTHR): primary anchor for HR-based zone calculation; determined via 30-minute time trial (average HR over final 10 minutes)
- The 80/20 method is a codification of patterns that evolved naturally among elite endurance athletes, validated by exercise physiologist Stephen Seiler's research
- Novice athletes begin with 90/10 TID for first 4-8 weeks, then progress to 85/15, then 80/20 over subsequent training blocks
- Monitoring methods: Heart Rate (primary), Pace (secondary), RPE (primary for short intervals and hilly terrain), Talk Test (field check for Zone 2 boundary)
- Cross-training (cycling, pool running, elliptical) counts toward TID and preserves the 80/20 balance; minimum 3 actual runs per week for running-specific adaptation
- Base Phase targets 85-90% low-intensity time; Peak Phase closes to ~77/23 as race-specific work increases; Taper Phase reduces total volume while preserving quality frequency
- No more than 2 quality sessions (containing any Zone 3-5 work) per week for standard athletes; advanced runners may handle up to 3; Z4-5 sessions hard-capped at 2 per week for ALL athletes regardless of level
- Races and time trials count toward the 20% high-intensity allocation; a 10K race = one high-intensity session for that week
- Quality sessions must be separated by at least 1 low-intensity day for physiological and neurological recovery

---

## 2. Formules et calculs

> **Note:** All HR boundaries in this extract use %LTHR (lactate threshold HR), not %HRmax. LTHR ≈ 85-92% of HRmax depending on athlete.

| Formule | Inputs | Output | Notes |
|---|---|---|---|
| LTHR vs HRmax note | — | — | Boundaries use %LTHR. LTHR ≈ HRmax × 0.88 (typical); derive from 30-min field test `[ref: §2 Zones]` |
| Weekly low-intensity time | total_weekly_training_time | low_intensity_time = total_weekly_training_time × 0.80 | Minimum target; measured in time, not distance `[ref: §0]` |
| Weekly high-intensity time | total_weekly_training_time | high_intensity_time = total_weekly_training_time × 0.20 | Includes Zones 3-5; Zone 3 sparingly `[ref: §0]` |
| LTHR field test | 30-min time trial | LTHR = avg HR over final 10 min of effort | Runner's primary HR anchor for all zone boundaries `[ref: §2]` |
| Zone 1 upper boundary (HR) | LTHR | Z1_max = LTHR × 0.81 | Below first ventilatory threshold `[ref: §2]` |
| Zone 2 lower boundary (HR) | LTHR | Z2_min = LTHR × 0.81 (= Z1 upper limit + 1) | Bottom of Zone 2 `[ref: §2 Zones]` |
| Zone 2 upper boundary (HR) | LTHR | Z2_max = LTHR × 0.89 | Top of low-intensity range `[ref: §2]` |
| Zone 3 upper boundary (HR) | LTHR | Z3_max = LTHR × 0.93 | Gray zone ceiling; moderate intensity `[ref: §2]` |
| Zone 4 upper boundary (HR) | LTHR | Z4_max = LTHR × 1.02 | Hard effort; high intensity floor `[ref: §2]` |
| Zone 5 (HR) | LTHR | Z5 > LTHR × 1.02 | Maximal effort `[ref: §2]` |
| Pace zones | recent_race_time, race_distance | Easy/Tempo/Interval pace targets | Derived from McMillan-style race equivalency calculator `[ref: §1]` |

---

## 3. Tables de référence

| Zone/Seuil | Valeur | Unité | Condition |
|---|---|---|---|
| Weekly low-intensity target | ≥ 80 | % of weekly training time | Minimum; Base Phase targets 85-90% `[ref: §0, §5]` |
| Weekly high-intensity target | ≤ 20 | % of weekly training time | Includes all moderate + high; Zone 3 sparingly `[ref: §0]` |
| Zone 1 RPE | 1-4 | RPE (0-10) | Very easy; full conversation effortless `[ref: §2]` |
| Zone 2 RPE | 5-6 | RPE (0-10) | Easy; comfortable conversation `[ref: §2]` |
| Zone 3 RPE | 7 | RPE (0-10) | Moderate; conversation effortful but possible `[ref: §2]` |
| Zone 4 RPE | 8 | RPE (0-10) | Hard; short phrases only `[ref: §2]` |
| Zone 5 RPE | 9-10 | RPE (0-10) | Maximal; speech not possible `[ref: §2]` |
| Talk test — Zone 1 | effortless speech | — | Any sentence without pausing for breath `[ref: §2]` |
| Talk test — Zone 2 upper boundary | comfortable but not effortless | — | Sentences possible; slight effort required `[ref: §2]` |
| Talk test — Zone 3 (gray zone) | effortful | — | Short phrases only; test fails for full sentences `[ref: §2]` |
| Foundation Run HR guardrail | Zone 1-2; RPE ≤ 6 | — | Must NOT exceed top of Zone 2 `[ref: §4]` |
| Recovery Run HR guardrail | Zone 1; RPE ≤ 2 | — | Lowest intensity run type `[ref: §4]` |
| Max quality sessions per week (any Z3-5) | 3 | sessions | Advanced runners only; standard athletes: max 2 `[ref: §5]` |
| Max Z4-5 sessions per week | 2 | sessions | Hard upper limit for ALL athletes regardless of level `[ref: §5]` |
| Min recovery between quality sessions | 1 | low-intensity day | Between any two quality sessions `[ref: §5]` |
| Min runs per week with cross-training | 3 | running sessions | For running-specific neuromuscular adaptation `[ref: §2]` |
| Base Phase low-intensity proportion | 85-90 | % of weekly training time | Higher than standard 80/20 `[ref: §5]` |
| Peak Phase low-intensity proportion | ~77 | % of weekly training time | Minimum floor; slightly more quality `[ref: §5]` |
| Taper Phase duration | 1-2 | weeks | Before goal race `[ref: §5]` |
| Return from break > 2 weeks | reduce volume by ≥ 50 | % | First week only; rebuild gradually `[ref: §3]` |

---

## 4. Règles prescriptives

### Intensity Selection by Zone

IF monitoring intensity by Heart Rate, THEN establish LTHR via 30-minute time trial before assigning any zone-based workout. `[ref: §2]`

IF a workout prescribes Zone 1-2 (low intensity), THEN Heart Rate must not exceed Z2_max (LTHR × 0.89) at any point during the run. `[ref: §4]`

IF a workout involves intervals shorter than 2 minutes, THEN use RPE as the primary intensity guide; Heart Rate will lag and is not a valid real-time measure for these efforts. `[ref: §3, §4]`

IF the athlete is running on hilly terrain, THEN use RPE or Heart Rate to govern effort; pace is not a valid intensity measure on gradients. `[ref: §3]`

IF a valid recent race time (within 2-3 months) is provided, THEN calculate personalized pace zones for all workout types using a race-equivalency calculator. `[ref: §1]`

### 80/20 Compliance Verification

IF total weekly training time is known, THEN verify that Zone 1-2 time ÷ total time ≥ 0.80 before approving the week's plan. `[ref: §0]`

IF the weekly plan contains more than 2 (standard athletes) or 3 (advanced athletes) sessions with any Zone 3-5 content, THEN revise the plan to reduce quality sessions to the applicable limit. `[ref: §5]`

IF two quality sessions appear on consecutive days in the weekly plan, THEN insert at least one low-intensity day between them. `[ref: §5]`

### Gray Zone Management

IF the athlete reports that easy runs feel "somewhat hard" or conversation requires effort, THEN classify this as gray-zone creep and reduce pace/effort until Zone 1-2 RPE (≤ 6) is achieved. `[ref: §0, §2]`

IF the athlete reports feeling stagnant in performance or consistently fatigued after easy runs, THEN diagnose as moderate-intensity rut and enforce strict Zone 1-2 discipline on all non-quality sessions immediately. `[ref: §0, §1]`

IF Zone 3 time exceeds 5% of weekly training time THEN reallocate that time to Zone 1-2 in the following week. `[ref: §0]`

### Race Handling Within Training

IF a goal race occurs during the training period, THEN count the race duration entirely toward the high-intensity (20%) allocation for that week. `[ref: §0]`

IF a race replaces a scheduled quality session, THEN cancel the other quality session that week to avoid exceeding 2 hard efforts. `[ref: §5]`

### Cross-Training

IF a scheduled easy or recovery run cannot be completed due to injury risk or fatigue, THEN substitute with a cross-training session of equal duration at the same intended intensity zone. `[ref: §2, §3]`

IF cross-training sessions are included in the weekly plan, THEN their duration counts toward total weekly training time for the purpose of 80/20 calculation. `[ref: §2]`

IF an athlete uses cross-training to supplement running, THEN maintain a minimum of 3 running sessions per week for running-specific neuromuscular adaptation. `[ref: §2]`

### Novice vs. Experienced Athletes

IF the athlete is a beginner (no structured training history), THEN start with Level 1 plan structure and enforce a conservative base phase (≥85% low-intensity time) starting from 90/10 TID and progressing to 85/15, then 80/20 over 8-12 weeks, before introducing any Zone 3-5 work. `[ref: §1]`

IF the athlete is returning from a training break exceeding 2 weeks, THEN reduce planned volume by at least 50% in the first week and rebuild gradually before re-entering the formal plan. `[ref: §3]`

IF the athlete is identified as injury-prone, THEN substitute 2-3 planned weekly runs with non-impact cross-training sessions (aggressive cross-training approach). `[ref: §1, §3]`

### Plan Phase Progression

IF the athlete completes the Base Phase, THEN advance to the Peak Phase; do not skip or reorder phases. `[ref: §5]`

IF the athlete completes a goal race, THEN enforce recovery protocol: Week 1 = no structured runs, light activity only; Week 2 = 3-4 short low-intensity runs only; re-evaluate readiness before starting a new plan. `[ref: §3]`

IF the athlete is in Taper Phase, THEN reduce total volume significantly by shortening low-intensity runs; maintain quality session frequency but reduce repetitions/duration within those sessions. `[ref: §5]`

---

## 5. Contre-indications et cas limites

- The 80/20 rule applies to aerobic endurance training only; it does not apply to resistance/strength training, which follows different physiological principles (muscle damage, CNS load, hypertrophy vs. aerobic adaptation)
- High-intensity work (Zones 4-5) must not exceed 2 sessions per week; exceeding this threshold provides diminishing returns and rapidly increases overtraining, fatigue, and injury risk
- The 80/20 rule does not specify a minimum absolute volume — very low-volume athletes may need to establish a base before the distribution becomes meaningful
- Elite athletes typically apply a stricter polarized model (closer to 85-90% low intensity during base phases); recreational athletes moving from threshold-heavy training may need a gradual transition rather than an immediate shift to 80/20
- If an athlete has fewer than 3 runs per week available, cross-training can fill aerobic volume but cannot fully replace the neuromuscular and biomechanical load of running — peak running performance requires actual running
- Zone 3 (Moderate) is permitted only for Tempo Runs, Cruise Intervals, and Fast Finish Runs; must remain under 5% of weekly training time — not counted in either the 80% or the 20%; defaulting to Zone 3 for all non-interval days is the exact pattern the 80/20 method is designed to eliminate
- The talk test is a valid field check but loses precision at altitude or in extreme heat/humidity where HR and ventilation rates are artificially elevated; rely on RPE under these conditions
- Pace-based zones are only valid on flat terrain; grade-adjusted pace or RPE must replace pace on hills
- Athletes with recent or recurring overuse injuries should not increase running volume to fill the 80% low-intensity quota; cross-training substitution is mandatory until injury resolves
- The 80% low-intensity minimum is not a ceiling — during Base Phase, 85-90% is normal and preferred; the 80% floor applies throughout all phases

---

## 6. Références sources

| Concept | Référence livre |
|---|---|
| 80/20 core philosophy and rationale | §0 — Core philosophy |
| Runner profile inputs and red flags | §1 — Runner profile inputs |
| Zone definitions (5-zone model, RPE, HR, talk test) | §2 — Canonical vocabulary + ontology |
| Decision rules (IF/THEN — substitution, scaling, returns) | §3 — Decision rules |
| Workout constructors (Foundation, Recovery, Long, Tempo, Intervals, etc.) | §4 — Workout constructors |
| Phase structure (Base, Peak, Taper) and weekly principles | §5 — Week/season structure |
| LTHR field test protocol | §2 — Lactate Threshold definition |
| Cross-training guidelines | §2 — Cross-Training definition |
| Moderate-intensity rut definition and diagnosis | §2 — Moderate-Intensity Run / §0 |
| Gray zone (Zone 3) and overuse warning | §0, §2 — Moderate-Intensity Run |
