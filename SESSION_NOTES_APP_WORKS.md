# SESSION NOTES — session/app-works

## Technical Debt Observed

### 1. No "start dev stack" script
Running the full stack requires 3 separate terminal commands. No `pnpm dev` at root level that starts both backend and frontend.
**Suggestion:** Add a root `dev` script that uses `concurrently` to start both.

### 2. Backend startup command is non-obvious
Must run `uvicorn app.main:app` from `backend/` dir OR set `PYTHONPATH=backend` from root.
Running `python -m uvicorn backend.app.main:app` from root fails due to relative imports.
**Suggestion:** Add a Makefile or pnpm script: `pnpm backend:dev`.

### 3. Docker Desktop required for local dev
PostgreSQL lives only in Docker. If Docker Desktop is not running, the entire backend fails with a confusing 500.
**Suggestion:** Add a `CONTRIBUTING.md` section "Prerequisites: Docker Desktop must be running."
OR add `docker-compose up -d db` to the dev start script with a health check.

### 4. No `.env.local` for frontend
API_BASE is hardcoded to `http://localhost:8000` in `apps/web/src/lib/api.ts`.
This is fine for local dev but will need env var support before any deployment.
**Suggestion:** When deploying, externalize `NEXT_PUBLIC_API_BASE`.

### 5. No user-facing seed instructions
New devs need to create an athlete via POST /athletes/onboarding manually.
**Suggestion:** Add a `scripts/seed.sh` or a `POST /dev/seed` endpoint (dev-only) that creates a known test user.

### 6. ThemeProvider flash on load
On SSR, `<html>` has no class. next-themes adds class on client. Possible flash-of-unstyled-content (FOUC) on dark->light transitions.
`:root` defaults are already dark so this is minimal. Low priority.
