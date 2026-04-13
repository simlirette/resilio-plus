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
