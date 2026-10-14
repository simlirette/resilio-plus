# SP2–SP5 — Lifting in the Claude Code coach

Date: 2026-10-14 · Parent: `2026-10-14-claude-code-hybrid-coach-design.md` · Status: approved ("Yes go, execute everything")

## Reorder vs umbrella (approved 2026-10-14)

| # | Now | Why |
|---|---|---|
| SP2 | Lifting data + analysis (Hevy client, sync, catalog, lifting profile, history/volume/progression) | Prescriptions need Hevy template ids; progression needs history |
| SP3 | Prescription (exercises in sessions, macro lifting blocks, validation wired into `plan validate-week`, load suggestions, adherence, calendar shows exercises) | |
| SP4 | Skills + CLAUDE.md + methodology doc | |
| SP5 | `resilio lift push` → Hevy routines (slot reuse) | |

## Athlete lifting goal (Simon, 2026-10-14)

`hypertrophy_athletic`: hypertrophy for athleticism, **no max-strength work**. Running block (10K focus) leads;
running and lifting equal priority in the profile. Gym Mon/Tue/Wed (+ optional Thu). Split Upper A / Legs / Upper B / optional arms.
Protected work: Nordic curls, RDL (hamstring cramps), step-downs, split squats, wall sits, hip abduction (right knee).
Light power/plyo once a week: approved.

## Verified Hevy API facts (OpenAPI at `https://api.hevyapp.com/docs/swagger-ui-init.js`, live probe 2026-10-14)

- Auth header `api-key`. Max `pageSize`: workouts 10, events 10, routines 10, folders 10, exercise_templates 100.
- `GET /v1/workouts/events?since=ISO` → `{page, page_count, events:[{type:"updated", workout:{…}} | {type:"deleted", id, deleted_at}]}`.
- Workout: `id, title, routine_id, description, start_time, end_time, updated_at, created_at, exercises[{index,title,notes,exercise_template_id,superset_id,sets[{index,type,weight_kg,reps,distance_meters,duration_seconds,rpe,custom_metric}]}]`. Set `type` ∈ warmup|normal|failure|dropset. Weights always kg.
- Template: `id, title, type (weight_reps|reps_only|bodyweight_reps|bodyweight_assisted_reps|duration|weight_duration|distance_duration|short_distance_weight), primary_muscle_group, secondary_muscle_groups[], equipment, is_custom`.
  Muscle groups: abdominals, shoulders, biceps, triceps, forearms, quadriceps, hamstrings, calves, glutes, abductors, adductors, lats, upper_back, traps, lower_back, chest, cardio, neck, full_body, other.
- `POST /v1/routines {routine:{title, folder_id, notes, exercises:[{exercise_template_id, superset_id, rest_seconds, notes, sets:[{type, weight_kg, reps, distance_meters, duration_seconds, custom_metric, rep_range:{start,end}}]}]}}` → 201 `{routine}`; **403 = routine limit exceeded**.
- `PUT /v1/routines/{id}` same body (folder_id ignored for moves) → 200; 404 if not the user's.
- `POST /v1/routine_folders {routine_folder:{title}}` → 201 folder. **No delete endpoints anywhere.**
- Simon's account: 31 workouts, existing folders "Prehab", "UPPER/LOWER + Arnold Split" (never touched by Resilio).

## SP2 — Lifting data + analysis

Layout (mirrors CLI → `resilio/api` → `resilio/core`):
- `resilio/schemas/lifting.py` — Pydantic models (stored workout, template, catalog entry, lifting profile, reports).
- `resilio/core/lifting/hevy_client.py` — `HevyClient(api_key, transport=None)`; typed errors `HevyConfigError` (no key), `HevyAuthError` (401), `HevyRateLimitError` (429 after retries), `HevyAPIError`. 429 → exponential backoff (3 tries). Key from `HEVY_API_KEY` only.
- `resilio/core/lifting/store.py` — `LiftingStore(base_dir)`; `data/lifting/workouts/YYYY-MM/<id>.yaml`, `sync_state.yaml`, `exercise_templates.yaml`, `hevy_routines.yaml`.
- `resilio/core/lifting/sync.py` — first run pages `/v1/workouts`; afterwards `/v1/workouts/events?since=<last_sync − 10 min>`; applies updates and deletes; state saved only after success.
- `resilio/core/lifting/catalog.py` — Hevy muscle → landmark group (`quadriceps→quads, lats|upper_back→back, abdominals→core, …`; `traps|lower_back|forearms|neck|cardio|full_body|other` → not counted). Lower-body flag from primary group. Pattern from title keywords (squat, deadlift/RDL/hinge, press, row/pull, lunge/split, jump/hop/bound/throw/slam → plyo, plank/crunch → core). SFR tier by title match against `.bmad-core/data/exercise-database.json`. Unknown template → listed as unmapped, never guessed.
- `resilio/core/lifting/analysis.py` — pure functions:
  - `e1rm(weight, reps)` Epley, only for reps ≤ 12 and weight > 0.
  - `exercise_history(workouts, template_id, weeks)` → per session: date, working sets, top set, best e1RM, total reps.
  - `weekly_volume(workouts, catalog, week_start, hybrid=True)` → hard sets (non-warmup) per landmark group, primary 1.0 / secondary 0.5; landmarks with MRV × (1 − hybrid_reduction) when hybrid; status below_mev | productive | above_mav | above_mrv; unmapped titles.
  - `progression(history, rep_range, increment_kg, deload=False)` → double progression: all working sets at top of range → `load + increment`; else same load, `+1 rep` target; deload → sets ×0.6 (rounded down, ≥1), same load. No load if no logged set in last 6 weeks (`reason: no_recent_history`).
- Landmarks copied to `resilio/core/lifting/volume_landmarks.json` (source noted) so the CLI does not depend on `.bmad-core`.
- Lifting profile = `lifting:` section on `AthleteProfile` (optional, backward compatible): `goal, gym_days, optional_days, split, compound_rep_range [6,10], accessory_rep_range [10,15], rir_target [1,3], min_reps 5, include_power, protected_exercises, blacklist, increment_kg {upper 2.5, lower 5.0}`.
- CLI `resilio lift`: `sync [--full]`, `templates sync | search QUERY [--muscle M]`, `history --exercise X [--weeks N]`, `volume [--week-start D] [--no-hybrid]`, `progression --exercise X [--deload]`, `profile get | set …`. `--exercise` accepts template id or title (case-insensitive exact, else unique substring).

## SP3 — Prescription

- `ExercisePrescription {exercise_template_id, title, kind (hypertrophy|power|prehab|core|mobility), sets, rep_range [lo,hi] | duration_seconds, target_rir, load_kg, rest_seconds, superset_group, notes}`; `StrengthSession.exercises: list[ExercisePrescription] = []`, `StrengthSession.title`.
- `LiftingBlock {start_week, end_week, focus (hypertrophy|maintenance|deload|power), sessions_per_week, weekly_sets: {group: sets}, notes}`; `MasterPlan.lifting_blocks: list[LiftingBlock] = []`.
- `validate_lifting_prescription(week, catalog, profile)` → errors: unknown template id, blacklisted exercise, reps < `min_reps` on non-power work, gym session on a non-gym day; warnings: rep range outside goal ranges, RIR < 1, protected exercises absent from the week, weekly hard sets above adjusted MRV, placement warnings from `validate_strength_placement` (now actually wired).
- `plan validate-week` runs it for weeks with `strength_sessions`.
- `resilio lift suggest-loads --file week.json` fills `load_kg` from `progression` (writes in place, reports per exercise).
- `resilio lift adherence --week N` → per planned session: matched Hevy workout (same date, else ±1 day by title), sets done vs planned, reps/RIR achieved, missing sessions.
- Calendar event description lists exercises (`3×8–10 Incline DB Press @ 25 kg, RIR 2`).

## SP4 — Skills

- Root `CLAUDE.md` + `AGENTS.md`: lifting section (commands, rules, athlete-goal handling), replaces the SP1 "schedule layer" note.
- `docs/coaching/lifting_methodology.md` — concurrent training for runners: interference management, hypertrophy volume landmarks with hybrid reduction, RIR, double progression, plyo dosing, knee/hamstring prehab, deloads aligned with running recovery weeks.
- Skills (both `.claude/` and `.agents/` trees): first-session (lifting intake → `lift sync`, `lift profile set`), macro-plan-create (`lifting_blocks`), weekly-plan-generate (exercises + `lift volume`, `lift progression`, `lift suggest-loads`), weekly-plan-apply (validation covers lifting, then `lift push`), weekly-analysis (`lift sync`, `lift adherence`, `lift volume`).
- Contract test: lifting commands mentioned in both trees.

## SP5 — Push to Hevy

- `resilio lift push --week N [--dry-run]`. Folder "Resilio" (found by title, else created; id stored).
- Slot key = weekday (`mon`…`sun`); title `Resilio · Mon · <session title>`; `hevy_routines.yaml` maps slot → routine id. Existing slot → PUT; new slot → POST into folder. Slots not used this week → PUT with existing exercises and title `Resilio · <Day> · (not scheduled)`.
- Sets: `warmup` sets (if any) then N `normal` sets with `rep_range`, `weight_kg = load_kg`, duration exercises use `duration_seconds`. Exercise notes carry `RIR x` + coach notes; routine notes carry week number and session intent.
- 403 (routine limit) → error with next steps; 404 on PUT → slot recreated with POST.
- Real pushes only after the athlete approves the week (skill rule). Development verification uses `--dry-run` only.

## Error handling

All API functions return model | `LiftError(error_type, message, next_steps)`; mapped to existing exit codes
(`config` missing key, `auth`, `rate_limit`, `network`, `validation`, `not_found`).

## Testing

Unit tests per module with `httpx.MockTransport` fixtures modelled on the verified shapes; store/sync with `tmp_path`;
pure-function tests for analysis/validation/payload building; CLI tests with `CliRunner`. No live API in tests.
Live verification: read-only `lift sync` + `templates sync` + analysis on Simon's data; `lift push --dry-run`.

## Non-goals

Strength-focused programming, nutrition, swim/bike, backend changes, deleting Hevy data, editing non-Resilio Hevy folders/routines.
