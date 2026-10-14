# SP1 Coach Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `cd ~/resilio-plus && claude` opens a du-phan-style coaching session on Simon's live data, including strength scheduling, Google Calendar sync and Hevy MCP read access.
**Architecture:** Port Simon's 4 code commits + WIP from `~/resilio-app` into `resilio-plus/resilio/` by cherry-pick (shared fork point `d7e762c`). Root `CLAUDE.md`/`AGENTS.md` become the coach persona copied from resilio-app; the current dev guides move to `backend/`. Live data is copied once; resilio-app is never modified.
**Tech Stack:** Python 3.13, Poetry 2.3.3, Typer CLI (`resilio`), pytest, git, Node 24 (`npx hevy-mcp@6.1.16`).
**Spec:** `docs/superpowers-optimized/specs/2026-10-14-sp1-coach-workspace-design.md`
**Assumptions:**
- Assumes `~/resilio-app` HEAD is `b52783c` with the 10-file WIP — will NOT pick up anything Simon commits there after 2026-10-14 (re-run Task 6 if so).
- Assumes `HEVY_API_KEY` is set as a Windows user env var — Task 5 verification fails if Claude Code was launched before it was set.
- Assumes the pytest venv at `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13` — `poetry install` keeps using it.

**Shell vars used below (Git Bash):**
```bash
RP=~/resilio-plus; RA=~/resilio-app
VENV=/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts
```

**Baseline (2026-10-14, before Task 1):** `pytest tests/unit` → 788 passed, 9 skipped, 2 failed (`test_config.py::test_get_repo_root_raises_when_not_in_repo`, `test_vdot_continuity.py::test_high_continuity_no_breaks` — pre-existing).

---

## File Structure

| Path | Change | Responsibility |
|---|---|---|
| `resilio/schemas/plan.py`, `resilio/core/plan.py`, `resilio/api/plan.py`, `resilio/cli/__init__.py`, `resilio/cli/commands/{calendar,plan}.py`, `resilio/core/{calendar_sync,google_calendar,repository}.py`, `resilio/schemas/config.py` | ported | strength sessions + calendar sync (from resilio-app) |
| `tests/unit/test_calendar_sync.py`, `tests/unit/test_calendar_automation.py` | ported | calendar tests |
| `docs/coaching/google_calendar_setup.md`, `docs/specs/google_calendar_sync.md`, `docs/coaching/cli/cli_planning.md` | ported | docs |
| `pyproject.toml`, `poetry.lock` | modify | 3 Google deps |
| `.gitignore` | modify | `credentials.json`, coach data subdirs |
| `.claude/skills/*`, `.agents/skills/*` | sync | du-phan skills at resilio-app version |
| `docs/archive/skills/{head,run,lift,swim,bike,nutrition}-coach/` | moved | archived head-coach chain |
| `CLAUDE.md`, `AGENTS.md` | replace | coach persona |
| `backend/CLAUDE.md`, `backend/AGENTS.md` | moved+edit | dev guides |
| `.mcp.json` | create | Hevy MCP server |
| `data/**`, `config/secrets.local.yaml`, `credentials.json` | copied, untracked | live athlete data |

---

### Task 1: Port the 4 code commits

**Files:** see File Structure rows "ported" + `pyproject.toml`, `poetry.lock`, `.gitignore`.

- [ ] **Step 1: Add resilio-app as a temporary remote and fetch**
```bash
cd $RP && git remote add resilio-app $RA && git fetch resilio-app
git log --oneline d7e762c..resilio-app/main | head -4   # expect b52783c 1de60eb 99f8566 d7aeb42 on top
```

- [ ] **Step 2: Cherry-pick in order**
```bash
git cherry-pick d7aeb42 99f8566 1de60eb b52783c
```
Conflict resolution rules (apply on each stop, then `git cherry-pick --continue`):
- `pyproject.toml`: keep resilio-plus's file (`git checkout --ours pyproject.toml`) then add these 3 lines inside `[project].dependencies`, after `"sentry-sdk[fastapi]>=2.0,<3.0",`:
  ```toml
      "google-api-python-client (>=2.197.0,<3.0.0)",
      "google-auth (>=2.53.0,<3.0.0)",
      "google-auth-oauthlib (>=1.4.0,<2.0.0)",
  ```
- `poetry.lock`: `git checkout --ours poetry.lock` (regenerated in Step 3).
- `CLAUDE.md`: `git checkout --ours CLAUDE.md` (root CLAUDE.md is replaced in Task 4).
- `.gitignore`: keep both sides.
- `resilio/**` / skills: merge by hand keeping both resilio-plus edits (`FatigueScore`, `b864e99`) and the strength/calendar additions.

- [ ] **Step 3: Lock and install**
```bash
cd $RP && poetry lock && poetry install
$VENV/python.exe -c "import googleapiclient, google_auth_oauthlib; print('ok')"
```
Expected: `ok`.

- [ ] **Step 4: Run the CLI unit suite**
```bash
$VENV/pytest.exe tests/unit -q -p no:cacheprovider | tail -4
```
Expected: same 2 pre-existing failures, passed count = 788 + calendar tests (≈ +24), no other failures.

- [ ] **Step 5: Commit lock change if separate**
```bash
git add pyproject.toml poetry.lock && git commit -m "chore(deps): lock Google Calendar client deps for coach CLI" || true
```

### Task 2: Apply resilio-app WIP + guard secrets

**Files:** `resilio/cli/commands/{calendar,plan}.py`, `resilio/core/{google_calendar,repository}.py`, `docs/coaching/{google_calendar_setup,cli/cli_planning}.md`, `.claude/skills/weekly-plan-apply/**`, `.agents/skills/weekly-plan-apply/**`, `tests/unit/test_calendar_automation.py`, `.gitignore`

- [ ] **Step 1: Export the WIP as a patch (read-only on resilio-app)**
```bash
git -C $RA diff > /tmp/ra-wip.patch && wc -l /tmp/ra-wip.patch
cd $RP && git apply --3way /tmp/ra-wip.patch
cp $RA/tests/unit/test_calendar_automation.py tests/unit/
```
Expected: patch applies (resolve any 3-way conflicts by hand, same rules as Task 1).

- [ ] **Step 2: Ignore Google OAuth client secret and coach data explicitly** — append to `.gitignore` under `# Resilio - LOCAL DATA (NEVER COMMIT)` if not already present after Task 1:
```gitignore
credentials.json
data/google_calendar/
data/athlete/
data/activities/
data/metrics/
data/plans/
data/state/
data/lifting/
```
Verify: `git check-ignore credentials.json data/google_calendar/token.json data/athlete/profile.yaml` prints all three.

- [ ] **Step 3: Tests**
```bash
$VENV/pytest.exe tests/unit -q -p no:cacheprovider | tail -4
```
Expected: only the 2 pre-existing failures.

- [ ] **Step 4: Commit**
```bash
git add -A resilio tests/unit docs .claude/skills .agents/skills .gitignore
git commit -m "feat(coach): port resilio-app calendar automation WIP + ignore OAuth/coach data"
git remote remove resilio-app
```

### Task 3: Sync du-phan skills, archive the head-coach chain

**Files:** `.claude/skills/*`, `.agents/skills/*`, `docs/archive/skills/*`

- [ ] **Step 1: Make shared skills identical to resilio-app's working tree**
```bash
cd $RP
for s in complete-setup first-session macro-plan-create plan-progress-review vdot-baseline-proposal weekly-analysis weekly-plan-apply weekly-plan-generate; do
  diff -rq .claude/skills/$s $RA/.claude/skills/$s >/dev/null || { rm -rf .claude/skills/$s; cp -r $RA/.claude/skills/$s .claude/skills/; echo "synced .claude $s"; }
  diff -rq .agents/skills/$s $RA/.agents/skills/$s >/dev/null || { rm -rf .agents/skills/$s; cp -r $RA/.agents/skills/$s .agents/skills/; echo "synced .agents $s"; }
done
```
- [ ] **Step 2: Archive the head-coach chain**
```bash
mkdir -p docs/archive/skills
for s in head-coach run-coach lift-coach swim-coach bike-coach nutrition-coach; do git mv .claude/skills/$s docs/archive/skills/$s; done
ls .claude/skills   # expect exactly the 8 du-phan skills
```
- [ ] **Step 3: Verify** — `diff -rq .claude/skills $RA/.claude/skills` prints nothing.
- [ ] **Step 4: Commit**
```bash
git add -A .claude/skills .agents/skills docs/archive/skills
git commit -m "chore(coach): align du-phan skills with resilio-app, archive head-coach chain"
```

### Task 4: Split CLAUDE.md / AGENTS.md (coach at root, dev in backend/)

**Files:** `CLAUDE.md`, `AGENTS.md`, `backend/CLAUDE.md`, `backend/AGENTS.md`

- [ ] **Step 1: Move dev guides**
```bash
cd $RP && git mv CLAUDE.md backend/CLAUDE.md && git mv AGENTS.md backend/AGENTS.md
```
- [ ] **Step 2: Edit `backend/CLAUDE.md` Development Rules** — replace
```
1. **`resilio/` is read-only** — legacy CLI, do not modify
2. **New logic goes in `backend/`**
```
with
```
1. **Coach CLI logic lives in `resilio/`** (used by Claude Code coaching sessions — see root `CLAUDE.md`); **app/backend logic lives in `backend/`**. Never import `backend/` from `resilio/`.
2. **New backend logic goes in `backend/`**
```
and in the Repository Map row for `resilio/` replace `Legacy Python CLI — read-only` with `Coach CLI (Claude Code sessions) — active`. Add as first line after the title: `> Backend/app developer guide. The repo root CLAUDE.md is the coach persona.`
- [ ] **Step 3: Create root coach files**
```bash
cp $RA/CLAUDE.md CLAUDE.md && cp $RA/AGENTS.md AGENTS.md
```
Then edit root `CLAUDE.md`:
  1. After the first heading line insert:
     ```markdown
     > **Resilio Plus — coach mode.** This repo is used as a personal coach in Claude Code. Developing the backend/apps? Follow `backend/CLAUDE.md` instead and say so at the start of the session.
     ```
  2. In "CLI Essentials" → "CLI Failure Rule" list, replace item 2 `` `.venv/bin/resilio` `` with `` `C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/resilio` (Windows Poetry venv) ``.
  3. Before "## Error Handling" insert:
     ```markdown
     ## Strength Sessions (schedule layer)

     Weekly plans carry `strength_sessions` (type, day, time, duration) next to running `workouts`. Until SP2 ships, exercise detail lives in Hevy; `validate_strength_placement` guards lower-body days against long/quality runs. Push the plan to Google Calendar with `resilio calendar sync` (`--dry-run` to preview).

     ## Hevy (MCP)

     The project MCP server `hevy` (`.mcp.json`, `hevy-mcp@6.1.16`, key from the `HEVY_API_KEY` env var) gives read access to Hevy: workouts, exercise history, routines, exercise templates. Use it to read lifting history when planning strength sessions. Creating or updating Hevy routines/workouts is allowed **only after the athlete explicitly approves the exact session content in chat**. Never print the API key.
     ```
- [ ] **Step 4: Same pointer + Hevy section in root `AGENTS.md`** (insert the coach-mode note after the first heading and the two sections before "## Error Handling", with "Codex" wording unchanged otherwise). AGENTS.md has no "Metric one-liners" heading; that is acceptable — skills cite `CLAUDE.md`.
- [ ] **Step 5: Verify every skill reference resolves**
```bash
grep -rhoE 'CLAUDE\.md "[^"]+"' .claude/skills | sed -E 's/CLAUDE\.md "([^".]+)\.?"/\1/' | sort -u | while read -r s; do grep -q "$s" CLAUDE.md && echo "OK  $s" || echo "MISSING  $s"; done
grep -q "Planning Approval Protocol" CLAUDE.md && echo "OK  Planning Approval Protocol"
```
Expected: only `OK` lines.
- [ ] **Step 6: Commit**
```bash
git add CLAUDE.md AGENTS.md backend/CLAUDE.md backend/AGENTS.md
git commit -m "docs(coach): root CLAUDE.md/AGENTS.md become coach persona; dev guides move to backend/"
```

### Task 5: Hevy MCP server

**Files:** Create `.mcp.json`

- [ ] **Step 1: Write `.mcp.json`**
```json
{
  "mcpServers": {
    "hevy": {
      "command": "npx",
      "args": ["-y", "hevy-mcp@6.1.16"],
      "env": {
        "HEVY_API_KEY": "${HEVY_API_KEY}",
        "HEVY_MCP_TELEMETRY": "0"
      }
    }
  }
}
```
- [ ] **Step 2: Verify server starts and connects**
```bash
cd $RP && claude mcp list 2>&1 | grep -i hevy
```
Expected: `hevy: npx -y hevy-mcp@6.1.16 - ✓ Connected`. If "Failed": check `HEVY_API_KEY` is visible to this shell (`[ -n "$HEVY_API_KEY" ] && echo set`) without printing it.
- [ ] **Step 3: Verify no key in file** — `grep -c "HEVY_API_KEY\": \"\${HEVY_API_KEY}\"" .mcp.json` → `1`.
- [ ] **Step 4: Commit**
```bash
git add .mcp.json && git commit -m "feat(coach): register pinned hevy-mcp server (telemetry off, key from env)"
```

### Task 6: Live data cutover

**Files:** untracked `data/{athlete,activities,metrics,plans,state,google_calendar}/`, `config/secrets.local.yaml`, `credentials.json`

- [ ] **Step 1: Refuse to overwrite existing coach data**
```bash
cd $RP && for d in athlete activities metrics plans state google_calendar; do [ -e data/$d ] && echo "EXISTS data/$d — stop and inspect"; done; [ -e config/secrets.local.yaml ] && echo "EXISTS secrets"
```
Expected: no output (verified 2026-10-14: `data/athlete/profile.yaml` missing).
- [ ] **Step 2: Copy**
```bash
for d in athlete activities metrics plans state google_calendar; do cp -r $RA/data/$d data/; done
cp $RA/config/secrets.local.yaml config/ && cp $RA/credentials.json .
```
- [ ] **Step 3: Nothing becomes tracked**
```bash
git status --porcelain | grep -E "data/|secrets|credentials" && echo "LEAK — stop" || echo "clean"
```
Expected: `clean`.
- [ ] **Step 4: Same answers from both repos**
```bash
for c in "status" "profile get" "plan show"; do
  a=$(cd $RA && poetry run resilio $c 2>/dev/null | md5sum); b=$(cd $RP && poetry run resilio $c 2>/dev/null | md5sum)
  [ "$a" = "$b" ] && echo "SAME  $c" || echo "DIFF  $c"
done
```
Expected: `SAME` for all three. On `DIFF`, diff the two outputs; a difference caused only by the WIP behaving identically but formatting paths differently is acceptable — record it.
- [ ] **Step 5: Calendar dry run against migrated token**
```bash
cd $RP && poetry run resilio calendar sync --dry-run | head -30
```
Expected: `ok: true`, events listed as update/unchanged (no mass "create" — that would mean state.json mapping was lost).

### Task 7: Full verification

- [ ] **Step 1: Full suite**
```bash
cd $RP && $VENV/pytest.exe tests -q -p no:cacheprovider 2>&1 | tail -8
```
Expected: ≥ 2987 + ported calendar tests passed; failures only the 4 pre-existing ones listed in `backend/CLAUDE.md`.
- [ ] **Step 2: Backend gates unchanged**
```bash
$VENV/python.exe -m mypy backend/app/ --config-file pyproject.toml | tail -1
$VENV/python.exe -m ruff check backend/ | tail -1
```
Expected: `Success: no issues found` and `All checks passed!`.
- [ ] **Step 3: Update test invariant in `backend/CLAUDE.md`** — replace `≥2987 passing — état V4 2026-08-19` with the new passed count and today's date (`état SP1 2026-10-14`). Commit:
```bash
git add backend/CLAUDE.md && git commit -m "docs(backend): raise test invariant after SP1 port"
```
- [ ] **Step 4: Acceptance checklist (spec)** — confirm #1 (Task 6.4), #3 (Task 4.5), #4 (Task 3.2), #5 (Task 7.1-2), #6 (Task 6.3, 5.3), #7 (Task 5.2 + in a fresh `claude` session ask the coach "what were my last 3 Hevy workouts?"). #2 (full weekly cycle in a fresh session) is the user's first real coaching session; run it with Simon.
- [ ] **Step 5: Push branch**
```bash
git push -u origin feat/claude-code-coach
```
