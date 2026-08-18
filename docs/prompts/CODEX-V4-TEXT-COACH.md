# Codex Execution Prompt — Resilio V4 "Text-Native Coach"

> Paste everything below the line into Codex. It is self-contained for a cold session.
> Goal statement it implements: `docs/GOAL-V4-TEXT-COACH.md`.

---

## MISSION

Turn Resilio Plus from an app-with-a-backend into **a coach that texts the athlete on Telegram and
writes their training plan into Google Calendar**. The AI coaching engine is already built and
frozen. Your job is to build the **transport and automation layer** around it, and to freeze the
web/mobile/desktop clients.

You are working in `C:\Users\simon\resilio-plus` — a Python 3.13 / FastAPI / LangGraph / SQLAlchemy 2
monorepo with a Next.js + Expo + Tauri frontend that is being paused.

---

## NON-NEGOTIABLE CONSTRAINTS

Read these before writing a single line.

1. **`BACKEND_FROZEN.md` governance holds.** You may **add** files, routes, DB tables, Alembic
   migrations, jobs, and services. You may **extend** LangGraph state with `NotRequired[...]` fields.
   You may **not** modify: any file in `backend/app/agents/`, any existing test, `pyproject.toml`
   mypy/ruff config, or the existing agent prompts in `backend/app/agents/prompts.py`.
2. **`resilio/` is read-only.** Legacy CLI. Never touch it.
3. **TDD is mandatory.** Red → green → refactor. Every new module gets tests written first.
4. **Invariants must pass before each work package is considered done.**

   **Never run these in the foreground with unbounded output.** The full suite is 2430 tests and
   mypy covers 131 files; streaming that through the tool wedges it. Always redirect to a file and
   read only the tail:

   ```bash
   # during a package — fast, scoped to what you touched
   PYTEST="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe"
   "$PYTEST" tests/backend/messaging -q --tb=line > /tmp/pt.txt 2>&1; tail -20 /tmp/pt.txt

   # end of a package — full gate, still bounded
   "$PYTEST" tests/ -q --tb=line -p no:cacheprovider > /tmp/pytest.txt 2>&1; tail -30 /tmp/pytest.txt
   python -m mypy backend/app/ --config-file pyproject.toml > /tmp/mypy.txt 2>&1; tail -20 /tmp/mypy.txt
   python -m ruff check backend/ > /tmp/ruff.txt 2>&1; tail -20 /tmp/ruff.txt
   poetry install > /tmp/poetry.txt 2>&1; tail -5 /tmp/poetry.txt
   ```

   Rules: run the **scoped** suite while iterating, the **full** suite once at the end of each
   package — not after every edit. Never `cat` a whole result file; always `tail`.

   **NEVER hold a live code-mode cell open waiting on a long command.** This is what killed the
   two previous sessions. The observed failure is: launch the full suite as a cell, then call
   `wait(cell_id=N, yield_time_ms=50000)` repeatedly for 15+ minutes, and the Node code-mode host
   dies mid-wait — `"code-mode host closed its stdout"`. When that host dies you lose the ability
   to execute *any* tool and the session is over. Codex logs nothing, because the failure is in the
   child process.

   Instead, **detach and poll the file**:

   ```bash
   # launch fully detached — the command returns immediately
   nohup "$PYTEST" tests/ -q --tb=line -p no:cacheprovider > /tmp/pytest.txt 2>&1 &
   echo "launched"

   # then, in SEPARATE short calls minutes apart, check the file — never a long wait:
   tail -5 /tmp/pytest.txt
   ```

   Each poll must be its own quick command that returns in under a second. Do useful work between
   polls (write the next test, read a file) rather than blocking. A run over ~20 minutes is a
   problem to investigate, not to wait out.

   **Measured baseline on `main` @ `18c34b8` (2026-08-18, full run 15m43s):**

   ```
   3 failed, 2616 passed, 16 skipped
   mypy: Success — no issues found in 159 source files
   ruff: 0 violations
   ```

   **These 3 failures are PRE-EXISTING and are NOT yours. Do not fix them, do not chase them, and
   do not treat them as a regression you caused.** Verified: the Phase D merge touched none of the
   files involved (0 commits against each path).

   | Test | Cause |
   |---|---|
   | `test_apple_health_endpoint.py::TestValidImport::test_minimal_valid_imports_one_day` | Date drift — fixtures dated 2026-04-14/15 vs date-relative import logic |
   | `test_apple_health_endpoint.py::TestValidImport::test_multi_day_imports_seven_days` | Same |
   | `test_config.py::TestGetRepoRoot::test_get_repo_root_raises_when_not_in_repo` | Environmental — `get_repo_root()` resolves a repo where the test expects none |

   Both areas are outside V4 scope, and fixing them would mean editing V1-FROZEN tests, which
   constraint 1 forbids. **Your gate is: exactly these 3 failures and no others, with the passing
   count at 2616 or higher.** A 4th failure means you broke something — stop and fix it.
5. **Atomic conventional commits**, one per logical task: `feat(telegram):`, `feat(gcal):`,
   `feat(jobs):`, `chore(freeze):`, `test(...)`, `docs(...)`.
6. **No new stack.** LangGraph + FastAPI + SQLAlchemy 2 (sync, psycopg2) + APScheduler + Pydantic v2.
   No Celery, no async ORM, no new web framework, no message broker.
7. **Secrets never land in the repo.** All credentials via env vars, documented in `.env.example`.
   Third-party refresh tokens are stored **Fernet-encrypted**, following the exact pattern in
   `backend/app/integrations/strava/oauth_service.py` (`encrypt_token` / `decrypt_token`).
8. **`freeze_time` is incompatible with Pydantic v2 datetime.date schema generation** in this repo.
   For time-dependent tests use a far-future fixed date window or a module-level `patch`, never
   `freeze_time` around Pydantic model construction.
9. **Migration numbering: verify, never assume.** Before writing any Alembic revision, run
   `alembic heads` and `ls alembic/versions/` and chain `down_revision` from the **actual** head.
   Any migration number written in this brief is indicative only and may be stale — at time of
   writing `0011` and `0012` are already taken by the Phase D branch, so T1 starts at `0013`.
   Every later package must inspect the tree and use the successor of the then-current head. A
   duplicate revision id forks the `down_revision` graph and breaks every migration downstream.
10. **This brief was written from reading the repo, not from running it.** Where a stated path,
    signature, table name, or number does not match the code, **the code wins** — correct it, and
    say so in your report. Do not bend the code to match the brief.

---

## WHAT ALREADY EXISTS — USE IT, DO NOT REBUILD IT

### The coaching engine (frozen, works)

| Thing | Path |
|---|---|
| Head Coach + 7 specialists | `backend/app/agents/` |
| Plan generation graph, 11 nodes, HITL interrupt/approve/revise | `backend/app/graphs/coaching_graph.py` |
| `CoachingService` singleton | `backend/app/services/coaching_service.py` |
| LangGraph SqliteSaver checkpointer | `LANGGRAPH_CHECKPOINT_DB`, default `data/checkpoints.sqlite` |
| Strava OAuth V2, Fernet tokens, incremental sync | `backend/app/integrations/strava/` |
| Hevy connector (API key) + CSV import | `backend/app/connectors/hevy.py`, `backend/app/integrations/hevy/` |
| Terra connector (HRV / sleep / RHR) | `backend/app/connectors/terra.py` |
| APScheduler: `run_job()` timeout wrapper, per-athlete registry, global cron | `backend/app/jobs/` |
| Observability: JSON logs, `correlation_id`, PII filter, `track_agent_call`, metrics | `backend/app/observability/` |
| Plan schema — `TrainingPlan`, `WorkoutSlot(id, date, sport, workout_type, duration_min, fatigue_score, notes)` | `backend/app/schemas/plan.py` |

### The conversational layer — merged, with coordinator invocation still stubbed

The Phase D graph modules and routes are on `main`. However, the live
`CoordinatorService._invoke_graph()` is still the D1 stub that returns `None`, and chat in the
`signup` / `scope_selection` phases resolves no graph. Treat graph invocation as unfinished
integration work despite the graph modules being present:

| Thing | Path | What it does |
|---|---|---|
| `CoordinatorService` | `backend/app/services/coordinator_service.py` | **Single routing entry point.** `dispatch(athlete_id, event_type, payload, db) -> DispatchResult`. `event_type ∈ {"chat","system_silent","system_proactive","system_injury"}`. It selects a graph by `journey_phase` + overlays, manages thread lifecycle, and validates phase transitions, but `_invoke_graph()` currently returns `None`. `signup` / `scope_selection` chat selects no graph. Existing graph runners expose `final_response` (`chat_turn`) or `question` (onboarding/follow-up/recovery), not one universal response key. |
| `chat_turn` graph | `backend/app/graphs/chat_turn.py` | Free-form message → intent → Head Coach direct / specialist chain (max 3) / clinical escalation / clarification. |
| `classify_intent` | `backend/app/services/classify_intent_service.py` | Haiku 4.5 gateway, <500ms SLA, fr/en/mixed detection. |
| `onboarding` graph | `backend/app/graphs/onboarding.py` | Blocs 1–6 with HITL interrupts, handoff, mid-onboarding injury handling. **This is the "first communication" flow — profile, goals, connectors, plan overview.** |
| `followup_transition`, `recovery_takeover` graphs | `backend/app/graphs/` | Phase transitions, injury overlay. |
| `MonitoringService` | `backend/app/services/monitoring_service.py` | `run_daily_checks()`, HRV trend, energy patterns, `check_proactive_message_allowed()` (pro-activity cap). |
| Routes | `backend/app/routes/chat.py`, `coordinator.py`, `followup.py`, `onboarding_d7.py` | HTTP surface over the above. |
| Frontend chat + onboarding UI (D13/D14) | `apps/web/` | **Will be frozen — do not extend.** |

`journey_phase` state machine (enforced in `coordinator_service.VALID_TRANSITIONS`):
`signup → scope_selection → onboarding → baseline_pending_confirmation → baseline_active →
followup_transition → steady_state`

---

## ARCHITECTURE YOU ARE BUILDING

```
   Telegram Bot API
        │  (webhook in prod, long-poll in dev)
        ▼
   TelegramChannel  ──────┐
        │                 │  implements MessagingChannel (send / send_with_buttons / max_message_length / format)
        ▼                 │
   MessagingGateway  ◄────┘        resolves telegram chat_id → athlete_id via messaging_identities
        │
        ├─ inbound  ──►  CoordinatorService.dispatch(...)   ← EXISTS as router; no HTTP, no JWT
        │                       │
        │                       └─► graph invocation wiring is still required
        │
        └─ outbound ◄──  NotificationService.send(athlete_id, text, buttons=[...])
                                ▲
                                │
   weekly_coach_cycle job ──────┘   (APScheduler cron, per athlete, athlete-local time)
        │
        │  sync → compute → generate → text plan + [Approve][Change][Reject] → WAIT
        │
        └─ on Approve ─► CalendarSyncService.push_week(plan)
                                │
                                ▼
                        GoogleCalendarClient  ──►  "Resilio Training" secondary calendar
```

**Critical design rule:** the Telegram layer calls `CoordinatorService` and the services
**directly, in-process**. It does **not** make HTTP calls to its own API and does **not** mint JWTs.
Identity is established once, by the verified `chat_id → athlete_id` mapping, and passed down.

---

## WORK PACKAGES

Execute in order. Each ends with a green invariant run and a commit.

---

### T0 — Land Phase D on `main` — ✅ **ALREADY COMPLETE (2026-08-18). SKIP THIS. START AT T1.**

Do not redo any of this. It is on `main` already:

| Commit | What |
|---|---|
| `9b04fc7` | `feat(mobile): WIP snapshot before V4 freeze` — the uncommitted mobile work was saved first |
| `3ad665d` | `feat(coordinator): merge Phase D conversational layer` — the 17-commit branch merged |
| `dd22081` | `fix(coordinator): sort merged router imports` — ruff |
| `1ad1678` | `fix(mobile): type sport serialization` — mypy |
| `b169365` | `fix(observability): align Sentry callback typing` — mypy |

Also done: the `.worktrees/phase-d-session-1` worktree is removed. The branches
`feat/phase-d-d1-coordinator` and `docs/v4-text-coach` are fully merged into `main` and kept only
as backup refs — you may ignore or delete them.

`main` now contains `coordinator_service.py`, `chat_turn.py`, `onboarding.py`,
`classify_intent_service.py`, `monitoring_service.py`, and the Phase D routes registered in
`backend/app/main.py`.

**Before starting T1**, run the bounded invariant gate once to confirm your baseline, and record the
numbers. If anything is red, fix that first — you inherit it, so do not build on top of it.

---

### T1 — Messaging core (channel-agnostic)

Build the abstraction **before** the Telegram specifics, so SMS/WhatsApp can slot in later.

**New: `backend/app/messaging/`**

- `base.py` — `MessagingChannel` protocol:
  ```python
  class MessagingChannel(Protocol):
      name: str
      def send(self, external_id: str, text: str) -> str: ...           # returns provider msg id
      def send_with_buttons(self, external_id: str, text: str,
                            buttons: list[Button]) -> str: ...
      def max_message_length(self) -> int: ...
      def format(self, text: str) -> str: ...                            # markdown → channel dialect
  ```
  Plus `Button(label: str, token: str)` — `token` is an opaque short id, never raw data.
- `gateway.py` — `MessagingGateway`:
  - `resolve_athlete(channel: str, external_id: str) -> str | None`
  - `handle_inbound(channel, external_id, text) -> None` → `CoordinatorService.dispatch(event_type="chat", payload={"message": text})`, then sends a recognized user-facing result (`final_response`, otherwise `question`) when present. It does not fabricate a reply while the coordinator returns `output=None`.
  - `link_identity(channel, external_id, link_code) -> str` — one-time code flow.
  - Unknown `external_id` → replies with an instruction to send their link code. **Never** auto-creates an athlete.
- `notification_service.py` — `NotificationService.send(athlete_id, text, buttons=None)`; resolves athlete → channel + external_id, chunks to `max_message_length()`, logs to `outbound_messages`.
- `chunking.py` — split on paragraph boundaries first, then sentence, then hard-cut. Never split inside a code block or a bullet line.

**New DB tables (Alembic — see migration-numbering rule below):**

```
messaging_identities(id, athlete_id FK, channel, external_id, verified_at, created_at)
    UNIQUE(channel, external_id);  INDEX(athlete_id)
messaging_link_codes(code PK, athlete_id FK, expires_at, consumed_at)
outbound_messages(id, athlete_id FK, channel, external_id, provider_message_id,
                  body, kind, created_at)
```

**Tests:** `tests/backend/messaging/test_gateway.py`, `test_chunking.py`,
`test_notification_service.py`. Cover: unknown external_id, expired link code, code reuse,
chunking at exactly the boundary, chunking a 12 000-char plan, athlete with no identity.

---

### T2 — Telegram channel

**New: `backend/app/integrations/telegram/`**

- `client.py` — thin `httpx` wrapper over Bot API: `sendMessage`, `answerCallbackQuery`,
  `setWebhook`, `getUpdates`. Retries on 429 honouring `retry_after`. Timeout 15s.
- `channel.py` — `TelegramChannel(MessagingChannel)`. **Use `parse_mode="HTML"`, not MarkdownV2** —
  MarkdownV2 escaping is a bug farm and LLM output is full of `.`, `-`, `!`, `(`. Implement
  `format()` as markdown-subset → HTML (`**b**`, `*i*`, `` `code` ``, bullet lines) with
  `html.escape()` on everything else. `max_message_length() == 4096`.
- `webhook.py` — `POST /integrations/telegram/webhook`:
  - Validates the `X-Telegram-Bot-Api-Secret-Token` header against `TELEGRAM_WEBHOOK_SECRET`. Reject
    with 403 otherwise. **This endpoint is unauthenticated by design** — the secret token *is* the auth.
  - Handles `message` (→ `gateway.handle_inbound`) and `callback_query` (→ T3).
  - **Returns 200 immediately and processes in a `BackgroundTask`.** Telegram retries on slow
    responses and LangGraph turns take seconds.
  - Deduplicates on `update_id` (in-memory LRU of 1000 is sufficient at this scale).
- `polling.py` — `run_polling_loop()` for local dev: `getUpdates` long-poll in a daemon thread,
  started from the FastAPI lifespan when `TELEGRAM_MODE=polling`.
- Send a "typing…" chat action before long operations — a 20-second silent gap reads as broken.

**Env vars (add to `.env.example`):**
```
TELEGRAM_BOT_TOKEN=
TELEGRAM_MODE=polling            # polling | webhook
TELEGRAM_WEBHOOK_SECRET=
TELEGRAM_BOOTSTRAP_CHAT_ID=      # optional: auto-link this chat_id to ADMIN_ATHLETE_ID on first message
```

**Tests:** mock the Bot API with `respx` scoped to `https://api.telegram.org`. **Do not** patch
`httpx.Client` globally — `TestClient` subclasses it and you will intercept your own ASGI dispatch
(this exact trap is documented in `CLAUDE.md` → Testing Gotchas). Cover: HTML escaping of a message
containing `<`, `&`, and an em-dash; 4096-char chunking; 429 retry; bad secret token → 403; duplicate
`update_id` ignored.

---

### T3 — Approval over text (human-in-the-loop)

The existing graphs interrupt and wait for approve/revise. Wire that to inline keyboard buttons.

**New: `backend/app/messaging/approvals.py`**

- Table (a new successor migration when T3 begins; do not amend T1's committed revision): `pending_approvals(token PK, athlete_id FK, thread_id, kind, payload_json, created_at, expires_at, resolved_at, resolution)`.
- `token` is a 16-char `secrets.token_urlsafe` slice. **Telegram `callback_data` is capped at 64
  bytes** — never put a thread_id or JSON in it; put the token and look the rest up.
- `create_approval(athlete_id, thread_id, kind) -> token`
- `resolve(token, resolution: Literal["approve","revise","reject"], athlete_id) -> PendingApproval` —
  rejects if expired (default TTL 7 days), already resolved, or belongs to another athlete.
- On `approve` → resume the graph via the existing approve path in
  `backend/app/routes/workflow.py` / `CoachingService`; then trigger T5 calendar push.
- On `revise` → prompt "What should change?"; the athlete's next free-text message is routed to the
  revise path with the stored `thread_id`, not to `chat_turn`. Track this with a short-lived
  `awaiting_revision_for_token` field on the identity row.
- On `reject` → archive the proposed plan, no calendar write, coach acknowledges.

**Tests:** expired token, replayed token, cross-athlete token (must 403), approve → calendar push
called once, revise → free-text captured and routed to revise not chat.

---

### T4 — Onboarding over text

The `onboarding` graph already produces the questions. You are building the rendering and the
connector hand-off.

- `MessagingGateway` renders each onboarding interrupt as a message; where the graph offers discrete
  choices, render them as inline buttons; otherwise accept free text.
- **Connector authorization over text.** The coach must send tappable links:
  - New: `GET /integrations/link/{deep_link_token}` — resolves a short-lived token to
    `(athlete_id, provider)` and 302-redirects into the existing
    `/integrations/strava/connect` (and equivalents). This exists so the athlete never has to be
    logged into a web session.
  - After the provider's OAuth callback succeeds, fire
    `CoordinatorService.dispatch(athlete_id, "system_silent", {"connector_connected": provider})`
    so the onboarding graph resumes and the coach texts "Strava connected — 47 activities imported."
  - The OAuth callback should render a dead-simple "Done — go back to Telegram" HTML page.
  - Register the per-athlete sync job on connect (`jobs/registry.py::register_athlete_jobs` already
    does this — verify it is called from the new path).
- **Terra** is the Garmin/Whoop/Oura/Apple-Watch wellness path. Verify the Terra auth widget URL flow
  and wire it the same way. If Terra requires a hosted widget redirect, use the same deep-link
  indirection.
- The macro plan overview at the end of onboarding goes out as a **formatted text summary** —
  phases, weekly hours per sport, key sessions, ACWR trajectory — with an approve/change gate (T3).

**Tests:** full onboarding transcript as an integration test — feed scripted inbound messages,
assert `journey_phase` walks `signup → … → baseline_pending_confirmation`, assert the connector
links are issued, assert the deep-link token is single-use and expires.

---

### T5 — Google Calendar

**New: `backend/app/integrations/google_calendar/`**

- `oauth_service.py` — mirror `integrations/strava/oauth_service.py` exactly:
  `connect()` / `callback()` / `get_valid_credential()`, refresh token **Fernet-encrypted** at rest,
  CSRF `state`, auto-refresh on 401.
  - Scope: **`https://www.googleapis.com/auth/calendar` is too broad — request
    `https://www.googleapis.com/auth/calendar.app.created`** so Resilio can only touch the calendar
    it creates. Fall back to `calendar.events` only if `calendar.app.created` proves insufficient for
    creating the secondary calendar; document whichever you land on.
  - Google OAuth in **test-user mode** (single athlete, no verification review). Document the
    Cloud Console setup steps in `docs/backend/INTEGRATIONS.md`.
- `client.py` — `httpx` wrapper: `calendars.insert`, `events.insert`, `events.patch`,
  `events.delete`, `events.list`. Honour 403 `rateLimitExceeded` with exponential backoff.
- `calendar_sync_service.py`:
  - `ensure_calendar(athlete_id) -> calendar_id` — creates a secondary calendar named
    **"Resilio Training"** on first use, stores the id. Never writes to `primary`. This makes the
    whole integration reversible by deleting one calendar.
  - `push_week(athlete_id, plan: TrainingPlan) -> SyncReport` — **idempotent**:
    - each `WorkoutSlot.id` maps to at most one Google event via `calendar_events`
    - slot present + no event → insert
    - slot present + event exists → patch (only if content hash changed)
    - event exists + slot gone → delete
    - returns counts of created / updated / deleted / unchanged
  - Also stamp `extendedProperties.private = {"resilio_slot_id": <slot.id>}` on every event so the
    mapping survives a DB restore.
- **Event rendering:**
  - Summary: `{sport emoji} {workout_type} — {key metric}` e.g. `🏃 Tempo — 8 km @ 4:35/km`
  - Start: `WorkoutSlot.date` + athlete's preferred hour for that sport (new column, default 07:00
    local); end = start + `duration_min`.
  - Description: full prescription (warm-up / main set / cool-down), the `FatigueScore` summary, and
    the Head Coach's one-line rationale. Plain text — Google Calendar descriptions render poorly with
    heavy HTML.
  - Reminder: popup 120 min before.
  - `colorId` per sport, consistent across weeks.
- Timezone: new `timezone` column on `athletes` (IANA string, default `America/Montreal`). All event
  times are athlete-local; send `timeZone` explicitly on every event — never rely on server tz.

**New DB (next migration after the actual Alembic head when T5 begins):**
```
google_calendar_credentials(athlete_id PK/FK, refresh_token_enc, calendar_id, scope,
                            connected_at, last_sync_at)
calendar_events(id, athlete_id FK, slot_id, gcal_event_id, content_hash, created_at, updated_at)
    UNIQUE(athlete_id, slot_id)
athletes.timezone (new column), athletes.preferred_session_hour_json (new column)
```

**Tests:** `respx`-mocked Google API. Cover: first push creates N events; identical re-push is a
no-op (0 API writes); changed duration → patch; removed slot → delete; DST boundary week
(America/Montreal, first Sunday of November — a 07:00 session must stay 07:00 local); token refresh
on 401; calendar deleted upstream → `ensure_calendar` recreates it.

---

### T6 — The weekly automation

**New: `backend/app/jobs/weekly_jobs.py`**

`run_weekly_coach_cycle(athlete_id: str) -> dict` — wrapped by the existing `run_job()` (timeout +
DB logging + correlation id). Steps, each individually failure-tolerant and logged:

1. **Sync** — force-run `sync_strava_for_athlete`, `sync_hevy_for_athlete`, `sync_terra_for_athlete`
   synchronously (not "wait for the interval job"). A provider failure degrades the week, it does not
   abort it — note it in the message ("couldn't reach Hevy, planned from Strava only").
2. **Compute** — `run_daily_snapshot` for the athlete: ACWR, Muscle Strain Index, energy/allostatic
   state, readiness.
3. **Generate** — `CoordinatorService.dispatch(athlete_id, "system_proactive", {"trigger":
   "weekly_cycle"})`. The plan_generation graph builds the week and interrupts awaiting approval.
4. **Render + send** — format the week (day-by-day, with the *reasoning*, not just the sessions) and
   send via `NotificationService` with `[✅ Approve] [✏️ Change] [❌ Skip this week]` (T3 tokens).
5. **Persist** the `thread_id` on the approval token. The job ends here — approval is asynchronous.
6. **On approval** (T3 callback path) — `CalendarSyncService.push_week()`, then confirm by text with
   the created/updated/deleted counts.

**Scheduling:**
- `jobs/registry.py`: add `register_weekly_cycle(athlete_id, scheduler, db)` — a `cron` trigger at
  the athlete's `weekly_cycle_day` / `weekly_cycle_hour` (new columns, defaults Sunday 18:00) in the
  athlete's `timezone`. APScheduler's `CronTrigger` accepts `timezone=` — use it, do not do manual
  UTC arithmetic.
- Call it from `restore_all_jobs()` at startup and on onboarding completion.
- `misfire_grace_time=7200` — a redeploy must not silently skip a week.
- Respect `MonitoringService.check_proactive_message_allowed()` — the pro-activity cap exists for a
  reason. The weekly plan is the one message that should be allowed to bypass a soft cap; make that
  explicit rather than accidental.
- **Reminder job (small, high value):** a daily 06:30-local job that texts the day's session. Add it
  behind `DAILY_REMINDER_ENABLED=false` so it can be turned on without a redeploy.

**Tests:** `tests/backend/jobs/test_weekly_jobs.py` + an E2E in `tests/e2e/` that fakes the clock
forward, runs the cycle against seeded Strava/Hevy fixtures, asserts a message went out with three
buttons, resolves the approve token, and asserts the calendar service was called with the right slots.

---

### T7 — Freeze the clients

- `apps/web/FROZEN.md`, `apps/mobile/FROZEN.md`, `apps/desktop/FROZEN.md` — each stating: frozen on
  2026-08-17 for V4, why, what still works, and what to do to unfreeze.
- Root `package.json`: remove `apps/web`, `apps/mobile`, `apps/desktop` from default `build` / `dev`
  / `typecheck` scripts. Keep them reachable as `build:web` etc. **Do not remove them from
  `pnpm-workspace.yaml`** — that would break `pnpm install`.
- Remove frontend jobs from CI if any exist.
- Head `docs/MOBILE_TESTFLIGHT_MVP.md` with a `> PAUSED 2026-08-17 — see docs/GOAL-V4-TEXT-COACH.md`
  banner. Do not delete the doc.
- `CLAUDE.md`: add a `V4` row to the Phase Status table, add a "Frontend frozen" note to the
  Workspace Structure section, and add the new reference docs to Key References.

---

### T8 — Deploy + live smoke test

- Extend `Dockerfile.backend` / `docker-compose.prod.yml` with the new env vars. No new services.
- `docs/backend/TELEGRAM-COACH.md` — setup runbook: BotFather steps, webhook registration curl,
  Google Cloud Console OAuth client steps, the link-code bootstrap, and how to re-run a weekly cycle
  by hand.
- `scripts/smoke_test_v4.py` — end-to-end against a running instance: link identity → send a chat
  message → assert a reply → force a weekly cycle → assert the message + buttons → approve → assert
  events land in the calendar.
- Update `.env.example` with every new variable and a one-line comment each.

---

## HOW TO WORK

- **One work package at a time.** Do not start T2 before T1's invariants are green and committed.
- **Stop and hand back at the end of every package.** Do not roll straight into the next one. Long
  sessions accumulate code-mode cells and host memory — the session that died was on cell 139 with
  55M cumulative input tokens. Finishing a package, committing, and letting the operator start a
  fresh session resets that. Say plainly which package is done and which is next.
- **Tests first, always.** If you cannot write the test, you do not understand the requirement yet —
  stop and say so rather than guessing.
- **Report honestly.** If a step is blocked (e.g. Terra's Garmin flow needs a live account, or
  `calendar.app.created` turns out not to permit calendar creation), finish everything else in the
  package, then state plainly what is blocked and why. Do not silently narrow scope.
- **When something in this brief conflicts with the code**, the code wins — flag the discrepancy in
  your report rather than bending the code to match the brief.
- After each package, print: files added, files modified, test count delta, and the four invariant
  results.

---

## ACCEPTANCE — V4 IS DONE WHEN

On a clean box, with nothing but a phone:

1. First message to the bot → onboarded fully over text: profile, goals, Strava + Hevy + Terra
   connected via tapped links, macro plan confirmed.
2. Seven days later, unprompted, a message arrives with next week's plan, the reasoning, and
   approve / change / reject buttons.
3. Replying `"too much volume Wednesday"` in plain language produces a revised week, re-texted.
4. Tapping **Approve** puts every session into a **"Resilio Training"** Google Calendar within
   seconds — correct dates, durations, full prescription in the description.
5. Re-running the same week **updates** those events instead of duplicating them; removed sessions
   are deleted.
6. The loop repeats the next week with zero manual intervention.
7. `pytest tests/` ≥ 2430 passing · `mypy --strict` 0 errors · `ruff check` 0 violations.

---

## OUT OF SCOPE — DO NOT BUILD

- Apple Messages / iMessage, SMS, WhatsApp adapters. (The `MessagingChannel` interface leaves room. That is all.)
- Direct Garmin Connect integration. Strava covers activities; Terra covers Garmin wellness.
- Reading the athlete's calendar to schedule around meetings. That is V4.1.
- Multi-user signup, billing, Google OAuth verification review.
- Any new web, mobile, or desktop UI.
- Voice notes, image parsing, media messages.
- Any modification to `backend/app/agents/` or to existing tests.
