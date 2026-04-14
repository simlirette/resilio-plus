# Advanced Marathoning — Agent Extract

**Source:** Pete Pfitzinger & Scott Douglas, Advanced Marathoning, Human Kinetics, 2nd edition
**Domain:** Running — Marathon periodization, LT, volume progression, race-specific preparation
**Agent cible:** Running Coach (principalement); Head Coach (règles de sécurité)

---

## 1. Concepts fondamentaux

- **Lactate threshold (LT) is the single most critical physiological variable for marathon success**, ahead of running economy and VO2max; training prioritization must reflect this hierarchy.
- **LT pace = current 15K to half-marathon race pace**; at this effort HR sits at 82–91% MHR (77–88% HRR); the LT run consists of a 20–40 min continuous tempo segment bracketed by warm-up and cool-down.
- **VO2max interval pace = current 5K race pace**; intervals of 600 m–1600 m (2–6 min each); total interval volume 5,000–10,000 m per session; recovery jog = 50–90% of interval duration.
- **Long run pace = goal marathon pace (MP) + 10–20%** (i.e., 10–20% slower than MP); maximum distance 22 miles (35 km); purpose is glycogen adaptation, fat oxidation, and musculoskeletal durability.
- **Marathon-pace (MP) run** = a medium-long or long run with a continuous segment at exact goal MP; HR 79–88% MHR (73–84% HRR); introduced in the later stages of a build-up for race-day specificity.
- **General aerobic (GA) run pace = MP + 15–25%**; HR 70–81% MHR (62–75% HRR); fills the majority of weekly mileage between quality sessions.
- **Recovery run**: HR strictly below 76% MHR (below 70% HRR); purpose is blood-flow flushing of metabolic waste, not fitness stimulus.
- **Strides**: 80–120 m repetitions at fast-but-relaxed effort (not sprint); performed after GA or recovery runs; improve running economy without generating significant lactate.
- **Periodization into 4 mesocycles**: (1) Base/Endurance — mileage build, low intensity; (2) Peak Mileage/LT — highest volume + regular tempo runs; (3) Pre-Taper/Race Prep — mileage decreases, marathon-pace long runs + tune-up races; (4) Taper — 3-week volume reduction, maintained intensity.
- **Taper duration = 3 weeks**; volume cut by 20–25% / 40% / 60% in weeks 3-out, 2-out, and race week (6 days), respectively; intensity is maintained throughout.
- **Volume progression cap = 10% per week OR ≤1 mile per training session per week** (whichever is binding); increases are made in steps: increase 1 week → hold 2–3 weeks → increase again.
- **Cutback (recovery) week every 3-4 weeks**: reduce weekly volume by 20-25% to allow adaptation before resuming progression. Volume holds for 2–3 weeks after each increase before the next step up; recovery is embedded in the step-hold cadence.
- **Hard/Easy principle**: every hard day (long run, LT run, VO2max intervals) must be followed by at least one easy day; advanced athletes may use back-to-back hard days followed by 2+ recovery days.
- **Tune-up races — long (15K–25K)**: require a 10-day block (4–6 day mini-taper + race + recovery days before next quality session).
- **Tune-up races — short (8K–12K)**: less recovery needed; can be run on tired legs as a training stimulus or with a short mini-taper for fitness assessment.
- **Glycogen depletion context**: long runs deplete glycogen stores; long run must be used to practice race-day nutrition and hydration strategies; taper allows full glycogen replenishment before race.
- **New mileage is added first to GA runs, medium-long runs, or warm-ups/cool-downs** — not to quality sessions.
- **Fitness is built by consistency over months**, not by individual heroic workouts.

---

## 2. Formules et calculs

| Formule | Inputs | Output | Notes |
|---|---|---|---|
| LT pace | Recent 15K or half-marathon race time | Pace per km/mile at lactate threshold | Equal to current 15K–HM race pace; use most recent all-out effort |
| VO2max interval pace | Recent 5K race time | Pace per km/mile for intervals | Current 5K race pace; never faster (e.g., not 1500 m pace) |
| Long run pace (fast bound) | MP | long_run_pace_fast | MP × 1.10 (10% slower than MP) `[ref: §3 Long Run]` |
| Long run pace (slow bound) | MP | long_run_pace_slow | MP × 1.20 (20% slower than MP) `[ref: §3 Long Run]` |
| Long run distance cap (% mileage) | weekly_mileage | max_long_run_distance | min(weekly_mileage × 0.29, 22 miles); use whichever is lower `[ref: §3 Long Run]` |
| GA run pace (fast bound) | Goal MP | MP × 1.15 | 15% slower than goal MP |
| GA run pace (slow bound) | Goal MP | MP × 1.25 | 25% slower than goal MP |
| Weekly volume increase cap (%) | Current weekly mileage | ≤ current_mileage × 0.10 | Hard ceiling: never exceed 10% week-over-week |
| Weekly volume increase cap (absolute) | Sessions per week, current mileage | ≤ n_sessions × 1 mile added | E.g., 6 sessions/week → max +6 miles; use whichever cap is lower |
| Taper week 1 volume | Peak weekly mileage | peak × 0.75–0.80 | 20–25% reduction from peak |
| Taper week 2 volume | Peak weekly mileage | peak × 0.60 | 40% reduction from peak |
| Taper race week volume (6 days) | Peak weekly mileage | peak × 0.40 | 60% reduction from peak |
| VO2max interval total volume per session | Individual interval distance, reps | 5,000 m ≤ total ≤ 10,000 m | Hard bounds; do not exceed upper limit |
| VO2max recovery jog duration | Interval duration | 0.50 × interval_time ≤ recovery ≤ 0.90 × interval_time | Jog at easy effort |
| Cross-training substitution (cycling) | Planned run duration | bike_duration = run_duration × 1.5 | E.g., 30 min run → 45 min bike |
| Water-running HR adjustment | Land target HR | target_HR_water = target_HR_land − 10% | Water running HR ~10% lower at equivalent effort |

---

## 3. Tables de référence

| Zone / Seuil | Valeur | Unité | Condition |
|---|---|---|---|
| LT run HR (MHR) | 82–91 | % MHR | During tempo segment |
| LT run HR (HRR) | 77–88 | % HRR | During tempo segment |
| LT tempo segment duration (min) | 20–40 | minutes | Hard constraint; ≤ ~7 miles |
| LT tempo segment duration (max extended) | ~7 | miles | Some schedules allow one longer LT run |
| VO2max interval pace | 5K race pace | — | Current race pace, not goal |
| VO2max interval HR (MHR) | 93–95 | % MHR | During interval |
| VO2max interval HR (HRR) | 91–94 | % HRR | During interval |
| VO2max interval length (duration) | 2–6 | minutes | Per repetition |
| VO2max interval length (distance) | 600–1600 | meters | Per repetition |
| VO2max total volume per session (min) | 5,000 | meters | Hard floor |
| VO2max total volume per session (max) | 10,000 | meters | Hard ceiling — do not exceed |
| VO2max recovery jog | 50–90 | % of interval time | Slow jog effort |
| Long run pace | MP + 10–20 | % slower than MP | Not faster than +10%, not slower than +20% |
| Long run HR (MHR) | 74–84 | % MHR | Entire run |
| Long run HR (HRR) | 65–78 | % HRR | Entire run |
| Long run max distance | 22 | miles (35 km) | Hard ceiling — never exceed |
| Long run % of weekly mileage | 22-29 | % | Cap at 29%; absolute max 22 miles (whichever is lower) `[ref: §3 Long Run]` |
| Long run max duration | 210 | min | Duration cap (3:30 h) for slow runners; applies when distance cap would exceed this duration `[ref: §3 Long Run]` |
| MP run HR (MHR) | 79–88 | % MHR | During MP segment |
| MP run HR (HRR) | 73–84 | % HRR | During MP segment |
| GA run pace | MP + 15–25 | % slower than MP | Daily runs between quality sessions |
| GA run HR (MHR) | 70–81 | % MHR | GA effort |
| GA run HR (HRR) | 62–75 | % HRR | GA effort |
| Recovery run HR (MHR) | < 76 | % MHR | Hard ceiling |
| Recovery run HR (HRR) | < 70 | % HRR | Hard ceiling |
| Strides length | 80–120 | meters | Per repetition |
| Taper duration | 3 | weeks | Fixed; start 3 weeks before marathon |
| Taper week 1 volume reduction | 20–25 | % below peak | Week 3 out |
| Taper week 2 volume reduction | 40 | % below peak | Week 2 out |
| Taper race week volume reduction | 60 | % below peak | 6 days before race |
| Volume increase cap (weekly %) | 10 | % per week | Never exceed |
| Volume increase cadence | 2–3 | weeks hold after each step | Hold before next increase |
| Ferritin red flag threshold | < 25 | ng/ml | Refer to physician |
| Immune suppression window post-hard effort | 12–72 | hours | After high-intensity or prolonged exercise |
| Tune-up race recovery block (long, 15K–25K) | 10 | days total | 4–6 day mini-taper + race + recovery |
| Taper strength training cutoff | 10 | days before race | Eliminate all strength training |

---

## 4. Règles prescriptives

### 4.1 Sélection des allures

- IF workout_type = VO2max interval, THEN set pace = current 5K race pace. [ref: §2 / §3]
- IF workout_type = Lactate Threshold run, THEN set pace = current 15K-to-half-marathon race pace. [ref: §2 / §3]
- IF workout_type = Marathon-Pace run, THEN set pace = goal marathon pace. [ref: §2 / §3]
- IF workout_type = Long Run, THEN set pace between MP + 10% and MP + 20% (slower). [ref: §2 / §3]
- IF workout_type = General Aerobic, THEN set pace between MP + 15% and MP + 25% (slower). [ref: §2 / §3]
- IF workout_type = Recovery run, THEN enforce HR < 76% MHR (< 70% HRR). [ref: §2 / §3]
- IF VO2max interval pace is set faster than current 5K race pace, THEN reject and reset to current 5K race pace. [ref: §2]

### 4.2 Progression de volume

- IF increasing weekly mileage, THEN limit increase to ≤ 10% of current weekly mileage. [ref: §3]
- IF increasing weekly mileage AND running ≥ 2 sessions/week, THEN also cap increase at ≤ 1 mile × number_of_weekly_sessions. [ref: §3]
- IF a mileage step-up has just been applied, THEN hold at the new level for 2–3 weeks before the next increase. [ref: §3]
- IF athlete is in a base-building phase (increasing mileage), THEN exclude VO2max interval sessions from the schedule. [ref: §3]
- IF adding miles to the schedule, THEN add them to GA runs, medium-long runs, or warm-up/cool-down segments first. [ref: §3]
- IF athlete has trained for 3-4 consecutive weeks without a cutback week THEN schedule a cutback week at 75-80% of previous week's volume `[ref: §2 Recovery]`

### 4.3 Taper

- IF marathon is 3 weeks away, THEN begin taper: reduce weekly mileage by 20–25% from peak. [ref: §2 / §5]
- IF marathon is 2 weeks away, THEN reduce weekly mileage by 40% from peak. [ref: §2 / §5]
- IF marathon is 6 days away (race week), THEN reduce weekly mileage by 60% from peak. [ref: §2 / §5]
- IF tapering, THEN maintain workout intensities at goal paces — do not reduce pace. [ref: §2 / §5]
- IF marathon is 10 days away, THEN eliminate all strength training. [ref: §5]

### 4.4 Séances de qualité — exigences warm-up/cool-down

- IF workout_type = Lactate Threshold run, THEN execute warm-up of 15–20 min (or 2–3 miles) at easy aerobic pace before tempo segment. [ref: §2 / §4]
- IF workout_type = Lactate Threshold run, THEN execute cool-down of ≥ 10–15 min at easy recovery pace after tempo segment. [ref: §4]
- IF workout_type = VO2max interval, THEN execute warm-up of 2–3 miles at easy aerobic pace followed by a few strides. [ref: §4]
- IF workout_type = VO2max interval, THEN execute cool-down of 2–3 miles at easy recovery pace. [ref: §4]
- IF workout_type = Long Run with MP segment, THEN begin run with 2–5 miles at long-run pace before the MP segment. [ref: §4]

### 4.5 Volume et durée des intervals VO2max

- IF total interval volume for session exceeds 10,000 m, THEN reduce number of repetitions to stay ≤ 10,000 m. [ref: §2 / §4]
- IF individual interval duration is < 2 min or > 6 min, THEN adjust interval distance to fall within 2–6 min range at 5K pace. [ref: §2]

### 4.6 Long Run Rules

- IF prescribed long run distance exceeds 22 miles, THEN cap at 22 miles. [ref: §2]
- IF long_run_distance > weekly_mileage × 0.29 THEN reduce long_run_distance to weekly_mileage × 0.29 `[ref: §3 Long Run]`
- IF long_run_distance > 22 miles THEN reduce long_run_distance to 22 miles `[ref: §3 Long Run]`
- IF long_run_duration_projected > 210 min THEN reduce long_run_distance until projected duration ≤ 210 min `[ref: §3 Long Run]`

### 4.7 Substitution et entraînement croisé

- IF a run must be replaced due to weather or minor injury risk, THEN substitute with appropriate cross-training activity. [ref: §3]
- IF substituting a recovery run with cycling, THEN set bike duration = planned run duration × 1.5. [ref: §3]
- IF substituting with water running, THEN prioritize interval format over steady-state and apply target_HR − 10% for equivalent effort. [ref: §3]

### 4.8 Retour après interruption

- IF training break < 10 days THEN resume at current calendar position in the schedule, skipping any missed sessions — do NOT attempt to make up missed workouts `[ref: §1 Return to Training]`
- IF training break = 10–20 days AND marathon is < 8 weeks away, THEN revise the race goal downward. [ref: §3]
- IF training break > 20 days, THEN revise the race goal downward regardless of time remaining to race. [ref: §3]
- IF a VO2max session was missed during the break, THEN reduce pace of the next VO2max session to account for lost fitness. [ref: §3]

### 4.9 Courses de calage (tune-up races)

- IF tune-up race distance is 15K–25K, THEN apply a 4–6 day mini-taper before the race and do not schedule a hard session within the 10-day block surrounding it. [ref: §5]
- IF tune-up race distance is 8K–12K AND athlete needs fitness assessment, THEN apply a short mini-taper before the race. [ref: §5]

### 4.10 Flags de sécurité (Head Coach)

- IF ferritin < 25 ng/ml, THEN pause training plan and refer athlete to a physician. [ref: §1]
- IF athlete shows persistent fatigue, elevated resting HR, disturbed sleep, or performance decline despite training, THEN flag as overtraining and pause hard sessions. [ref: §1]
- IF athlete has fever or systemic illness symptoms, THEN suspend all high-intensity and prolonged sessions for the duration of illness. [ref: §1]
- IF athlete is limping or reports pain that worsens during a run, THEN stop the session immediately and do not resume until pain-free. [ref: §1]
- IF immune suppression window (12–72 h after high-intensity or prolonged effort) coincides with illness exposure risk, THEN treat as elevated illness risk. [ref: §1]

---

## 5. Contre-indications et cas limites

- **Never run at faster than goal marathon pace** during a long run — this converts the session into a race effort, compromises recovery, and defeats the glycogen adaptation stimulus.
- **Long run distance hard ceiling = 22 miles (35 km)**; runs beyond this distance yield minimal additional adaptation while dramatically increasing recovery time and injury risk.
- **LT tempo segment must not exceed 40 min (or ~7 miles)**; running longer at LT pace is not a tempo run — it shifts to a different stimulus and increases injury risk.
- **LT tempo pace must not be faster than current 15K–HM race pace**; running faster changes the metabolic stimulus and becomes counterproductive for marathon training.
- **VO2max intervals must not be faster than current 5K race pace**; running at 1500 m pace or faster generates lactate levels irrelevant to marathoners and reduces VO2max stimulus.
- **VO2max sessions must not be performed during a base-building (mileage increase) phase**; the combination elevates injury risk and compromises adaptation.
- **Recovery runs must not be extended or accelerated**; running too fast or too long on recovery days adds fatigue without benefit and erodes the quality of subsequent hard sessions.
- **Taper intensity must not be reduced along with volume**; detraining (loss of fitness + psychological sluggishness) results from cutting both simultaneously.
- **Strength training must be eliminated ≥ 10 days before the marathon**; residual muscle damage from resistance work impairs race-day performance.
- **Mileage must never increase more than 10% per week under any circumstances**, even if the athlete feels strong — the adaptation lag means injury risk peaks 2–3 weeks after the spike.
- **Novice distinction**: the book targets experienced marathoners; runners with < 1 year of consistent training or < 40 miles/week baseline are at elevated risk when following these schedules at full prescribed volumes.
- **Elite distinction**: elite runners (sub-2:20 male / sub-2:45 female) may tolerate peak weeks of 110–140 miles; the AI coach should flag when prescribed volumes approach an untrained athlete's physiological ceiling.
- **Age-related recovery**: older athletes require longer recovery between hard sessions; the standard hard/easy alternation may need to become hard/easy/easy.
- **Iron deficiency (ferritin < 25 ng/ml)** severely limits aerobic adaptation; training load must be suspended pending physician evaluation — continuing training while iron-depleted produces overtraining without fitness gains.
- **Illness during taper**: any systemic illness with fever during the final 3 weeks requires postponing or abandoning the race target — attempting to race through illness post-immune suppression is contraindicated.
- **Marathon-pace segments in long runs** are only appropriate in the later build-up and pre-taper phases; introducing them too early overwhelms recovery capacity.

---

## 6. Références sources

| Concept | Référence livre |
|---|---|
| Core philosophy — physiological hierarchy (LT > economy > VO2max) | §0 — Core Philosophy |
| Runner profile inputs + red flags | §1 — Runner Profile Inputs |
| LT run definition, pace, HR, duration | §2 — Canonical Vocabulary: Lactate Threshold Run |
| VO2max interval definition, pace, HR, volume | §2 — Canonical Vocabulary: VO2max Interval |
| Long run definition, pace, HR, max distance | §2 — Canonical Vocabulary: Long Run |
| Marathon-pace run definition, pace, HR | §2 — Canonical Vocabulary: Marathon-Pace Run |
| GA run definition, pace, HR | §2 — Canonical Vocabulary: General Aerobic Run |
| Recovery run definition, HR ceiling | §2 — Canonical Vocabulary: Recovery Run |
| Strides definition, distance, intensity | §2 — Canonical Vocabulary: Strides |
| Taper duration, volume reductions by week | §2 — Canonical Vocabulary: Taper |
| Pace selection decision rules | §3 — Decision Rules: Pace Selection Logic |
| Volume progression + hold cadence | §3 — Decision Rules: Training Progression & Volume Management |
| Cross-training substitution rules | §3 — Decision Rules: Workout Substitution |
| Missed training / return from break | §3 — Decision Rules: Scaling for Missed Training |
| LT tempo run constructor (warm-up, main, cool-down) | §4 — Workout Constructors: Lactate Threshold Run |
| VO2max interval constructor | §4 — Workout Constructors: VO2max Interval Run |
| Long run constructor (MP variation) | §4 — Workout Constructors: Long Run |
| 4-phase mesocycle structure | §5 — Week/Season Structure: Training Phases |
| Hard/Easy principle + back-to-back pattern | §5 — Week/Season Structure: The Hard/Easy Principle |
| Taper principles (non-negotiable) | §5 — Week/Season Structure: Tapering Principles |
| Tune-up race protocols (long + short) | §5 — Week/Season Structure: Incorporating Tune-Up Races |
