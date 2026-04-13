# Daniels' Running Formula — Agent Extract

**Source:** Jack Daniels, Daniels' Running Formula, Human Kinetics, 3rd edition
**Domain:** Running — VDOT, training zones (E/M/T/I/R), phase structure, return-to-running
**Agent cible:** Running Coach (principalement); Head Coach (règles de sécurité)

---

## 1. Concepts fondamentaux

- VDOT = pseudo-VO2max index derived from recent race performance; governs all training paces
- 5 training intensities: E (Easy), M (Marathon), T (Threshold), I (Interval), R (Repetition)
- Train at current fitness, not goal fitness — VDOT based on last race ≤4-6 weeks ago
- Phase structure: 4 phases (I=Foundation/E+L, II=Repetition/R, III=Interval/I, IV=Threshold/T)
- Hard/Easy: quality sessions require recovery days; never 2 consecutive hard days without compensation
- Volume progressed conservatively: hold new stress level 3-4 weeks before increasing
- Rest = training: recovery, sleep, nutrition are non-negotiable inputs
- 10% weekly mileage cap — never exceeded

---

## 2. Formules et calculs

| Formule | Inputs | Output | Notes |
|---|---|---|---|
| VDOT lookup | race_distance, race_time | VDOT (integer) | `[ref: Table 5.1]` |
| Training paces | VDOT | E_pace, M_pace, T_pace, I_pace, R_pace | `[ref: Table 5.2]` |
| 6-Second Rule | R_pace | I_pace = R_pace − 6 s/400m; T_pace = I_pace − 6 s/400m | For VDOT > 50; use 7-8 s for VDOT 40-50 `[ref: §2]` |
| T-pace volume cap | weekly_mileage | max_T_volume = weekly_mileage × 10% | Single continuous T run also capped `[ref: §2 T-Pace]` |
| I-pace volume cap | weekly_mileage | max_I_volume = min(10 km, weekly_mileage × 8%) | Per session `[ref: §2 I-Pace]` |
| R-pace volume cap | weekly_mileage | max_R_volume = min(8 km, weekly_mileage × 5%) | Per session `[ref: §2 R-Pace]` |
| Long run cap | weekly_mileage | max_long = min(weekly_mileage × 25-30%, 150 min) | 150 min = practical cap `[ref: §2 L-Pace]` |
| VDOT break — short | pre_break_VDOT, break_days (6-28) | adjusted_VDOT = pre_break_VDOT × 0.93-0.99 | `[ref: Table 9.2]` |
| VDOT break — long | pre_break_VDOT, cross_trained (bool) | adjusted_VDOT = pre_break_VDOT × 0.80-0.92 | For break > 8 weeks `[ref: Table 9.2]` |

---

## 3. Tables de référence

| Zone/Seuil | Valeur | Unité | Condition |
|---|---|---|---|
| E-pace effort | conversational | — | No HR cap specified; sustainable conversation `[ref: §2 E-Pace]` |
| T-pace effort | comfortably hard | — | Controlled steady-state; not race effort `[ref: §2 T-Pace]` |
| I-pace work bout (min) | 3 | min | Per repetition `[ref: §2 I-Pace]` |
| I-pace work bout (max) | 5 | min | Per repetition `[ref: §2 I-Pace]` |
| R-pace work bout (max) | 2 | min | Per repetition `[ref: §2 R-Pace]` |
| I-pace recovery duration | ≥ work bout duration | min | Equal to work bout duration; never less `[ref: §2 I-Pace]` |
| R-pace recovery duration | 2-3× work bout duration | min | Near-full recovery required `[ref: §2 R-Pace]` |
| Phase length (ideal) | 6 | weeks | Compress if season < 24 weeks `[ref: §5]` |
| VDOT update minimum interval | 3-4 | weeks | Between updates `[ref: §3]` |
| Break ≤5 days → load | 100 | % | Resume at 100% previous load `[ref: §3]` |
| Break 6-28 days → first half load | 50 | % | Of return period `[ref: §3]` |
| Break 6-28 days → second half load | 75 | % | Of return period `[ref: §3]` |
| Altitude threshold | 7,000 | ft | Adjust I/T to effort; keep R_pace same `[ref: §3]` |

---

## 4. Règles prescriptives

### Pace Selection Logic

- IF runner provides a recent race time THEN look up race distance and time in Table 5.1 to determine current VDOT `[ref: §3 Pace Selection Logic]`
- IF VDOT is determined from Table 5.1 THEN use that VDOT in Table 5.2 to set all training paces (E, M, T, I, R) `[ref: §3 Pace Selection Logic]`
- IF runner has no recent race time AND has a recent mile time THEN use mile race pace as R-pace for 400m repetitions `[ref: §3 Pace Selection Logic]`
- IF runner has no recent race time AND has a recent mile time THEN calculate I-pace as R-pace − 6 s/400m AND T-pace as I-pace − 6 s/400m (6-Second Rule) `[ref: §3 Pace Selection Logic]`
- IF VDOT is in the 40-50 range AND using 6-Second Rule THEN use 7-8 seconds per 400m instead of 6 seconds `[ref: §3 Pace Selection Logic]`
- IF runner is a novice with very slow performance THEN use Table 5.3 to determine R, I, T, and M paces based on their Mile or 5K time `[ref: §3 Pace Selection Logic]`

### Progression Logic

- IF runner completes 4-6 weeks of consistent training at a given VDOT level AND workouts begin to feel easier THEN a new race to recalculate VDOT is warranted `[ref: §3 Progression Logic]`
- IF runner completes a new race AND achieves a better time THEN recalculate VDOT based on the new performance AND adjust all training paces accordingly `[ref: §3 Progression Logic]`
- IF a new race performance occurs within 3-4 weeks of the last VDOT update THEN note the result but do NOT update training paces until the adaptation period has elapsed `[ref: §3 Progression Logic]`

### Workout Substitution & Modification Logic

- IF scheduled for a quality workout AND weather is adverse (e.g., high wind) THEN substitute with a less pace-dependent workout achieving a similar purpose (e.g., fartlek or hard hill repeats) `[ref: §3 Workout Substitution & Modification Logic]`
- IF scheduled for a quality workout AND weather is adverse AND substitution is not feasible THEN swap the quality day with a scheduled E-day AND perform the quality workout on the day with better weather `[ref: §3 Workout Substitution & Modification Logic]`
- IF training at altitude ≥ 7,000 ft THEN keep R-pace unchanged from sea-level pace AND increase recovery time `[ref: §3 Workout Substitution & Modification Logic]`
- IF training at altitude ≥ 7,000 ft THEN run I-pace and T-pace by effort only, not by target pace `[ref: §3 Workout Substitution & Modification Logic]`
- IF training at altitude ≥ 7,000 ft THEN run E and L runs by feel and normal breathing pattern `[ref: §3 Workout Substitution & Modification Logic]`

### Scaling & Return-to-Running Logic

- IF returning from a break of 5 days or fewer THEN resume training at 100% of previous workload and VDOT `[ref: §3 Scaling & Return-to-Running Logic]`
- IF returning from a break of 6-28 days THEN reduce training load to 50% for the first half of the return period AND 75% for the second half `[ref: §3 Scaling & Return-to-Running Logic]`
- IF returning from a break of 6-28 days THEN adjust VDOT to ~93-99% of pre-break VDOT per Table 9.2 `[ref: §3 Scaling & Return-to-Running Logic]`
- IF returning from a break of more than 8 weeks THEN follow a structured multi-week return plan: 3 weeks at 33% load, 3 weeks at 50% load, with mileage caps `[ref: §3 Scaling & Return-to-Running Logic]`
- IF returning from a break of more than 8 weeks THEN reduce VDOT to ~80-92% of pre-break VDOT per Table 9.2, depending on whether cross-training was maintained `[ref: §3 Scaling & Return-to-Running Logic]`

### Guardrail Rules (§2 and §4)

- IF total_T_volume_in_session > weekly_mileage × 10% THEN reduce T volume to cap `[ref: §2 T-Pace]`
- IF I_pace_work_bout_duration > 5 min THEN shorten to 5 min maximum `[ref: §2 I-Pace]`
- IF R_pace_work_bout_duration > 2 min THEN shorten to 2 min maximum `[ref: §2 R-Pace]`
- IF runner sick OR injured THEN pause all training; do not modify and continue `[ref: §0]`

---

## 5. Contre-indications et cas limites

- Do NOT set VDOT from goal race time — current race performance only `[ref: §0]`
- Do NOT update VDOT more than once every 3-4 weeks even after a new race `[ref: §3]`
- Do NOT run I-pace work bouts > 5 min — stimulus shifts away from VO2max `[ref: §2 I-Pace, Figure 4.3]`
- Do NOT run R-pace work bouts > 2 min — neuromuscular purpose degrades; form suffers `[ref: §2 R-Pace]`
- Do NOT train when sick or injured — no exceptions `[ref: §0, §1]`
- Phase III (I-pace) can be skipped for short seasons (< 9 weeks) — go Phase II → Phase IV directly `[ref: §5]`
- Altitude ≥ 7,000 ft: R_pace unchanged but increase recovery; T_pace and I_pace by effort only, not target pace `[ref: §3]`
- VDOT 6-Second Rule uses 7-8s/400m for VDOT 40-50 range, not 6s `[ref: §3]`

---

## 6. Références sources

| Concept | Référence livre |
|---|---|
| VDOT lookup table | Table 5.1 |
| Training pace table (all zones) | Table 5.2 |
| Novice pace table | Table 5.3 |
| Break duration / VDOT decay | Table 9.2 |
| I-pace: faster ≠ better | Figure 4.3 |
| Phase structure | §5 Week/Season Structure |
| All IF/THEN decision rules | §3 Decision Rules |
| Workout constructors (guardrails) | §4 Workout Constructors |
