# Security Checklist — Pre-PR / Pre-Push

Run through this checklist before opening a PR or pushing to main.

---

## Secrets

- [ ] No real credentials in any committed file (code, docs, plan files, specs)
  - Use `CHANGEME` in docs and `.env.example`
  - Use environment variables in code: `os.environ.get("KEY", "default")`
- [ ] `.env` is **not** staged: `git status` shows it as untracked or gitignored
- [ ] New secrets added to `.env.example` with `CHANGEME` placeholder
- [ ] **Primary check:** `gitleaks detect --source . --log-opts="--all"` (required before every push)
- [ ] **Supplemental check:** `git diff --staged | grep -iE "sk-ant|client_secret=[a-f0-9]{20,}|api_key=[a-f0-9-]{32,}"`

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
- [ ] Any CORS changes must include written justification (in PR description or commit message) explaining why the change is needed

---

## Input validation

- [ ] New route parameters use Pydantic types (FastAPI validates automatically)
- [ ] Path parameters that are IDs are `str` (UUID validated at model layer, not route layer)
- [ ] File uploads check MIME type and size

---

## Backups and temp files

- [ ] No `*.backup`, `*.backup2`, `*.bak` files staged
- [ ] No `.env` or `.env.local` staged
