# Security Audit & Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit the repo for leaked secrets and security gaps, produce security documentation, and fix CORS + unauthenticated routes in code.

**Architecture:** Four tasks executed in criticality order: documentation (audit + manual actions + BFG plan + PR checklist) → .gitignore hardening → CORS whitelist → auth guard on `GET /athletes/`. Each task is independently committable. No destructive git operations — history rewrite is documented for manual execution by Simon-Olivier only.

**Tech Stack:** Python 3.13, FastAPI, pytest, bash git commands (no external scanner required — gitleaks/trufflehog not installed).

---

## File Map

| File | Action |
|---|---|
| `docs/security/AUDIT-2026-04-13.md` | Create — full findings: leaked commits, code gaps, remediation status |
| `docs/security/MANUAL-ACTIONS.md` | Create — credential rotation steps for Simon-Olivier |
| `docs/security/BFG-REWRITE-PLAN.md` | Create — BFG history rewrite procedure (destructive, requires explicit confirmation) |
| `docs/security/SECURITY-CHECKLIST.md` | Create — PR checklist for future contributors |
| `.gitignore` | Modify — add `*.backup2`, uncomment `.idea/` |
| `backend/app/main.py` | Modify — replace `allow_origins=["*"]` with env-driven whitelist |
| `.env.example` | Modify — add `ALLOWED_ORIGINS` entry |
| `backend/app/routes/athletes.py` | Modify — guard `GET /athletes/`; add TODO on `POST /athletes/` |
| `tests/backend/api/test_athletes.py` | Modify — update 2 tests that assume `GET /athletes/` is unauthenticated |

---

### Task 1: Security documentation

**Files:**
- Create: `docs/security/AUDIT-2026-04-13.md`
- Create: `docs/security/MANUAL-ACTIONS.md`
- Create: `docs/security/BFG-REWRITE-PLAN.md`
- Create: `docs/security/SECURITY-CHECKLIST.md`

No code changes. No tests. Pure documentation.

- [ ] **Step 1: Create `docs/security/AUDIT-2026-04-13.md`**

```markdown
# Security Audit — 2026-04-13

**Auditor:** Claude Code (automated scan + manual review)
**Repo:** resilio-plus
**Date:** 2026-04-13

---

## 1. Git History Scan

Scan performed with `git log -S` for known secret patterns across all 740 commits.

### Confirmed leaked credentials

| # | Secret type | Value (partial) | Commit | File | Date |
|---|---|---|---|---|---|
| 1 | Strava OAuth client secret | `31d0dea4...beae24fba` | `38c951f` | `docs/superpowers/plans/2026-04-05-session3-connectors.md` | 2026-04-05 |
| 2 | Hevy API key | `fe874ad5-90b6-437a-ad0b-81162c850400` | `38c951f` | `docs/superpowers/plans/2026-04-05-session3-connectors.md` | 2026-04-05 |

Both secrets appear as example values in an implementation plan document. They are present in GitHub history since push of `38c951f`.

**Current state of working tree:** Neither secret appears in any current file. The `.env` file is gitignored and was never committed.

**ANTHROPIC_API_KEY:** Present in `.env` (local only). Never appears in git history. No action required beyond keeping `.env` gitignored.

### No other leaked secrets found

Patterns scanned:
- `sk-ant-api` (Anthropic)
- `STRAVA_CLIENT_SECRET=[a-f0-9]` (real value, not CHANGEME)
- `HEVY_API_KEY=[a-f0-9-]` (real value)
- `JWT_SECRET_KEY=` (no real value found in history)
- `DATABASE_URL=postgresql.*@` (only dev defaults found — `resilio:resilio@localhost`)

---

## 2. Current Code Gaps

| # | Severity | Finding | File | Line | Status |
|---|---|---|---|---|---|
| 1 | 🔴 HIGH | `CORS allow_origins=["*"]` — accepts any origin | `backend/app/main.py` | 37 | **Fixed in this audit** |
| 2 | 🟠 HIGH | `GET /athletes/` — no auth, lists all athletes | `backend/app/routes/athletes.py` | 54 | **Fixed in this audit** |
| 3 | 🟡 INFO | `POST /athletes/` — no auth (by design, pre-onboarding) | `backend/app/routes/athletes.py` | 59 | TODO comment added, proper fix in Part 8 |
| 4 | 🟡 LOW | `*.backup2` not in `.gitignore` | `.gitignore` | — | **Fixed in this audit** |

### Not flagged (reviewed and OK)

- All other routes: protected via `get_current_athlete_id` + `_require_own` dependency chain
- Pydantic validation: active on all route inputs (FastAPI validates automatically)
- Logging: no secrets, tokens, or passwords logged anywhere
- `.env`: gitignored, never committed
- `.env.example`: exists, all values are `CHANGEME`
- `alembic.ini`: hardcoded `resilio:resilio@localhost` — dev default only, overridden by `DATABASE_URL` env var in all real environments

---

## 3. Remediation Summary

| Action | Type | Status |
|---|---|---|
| Rotate Strava client secret | Manual — Simon-Olivier | ⏳ See MANUAL-ACTIONS.md |
| Rotate Hevy API key | Manual — Simon-Olivier | ⏳ See MANUAL-ACTIONS.md |
| BFG history rewrite to remove `38c951f` content | Manual — Simon-Olivier | ⏳ See BFG-REWRITE-PLAN.md |
| CORS whitelist | Code fix | ✅ Done |
| Auth on `GET /athletes/` | Code fix | ✅ Done |
| `.gitignore` hardening | Config fix | ✅ Done |
```

- [ ] **Step 2: Create `docs/security/MANUAL-ACTIONS.md`**

```markdown
# Manual Actions Required — Simon-Olivier

These actions cannot be automated. Each must be completed in an external dashboard.

---

## Priority: IMMEDIATE

### Action 1 — Revoke Strava client secret

The secret `31d0dea45c6a0c9ea7df168b03fbd13beae24fba` was committed to GitHub in commit `38c951f` on 2026-04-05 and is still in history.

**Steps:**
1. Go to [Strava Developer Portal](https://www.strava.com/settings/api)
2. Find your app (Resilio Plus / client ID `215637`)
3. Click "Reset Client Secret" or equivalent
4. Copy the new secret
5. Update `.env`: `STRAVA_CLIENT_SECRET=<new_secret>`
6. Update any deployed environment variables (Docker, server, etc.)

**Verify:** Old secret `31d0dea4...beae24fba` can no longer exchange tokens.

---

### Action 2 — Revoke Hevy API key

The key `fe874ad5-90b6-437a-ad0b-81162c850400` was committed to GitHub in commit `38c951f` on 2026-04-05.

**Steps:**
1. Go to [Hevy Developer Portal](https://hevy.com/settings?tab=developer)
2. Find the API key `fe874ad5-90b6-437a-ad0b-81162c850400`
3. Revoke / delete it
4. Generate a new API key
5. Update `.env`: `HEVY_API_KEY=<new_key>`
6. Update any deployed environment variables

**Verify:** Old key `fe874ad5...` returns 401 on a test request.

---

## Priority: WHEN READY

### Action 3 — Execute BFG history rewrite

After completing Actions 1 and 2 (credentials are dead before rewriting history), follow the procedure in `BFG-REWRITE-PLAN.md` to remove the secrets from git history entirely.

This step is optional once credentials are rotated (dead secrets in history are low risk), but is recommended for hygiene.
```

- [ ] **Step 3: Create `docs/security/BFG-REWRITE-PLAN.md`**

```markdown
# BFG History Rewrite Plan

**Purpose:** Remove the file `docs/superpowers/plans/2026-04-05-session3-connectors.md` from all git history, eliminating the committed Strava and Hevy credentials.

**Prerequisites:**
- Actions 1 and 2 in `MANUAL-ACTIONS.md` MUST be completed first (rotate credentials before rewriting)
- Java runtime installed (BFG requires JVM): `java -version`
- No open PRs or in-flight branches (you are a solo developer — confirm with `git branch -a`)

**⚠️ WARNING: This operation rewrites git history and force-pushes. It is irreversible.**

---

## Step 1 — Download BFG Repo Cleaner

```bash
# Download BFG jar (one-time)
curl -L https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar -o ~/bfg.jar
java -jar ~/bfg.jar --version
```

Expected: `bfg 1.14.0`

---

## Step 2 — Clone a fresh mirror of the repo

```bash
cd ~/Desktop  # or any temp location outside the repo
git clone --mirror https://github.com/simlirette/resilio-plus.git resilio-plus-mirror.git
cd resilio-plus-mirror.git
```

---

## Step 3 — Run BFG to delete the file from history

The target file is `docs/superpowers/plans/2026-04-05-session3-connectors.md`.

```bash
java -jar ~/bfg.jar \
  --delete-files "2026-04-05-session3-connectors.md" \
  resilio-plus-mirror.git
```

Expected output includes: `Cleaning commits: ... Deleted text matching: ...`

---

## Step 4 — Expire reflog and GC

```bash
cd resilio-plus-mirror.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

---

## Step 5 — Verify the file is gone

```bash
git log --all --oneline -- "docs/superpowers/plans/2026-04-05-session3-connectors.md"
```

Expected: **no output** (file no longer in any commit).

---

## Step 6 — Force push

```bash
git push --force
```

---

## Step 7 — Update local clone

Back in your working copy (`C:\Users\simon\resilio-plus`):

```bash
git fetch --all
git reset --hard origin/main
```

---

## Step 8 — Verify on GitHub

1. Go to `https://github.com/simlirette/resilio-plus/commit/38c951f`
2. Confirm: "This commit does not belong to any branch on this repository" or 404
3. Search GitHub for `31d0dea45c6a0c9ea7df168b03fbd13beae24fba` — should return no results

---

## CONFIRMATION GATE

**Do not execute Step 6 (force push) without re-reading this document and confirming all prerequisites are met.**

Checklist before force push:
- [ ] Strava client secret rotated and verified dead
- [ ] Hevy API key rotated and verified dead
- [ ] BFG output confirmed file deleted in Step 3
- [ ] `git log --all` confirms file gone in Step 5
- [ ] No open PRs or collaborator branches
```

- [ ] **Step 4: Create `docs/security/SECURITY-CHECKLIST.md`**

```markdown
# Security Checklist — Pre-PR / Pre-Push

Run through this checklist before opening a PR or pushing to main.

---

## Secrets

- [ ] No real credentials in any committed file (code, docs, plan files, specs)
  - Use `CHANGEME` in docs and `.env.example`
  - Use environment variables in code: `os.environ.get("KEY", "default")`
- [ ] `.env` is **not** staged: `git status` shows it as untracked or gitignored
- [ ] New secrets added to `.env.example` with `CHANGEME` placeholder
- [ ] Quick scan: `git diff --staged | grep -iE "sk-ant|client_secret=[a-f0-9]|api_key=[a-f0-9-]{30}"`

### After any new credential exposure (however it happened)
1. Rotate the credential immediately in the external dashboard
2. Add it to `docs/security/MANUAL-ACTIONS.md`
3. Consider BFG rewrite per `docs/security/BFG-REWRITE-PLAN.md`

---

## Authentication

- [ ] Every new endpoint has `Depends(get_current_athlete_id)` or `Depends(_require_own_*)`
- [ ] If an endpoint is intentionally public, add an explicit comment:
  ```python
  # PUBLIC: unauthenticated by design — registration endpoint
  @router.post("/onboarding")
  ```
- [ ] If auth is deferred to a future phase, add:
  ```python
  # TODO(auth-partN): protect with <dependency> once Part N is implemented
  ```

---

## CORS

- [ ] `allow_origins` is never `["*"]` — always explicit list from `ALLOWED_ORIGINS` env var
- [ ] New frontend origins added to both `.env.example` and the default fallback in `main.py`

---

## Input validation

- [ ] New route parameters use Pydantic types (FastAPI validates automatically)
- [ ] Path parameters that are IDs are `str` (UUID validated at model layer, not route layer)
- [ ] File uploads check MIME type and size

---

## Backups and temp files

- [ ] No `*.backup`, `*.backup2`, `*.bak` files staged
- [ ] No `.env` or `.env.local` staged
```

- [ ] **Step 5: Run existing tests to confirm still passing**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe /c/Users/simon/resilio-plus/tests/ -q --ignore=/c/Users/simon/resilio-plus/tests/test_db 2>&1 | tail -5
```

Expected: ≥2021 passed, 0 failed.

- [ ] **Step 6: Commit all documentation**

```bash
cd /c/Users/simon/resilio-plus
git add docs/security/AUDIT-2026-04-13.md docs/security/MANUAL-ACTIONS.md docs/security/BFG-REWRITE-PLAN.md docs/security/SECURITY-CHECKLIST.md
git commit -m "docs(security): add audit findings, manual actions, BFG plan, PR checklist"
```

---

### Task 2: .gitignore hardening

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add `*.backup2` and uncomment `.idea/`**

Read `.gitignore` first. Then make two edits:

**Edit 1:** Find the line `*.backup` (currently around line 233) and add `*.backup2` immediately after it:

Before:
```
*.backup
```

After:
```
*.backup
*.backup2
```

**Edit 2:** Find the commented `.idea/` line (currently around line 188):
```
#.idea/
```
Replace with:
```
.idea/
```

- [ ] **Step 2: Verify the untracked backup2 file is now gitignored**

```bash
cd /c/Users/simon/resilio-plus
git check-ignore -v backend/app/models/athlete_state.py.backup2
```

Expected output: `.gitignore:234:*.backup2	backend/app/models/athlete_state.py.backup2`

- [ ] **Step 3: Run tests**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe /c/Users/simon/resilio-plus/tests/ -q --ignore=/c/Users/simon/resilio-plus/tests/test_db 2>&1 | tail -3
```

Expected: ≥2021 passed, 0 failed.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add .gitignore
git commit -m "chore(security): harden .gitignore — add *.backup2, uncomment .idea/"
```

---

### Task 3: CORS whitelist

**Files:**
- Modify: `backend/app/main.py`
- Modify: `.env.example`

- [ ] **Step 1: Write failing test**

Create `tests/backend/api/test_cors.py`:

```python
"""CORS middleware must not use wildcard origin."""
from app.main import app
from fastapi.testclient import TestClient


def test_cors_rejects_unlisted_origin():
    """A request from an unlisted origin must NOT get CORS headers."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.options(
        "/athletes/",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Either the header is absent, or it does not contain the evil origin
    acao = resp.headers.get("access-control-allow-origin", "")
    assert acao != "http://evil.example.com", (
        "CORS wildcard is active — unlisted origin was reflected"
    )
    assert acao != "*", "CORS allow_origins=[\"*\"] is still set"


def test_cors_allows_localhost_3000():
    """Requests from localhost:3000 (Next.js dev) must get CORS headers."""
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.options(
        "/athletes/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    acao = resp.headers.get("access-control-allow-origin", "")
    assert acao == "http://localhost:3000", (
        f"Expected localhost:3000 to be allowed, got: {acao!r}"
    )
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe /c/Users/simon/resilio-plus/tests/backend/api/test_cors.py -v 2>&1 | tail -15
```

Expected: `test_cors_rejects_unlisted_origin` FAILS (wildcard still active).

- [ ] **Step 3: Fix `backend/app/main.py`**

Replace the current CORS block. Read the file first, then make this edit.

Current (lines 1-5 and 35-41):
```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
```
and:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

New — add `import os` at top and replace the middleware block:

**Edit 1:** Change the imports section (add `import os`):
```python
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
```

**Edit 2:** Replace the `app.add_middleware(...)` block:
```python
_raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:4000,http://localhost:8081,http://localhost:19000",
)
_ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

- [ ] **Step 4: Add `ALLOWED_ORIGINS` to `.env.example`**

Append to `.env.example`:
```
# CORS — comma-separated list of allowed frontend origins
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:4000,http://localhost:8081,http://localhost:19000
```

- [ ] **Step 5: Run tests**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe /c/Users/simon/resilio-plus/tests/backend/api/test_cors.py -v 2>&1 | tail -10
```

Expected: both tests PASS.

- [ ] **Step 6: Run full suite**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe /c/Users/simon/resilio-plus/tests/ -q --ignore=/c/Users/simon/resilio-plus/tests/test_db 2>&1 | tail -5
```

Expected: ≥2023 passed (2021 + 2 new), 0 failed.

- [ ] **Step 7: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add backend/app/main.py .env.example tests/backend/api/test_cors.py
git commit -m "fix(security): replace CORS wildcard with explicit origin whitelist"
```

---

### Task 4: Auth on `GET /athletes/` + TODO on `POST /athletes/`

**Files:**
- Modify: `backend/app/routes/athletes.py`
- Modify: `tests/backend/api/test_athletes.py`

- [ ] **Step 1: Write failing test for the auth requirement**

The tests `test_list_athletes_empty` and `test_list_athletes_after_create` currently use the unauthenticated `client` fixture and expect 200. After the fix they must return 401.

Read `tests/backend/api/test_athletes.py` first (it is already at `C:\Users\simon\resilio-plus\tests\backend\api\test_athletes.py`).

Replace the two unauthenticated list tests with correct versions. The full updated file:

```python
from tests.backend.api.conftest import athlete_payload


def test_list_athletes_requires_auth(client):
    """GET /athletes/ must return 401 without a token."""
    resp = client.get("/athletes/")
    assert resp.status_code == 401


def test_list_athletes_returns_own_athlete(authed_client):
    """GET /athletes/ with valid token returns at least the authed athlete."""
    c, athlete_id = authed_client
    resp = c.get("/athletes/")
    assert resp.status_code == 200
    ids = [a["id"] for a in resp.json()]
    assert athlete_id in ids


def test_create_athlete_returns_201(client):
    resp = client.post("/athletes/", json=athlete_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Alice"
    assert body["primary_sport"] == "running"
    assert "id" in body


def test_get_athlete_returns_200(authed_client):
    c, athlete_id = authed_client
    resp = c.get(f"/athletes/{athlete_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == athlete_id


def test_update_athlete_returns_200(authed_client):
    c, athlete_id = authed_client
    resp = c.put(f"/athletes/{athlete_id}", json={"name": "Bob", "age": 25})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Bob"
    assert body["age"] == 25


def test_delete_athlete_returns_204(authed_client):
    c, athlete_id = authed_client
    resp = c.delete(f"/athletes/{athlete_id}")
    assert resp.status_code == 204


def test_create_athlete_missing_required_field_returns_422(client):
    payload = athlete_payload()
    del payload["name"]
    resp = client.post("/athletes/", json=payload)
    assert resp.status_code == 422


def test_get_athlete_without_token_returns_401(client):
    create_resp = client.post("/athletes/", json=athlete_payload())
    athlete_id = create_resp.json()["id"]
    resp = client.get(f"/athletes/{athlete_id}")
    assert resp.status_code == 401


def test_get_athlete_with_wrong_token_returns_403(authed_client):
    c, _ = authed_client
    resp = c.get("/athletes/some-other-athlete-id")
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to confirm the two new tests fail**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe /c/Users/simon/resilio-plus/tests/backend/api/test_athletes.py::test_list_athletes_requires_auth /c/Users/simon/resilio-plus/tests/backend/api/test_athletes.py::test_list_athletes_returns_own_athlete -v 2>&1 | tail -10
```

Expected: both FAIL — `test_list_athletes_requires_auth` gets 200 instead of 401; `test_list_athletes_returns_own_athlete` may pass or fail depending on current state.

- [ ] **Step 3: Fix `backend/app/routes/athletes.py`**

Read the file. Make two changes:

**Change 1:** Replace the `list_athletes` function (currently at line 54):

Before:
```python
@router.get("/", response_model=list[AthleteResponse])
def list_athletes(db: DB) -> list[AthleteResponse]:
    return [athlete_model_to_response(m) for m in db.query(AthleteModel).all()]
```

After:
```python
@router.get("/", response_model=list[AthleteResponse])
def list_athletes(
    _: Annotated[str, Depends(get_current_athlete_id)],
    db: DB,
) -> list[AthleteResponse]:
    return [athlete_model_to_response(m) for m in db.query(AthleteModel).all()]
```

**Change 2:** Add a TODO comment to `create_athlete` (currently at line 59):

Before:
```python
@router.post("/", response_model=AthleteResponse, status_code=201)
def create_athlete(data: AthleteCreate, db: DB) -> AthleteResponse:
```

After:
```python
@router.post("/", response_model=AthleteResponse, status_code=201)
# TODO(auth-part8): protect with get_current_user once Part 8 auth session is implemented.
# Do NOT add get_current_athlete_id here — this route is called pre-auth during onboarding.
def create_athlete(data: AthleteCreate, db: DB) -> AthleteResponse:
```

- [ ] **Step 4: Run the two new tests**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe /c/Users/simon/resilio-plus/tests/backend/api/test_athletes.py::test_list_athletes_requires_auth /c/Users/simon/resilio-plus/tests/backend/api/test_athletes.py::test_list_athletes_returns_own_athlete -v 2>&1 | tail -10
```

Expected: both PASS.

- [ ] **Step 5: Run full athletes test file**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe /c/Users/simon/resilio-plus/tests/backend/api/test_athletes.py -v 2>&1 | tail -15
```

Expected: all tests PASS (9 tests total).

- [ ] **Step 6: Run full suite**

```bash
/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe /c/Users/simon/resilio-plus/tests/ -q --ignore=/c/Users/simon/resilio-plus/tests/test_db 2>&1 | tail -5
```

Expected: ≥2023 passed, 0 failed.

- [ ] **Step 7: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add backend/app/routes/athletes.py tests/backend/api/test_athletes.py
git commit -m "fix(security): require auth on GET /athletes/; TODO on POST /athletes/ for Part 8"
```

---

## Self-Review Checklist

- [ ] `poetry install` succeeds after all changes
- [ ] `pytest tests/ --ignore=tests/test_db -q` shows ≥2023 passed, 0 failed
- [ ] `GET /athletes/` returns 401 without token (test confirms this)
- [ ] CORS wildcard gone — `allow_origins` reads from `ALLOWED_ORIGINS` env var
- [ ] `docs/security/MANUAL-ACTIONS.md` documents both credential rotations
- [ ] `docs/security/BFG-REWRITE-PLAN.md` documents history rewrite with confirmation gate
- [ ] `.gitignore` covers `*.backup2`
- [ ] No new `TBD` or placeholder in any created file
