# Pre-Launch Audit Implementation Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:executing-plans to implement this plan task-by-task.

**Goal:** Exhaustive pre-launch audit of Resilio+ backend — identify everything missing, broken, or inconsistent; fix critical issues; document the rest.
**Architecture:** Triage-first (read-only checks → report → targeted fixes → runtime verification). Report is the primary artifact; fixes are motivated by the report findings.
**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, pytest, Docker, mypy, ruff.
**Assumptions:**
- Docker may not be available in the execution environment — runtime checks (Axis E) produce "manual verification required" if `docker` command fails.
- Apple Health integration (`backend/app/integrations/apple_health/`) is excluded — parallel session in progress.
- Auth allowlist of intentionally public routes: `/health`, `/ready`, `/ready/deep`, `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/reset-password`, `GET /auth/reset-password`, `POST /athletes/` (pre-auth onboarding by design — `TODO(auth-part8)` comment is intentional and documented).

---

## Deliverables

1. `docs/PRE-LAUNCH-AUDIT.md` — per-axis findings, pass/fail, findings table
2. `docs/V1.1-BACKLOG.md` — deferred items with justification
3. Inline fixes: .backup file deletion, .env.example gaps, any critical auth/doc issues found

## Non-Goals

- Apple Health integration (parallel session)
- Frontend audit
- Performance benchmarks
- Penetration testing

---

## File Structure

**Created:**
- `docs/PRE-LAUNCH-AUDIT.md`
- `docs/V1.1-BACKLOG.md`

**Modified (if issues found):**
- `.env.example` — add missing env var documentation
- Any doc file with confirmed drift

**Deleted:**
- All `.backup` files (8 found)

---

## Task Breakdown

### Task 1: Run Full Test Suite
Run `pytest tests/ -q --tb=short --timeout=60` and capture exact counts, failures, skip counts.
Document known flakes: `test_history_shows_logged_count`, `test_high_continuity_no_breaks`.

### Task 2: Code Coherence Scan
- Grep TODO/FIXME/HACK across all Python files → classify each
- List all `.backup` files → delete them
- Scan for orphaned files (Python files with no imports referencing them)

### Task 3: Env Var Completeness Check
- Collect all `os.getenv()` / `os.environ` calls from `backend/app/`
- Diff against `.env.example` keys
- Add any missing keys with comments

### Task 4: Auth Coverage Check
- For every `@router.{get,post,patch,delete,put}` in `backend/app/routes/`
- Verify each has `Depends(get_current_athlete_id)` or `Depends(_require_admin)` or is in the public allowlist
- Flag any endpoint not covered

### Task 5: CORS + Security Scan
- Check CORS origin configuration in `main.py`
- Verify no hardcoded secrets/tokens in codebase
- Check Pydantic request body validation on all POST/PATCH routes

### Task 6: Docs vs Code Verification
- API-CONTRACT.md: list all documented endpoints, cross-ref with actual route decorators
- ATHLETE-STATE.md: compare documented schema fields vs `AthleteState` Pydantic model
- AGENT-SPECS.md: verify agent list matches `backend/app/agents/` directory
- INTEGRATIONS.md: verify connector files match documented integrations
- `.env.example`: verified in Task 3

### Task 7: Feature Completeness Matrix
- From CLAUDE.md phase table (V3-A through V3-W), list all claimed features
- For each: verify code exists, test exists, doc exists
- Produce matrix: Feature × {code ✅/❌, tests ✅/❌, docs ✅/❌}

### Task 8: Runtime Verification (Docker)
- `docker info` → if fails, mark E-axis as "manual verification required"
- If Docker available: `docker-compose build`, `docker-compose up -d`, hit /health + /ready, run smoke test
- Capture result

### Task 9: Write PRE-LAUNCH-AUDIT.md
Synthesize all findings from Tasks 1–8 into structured report.

### Task 10: Write V1.1-BACKLOG.md
Collect all non-critical findings into prioritized backlog.

### Task 11: Apply Fixes
- Delete .backup files
- Fix .env.example gaps
- Fix any critical auth issue found
- Fix any confirmed doc drift (wrong, not just missing)

### Task 12: Final Verification
- `pytest tests/backend/ tests/e2e/ -q --timeout=60` → must match baseline
- `python -m mypy backend/app/ --config-file pyproject.toml` → 0 errors
- `python -m ruff check backend/` → 0 violations
- Commit + push

### Task 13: Update CLAUDE.md
Add audit results to phase table and development rules.
