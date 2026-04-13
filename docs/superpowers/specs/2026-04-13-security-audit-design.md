# Security Audit & Remediation — Design Spec

**Date:** 2026-04-13
**Status:** Approved
**Trigger:** Real credentials (`STRAVA_CLIENT_SECRET`, `HEVY_API_KEY`) leaked in commit `38c951f` in a docs/plan file — still present in GitHub history.

---

## Objective

Audit the full repo for exposed secrets and security gaps, remediate all automatable findings in code, and produce actionable documentation for manual steps (credential rotation, eventual BFG history rewrite).

---

## Findings Summary

| Severity | Finding | File / Location |
|---|---|---|
| 🔴 CRITICAL | `STRAVA_CLIENT_SECRET=31d0dea45c6a0c9ea7df168b03fbd13beae24fba` in git history | `38c951f` — `docs/superpowers/plans/2026-04-05-session3-connectors.md` |
| 🔴 CRITICAL | `HEVY_API_KEY=fe874ad5-90b6-437a-ad0b-81162c850400` in git history | `38c951f` — same file |
| 🔴 HIGH | `CORS allow_origins=["*"]` — accepts requests from any origin | `backend/app/main.py:37` |
| 🟠 HIGH | `GET /athletes/` unauthenticated — lists all athletes in DB | `backend/app/routes/athletes.py:54` |
| 🟠 HIGH | `POST /athletes/` unauthenticated — creates athletes directly | `backend/app/routes/athletes.py:59` |
| 🟡 LOW | `*.backup2` not covered by `.gitignore` (only `*.backup`) | `.gitignore` |
| ✅ OK | `.env` never committed — correctly gitignored | — |
| ✅ OK | `.env.example` exists with `CHANGEME` placeholders | — |
| ✅ OK | No secrets in log statements | — |
| ✅ OK | All other routes use `get_current_athlete_id` + `_require_own` | — |
| ✅ OK | Pydantic validation active on all route inputs | — |

---

## Approach

**History rewrite: deferred.** The leaked credentials must be rotated immediately (MANUAL-ACTIONS.md). The BFG Repo Cleaner rewrite is documented separately in `BFG-REWRITE-PLAN.md` for Simon-Olivier to execute after reviewing the plan. No `git filter-branch` or `git push --force` without explicit confirmation.

**Code fixes: immediate.** CORS whitelist, auth guards, `.gitignore` hardening, security checklist — all automated and committed one-by-one.

---

## File Map

| File | Action |
|---|---|
| `docs/security/AUDIT-2026-04-13.md` | Create — full findings, gitleaks output, current code gaps |
| `docs/security/MANUAL-ACTIONS.md` | Create — credential rotation steps Simon-Olivier must do manually |
| `docs/security/BFG-REWRITE-PLAN.md` | Create — BFG history rewrite procedure (destructive, requires explicit confirmation before execution) |
| `docs/security/SECURITY-CHECKLIST.md` | Create — PR checklist for future contributors |
| `backend/app/main.py` | Modify — replace `allow_origins=["*"]` with env-driven explicit whitelist |
| `backend/app/routes/athletes.py` | Modify — add auth to `GET /athletes/`; add `# TODO(auth-part8)` to `POST /athletes/` |
| `.gitignore` | Modify — add `*.backup2`, verify `.env.*` coverage |

---

## Section 1 — Documentation output

### `docs/security/AUDIT-2026-04-13.md`

Sections:
1. **Git history scan** — gitleaks results (run `gitleaks detect --source . --log-opts="--all"`)
2. **Committed secrets** — exact commit SHA, file, line, secret type, date
3. **Current code gaps** — CORS, auth gaps (with file:line)
4. **Status** — what was auto-fixed, what requires manual action

### `docs/security/MANUAL-ACTIONS.md`

Actions required by Simon-Olivier in external dashboards:

| # | Action | Service | Urgency |
|---|---|---|---|
| 1 | Revoke `STRAVA_CLIENT_SECRET` ending `beae24fba` and generate new secret | Strava Developer Portal | Immediate |
| 2 | Revoke `HEVY_API_KEY` `fe874ad5-90b6-437a-ad0b-81162c850400` and generate new key | Hevy Developer Portal | Immediate |
| 3 | Update `.env` with new credentials | Local machine | After #1 and #2 |
| 4 | Review `BFG-REWRITE-PLAN.md` and execute when ready | GitHub + local | When ready |

### `docs/security/BFG-REWRITE-PLAN.md`

Step-by-step BFG Repo Cleaner procedure:
- Pre-requisites (Java, BFG jar download)
- Exact files to purge: `docs/superpowers/plans/2026-04-05-session3-connectors.md`, `docs/superpowers/specs/2026-04-05-session3-connectors-design.md`
- Commands: `git clone --mirror`, `bfg --delete-files`, `git reflog expire`, `git gc`, `git push --force`
- Post-rewrite: verify history clean, notify any collaborators (none currently)
- **Confirmation gate:** this file must be reviewed and Simon-Olivier must type `CONFIRM` at the CLI before any force-push

### `docs/security/SECURITY-CHECKLIST.md`

PR checklist covering:
- No real credentials in code, docs, or plan files (use `CHANGEME` / env vars only)
- `.env` changes go to `.env.example` only
- New endpoints must have `Depends(get_current_athlete_id)` or explicit `# TODO(auth)` comment
- CORS changes require justification
- No `*.backup*` files committed
- Run `gitleaks detect --source . --log-opts="--all"` before push

---

## Section 2 — CORS fix

**Current (`backend/app/main.py:37`):**
```python
allow_origins=["*"],
allow_credentials=False,
```

**New:**
```python
_raw = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:4000,http://localhost:8081,http://localhost:19000",
)
_ALLOWED_ORIGINS = [o.strip() for o in _raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

Add `ALLOWED_ORIGINS` to `.env.example`:
```
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:4000,http://localhost:8081,http://localhost:19000
```

**Ports covered:** Next.js (3000), Docker frontend (4000), Expo Go (8081), Expo Metro (19000).

---

## Section 3 — Auth gaps

### `GET /athletes/` — add auth guard

Add `get_current_athlete_id` dependency (same pattern as all other list endpoints):

```python
@router.get("/", response_model=list[AthleteResponse])
def list_athletes(
    current_id: Annotated[str, Depends(get_current_athlete_id)],
    db: DB,
) -> list[AthleteResponse]:
    return [athlete_model_to_response(m) for m in db.query(AthleteModel).all()]
```

### `POST /athletes/` — TODO comment only

`POST /athletes/` is used by `POST /onboarding` internally and its correct auth guard requires `get_current_user` from the future Partie 8 auth system. Do **not** add a broken guard now. Add a clear TODO:

```python
@router.post("/", response_model=AthleteResponse, status_code=201)
# TODO(auth-part8): protect with get_current_user once Part 8 auth session is implemented.
# Do NOT add get_current_athlete_id here — this route is called pre-auth during onboarding.
def create_athlete(data: AthleteCreate, db: DB) -> AthleteResponse:
```

---

## Section 4 — `.gitignore` hardening

Add to `.gitignore`:
```
# Backup variants not covered by *.backup
*.backup2
*.bak

# IDE
.idea/
.vscode/settings.json
```

Verify existing coverage:
- `*.backup` ✅ already present
- `.env` ✅ already present
- `*.db` ✅ already present (added in V3-K)
- `*.sqlite` ✅ already present

---

## Invariants

- `pytest tests/` ≥ 2021 passed after each fix
- No existing test broken by auth change on `GET /athletes/` — existing `test_list_athletes` tests must be updated to provide auth token
- `poetry install` must pass
- Each fix is one atomic commit

---

## Out of Scope

- Pydantic validation: already active on all route inputs — no gaps found
- Logging: no secrets found in log statements — no changes needed
- SQLite: project is PostgreSQL-only since V3-A — no action
- Hevy/Strava/Terra connectors: no hardcoded secrets in current files — env-driven
