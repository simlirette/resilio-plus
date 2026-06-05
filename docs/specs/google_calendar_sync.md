# Google Calendar Sync — Design Proposal

**Status:** awaiting validation (no code written yet)
**Author:** AI coach session, 2026-06-05
**Scope:** Push the local training plan into a dedicated Google Calendar so the
athlete consumes sessions on iPhone (notifications + detail). One-way:
local plan = source of truth, calendar = consumption mirror.

---

## 1. Module structure (mirrors the Strava pattern)

Strava lives flat in `resilio/core/strava.py` (plain functions, `httpx`,
`tenacity`, tokens persisted by the CLI command, JSON envelopes). Mirror it:

| New file | Role |
|----------|------|
| `resilio/core/google_calendar.py` | `GoogleCalendarClient`: auth, refresh, ensure_calendar, list/insert/patch/delete events. **Only** place that imports `googleapiclient` / `google.oauth2`. |
| `resilio/core/calendar_sync.py` | `PlanToCalendarSync`: `MasterPlan` → event dicts (mapping table) + upsert/diff orchestration (idempotence). No Google import — takes the client as a dependency. |
| `resilio/schemas/calendar.py` | Pydantic `CalendarEvent`, `CalendarSyncReport`. |
| `resilio/cli/commands/calendar.py` | Typer subapp: `resilio calendar auth`, `resilio calendar sync`. |
| `schemas/config.py` + `templates/settings.yaml` | Add `GoogleCalendarSettings` (default times, timezone, reminders, gym schedule). |

State & secrets:
- OAuth client (`client_id`/`client_secret`): read from the existing
  `credentials.json` (desktop app, already in repo root). Path configurable.
- `data/google_calendar/token.json` — refresh token (gitignored via `data/`).
- `data/google_calendar/state.json` — dedicated `calendar_id` + last-sync meta.

CLI wiring: one line in `resilio/cli/__init__.py`
(`app.add_typer(calendar.app, name="calendar", ...)`).

New deps (encapsulated, lazy-imported in the client only):
`google-api-python-client`, `google-auth`, `google-auth-oauthlib`.

---

## 2. Auth flow

Desktop OAuth via `google-auth-oauthlib` (works on Windows 11):

- First run (`resilio calendar auth`): `InstalledAppFlow.from_client_secrets_file`
  → `run_local_server(port=0)` opens the browser, athlete authorizes, token
  persisted to `data/google_calendar/token.json`.
- Later runs: load token, silent `Credentials.refresh()` when expired.
- Scope: **`https://www.googleapis.com/auth/calendar.events` only** (not full
  `calendar`). Lets us create/manage events in a calendar we own.
- Note: creating the dedicated calendar needs `calendar` scope, not just
  `calendar.events`. See decision Q below — either widen scope to
  `calendar` for the create-once, or target the primary calendar.

---

## 3. Plan → events mapping

Read path: `resilio.api.plan.get_plan_weeks(week_number=current, count=N)` →
`WeekPlan.workouts` (`WorkoutPrescription`). Running only (see §6).

| Plan `workout_type` | Title | Description | Default time (wk) | Reminder |
|---|---|---|---|---|
| `easy` | 🏃 Easy run {dist}km Z2 | WU/CD + `pace_range` + notes | 06:30 | 30 min |
| `tempo` / `intervals` / `fartlek` / `strides` | 🏃 {structured summary} | WU + `intervals[]` w/ paces + CD + notes | 06:30 | 30 min |
| `long_run` | 🏃 Long run {dist}km | full detail + notes | 08:00 (weekend) | 60 min |
| `race` | 🏁 Race {dist}km | notes | from plan | 60 min |
| `rest` | 🛌 Rest | notes or empty | all-day | none |
| gym (see §6) | 🏋️ {Leg/Push/Pull day} | "Voir Hevy pour le détail" — nothing else | 18:00 | 30 min |

- Times/timezone configurable in settings (`America/Toronto` default).
- Description built from `WorkoutPrescription` fields already present
  (`pace_range`, `warmup_km`, `cooldown_km`, `intervals`, `target_rpe`, `notes`).

---

## 4. Idempotence (critical)

- Deterministic key `resilio-{date_iso}-{workout_type}-w{week}` stored in
  event **`extendedProperties.private.resilio_uid`** (NOT the Google event
  `id`, which has a restricted charset). Source-of-truth marker = also store
  `private.resilio_managed = "1"`.
- Sync algorithm for the target window [today → today + N weeks]:
  1. List remote events with `privateExtendedProperty=resilio_managed=1`.
  2. Build `{resilio_uid: remote_event}`.
  3. For each planned workout → desired event. **insert** if uid absent,
     **patch** if present and changed (title/desc/time/reminder diff),
     no-op if identical.
  4. **delete** remote managed events whose uid is no longer in the plan.
- Only touch events dated **today or later** — past events are never modified
  or deleted (preserves history when a plan is regenerated mid-week).
- Regenerating the plan 10× = stable (same uids → patch/no-op, never dup).

---

## 5. Calendar target

First run: create calendar "Resilio Training" (color set), store `calendar_id`
in `state.json`. Athlete can toggle/recolor without touching their main
calendar. Fallback (config): target `primary`.

---

## 6. OPEN DECISIONS (need your call before coding)

**Q1 — Gym sessions (blocking).** The persisted plan (`current_plan.yaml` →
`MasterPlan.weeks[].workouts`) holds **running workouts only**. `WorkoutType`
has no gym/strength value, and `multi_sport_schedule` exists only on
`MonthlyPlan`, which is not the persisted plan. So there is nowhere in the plan
to read your 4 gym sessions/week from. Options below.

**Q2 — OAuth client location / scope.** Reuse the existing `credentials.json`
(Google-native, already present) vs move client_id/secret into
`secrets.local.yaml` (Strava convention). Plus scope width for calendar
creation.

**Q3 — Completed-session marking.** Strava already knows what's done. Mark the
matching calendar event with a ✅ title prefix, or leave events untouched?

---

## 7. CLI surface

```
resilio calendar auth                 # one-time browser authorization
resilio calendar sync [--weeks N] [--dry-run] [--force]
```
`--dry-run` prints the insert/patch/delete plan without any API write.
`--force` ignores local state and re-fetches/re-evaluates the full window.

## 8. Tests
- Mapping fixtures: one per workout_type → expected event dict.
- Idempotence: same plan twice → second run = all no-op.
- Diff: changed distance/time → patch; removed workout → delete; past event → untouched.
- Google client mocked for CLI tests. Optional live test behind
  `@pytest.mark.integration` (skipped by default).
- `pytest`, `mypy resilio`, `black`, `ruff` all green.

## 9. Security note
`credentials.json` sits in the repo root and is **not** in `.gitignore`. It is
currently **untracked** (verified — never committed, secret not in git
history), so no rotation needed, but it MUST be gitignored before any commit to
avoid leaking the client secret. Will add `credentials.json` +
`data/google_calendar/` patterns.
