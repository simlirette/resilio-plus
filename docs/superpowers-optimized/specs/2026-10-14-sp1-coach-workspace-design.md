# SP1 — Coach Workspace

Date: 2026-10-14 · Parent: `2026-10-14-claude-code-hybrid-coach-design.md`

## Goal

`cd ~/resilio-plus && claude` opens a coaching session that works exactly like
today's `~/resilio-app` (du-phan clone + Simon's strength/calendar commits), on
Simon's live data. No new lifting logic yet — SP1 is the foundation SP2–SP5 build on.

## Current state (verified 2026-10-14)

- Root `CLAUDE.md` / `AGENTS.md` are backend developer guides; they call `resilio/` "legacy, read-only".
- 5 inherited skills cite `CLAUDE.md` sections that no longer exist
  ("Planning Approval Protocol", "CLI Failure Rule", "Metric one-liners",
  "Athlete-Facing Communication Guidelines", "Conversational Pacing").
- `resilio/` forked from du-phan at `d7e762c` (2026-03-12). `~/resilio-app` shares the same
  fork point and adds 4 code commits (`d7aeb42`, `99f8566`, `1de60eb`, `b52783c`:
  `StrengthSession`, `validate_strength_placement`, Google Calendar client/sync,
  `resilio calendar auth|sync`) plus uncommitted WIP in 10 files (calendar + plan apply).
  Its 6 doc commits (phase0 spec/plan) already exist in resilio-plus.
- Live data in `~/resilio-app/data/` (athlete, activities 2025-09→2026-10, metrics, plans,
  state, google_calendar) and `~/resilio-app/config/secrets.local.yaml`.
- `.gitignore` has `data/*` (with JSON allow-list for backend knowledge files) and
  `config/secrets.local.yaml`.
- `.claude/skills/` also contains the `/head-coach` chain (head-coach, run-coach,
  lift-coach, swim-coach, bike-coach, nutrition-coach) — never used (`.coaching/` absent).

## Changes

### 1. Port resilio-app code
- Add `~/resilio-app` as a temporary git remote; cherry-pick the 4 code commits onto a
  branch in resilio-plus. Resolve conflicts against resilio-plus's own `resilio/` changes
  (`FatigueScore` schema, `b864e99`).
- Apply the uncommitted WIP as a patch (generated with `git diff` in resilio-app, **read-only
  for resilio-app** — nothing is committed or changed there), as a separate commit.
- Add the Google client deps (`google-api-python-client`, `google-auth`,
  `google-auth-oauthlib`) to `pyproject.toml` if missing; `poetry lock` + install.
- Remove the remote afterwards.

### 2. Coach `CLAUDE.md` / dev guide split
- Move current root `CLAUDE.md` → `backend/CLAUDE.md` (content unchanged except: drop the
  "`resilio/` is read-only" rule; add rule "coach CLI logic lives in `resilio/`, backend logic in
  `backend/`"; update test invariant count after the port).
- New root `CLAUDE.md` = `~/resilio-app/CLAUDE.md` adapted:
  project name, Windows invocation (`poetry run resilio …`), pointer line
  "Developing the backend/apps? See `backend/CLAUDE.md`", strength-session section
  (schedule-only until SP2), Google Calendar commands, Hevy MCP section (below).
  All section titles the skills cite must exist verbatim.
- Same split for `AGENTS.md` (root = coach, `backend/AGENTS.md` = dev) to keep Codex parity.

### 3. Skills
- `.claude/skills/` and `.agents/skills/`: sync the 8 du-phan skills to resilio-app's
  versions (only `weekly-plan-generate` and `weekly-plan-apply` differ — strength + calendar).
- Move head-coach, run-coach, lift-coach, swim-coach, bike-coach, nutrition-coach to
  `docs/archive/skills/` (kept as reference material for SP3; not discoverable as skills).
- Keep `.claude/agents/vdot-analyst.md`.

### 4. Live data cutover
- One-time copy `~/resilio-app/data/{athlete,activities,metrics,plans,state,google_calendar}`
  → `~/resilio-plus/data/`, and `config/secrets.local.yaml`. Merge `config/settings.yaml`
  keys from resilio-app (calendar settings) into resilio-plus's.
- Verify with `git status` that nothing under `data/` or secrets becomes tracked.
- After cutover `~/resilio-app` is not used for coaching anymore (left intact, not deleted).

### 5. Hevy MCP (read access now, write path in SP5)
- Project `.mcp.json`: server `hevy`, command `npx -y hevy-mcp@6.1.16`
  (latest stable ≥ 2 weeks old on 2026-10-14; Node v24 installed, needs ≥ 20),
  env `HEVY_API_KEY=${HEVY_API_KEY}`, `HEVY_MCP_TELEMETRY=0`.
  Bump only deliberately, to a release ≥ 2 weeks old.
- Key comes from the user's environment, never committed. `CLAUDE.md` documents it and says:
  until SP5, the coach may create Hevy routines via MCP only after explicit athlete approval
  of the session content.

## Acceptance criteria

1. `poetry run resilio status`, `profile get`, `plan show` in resilio-plus return the same data as in resilio-app.
2. A weekly cycle works end to end in a fresh session: weekly-analysis → weekly-plan-generate
   (runs + strength sessions) → weekly-plan-apply → `resilio calendar sync` updates the existing
   Google Calendar events (no duplicates).
3. `grep` of every `CLAUDE.md "…"` reference in `.claude/skills/**` resolves to a heading in root `CLAUDE.md`.
4. Only du-phan skills + vdot-analyst are discoverable; head-coach chain lives in `docs/archive/skills/`.
5. Full test suite: CLI tests incl. ported calendar tests pass; backend suite unchanged
   (same pre-existing 4 failures, nothing new). mypy/ruff for `backend/` unchanged.
6. `git status` after cutover shows no data/secret files; `.mcp.json` contains no key.
7. Hevy MCP: `get-workouts` returns Simon's recent workouts in a Claude Code session.

## Failure modes considered

| Risk | Severity | Handling |
|---|---|---|
| Cherry-pick conflicts in `resilio/schemas/plan.py` / `core/plan.py` vs resilio-plus edits | Minor | Small known diff (FatigueScore); resolve by hand, tests gate it. |
| `data/*` allow-list (`!data/*.json`) lets a migrated file get tracked — e.g. OAuth `data/google_calendar/token.json` | Critical if it happens | Subdir files shouldn't match a root-level allow-list, but don't rely on it: add explicit ignores per coach data subdir + acceptance #6. |
| Backend and CLI both use `data/` | Minor | Disjoint names (`resilio.db`, `checkpoints.sqlite`, `*.json` at root vs coach subdirs). |
| Coach persona leaks into backend dev sessions | Minor | Root `CLAUDE.md` says: if the user asks to develop code, follow `backend/CLAUDE.md`. Documented. |
| Simon keeps logging in resilio-app during migration → data drift | Minor | Single cutover moment; re-copy if the gap > 0 days before first resilio-plus session. |
| Third-party `hevy-mcp` package (supply chain, key access) | Minor | Exact version pin, telemetry off, key via env only. |

## Non-goals

Any lifting logic (SP2+), upstream du-phan merge, backend/app changes, deleting `~/resilio-app`.
