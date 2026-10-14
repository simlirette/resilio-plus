# Claude Code Hybrid Coach — Umbrella Design

Date: 2026-10-14 · Status: approved (design) · Owner: Simon

## Goal

Use resilio-plus as a personal coach run entirely inside Claude Code sessions,
the way du-phan/resilio-app works (coach persona in `CLAUDE.md` + `resilio` CLI
+ skills), with **weight lifting as a first-class planned sport**: exercises,
sets × reps, RIR/load targets, progression and deloads — not just load.
Prescribed lifting sessions land in Hevy automatically so nothing is typed by hand.

## Locked decisions

| Topic | Decision |
|---|---|
| Lifting depth | Full prescription (exercises, sets × reps, RIR or load, rest, progression, deloads). Executed and logged in Hevy. |
| Lifting history | Hevy API (Hevy Pro key). |
| Run data | Strava (unchanged). No Intervals.icu migration. |
| Coach location | resilio-plus repo root. Root `CLAUDE.md` = coach persona; backend dev guide moves to `backend/CLAUDE.md`. |
| Architecture | Approach A — native extension of the `resilio/` CLI (`resilio/core/lifting/`, `resilio lift …`). Backend (`backend/`) untouched. |
| Hevy write path | Deterministic `resilio lift push` (plan → Hevy routines, idempotent). `hevy-mcp` (chrisdoc, MIT) installed as a project MCP server for reads and ad-hoc requests. See "Hevy integration". |

Rejected: CLI importing `backend/app/core` (couples to FastAPI/SQLAlchemy, backend
is frozen, its lifting heuristics are shallow); lifting in skills/markdown only
(no computation, no guardrails); cloning Hevy's ChatGPT app (closed source,
hosted by Hevy, ChatGPT-only OAuth — nothing to clone).

## Sub-projects and order

| # | Sub-project | Delivers | Spec |
|---|---|---|---|
| SP1 | Coach workspace | Working Claude Code coach at today's resilio-app level (runs + strength schedule + Google Calendar), on live data | `2026-10-14-sp1-coach-workspace-design.md` |
| SP2 | Lifting model + computation | Profile `lifting:` section, `ExercisePrescription`, macro `lifting_block`, `resilio lift history/volume/progression/templates`, lifting guardrails | written after SP1 ships |
| SP3 | Lifting skills | first-session, macro-plan-create, weekly-plan-generate/apply, weekly-analysis extended for lifting | after SP2 |
| SP4 | Hevy data in | `resilio lift sync` (incremental via `/v1/workouts/events`), exercise map (Hevy template → muscles, pattern, lower-body flag, SFR tier) | after SP3 |
| SP5 | Hevy + calendar out | `resilio lift push` → Hevy routines; calendar events list exercises | after SP4 |

Note: SP4 may be pulled before SP3 if SP3 needs real history for testing; decided at SP2 plan time.

## Hevy integration (added 2026-10-14)

Facts checked:
- Hevy's ChatGPT app (`@hevy`, replaced HevyGPT) is Hevy-hosted, ChatGPT-only, OAuth to Hevy. Not cloneable, not usable from Claude Code.
- Hevy public API (`https://api.hevyapp.com/v1`, Pro key) supports create/update routines,
  routine folders, exercise templates, workouts, workout events, exercise history.
  **It has no delete endpoints.**
- `hevy-mcp` (github.com/chrisdoc/hevy-mcp, MIT, npm, Node ≥ 20, stdio) wraps that API
  as 23 MCP tools incl. `create-routine`, `update-routine`, `create-routine-folder`,
  `search-exercise-templates`, `get-exercise-history`. Published builds send telemetry
  by default; `HEVY_MCP_TELEMETRY=0` disables it.

Design:
1. **Write path = CLI, not the LLM.** `resilio lift push --week N` converts the
   validated week plan into Hevy routine payloads and calls the API itself. Reason:
   the plan YAML is the source of truth; an LLM retyping JSON into MCP calls can drift
   from what was validated, and pushes must be idempotent.
2. **Slot reuse, because Hevy cannot delete.** A "Resilio" routine folder holds one
   routine per planned lifting slot (e.g. `Resilio · Mon · Lower Strength`). Each
   week `push` *updates* the existing slot routine (stored id map in
   `data/lifting/hevy_routines.yaml`) instead of creating new ones, so the folder never
   accumulates stale routines. Slots no longer used are renamed `Resilio · (unused)`.
3. **hevy-mcp for everything else.** Project `.mcp.json` registers
   `npx -y hevy-mcp@6.1.16` (pinned; see SP1) with `HEVY_API_KEY` from the environment and
   `HEVY_MCP_TELEMETRY=0`. The coach uses it for exercise-template search while
   designing sessions, ad-hoc one-off workouts ("give me a 30 min upper session
   today"), and reading history before SP4 exists.
4. Fallback when the API is unavailable: `push` fails closed; the plan stays valid
   and the session prescription is shown in chat/calendar description for manual entry.

## Cross-cutting rules

- Tools compute, coach judges (du-phan principle). No paces, loads or volumes invented by the LLM.
- Strava stays the only source for training load (CTL/ATL/ACWR). Hevy supplies lift
  detail only; Hevy workouts and Strava strength activities are paired by date/start ±30 min
  for adherence. No double counting.
- Loads are prescribed only for exercises with a logged set in the last 6 weeks;
  otherwise RIR-only with a "find working load" note.
- Unmapped Hevy exercises are reported as blocking in `lift volume`; the coach asks the athlete to classify.

## Non-goals

Swim/bike planning, nutrition, Intervals.icu, merging du-phan upstream v0.3.0,
backend/Telegram changes, web/mobile apps.
