# Lifting for Hybrid Athletes: Coaching Methodology

How the coach programs strength training next to a running goal. Tools compute
(`resilio lift …`); the coach decides. Every number below is a default the coach
can override with a stated reason.

## 1. Goal types (profile `lifting.goal`)

| Goal | Intent | Working reps | Effort | Notes |
|---|---|---|---|---|
| `hypertrophy_athletic` | Muscle and athleticism without max-strength work | compounds 6–10, accessories 10–15 | RIR 1–3 | Nothing below 5 reps except power/plyo. Default for runners. |
| `hypertrophy` | Muscle first | 6–12 / 10–20 | RIR 0–3 | Lower-body volume still capped by running load. |
| `maintenance` | Keep what you have during a heavy running block | 6–12 | RIR 2–3 | ~⅓ of usual volume holds strength and size for weeks. |
| `strength` | Max strength | 3–6 | RIR 1–3 | Not used for the current athlete. |

RIR = reps in reserve (RIR 2 = could have done 2 more). Hevy logs RPE; RPE ≈ 10 − RIR.

## 2. Interference: running + lifting in one week

- The running goal leads when `running_priority` is primary or equal and a race/test is ahead.
  Legs already get large stimulus from running, so **lower-body lifting stays near MEV to low MAV**;
  upper body can go to MAV.
- **Placement** (checked by `validate-week`): no heavy legs the day before a long run, intervals,
  strides or a time trial; no legs and a run on the same day unless the run is easy and comes first
  with ≥ 6 h between. Upper body next to hard runs is fine.
- Hard running and hard lifting on the same day beat spreading fatigue across every day:
  "hard days hard, easy days easy".
- Lifting deloads line up with running recovery weeks.

## 3. Volume landmarks (hard sets per muscle group per week)

From `resilio/core/lifting/volume_landmarks.json` (Israetel MEV/MAV/MRV). `resilio lift volume`
counts a set for the primary muscle and half a set for each secondary muscle, and reduces MRV
by `hybrid_reduction` (quads −40 %, hamstrings −30 %, glutes/calves −20 %) because running already loads them.

- Below MEV for several weeks → muscle is maintained at best.
- MEV → MAV: productive range. Start a block near MEV and add 1–2 sets per muscle per week.
- Above the (hybrid) MRV → recovery debt; cut sets or the run quality suffers first.

## 4. Progression (double progression)

`resilio lift progression` / `resilio lift suggest-loads` apply it from Hevy history:

1. Work inside the rep range at the target RIR.
2. When **every** working set reaches the top of the range, add load (upper +2.5 kg, lower +5 kg,
   rounded to 0.5 kg) and restart at the bottom of the range.
3. Otherwise keep the load and add a rep to the weakest set.
4. Below the range → repeat the load.
5. No logged set in the last 6 weeks → **no load suggestion**: prescribe by RIR and let the
   athlete find the working load. Never invent loads.
6. Deload week: ~40 % fewer sets, same load, RIR 3–4.

## 5. Power and plyometrics (`include_power: true`)

Once a week, fresh (start of the legs session or before an easy run day): 2–4 sets × 3–5 reps
of box jumps, broad jumps, pogo hops or med-ball throws. Full recovery between sets, maximal
intent, stop when quality drops. Counts as `kind: power`: excluded from hypertrophy volume
and from the min-reps rule. Benefits running economy and athleticism at little fatigue cost.

## 6. Prehab / protected work (`protected_exercises`)

Exercises tied to the athlete's history stay in every week unless the athlete removes them;
`validate-week` warns when one is missing.

- **Hamstring cramps late in races** (fatigue cramping, not injury): eccentric hamstring work,
  e.g. Nordic curls 2–3 × 4–8 and RDL, plus more aerobic volume.
- **Anterior knee tightness**: quad and hip strength, e.g. split squats, step-downs, wall sits,
  hip abduction. Progress gradually; pain (not tightness), swelling, or pain on stairs means
  reduce load and tell the coach.

## 7. Session design checklist

1. Session `title` from the profile split (e.g. "Upper A").
2. 4–7 exercises: compounds first, accessories after, prehab/core last (power first if present).
3. Each exercise has a **Hevy template id** (`resilio lift templates search`), sets, rep range,
   target RIR, rest (compounds 120–180 s, accessories 60–90 s).
4. Run `resilio lift suggest-loads --file <week.json>` to fill loads from history.
5. `resilio plan validate-week --file <week.json>` must pass. Address every lifting warning
   or explain why it is accepted.

## 8. Reviewing the week

- `resilio lift sync`, then `resilio lift adherence --week N`: sessions done, sets done vs planned,
  reps vs range, loads vs prescribed.
- `resilio lift volume --week-start <Monday>`: actual hard sets per muscle.
- Signals to act on: sessions repeatedly moved or missed (fix the schedule, not the athlete),
  reps below range two sessions in a row (hold or reduce load), heavy-legs complaints before
  quality runs (move legs or cut lower-body sets), unmapped exercises (classify them).
