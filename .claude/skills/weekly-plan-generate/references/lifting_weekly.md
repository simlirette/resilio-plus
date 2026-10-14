# Lifting in the Weekly Plan

Read when the athlete has `lifting` in their profile (`resilio lift profile get`).
Methodology: `docs/coaching/lifting_methodology.md`.

## Inputs (run before designing the gym days)

```bash
resilio lift sync                              # fresh Hevy history (sets, reps, kg)
resilio lift profile get                       # goal, gym days, split, rep ranges, RIR, protected list
resilio lift blocks get                        # this block's focus, sessions/week, weekly set targets
resilio lift volume --week-start <PREV_MONDAY> # what was actually done last week
```

If `lift sync` returns `error_type: config` (no `HEVY_API_KEY`), continue without history:
prescribe by RIR, no loads, and tell the athlete once.

## Design rules

- Gym sessions only on `gym_days` (+ `optional_days` when the athlete wants them). `validate-week` errors otherwise.
- Follow the block's `sessions_per_week` and `weekly_sets`; stay inside the hybrid MRV.
- Place legs per the running week: never the day before long run / intervals / strides / time trial.
- Every session lists `exercises` with Hevy template ids (`resilio lift templates search "<name>"`).
- Include every `protected_exercises` entry at least once per week.
- If `include_power`, one power/plyo exercise per week (`kind: power`, 2–4 × 3–5, no RIR).
- Recovery week (`is_recovery_week: true`): ~40 % fewer sets, same loads, RIR 3–4.

## JSON (inside the week, next to `workouts`)

```json
"strength_sessions": [
  {
    "date": "2026-10-20", "day_of_week": 1, "session_type": "legs", "week_number": 2,
    "title": "Legs", "time_of_day": "15:00", "duration_minutes": 60,
    "notes": "Power first while fresh. Knee: stop step-downs if pain (not tightness).",
    "exercises": [
      {"exercise_template_id": "56092DD1", "title": "Box Jump", "kind": "power",
       "sets": 3, "rep_range": [3, 5], "rest_seconds": 120},
      {"exercise_template_id": "72CFFAD5", "title": "Romanian Deadlift (Dumbbell)", "kind": "hypertrophy",
       "sets": 3, "rep_range": [8, 10], "target_rir": 2, "rest_seconds": 150},
      {"exercise_template_id": "108D7A14", "title": "Nordic Hamstrings Curls", "kind": "prehab",
       "sets": 2, "rep_range": [4, 8], "target_rir": 2, "rest_seconds": 120}
    ]
  }
]
```

Exercise fields: `exercise_template_id`, `title`, `kind` (hypertrophy | power | prehab | core | mobility),
`sets`, `warmup_sets`, `rep_range` [low, high] **or** `duration_seconds`, `target_rir`, `load_kg`,
`rest_seconds`, `superset_group`, `notes`.

## Loads, then validation

```bash
resilio lift suggest-loads --file /tmp/weekly_plan_wN.json   # fills load_kg from history (never guesses)
resilio plan validate-week --file /tmp/weekly_plan_wN.json   # runs + lifting checks
```

Report `data.lifting_planned_volume` in the review and address every lifting warning
(missing protected exercise, RIR too low, above MRV, legs before quality run) or state why it is accepted.

## Presenting to the athlete

Per session: day, title, then one line per exercise, e.g.
`3×8–10 Romanian Deadlift (Dumbbell) @ 20 kg · RIR 2 · rest 150s`.
Say which loads came from history and which are "find your working load at RIR 2".
After approval, the apply step pushes the sessions to Hevy (folder "Resilio").
