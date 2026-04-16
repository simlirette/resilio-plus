# Pre-Launch Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exhaustive pre-launch audit of Resilio+ backend — find, fix critical issues, document the rest.
**Architecture:** Triage-first: read-only checks → report → targeted fixes → final verification.
**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, pytest, Docker, mypy, ruff.
**Assumptions:**
- Assumes Docker may be unavailable — Axis E marked "manual verification required" if `docker info` fails.
- Assumes Apple Health integration (`backend/app/integrations/apple_health/`) is excluded — parallel session.
- Public route allowlist: `/health`, `/ready`, `/ready/deep`, `POST /auth/*`, `GET /auth/reset-password`, `POST /athletes/` (onboarding), `POST /athletes/onboarding`, `GET /integrations/strava/callback`.
- VENV: `/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts`

**Pre-scan findings (confirmed before plan was written):**
- 3 unprotected routes in `connectors.py`: POST /connectors/hevy, GET /connectors, DELETE /connectors/{provider} — **CRITICAL**
- 8 .backup files to delete
- `CLAUDE_API_KEY` env var used in code, not in .env.example — **minor**
- 1 TODO in athletes.py:62 — intentional, V1.1
- 8 skipped tests in test_workflows.py — all justified

---

## Files

**Created:**
- `docs/PRE-LAUNCH-AUDIT.md`
- `docs/V1.1-BACKLOG.md`

**Modified:**
- `backend/app/routes/connectors.py` — add `_require_own` to 3 routes
- `.env.example` — add CLAUDE_API_KEY alias comment

**Deleted:**
- 8 `.backup` files

---

### Task 1: Full Test Suite

**Files:** none modified

- [ ] **Step 1: Run full test suite**

Run: `$VENV/pytest.exe tests/ -q --tb=short --timeout=60 2>&1 | tail -20`
Expected: ~2378 passing, 2 pre-existing flakes, 8 skipped, 16 warnings

- [ ] **Step 2: Confirm flakes**

Known flakes: `test_history_shows_logged_count`, `test_high_continuity_no_breaks`. Any other failures are new issues requiring investigation.

---

### Task 2: Code Coherence Scan

**Files:** none modified yet

- [ ] **Step 1: Grep TODO/FIXME/HACK**

Run: `grep -rn "TODO\|FIXME\|HACK" /c/Users/simon/resilio-plus/backend --include="*.py" | grep -v "__pycache__"`
Expected: 1 result — `athletes.py:62` TODO(auth-part8). Classify as intentional → V1.1 backlog.

- [ ] **Step 2: List .backup files**

Run: `find /c/Users/simon/resilio-plus -name "*.backup" 2>/dev/null`
Expected: 8 files (7 in agents/, 1 in docs/backend/)

- [ ] **Step 3: Confirm no orphaned Python files**

Run: `ls /c/Users/simon/resilio-plus/backend/app/connectors/*.py | xargs basename -a`
Check: each connector file is imported somewhere. `fatsecret.py` is documented as "out of scope" in CLAUDE.md — classify to V1.1 backlog.

---

### Task 3: Env Var Completeness Check

**Files:** `.env.example` (if gaps found)

- [ ] **Step 1: List all env vars used in code**

Run: `grep -roh "os\.getenv(\"[^\"]*\"\|os\.environ\.get(\"[^\"]*\"\|os\.environ\[\"[^\"]*\"" /c/Users/simon/resilio-plus/backend/app --include="*.py" | sed 's/.*("\([^"]*\)".*/\1/' | sort -u`
Expected: ~23 vars including CLAUDE_API_KEY.

- [ ] **Step 2: Diff against .env.example**

Run: `grep -v "^#" /c/Users/simon/resilio-plus/.env.example | grep "=" | sed 's/=.*//' | sort`
Compare the two lists. CLAUDE_API_KEY will be missing.

- [ ] **Step 3: Add CLAUDE_API_KEY to .env.example**

Add after the ANTHROPIC_API_KEY line:
```
# CLAUDE_API_KEY=  # Alternative name for ANTHROPIC_API_KEY (checked as fallback in plan_import_service.py)
```

---

### Task 4: Auth Coverage Fix — CRITICAL

**Files:** `backend/app/routes/connectors.py`

3 routes confirmed missing `_require_own` dependency:
- `POST /{athlete_id}/connectors/hevy` (line 206)
- `GET /{athlete_id}/connectors` (line 361)
- `DELETE /{athlete_id}/connectors/{provider}` (line 409)

- [ ] **Step 1: Fix POST /connectors/hevy**

Add `_: Annotated[str, Depends(_require_own)]` parameter:
```python
@router.post("/{athlete_id}/connectors/hevy", status_code=201)
def hevy_connect(
    athlete_id: str,
    req: HevyConnectRequest,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ConnectorStatus:
```

- [ ] **Step 2: Fix GET /connectors**

```python
@router.get("/{athlete_id}/connectors", response_model=ConnectorListResponse)
def list_connectors(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ConnectorListResponse:
```

- [ ] **Step 3: Fix DELETE /connectors/{provider}**

```python
@router.delete("/{athlete_id}/connectors/{provider}", status_code=204)
def delete_connector(
    athlete_id: str,
    provider: Literal["strava", "hevy", "terra"],
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> None:
```

- [ ] **Step 4: Verify with mypy**

Run: `$VENV/python.exe -m mypy backend/app/routes/connectors.py --config-file pyproject.toml`
Expected: no errors

- [ ] **Step 5: Run connector tests**

Run: `$VENV/pytest.exe tests/backend/ -q -k "connector" --tb=short`
Expected: all pass

---

### Task 5: CORS + Security Scan

**Files:** none modified

- [ ] **Step 1: Verify CORS config**

CORS is env-driven via `ALLOWED_ORIGINS`. Default includes localhost:3000/4000/8081/19000. `allow_credentials=True` — acceptable since origins are explicitly listed. Classify as: PASS.

- [ ] **Step 2: Check for hardcoded secrets**

Run: `grep -rn "sk-\|eyJ\|Bearer \|secret=\|api_key=" /c/Users/simon/resilio-plus/backend/app --include="*.py" | grep -v "__pycache__" | grep -v "test" | grep -v "#"`
Expected: 0 hardcoded secrets. Any hits require manual review.

- [ ] **Step 3: Check Pydantic validation on POST/PATCH routes**

Run: `grep -A5 "@router.post\|@router.patch" /c/Users/simon/resilio-plus/backend/app/routes/*.py | grep -v "__pycache__" | grep "def \|BaseModel\|: [A-Z]" | head -60`
Verify: all POST/PATCH bodies use Pydantic models or File(...). Flag any `dict` or untyped body.

---

### Task 6: Docs vs Code Verification

**Files:** none (read-only scan; only fix confirmed wrong docs, not missing ones)

- [ ] **Step 1: Agent list check**

Run: `ls /c/Users/simon/resilio-plus/backend/app/agents/*.py | grep -v __pycache__ | xargs basename -a`
Cross-ref with AGENT-SPECS.md agent list. Document any gap.

- [ ] **Step 2: Connector list check**

Run: `ls /c/Users/simon/resilio-plus/backend/app/connectors/*.py | grep -v __pycache__ | xargs basename -a`
Cross-ref with INTEGRATIONS.md. Document any gap.

- [ ] **Step 3: Route count spot-check**

Run: `grep -c "@router\." /c/Users/simon/resilio-plus/backend/app/routes/*.py | grep -v ":0"`
Document total route count vs what API-CONTRACT.md covers. Flag large discrepancies.

- [ ] **Step 4: AthleteState field check**

Run: `grep "^\s*[a-z_]*:" /c/Users/simon/resilio-plus/backend/app/models/athlete_state.py | grep -v "#" | head -40`
Compare top-level fields vs ATHLETE-STATE.md documented schema. Flag any missing/renamed fields.

---

### Task 7: Feature Completeness Matrix

**Files:** none (analysis only)

- [ ] **Step 1: List all V3 phases from CLAUDE.md**

Phases V3-A through V3-W — all marked ✅ Complete. For each, verify:
- Code: does the primary module/file referenced in CLAUDE.md exist?
- Tests: does a test file covering that feature exist?
- Docs: does a reference doc in docs/backend/ exist?

Key phases to spot-check:
- V3-D (LangGraph): `backend/app/graphs/`, `tests/runtime/`, `docs/backend/LANGGRAPH-FLOW.md`
- V3-O (Auth): `backend/app/routes/auth.py`, `tests/backend/api/test_auth.py`, `docs/backend/AUTH.md`
- V3-P (Hevy CSV + Nutrition): `backend/app/integrations/hevy/`, `backend/app/integrations/nutrition/`, `docs/backend/INTEGRATIONS.md`
- V3-S (Jobs): `backend/app/jobs/`, `tests/backend/test_jobs*`, `docs/backend/JOBS.md`
- V3-U (Observability): `backend/app/observability/`, `tests/backend/test_observability*`, `docs/backend/OBSERVABILITY.md`
- V3-W (Typing): mypy 0 errors (verified), ruff 0 violations (verified), `docs/backend/TYPING-CONVENTIONS.md`

Run: `ls /c/Users/simon/resilio-plus/tests/backend/ | head -30` and `ls /c/Users/simon/resilio-plus/docs/backend/`

---

### Task 8: Runtime Verification

**Files:** none

- [ ] **Step 1: Check Docker availability**

Run: `docker info 2>&1 | head -3`
If fails: mark Axis E as "manual verification required — Docker not available in this environment."
If passes: continue to Step 2.

- [ ] **Step 2: docker-compose build** (only if Docker available)

Run: `docker-compose -f docker-compose.yml build backend 2>&1 | tail -10`
Expected: `Successfully built` or `=> exporting to image`

- [ ] **Step 3: Smoke test** (only if Docker available)

Run: `docker-compose -f docker-compose.yml up -d backend && sleep 5 && curl -s http://localhost:8000/health && docker-compose down`
Expected: `{"status":"ok"}`

---

### Task 9: Write PRE-LAUNCH-AUDIT.md

**Files:** `docs/PRE-LAUNCH-AUDIT.md` (create)

- [ ] **Step 1: Create audit report**

Write `docs/PRE-LAUNCH-AUDIT.md` with findings from Tasks 1–8. Structure:

```markdown
# Resilio+ Pre-Launch Audit — 2026-04-16

## Summary
| Axis | Status | Critical Issues | Notes |
...

## A — Tests
## B — Code Coherence  
## C — Env Vars
## D — Security (Auth + CORS)
## E — Runtime
## F — Docs vs Code
## G — Feature Completeness Matrix
```

---

### Task 10: Write V1.1-BACKLOG.md

**Files:** `docs/V1.1-BACKLOG.md` (create)

- [ ] **Step 1: Create backlog**

Write `docs/V1.1-BACKLOG.md` with all deferred items:
- `POST /athletes/` auth (pre-auth onboarding design decision)
- `FatSecretConnector` (class only, not integrated)
- Any doc coverage gaps found
- Skipped tests in test_workflows.py (covered by integration tests)
- Any feature matrix gaps

---

### Task 11: Apply Fixes

**Files:** `.backup` files (delete), `.env.example` (modify), `connectors.py` (already fixed in Task 4)

- [ ] **Step 1: Delete .backup files**

```bash
rm /c/Users/simon/resilio-plus/backend/app/agents/energy_coach/agent.py.backup
rm /c/Users/simon/resilio-plus/backend/app/agents/head_coach.py.backup
rm /c/Users/simon/resilio-plus/backend/app/agents/lifting_coach.py.backup
rm /c/Users/simon/resilio-plus/backend/app/agents/nutrition_coach.py.backup
rm /c/Users/simon/resilio-plus/backend/app/agents/recovery_coach.py.backup
rm /c/Users/simon/resilio-plus/backend/app/agents/running_coach.py.backup
rm /c/Users/simon/resilio-plus/backend/app/models/athlete_state.py.backup
rm /c/Users/simon/resilio-plus/docs/backend/INTEGRATIONS.md.backup
```

- [ ] **Step 2: Verify deletions**

Run: `find /c/Users/simon/resilio-plus -name "*.backup"`
Expected: no output

- [ ] **Step 3: Commit all fixes**

```bash
git add backend/app/routes/connectors.py .env.example
git commit -m "fix(security): add _require_own auth to hevy connect, list connectors, delete connector"
```

---

### Task 12: Final Verification

**Files:** none

- [ ] **Step 1: Full test suite**

Run: `$VENV/pytest.exe tests/backend/ tests/e2e/ -q --timeout=60 2>&1 | tail -10`
Expected: same baseline (or better) vs pre-audit run.

- [ ] **Step 2: mypy + ruff**

Run: `$VENV/python.exe -m mypy backend/app/ --config-file pyproject.toml && $VENV/python.exe -m ruff check backend/`
Expected: 0 errors, 0 violations

- [ ] **Step 3: Push**

```bash
git push origin main
```

---

### Task 13: Update CLAUDE.md

**Files:** `CLAUDE.md`

- [ ] **Step 1: Add audit phase to phase table and update latest phases section**

Add `V3-X | Pre-Launch Audit | ✅ Complete (2026-04-16)` to phase table.
Update "Dernières phases complétées" section.
