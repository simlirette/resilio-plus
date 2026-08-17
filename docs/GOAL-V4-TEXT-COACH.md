# Resilio V4 — Text-Native Coach

> **Status:** Goal statement, 2026-08-17.
> **Supersedes as active priority:** frontend work (web / mobile / desktop) — see §5 Freeze.
> **Does NOT supersede:** `resilio-master-v3.md` (backend architecture remains the reference).

---

## 1. The goal in one paragraph

**Resilio stops being an app you open and becomes a coach who texts you.**

The athlete talks to the Head Coach in **Telegram**, in natural language, exactly as they would text a
human coach. The coach onboards them, connects their data sources, builds their plan, and then —
**every week, unprompted** — pulls the last 7 days from Strava / Hevy / Terra, regenerates the coming
week, texts it over, waits for a yes, and writes the approved sessions straight into **Google
Calendar**. No app. No dashboard. No login. The training plan lives where the athlete already lives:
their messages and their calendar.

---

## 2. Why this is the right move

| | |
|---|---|
| **The backend is finished, the frontend is not.** | Backend V1-FROZEN: 2430 tests, 0 mypy errors, dockerized. Phase D (conversational layer) is 15/15 sessions done on an unmerged branch. The web app is partial and the mobile app is mid-TestFlight. The value is already built — it just has no usable surface. |
| **Chat is the native interface for this product.** | Resilio's whole differentiator is *judgment under conflicting signals* ("you squatted heavy yesterday, Thursday's intervals move to Friday"). That is a conversation, not a dashboard. Every UI we build is a lossy rendering of a conversation the agents are already having. |
| **The calendar is where a plan actually gets obeyed.** | The product vision doc already records the behaviour: *"Currently I use google calendar for the training planning."* Athletes don't check apps, they check calendars. Writing to Google Calendar is the shortest path from "plan generated" to "session executed". |
| **Zero client to build, ship, or review.** | Telegram Bot API is free, official, cross-platform, has inline buttons for approve/revise, and needs no App Store review, no TestFlight, no Tauri signing, no design system. Ship time drops from months to weeks. |

---

## 3. Scope — what V4 delivers

### 3.1 First contact (one time)

The coach runs the existing `onboarding` LangGraph (blocs 1–6, human-in-the-loop interrupts) **over
text**:

1. **Athlete profile** — age, sex, weight, training history, injury history, constraints.
2. **Goals** — target event(s), dates, priorities across sports, non-negotiable rest days.
3. **Data connection** — coach sends tap-to-authorize links for **Strava** (activities: run / bike /
   swim, incl. everything a Garmin watch pushes), **Hevy** (lifting sets/reps/load), **Terra**
   (wellness: HRV, sleep, RHR — this is the Garmin/Whoop/Oura/Apple Watch path).
4. **Plan overview** — coach texts the shape of the macro plan (phases, weekly hour budget per sport,
   key sessions, ACWR trajectory) and asks for confirmation before anything is generated in detail.

### 3.2 The weekly loop (forever after)

Runs automatically, once a week, at the athlete's local time:

```
  ┌─ 1. SYNC ──────── force-pull Strava + Hevy + Terra (last 7d)
  │
  ├─ 2. COMPUTE ───── ACWR, Muscle Strain Index, Energy/allostatic state, readiness
  │
  ├─ 3. GENERATE ──── Head Coach + specialists build next week (existing plan_generation graph)
  │
  ├─ 4. TEXT ──────── coach messages the week + the *reasoning* + [Approve] [Change] [Reject]
  │
  ├─ 5. WAIT ──────── LangGraph interrupt. Athlete can reply in plain language
  │                   ("too much volume", "I'm travelling Thursday") → revise → re-text
  │
  └─ 6. CALENDAR ──── on approval only: write each session into a dedicated
                      "Resilio Training" Google Calendar (idempotent, updatable, deletable)
```

Between weekly cycles the athlete can text the coach **anything, anytime** — the `chat_turn` graph
(intent classification → Head Coach direct / specialist chain / clinical escalation) already handles
this and is unchanged.

### 3.3 Decisions locked (2026-08-17)

| Decision | Choice | Reason |
|---|---|---|
| **Channel** | **Telegram only** | Official Bot API, free, inline keyboards, cross-platform, zero infra. Apple Messages has no send API — reaching it needs a paid gateway or a 24/7 Mac, both rejected for V4. SMS/WhatsApp adapters may follow behind the same `MessagingChannel` interface. |
| **Garmin** | **Strava + Terra, no direct integration** | Garmin auto-pushes activities to Strava (already integrated, OAuth V2, incremental sync). Terra (already integrated) covers Garmin *wellness* — HRV, sleep, RHR. Garmin's own API is gated behind a B2B developer program; the unofficial lib requires storing the athlete's raw password. Neither is worth it at this scope. |
| **Deployment scope** | **Single athlete, self-hosted** | One Fly.io/VPS box, one Telegram bot, Google OAuth in test-user mode (no verification review needed under 100 users). The backend is already multi-tenant (`athlete_id`-keyed everywhere), so productizing later is configuration, not a rewrite. |
| **Calendar write** | **Approval-gated** | The coach texts the plan and only writes to Calendar after an explicit yes. Reuses the existing LangGraph `interrupt` / approve / revise pattern verbatim. No surprise calendar writes. |
| **Calendar direction** | **Write-only in V4** | Push sessions out. Reading the athlete's free/busy to schedule *around* meetings is V4.1 — high value, but it is a scheduling-constraint change to the Head Coach, not a transport change. |

---

## 4. What already exists (do not rebuild)

| Capability | Where | Status |
|---|---|---|
| Head Coach + 7 specialist agents | `backend/app/agents/` | ✅ V1-FROZEN — **read-only** |
| Plan generation graph (11 nodes, HITL approve/revise) | `backend/app/graphs/coaching_graph.py` | ✅ V1-FROZEN |
| `CoordinatorService.dispatch()` — single entry point, routes by `journey_phase` | `backend/app/services/coordinator_service.py` | ✅ Phase D branch |
| `chat_turn` graph + `classify_intent` (Haiku 4.5, <500ms) | `backend/app/graphs/chat_turn.py` | ✅ Phase D branch |
| `onboarding` graph — blocs 1–6, HITL interrupts, mid-onboarding injury handling | `backend/app/graphs/onboarding.py` | ✅ Phase D branch |
| `MonitoringService` — proactive event detection + pro-activity cap | `backend/app/services/monitoring_service.py` | ✅ Phase D branch |
| Strava OAuth V2 (Fernet-encrypted tokens, incremental sync) | `backend/app/integrations/strava/` | ✅ V1-FROZEN |
| Hevy + Terra connectors | `backend/app/connectors/` | ✅ V1-FROZEN |
| APScheduler jobs (per-athlete sync, global cron, timeout wrapper, DB logging) | `backend/app/jobs/` | ✅ V1-FROZEN |
| Observability (JSON logs, correlation IDs, PII filter, metrics, Sentry) | `backend/app/observability/` | ✅ V1-FROZEN |

**The genuinely new surface area for V4 is small:** a Telegram transport, a Google Calendar
connector, an approval-token table, and one weekly cron job.

---

## 5. Freeze — what stops

| Target | Action |
|---|---|
| `apps/web` (Next.js) | **Frozen.** Kept buildable, removed from the default build/CI path. `FROZEN.md` added. Not deleted — the Phase D chat UI (D13/D14) is the reference implementation for a future web surface. |
| `apps/mobile` (Expo / TestFlight) | **Frozen.** In-flight work committed first so nothing is lost. `docs/MOBILE_TESTFLIGHT_MVP.md` marked paused, not abandoned. |
| `apps/desktop` (Tauri) | **Frozen.** Scaffold only, no loss. |
| `packages/ui-web`, `packages/ui-mobile`, `packages/design-tokens` | **Frozen** (they exist only to serve the frozen apps). `packages/api-client` and `packages/shared-logic` stay maintained — a future surface will need them. |
| Backend | **Unfrozen for additive work only.** V1-FROZEN governance holds: new files, new routes, new tables, state extensions are allowed. Existing agents, existing tests, and mypy/ruff config are not to be modified. |

---

## 6. Definition of done

V4 ships when, on a clean box, with nothing but a phone:

1. The athlete messages the bot on Telegram for the first time and is **onboarded end-to-end over
   text** — profile, goals, Strava + Hevy + Terra connected via tapped links, macro plan confirmed.
2. Seven days later, **without the athlete doing anything**, a message arrives with next week's plan,
   the reasoning behind it, and approve/change/reject buttons.
3. Replying "too much volume Wednesday" in plain language produces a **revised** week, re-texted.
4. Tapping **Approve** puts every session into a **"Resilio Training"** Google Calendar within
   seconds — correct dates, durations, and the full prescription in the event description.
5. Re-running the week **updates** those events rather than duplicating them; removed sessions are
   deleted.
6. The whole loop repeats the following week with zero manual intervention.
7. `pytest tests/` ≥ 2430 passing, `mypy --strict` 0 errors, `ruff check` 0 violations — unchanged.

---

## 7. Explicitly out of scope for V4

- Apple Messages / iMessage, SMS, WhatsApp (the `MessagingChannel` interface leaves room; no adapter is built).
- Direct Garmin Connect integration.
- Reading the athlete's calendar to schedule around existing commitments (→ V4.1).
- Multi-user signup, billing, Google OAuth app verification.
- Any new web, mobile, or desktop UI.
- Voice notes, image parsing, or media in the chat channel.
