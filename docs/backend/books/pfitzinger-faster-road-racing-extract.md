# Faster Road Racing — Agent Extract

**Source:** Pete Pfitzinger & Philip Latter, Faster Road Racing, Human Kinetics, 2015
**Domain:** Running — 5K to half-marathon race-specific training, lactate threshold, running economy
**Agent cible:** Running Coach (principalement); Head Coach (règles de sécurité)

---

## 1. Concepts fondamentaux

- **Training success is built on consistency, staying healthy, and long-term perseverance**; no individual workout overrides the need for sustainable progression.
- **Four primary training types exist**: endurance runs (long runs), lactate threshold (LT) runs, VO₂max intervals, and speed work; all other runs are general aerobic or recovery.
- **LT pace = the pace a well-trained runner can sustain in a race lasting approximately 60 minutes**; HR sits at 82–91% MHR (77–88% HRR); the single best predictor of race performance for distances 8K to half marathon.
- **VO₂max interval pace = current 5K race pace (effort equivalent to 3K-5K race effort, pace anchored at 5K)**; intervals of 600 m–1600 m (2–6 min each); recovery jog = 50–90% of interval duration; total session volume accumulates time at 95–100% VO₂max.
- **Long run pace = 20–33% slower than current 10K race pace** (or 17–29% slower than 15K–HM race pace); HR 74–84% MHR (65–78% HRR); performed once per week as cornerstone of training.
- **General aerobic (GA) run pace = conversational effort**; HR 70–81% MHR (62–75% HRR); constitutes the majority of weekly mileage between quality sessions.
- **Recovery run**: short, easy; sole purpose is blood-flow flushing of metabolic waste and promoting adaptation; must be truly easy to preserve the quality of subsequent hard sessions.
- **Strides = short accelerations of 15–25 seconds** (~100 m); performed after easy runs; improve running economy and neuromuscular speed without significant lactate accumulation.
- **Power hills = uphill efforts of 8–15 seconds** at maximal power; build leg strength that transfers directly to race speed; recovery = walk or jog back down.
- **Periodization follows two phases**: (1) Base Training — aerobic base build, increasing mileage, no VO₂max intervals; (2) Race-Specific Training — layered quality workouts targeted at goal race distance physiology (more VO₂max for 5K, more LT for half marathon).
- **Race-distance hierarchy for physiological emphasis**: 5K–8K → VO₂max is dominant quality; 10K–15K → VO₂max + LT balanced; half marathon → LT is dominant quality.
- **Volume progression cap = 10% per week**; increase is applied for 1 week, then held for at least 1 week before the next increase; intensity must be reduced when increasing mileage.
- **Cutback (recovery) week every 3–4 weeks**: reduce weekly volume by 20–25%; this embeds adaptation before resuming progression.
- **Hard/Easy principle**: hard sessions (long runs, LT, VO₂max) must be separated by at least one easy day; the easy day must be genuinely easy (not moderately hard) to allow positive physiological adaptation.
- **Taper structure varies by race distance**: shorter races (5K) need shorter tapers (~1–2 weeks); half marathon requires 2–3 weeks; volume is cut significantly while intensity is maintained.
- **Tune-up races serve dual purpose**: fitness assessment and race-specific stimulus; shorter races (5K–10K) need less recovery than longer tune-up races (10-mile–HM).
- **Warm-up before all quality sessions and races**: 10–20 min easy run + dynamic stretching + drills + 4–6 strides; pre-race warm-up total ~45 minutes, ending 5 minutes before start.
- **Cool-down after all quality sessions**: 10–20 min easy run + static stretching (holds 20–30 seconds); clears lactate and reduces adrenaline; does not prevent DOMS.
- **Supplementary training (strength, plyometrics, flexibility) is non-optional** for improving running economy, correcting muscle imbalances, and preventing injury; 2–3 strength sessions per week; plyometrics ≤ 2/week.
- **Running economy improvements** come from strides, power hills, plyometrics, and running drills; improved economy directly lowers energy cost at any given pace.
- **Cross-training replaces running volume during injury** at equivalent perceived exertion; must include interval-based sessions to maintain running fitness, not just steady-state aerobic work.
- **Masters runners (age 40+) require additional recovery days** between hard sessions and longer tapers; volume and recovery rules scale with age bracket.
- **New mileage should be added to GA runs and warm-up/cool-down segments**, not to quality sessions.

---

## 2. Formules et calculs

| Formule | Inputs | Output | Notes |
|---|---|---|---|
| LT pace | Recent race time for ~60-min effort (typically 15K or HM) | Pace per km/mile at lactate threshold | Equal to current 15K–HM race pace; use most recent all-out effort |
| VO₂max interval pace | Recent 5K race time | Pace per km/mile for intervals | 5K race pace; effort in 3K-5K range; never faster than 5K pace |
| Long run pace (fast bound) | Current 10K race pace | long_run_pace_fast = 10K_pace × 1.20 | 20% slower than 10K pace `[ref: §2 Endurance Runs]` |
| Long run pace (slow bound) | Current 10K race pace | long_run_pace_slow = 10K_pace × 1.33 | 33% slower than 10K pace `[ref: §2 Endurance Runs]` |
| Long run pace alternate (fast) | Current 15K–HM pace | long_run_pace_fast = HM_pace × 1.17 | 17% slower than 15K–HM pace `[ref: §2 Endurance Runs]` |
| Long run pace alternate (slow) | Current 15K–HM pace | long_run_pace_slow = HM_pace × 1.29 | 29% slower than 15K–HM pace `[ref: §2 Endurance Runs]` |
| Weekly volume increase cap | Current weekly mileage | ≤ current_mileage × 0.10 | Hard ceiling; never exceed 10% week-over-week `[ref: §3]` |
| VO₂max recovery jog duration | Interval duration | 0.50 × interval_time ≤ recovery ≤ 0.90 × interval_time | Jog at easy effort `[ref: §2 VO₂max]` |
| LT interval recovery jog | Work interval duration | 0.20 × interval_time ≤ recovery ≤ 0.40 × interval_time | E.g., 2–4 min recovery for 8–10 min interval `[ref: §2 LT]` |
| Cross-training substitution (cycling) | Planned run duration | bike_duration = run_duration × 1.50 | To replace a recovery run `[ref: §2 Cross-Training]` |
| Masters recovery multiplier (age 36–45) | Post-VO₂max session | +1 recovery day vs standard schedule | `[ref: §3 Masters]` |
| Masters recovery multiplier (age 46–55) | Post-VO₂max session | +2 recovery days vs standard schedule | `[ref: §3 Masters]` |
| Masters recovery multiplier (age 56–65) | Post-VO₂max session | +2–3 recovery days vs standard schedule | `[ref: §3 Masters]` |

---

## 3. Tables de référence

| Zone / Seuil | Valeur | Unité | Condition |
|---|---|---|---|
| LT run HR (MHR) | 82–91 | % MHR | During tempo segment |
| LT run HR (HRR) | 77–88 | % HRR | During tempo segment |
| LT interval recovery | 20–40 | % of work interval duration | Jog recovery between LT reps |
| VO₂max interval pace | 5K race pace | — | Effort in 3K-5K range; pace anchored at 5K; never goal pace |
| VO₂max interval duration (per rep) | 2–6 | minutes | Hard constraint; 600 m–1600 m typical |
| VO₂max interval recovery | 50–90 | % of interval duration | Slow jog effort |
| Long run pace (10K-based) | 10K pace + 20–33 | % slower | HR 74–84% MHR |
| Long run HR (MHR) | 74–84 | % MHR | Entire run |
| Long run HR (HRR) | 65–78 | % HRR | Entire run |
| Long run % of weekly mileage | 20–25 | % | Shorter-distance runners; lower than marathon (22–29%) |
| GA run HR (MHR) | 70–81 | % MHR | Daily runs between quality sessions |
| GA run HR (HRR) | 62–75 | % HRR | Daily runs between quality sessions |
| Strides duration | 15–25 | seconds | Per repetition (~100 m) |
| Power hill duration | 8–15 | seconds | Per uphill repetition |
| Warm-up easy run | 10–20 | minutes | Before all quality sessions |
| Pre-race warm-up total | ~45 | minutes | End 5 min before start |
| Cool-down easy run | 10–20 | minutes | After all quality sessions |
| Static stretch hold | 20–30 | seconds | Post-workout, muscles warm |
| Dynamic stretching (pre-run) | ≤ 5 | minutes | Before quality sessions |
| Volume increase cap | 10 | % per week | Hard ceiling |
| Volume hold after increase | ≥ 1 | week | Before next step up |
| Cutback week frequency | every 3–4 | weeks | Reduce 20–25% |
| Cutback week volume reduction | 20–25 | % | From previous week's volume |
| Taper duration — 5K | 1–2 | weeks | Volume cut, intensity maintained |
| Taper duration — 10K | 2 | weeks | Volume cut, intensity maintained |
| Taper duration — half marathon | 2–3 | weeks | Volume cut, intensity maintained |
| Taper week 1 volume reduction | 20–25 | % of peak | All distances; first taper week `[ref: §4 Taper]` |
| Taper week 2 volume reduction (HM) | 35–40 | % of peak | Half marathon only; second taper week `[ref: §4 Taper]` |
| Taper final week volume reduction | 50–60 | % of peak | Race week `[ref: §4 Taper]` |
| Masters taper extension | +several days | days added | E.g., 17-day taper vs standard 14-day for goal race |
| Strength training frequency | 2–3 | times/week | Not within 24–36 h before a hard run |
| Plyometrics frequency | ≤ 2 | times/week | Only on recovery or GA days; not fatigued |
| Plyometrics rest between sets | ≥ 1 | minute | Due to high intensity |
| Masters min recovery (age 40–49, 5K) | 5 | days before next hard workout | `[ref: §3 Masters]` |
| Masters min recovery (age 50–59, 8K–10K) | 7 | days before next hard workout | `[ref: §3 Masters]` |
| Masters min recovery (age 60–69, 15K–HM) | 10 | days before next hard workout | `[ref: §3 Masters]` |

---

## 4. Règles prescriptives

### 4.1 Sélection des allures

- IF workout_type = VO₂max interval, THEN set pace = current 3K–5K race pace. [ref: §2 VO₂max / §3]
- IF workout_type = Lactate Threshold run, THEN set pace = current ~60-min race pace (15K–HM race pace equivalent). [ref: §2 LT / §3]
- IF workout_type = Long Run, THEN set pace between 10K_pace × 1.20 and 10K_pace × 1.33 (20–33% slower than 10K pace). [ref: §2 Endurance Runs]
- IF workout_type = General Aerobic, THEN set pace at conversational effort, HR 70–81% MHR. [ref: §2 GA / §3]
- IF workout_type = Recovery run, THEN pace = very easy; purpose = blood flow only, no training stress. [ref: §2 Recovery]
- IF VO₂max interval pace is set faster than current 5K race pace, THEN reject and reset to current 5K race pace. [ref: §2 VO₂max]

### 4.2 Progression de volume

- IF increasing weekly mileage, THEN limit increase to ≤ 10% of current weekly mileage. [ref: §3]
- IF a mileage step-up has just been applied, THEN hold at the new level for ≥ 1 week before the next increase. [ref: §3]
- IF athlete is in a base-building phase (increasing mileage), THEN remove VO₂max interval sessions from the schedule. [ref: §3]
- IF adding miles to the schedule, THEN add them to GA runs or warm-up/cool-down segments first — not to quality sessions. [ref: §3]
- IF athlete has trained for 3–4 consecutive weeks without a cutback, THEN schedule a cutback week at 75–80% of previous week's volume. [ref: §3]

### 4.3 Taper par distance de course

- IF goal race = 5K, THEN begin taper 1–2 weeks before race; IF taper week = 1 THEN reduce weekly volume by 20–25% from peak; IF taper week = final (race week) THEN reduce weekly volume by 50–60% from peak; maintain intensity throughout. `[ref: §4 Taper]`
- IF goal race = 10K, THEN begin taper 2 weeks before race; IF taper week = 1 THEN reduce weekly volume by 20–25% from peak; IF taper week = final (race week) THEN reduce weekly volume by 50–60% from peak; maintain intensity throughout. `[ref: §4 Taper]`
- IF goal race = half marathon, THEN begin taper 2–3 weeks before race; IF taper week = 1 THEN reduce weekly volume by 20–25% from peak; IF taper week = 2 THEN reduce weekly volume by 35–40% from peak; IF taper week = final (race week) THEN reduce weekly volume by 50–60% from peak; maintain intensity throughout. `[ref: §4 Taper]`
- IF tapering, THEN maintain workout intensities at race paces — reduce volume only, not pace. [ref: §5 Taper]
- IF runner_is_master AND approaching goal race, THEN extend taper by several days beyond the standard duration (e.g., 17-day taper instead of 14-day). [ref: §3 Masters / §5 Taper]

### 4.4 Exigences warm-up / cool-down

- IF workout_type = VO₂max interval OR Lactate Threshold OR Speed, THEN execute warm-up: 10–20 min easy run + dynamic stretching + drills + 4–6 strides. [ref: §2 Warm-Up]
- IF workout_type = VO₂max interval OR Lactate Threshold OR Speed, THEN execute cool-down: 10–20 min easy run + static stretching (20–30 sec holds). [ref: §2 Cool-Down]
- IF workout_type = race, THEN execute full ~45-min warm-up ending exactly 5 minutes before the start. [ref: §2 Warm-Up]

### 4.5 Volume et durée des intervalles VO₂max

- IF individual VO₂max interval duration < 2 min, THEN increase distance until interval duration ≥ 2 min at current 5K pace. [ref: §2 VO₂max]
- IF individual VO₂max interval duration > 6 min, THEN reduce distance until interval duration ≤ 6 min at current 5K pace. [ref: §2 VO₂max]
- IF VO₂max recovery duration < 50% of interval duration, THEN extend recovery to 50% of interval duration. [ref: §2 VO₂max]

### 4.6 Substitution entraînement (météo, maladie, blessure)

- IF weather_is_hot_and_humid (high humidity, temps 80s–90s°F / 27–37°C) AND workout_type = VO₂max OR Lactate Threshold, THEN postpone or cancel the quality workout. [ref: §3]
- IF runner_is_injured AND reports pain at injury site, THEN stop workout immediately and substitute with cross-training. [ref: §3]
- IF runner_is_injured, THEN replace running sessions with cross-training at equivalent perceived exertion; prioritize interval formats over steady-state. [ref: §3]
- IF substituting a recovery run with cycling, THEN set bike duration = planned run duration × 1.5. [ref: §2 Cross-Training]
- IF runner_is_sick with symptoms below the chest (lung congestion), THEN suspend all training until recovered. [ref: §3]
- IF runner_is_sick with symptoms above the neck only (runny nose, no fever), THEN substitute hard session with a recovery run or rest day. [ref: §3]

### 4.7 Courses de calage (tune-up races)

- IF tune-up race distance ≥ 10-mile OR half marathon, THEN apply a multi-day mini-taper before the race and do not schedule a hard session within the 10-day block surrounding it. [ref: §5]
- IF tune-up race distance = 5K–10K AND athlete needs fitness assessment, THEN apply a short mini-taper before the race. [ref: §5]
- IF tune-up race distance = 5K–10K AND athlete needs race-specific training stimulus, THEN run on tired legs without a taper. [ref: §5]

### 4.8 Règles masters

- IF runner_age IN [36–45], THEN add 1 extra recovery day after each VO₂max session. [ref: §3 Masters]
- IF runner_age IN [46–55], THEN add 2 extra recovery days after each VO₂max session AND 1 extra day after tempo/long runs. [ref: §3 Masters]
- IF runner_age IN [56–65], THEN add 2–3 extra recovery days after each VO₂max session. [ref: §3 Masters]
- IF runner_age IN [40–49] AND race_distance = 5K, THEN enforce ≥ 5 days before next hard workout. [ref: §3 Masters]
- IF runner_age IN [50–59] AND race_distance = 8K–10K, THEN enforce ≥ 7 days before next hard workout. [ref: §3 Masters]
- IF runner_age IN [60–69] AND race_distance = 15K–HM, THEN enforce ≥ 10 days before next hard workout. [ref: §3 Masters]

### 4.9 Entraînement complémentaire (force / pliométrie)

- IF scheduling strength training, THEN place session ≥ 24–36 hours before any hard running session. [ref: §2 Strength]
- IF scheduling plyometrics, THEN place session only on recovery or GA days when muscles are not fatigued. [ref: §2 Plyometrics]
- IF athlete is performing plyometrics, THEN rest ≥ 1 minute between sets. [ref: §2 Plyometrics]

### 4.10 Race-Distance Training Emphasis

- IF goal_race = 5K THEN schedule minimum 2 VO₂max sessions per week during race-specific phase AND 1 LT session per week. `[ref: §2 5K Training]`
- IF goal_race = 10K THEN schedule 1–2 VO₂max sessions AND 1 LT session per week during race-specific phase. `[ref: §2 10K Training]`
- IF goal_race = half_marathon THEN schedule 1 VO₂max session AND 1–2 LT sessions per week during race-specific phase. `[ref: §2 HM Training]`
- IF goal_race = half_marathon THEN include at least 1 HM-pace run per week in final 6 weeks before race. `[ref: §2 HM Training]`

### 4.11 Flags de sécurité (Head Coach)

- IF athlete shows persistent fatigue, elevated waking HR > 5 bpm above usual for ≥ 2 consecutive days, disturbed sleep ≥ 3 days, irritability, or unexplained weight loss, THEN flag as overreaching and pause all hard sessions. [ref: §1 Red Flags]
- IF athlete has fever or symptoms below the chest, THEN suspend all high-intensity and prolonged sessions for the duration of illness. [ref: §1 / §3]
- IF athlete is limping or reports pain that alters running biomechanics, THEN stop the session immediately and do not resume until pain-free. [ref: §1 Red Flags]
- IF athlete reports increased sense of exertion at a given pace persisting across multiple sessions, THEN reduce training load and flag as potential overreaching. [ref: §1 Red Flags]

---

## 5. Contre-indications et cas limites

- **5K-specific volume limits**: runners targeting 5K have lower absolute volume ceilings than HM-focused runners; the long run at 20–25% of weekly mileage is lower than the marathon equivalent (22–29%), reflecting shorter-distance physiology.
- **VO₂max intervals must never be run faster than current 5K race pace** — running at 1500 m pace shifts to anaerobic stimulus, reduces VO₂max adaptation, and increases injury risk.
- **LT workouts run too fast** shift the metabolic stimulus toward the anaerobic system and are less effective for improving lactate threshold; common error especially for motivated athletes.
- **Recovery runs run too fast** hinder recovery instead of promoting it; this is a high-frequency error when running with partners who have different session goals.
- **Long runs run too fast** compromise recovery for other key sessions during the week; long run pace must be strictly 20–33% slower than 10K race pace, not faster.
- **Base-building phase (mileage increase) is incompatible with VO₂max interval sessions**; combining both simultaneously elevates injury risk and compromises adaptation.
- **Strength training performed < 24 hours before a hard run** compromises running performance and increases injury risk from accumulated neuromuscular fatigue.
- **Plyometrics performed with poor form or while fatigued** carry elevated injury risk; form integrity is a prerequisite for every repetition.
- **Stopping abruptly after a hard effort** without a cool-down can cause blood pooling in the legs and dizziness; cool-down is mandatory after all quality sessions.
- **Prolonged static stretching before a workout** may temporarily reduce muscle strength; static stretching is only appropriate post-run when muscles are warm.
- **Taper intensity must never be reduced alongside volume** — cutting both simultaneously leads to detraining and race-day sluggishness.
- **Masters athletes following standard recovery schedules** designed for younger athletes face elevated injury and overtraining risk; the age-scaled recovery rules in §3 are non-negotiable for athletes 40+.
- **Gap note**: the source file does not specify the exact total VO₂max session volume (meters) for 5K–HM athletes (contrast Advanced Marathoning's 5,000–10,000 m bounds); apply the 2–6 min per interval rule as the binding constraint.

---

## 6. Références sources

| Concept | Référence livre |
|---|---|
| Core philosophy — consistency, base building, supercompensation | §0 — Core Philosophy |
| Runner profile inputs + red flags (overreaching, illness, pain) | §1 — Runner Profile Inputs |
| Endurance run definition, pace, HR, failure modes | §2 — Canonical Vocabulary: Endurance Runs |
| General aerobic run definition, pace, HR | §2 — Canonical Vocabulary: General Aerobic Runs |
| Recovery run definition, purpose, failure modes | §2 — Canonical Vocabulary: Recovery Runs |
| LT run definition, pace, HR, interval recovery | §2 — Canonical Vocabulary: Lactate Threshold Training |
| VO₂max interval definition, pace, duration, recovery | §2 — Canonical Vocabulary: VO₂max Training |
| Speed training — strides duration, form cues | §2 — Canonical Vocabulary: Speed Training |
| Power hills — duration, execution, failure modes | §2 — Canonical Vocabulary: Speed Training (Hill Training) |
| Warm-up structure and pre-race protocol | §2 — Canonical Vocabulary: Warm-Up |
| Cool-down structure, static stretch duration | §2 — Canonical Vocabulary: Cool-Down |
| Cross-training substitution, cycling duration formula | §2 — Canonical Vocabulary: Supplementary Training (Cross-Training) |
| Strength training frequency, scheduling constraints | §2 — Canonical Vocabulary: Supplementary Training (Strength & Plyometrics) |
| Plyometrics frequency, rest, form requirements | §2 — Canonical Vocabulary: Supplementary Training (Strength & Plyometrics) |
| Dynamic and static stretching rules | §2 — Canonical Vocabulary: Supplementary Training (Flexibility & Drills) |
| Pace selection decision rules | §3 — Decision Rules: Pace Selection Logic |
| Volume progression + hold cadence | §3 — Decision Rules: Training Progression and Scaling |
| Workout substitution (weather, illness, injury) | §3 — Decision Rules: Workout Substitution |
| Masters recovery scaling by age bracket | §3 — Decision Rules: Scaling for Special Populations |
| LT interval constructor (warm-up, main, cool-down) | §4 — Workout Constructors: Lactate Threshold (Intervals) |
| VO₂max interval constructor | §4 — Workout Constructors: VO₂max (Intervals) |
| Strides constructor | §4 — Workout Constructors: Speed (Strides) |
| Power hills constructor | §4 — Workout Constructors: Power (Short Hills) |
| Two-phase periodization structure | §5 — Week/Season Structure: Training Phases |
| Hard/Easy distribution principle | §5 — Week/Season Structure: Distribution of Quality Sessions |
| Taper principles — volume, intensity, masters extension | §5 — Week/Season Structure: Tapering Principles |
