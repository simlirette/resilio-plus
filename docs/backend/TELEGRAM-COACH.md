# Telegram Text Coach — Setup and Operations Runbook

> **Status:** V4, 2026-08-19. Implements `docs/GOAL-V4-TEXT-COACH.md`.
> Single athlete, self-hosted. Everything below assumes one box, one bot, one
> Google account.

The athlete talks to Resilio in Telegram. Once a week the coach texts next
week's plan with `[✅ Approve] [✏️ Change] [❌ Skip this week]`; approving writes
every session into a dedicated **Resilio Training** Google Calendar.

---

## 0. Quickstart — running it on your own laptop today

No public URL, no tunnel, no cloud. Telegram polling needs no inbound
connection, and both OAuth providers accept a loopback redirect, so the whole
thing runs locally. Total: about fifteen minutes, most of it in BotFather and
the Google console.

### 0.1 Get the two secrets you cannot generate

1. **Telegram bot token** — message [@BotFather](https://t.me/BotFather), `/newbot`,
   copy the token.
2. **Anthropic API key** — the coach is the product; without it nothing thinks.

### 0.2 Generate the ones you can

```bash
poetry run python scripts/bootstrap_v4.py --keys
```

Paste all four lines into `.env`. Encryption keys are write-once: rotating one
makes every token stored under it unreadable.

### 0.3 Fill in the rest of `.env`

```
DATABASE_URL=postgresql+psycopg2://resilio:resilio@127.0.0.1:5432/resilio_db
TELEGRAM_BOT_TOKEN=<from BotFather>
TELEGRAM_MODE=polling
PUBLIC_BASE_URL=http://127.0.0.1:8000
ANTHROPIC_API_KEY=<yours>
```

> **Use `127.0.0.1`, not `localhost`.** On Windows with WSL installed,
> `wslrelay.exe` can hold `[::1]:5432`, and `localhost` resolves to IPv6 first —
> so every connection dies with *"server closed the connection unexpectedly"*
> while `docker ps` cheerfully reports the database as healthy. This costs an
> hour if you do not know it.

### 0.4 Start everything

```powershell
.\scripts\start_coach.ps1
```

That brings up Postgres, migrates to head, runs the preflight, and starts the
backend. If the preflight reports something missing it stops before starting,
and tells you which variable.

### 0.5 Create yourself and link your phone

In a second terminal:

```bash
poetry run python scripts/bootstrap_v4.py --name "Your Name" --age 34 --sex M --weight-kg 75 --height-cm 180 --primary-sport running --hours-per-week 8 --timezone America/Montreal
```

It prints your athlete id (put it in `.env` as `ADMIN_ATHLETE_ID`) and a
one-time link code. Message your bot with **just that code**. The coach replies
"Telegram connected to Resilio."

The numbers you pass are what the coach plans from — age, sex, weight and
weekly hours drive VDOT, macros and load. Re-run the script with different
flags to correct them; it updates in place.

### 0.6 Connect your data

Send `/connect`. You get one tappable link per provider.

- **Hevy / Terra** — the link opens a one-field page; paste the key.
- **Strava / Google** — these are OAuth. Open those two links **in the browser
  on the laptop running the backend**, not on your phone: the redirect goes to
  `127.0.0.1`, which only that machine can reach. Same account either way.

For Strava, set the callback domain to `127.0.0.1` in your Strava API
application. For Google, add
`http://127.0.0.1:8000/integrations/link/callback/google` as an authorized
redirect URI. Google accepts loopback addresses for exactly this case.

### 0.7 Use it

- Talk to it. Anything: "legs are wrecked", "how did last week go?".
- `/plan` builds next week now instead of waiting for Sunday.
- Tap **Approve** and the sessions appear in a new "Resilio Training" calendar.
- Tap **Change**, reply "too much volume Wednesday", get a revised week.
- Sunday 18:00 local, it does all of that unprompted, forever.

### 0.8 When you want it always-on

The laptop has to be awake for the Sunday cycle to fire (a missed window is
picked up within 2h of the machine coming back — `misfire_grace_time=7200` —
but a laptop that was closed all Sunday misses the week). Moving to a small
VPS or Fly.io is §5 of `docs/backend/DEPLOYMENT.md`; switch
`TELEGRAM_MODE=webhook`, set a real `PUBLIC_BASE_URL`, and update both redirect
URIs.

---

## 1. What you have to set up, once

### 1.1 Telegram bot

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → name it → copy the token.
2. `TELEGRAM_BOT_TOKEN=<token>` in `.env`.
3. Optional but recommended: `/setcommands` on BotFather, paste:

   ```
   connect - Links to connect Strava, Hevy, Terra and Google Calendar
   status - What is connected and where you are in the journey
   plan - Build next week now
   help - What I understand
   ```

4. Pick a delivery mode:

   | Mode | When | Set |
   |---|---|---|
   | `polling` | local dev, or a box with no public URL | `TELEGRAM_MODE=polling` |
   | `webhook` | production behind HTTPS | `TELEGRAM_MODE=webhook` + `TELEGRAM_WEBHOOK_SECRET` |

   Register the webhook once the box is reachable:

   ```bash
   curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
     -d "url=$PUBLIC_BASE_URL/integrations/telegram/webhook" \
     -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
   ```

   Check it: `curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"`.

> **Webhook + workers:** `update_id` de-duplication is an in-memory LRU, so it is
> process-local. Run `WEB_CONCURRENCY=1` in webhook mode, or accept that a
> Telegram retry hitting a different worker can be processed twice.

### 1.2 Google Calendar

1. Google Cloud Console → new project (or reuse one).
2. **APIs & Services → Library** → enable **Google Calendar API**.
3. **OAuth consent screen** → External → fill the required fields → **Test users**:
   add your own Google account. Stay in *Testing*; publishing (and its review)
   is unnecessary under 100 users.
4. **Credentials → Create credentials → OAuth client ID → Web application**.
   Authorized redirect URI:

   ```
   $PUBLIC_BASE_URL/integrations/link/callback/google
   ```

5. Put the client id/secret in `.env` as `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.
6. Generate the at-rest key for the refresh token — `bootstrap_v4.py --keys`
   prints it alongside the others (§0.2), or on its own:

   ```bash
   poetry run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   → `GOOGLE_ENCRYPTION_KEY`.

**Scope:** `https://www.googleapis.com/auth/calendar.app.created` — Resilio can
create a secondary calendar and manage events **on calendars it created**, and
nothing else. Your personal calendar is not readable or writable by the app.
Deleting the "Resilio Training" calendar removes the integration's entire
footprint.

### 1.3 Strava redirect

Point Strava's callback at the text-coach leg so the athlete lands on a
"go back to Telegram" page instead of raw JSON:

```
STRAVA_REDIRECT_URI=$PUBLIC_BASE_URL/integrations/link/callback/strava
```

Set the same URL in the Strava API application settings.

### 1.4 Everything else

`PUBLIC_BASE_URL` must be the origin **the athlete's phone can reach** — it is
what connect links are built from. `ADMIN_ATHLETE_ID` gates `/admin/*` and the
optional bootstrap identity. Full variable list: `.env.example`.

No new services: the Telegram runtime and the weekly cron live inside the
existing backend container. `docker-compose.yml` already passes `.env` through
with `env_file`, so nothing in the compose files needs editing for V4.

---

## 2. First contact — linking a chat to an athlete

The bot never auto-creates an athlete. A chat becomes an identity in one of two
ways.

**Link code (normal path).** `bootstrap_v4.py` mints one on every run and
prints it — that is the intended path:

```bash
poetry run python scripts/bootstrap_v4.py
```

Send that code to the bot as a plain message. If you would rather do it by hand:

```sql
INSERT INTO messaging_link_codes (code, athlete_id, expires_at)
VALUES ('join-me-1234', '<athlete-uuid>', NOW() + INTERVAL '1 hour');
```

**Bootstrap (single-athlete convenience).** Set `TELEGRAM_BOOTSTRAP_CHAT_ID` to
your own private chat id and `ADMIN_ATHLETE_ID` to your athlete uuid; the first
message from that chat links itself. Find the chat id by messaging the bot and
reading `getUpdates`:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates" | jq '.result[].message.chat.id'
```

---

## 3. Connecting data sources over text

`/connect` mints one **single-use, two-hour** link per provider:

| Provider | What the link does |
|---|---|
| Strava | 302 into Strava OAuth, back to a done page |
| Google | 302 into Google consent, back to a done page |
| Hevy | one-field page to paste an API key (Hevy → Settings → Developer) |
| Terra | 302 to `TERRA_WIDGET_URL` if set, otherwise a page to paste a Terra user id |

On success the sync job is registered, the coordinator is told, and the athlete
gets a confirmation message. These endpoints are unauthenticated **by design**:
the opaque single-use token is the credential, the same trust model as the
Telegram webhook secret.

---

## 4. The weekly loop

Registered per athlete at `weekly_cycle_day` / `weekly_cycle_hour` (default
Sunday 18:00) in the athlete's own `timezone`, with `misfire_grace_time=7200`
so a redeploy over the window delays the week instead of skipping it.

```
sync (strava, hevy, terra)  →  snapshot (ACWR, strain, readiness)
      →  generate week  →  text it with three buttons  →  WAIT
                                                          │
   approve ─────────────────────────────────────────────► calendar push
   change  ─► "what should change?" ─► free text ─► revised week ─► buttons
   skip    ─► archived, nothing written
```

A provider that fails degrades the week and is named in the message
("Planned without fresh data from: hevy."); it never cancels it.

Change the schedule:

```sql
UPDATE athletes SET weekly_cycle_day = 6, weekly_cycle_hour = 18,
       timezone = 'America/Montreal' WHERE id = '<athlete-uuid>';
```

then restart the app (the cron is registered at startup).

**Run a cycle by hand** — either text `/plan`, or:

```bash
PYTHONPATH=backend poetry run python - <<'PY'
from app.db.database import SessionLocal
from app.jobs.weekly_jobs import run_weekly_cycle_now
with SessionLocal() as db:
    print(run_weekly_cycle_now("<athlete-uuid>", db).as_dict())
PY
```

**Daily reminder** (off by default): `DAILY_REMINDER_ENABLED=true` sends the
day's sessions at 06:30 local. It is registered alongside the weekly cycle, so
flipping the flag needs no redeploy of the schedule — only a restart if the job
was never registered.

---

## 5. Approvals

`pending_approvals` holds one row per decision: a 16-character token, the parked
`thread_id`, and a 7-day TTL. The token is the **only** thing in Telegram's
`callback_data` (capped at 64 bytes) — everything else is looked up server-side.
`resolve()` rejects expired, already-resolved, and cross-athlete tokens, and
verifies ownership *before* touching anything.

Tapping **Change** does not consume the token: the identity row is latched, the
next free-text message is routed to the revise path instead of a chat turn, and
the revised week arrives with a fresh token.

Inspect what is outstanding:

```sql
SELECT token, kind, created_at, expires_at, resolution
FROM pending_approvals WHERE athlete_id = '<uuid>' ORDER BY created_at DESC LIMIT 10;
```

---

## 6. Calendar behaviour

- One secondary calendar named **Resilio Training**, created on first push and
  recreated automatically if you delete it upstream.
- Each `WorkoutSlot.id` maps to at most one event (`calendar_events`, unique on
  `(athlete_id, slot_id)`), and every event carries
  `extendedProperties.private.resilio_slot_id` so the mapping survives a DB restore.
- Re-pushing an unchanged week performs **zero** API writes — event bodies are
  content-hashed.
- Sessions dropped from a pushed week are deleted; events in **other** weeks are
  never touched (pruning is scoped to the Monday–Sunday weeks the plan covers).
- Times are athlete-local with an explicit `timeZone`, so a 07:00 session stays
  07:00 across a DST change. Default hour 07:00, override per sport via
  `athletes.preferred_session_hour_json`, e.g. `{"running": 6, "lifting": 18}`.
- Reminder: popup 120 minutes before. Colour is stable per sport.

---

## 7. Smoke test

Against a running instance:

```bash
PYTHONPATH=backend poetry run python scripts/smoke_test_v4.py \
  --base-url https://coach.example.com \
  --athlete-id <athlete-uuid> \
  --external-id <telegram chat id>
```

It checks `/health` + `/ready`, link redemption, an inbound message producing a
reply, a forced weekly cycle sending a plan, and approval writing the calendar.
Add `--skip-calendar` to stop before any calendar write. It sends real messages
— run it against a bot you own.

---

## 8. Troubleshooting

| Symptom | Look at |
|---|---|
| `server closed the connection unexpectedly` from Postgres | On Windows, WSL may own `[::1]:5432`. Use `127.0.0.1` in `DATABASE_URL`, never `localhost`. |
| Bot silent in polling mode | `TELEGRAM_BOT_TOKEN` set? logs for `telegram_polling_*`? another process already long-polling (Telegram allows one)? |
| Bot silent in webhook mode | `getWebhookInfo` → `last_error_message`; secret mismatch answers 403 |
| "Send your link code here…" on every message | the chat is not linked — see §2 |
| Buttons do nothing | callback arrived but the token is dead — the coach replies why; check `pending_approvals.resolution` |
| "No calendar is connected yet" after approve | Google not connected, or `GOOGLE_CALENDAR_ENABLED=false` |
| Approve returns 403-ish silence | cross-athlete token; logged as `approval_cross_athlete_denied` |
| Duplicate events | check `calendar_events` — a missing row means the mapping was lost; the next push re-adopts by re-inserting |
| Weekly message never arrives | `GET /admin/jobs` (needs `ADMIN_ATHLETE_ID`) for `weekly_cycle` runs; check the athlete's `timezone` |
| Weekly message arrives without a plan | `weekly_cycle_no_plan` in logs — the plan graph returned nothing; usually a missing `ANTHROPIC_API_KEY` |

Useful queries:

```sql
-- what went out
SELECT created_at, kind, left(body, 80) FROM outbound_messages
WHERE athlete_id = '<uuid>' ORDER BY created_at DESC LIMIT 20;

-- job history
SELECT started_at, job_type, status, duration_ms, error_message
FROM job_runs WHERE job_type IN ('weekly_cycle', 'daily_reminder')
ORDER BY started_at DESC LIMIT 20;
```

---

## 9. Related reference

- `docs/GOAL-V4-TEXT-COACH.md` — the why, and the locked decisions
- `docs/backend/INTEGRATIONS.md` — Strava, Hevy, Terra, nutrition
- `docs/backend/JOBS.md` — the scheduler, `run_job`, `/admin/jobs`
- `docs/backend/DEPLOYMENT.md` — Docker, Fly.io / Railway / VPS
- `docs/backend/OBSERVABILITY.md` — logs, correlation ids, `/admin/metrics`
- `docs/backend/HUMAN-IN-THE-LOOP.md` — the interrupt/resume pattern behind approvals
