# Session 14 — Docker Full-Stack + E2E Tests + Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the full stack runnable with `docker compose up`, add 4 Playwright E2E smoke tests, and replace the hardcoded API URL with an env var.

**Architecture:** Three independent pieces — (1) polish `lib/api.ts` + env example, (2) frontend Dockerfile + compose service + standalone Next.js config, (3) Playwright install + 4 E2E tests covering page render and auth redirect. Each task commits independently.

**Tech Stack:** Next.js 15 (standalone output), Docker multi-stage build, Playwright 1.50+, Node 22 Alpine.

---

## File Map

| File | Action | Responsible for |
|------|--------|----------------|
| `frontend/src/lib/api.ts` | Modify | Use `NEXT_PUBLIC_API_URL` env var with fallback |
| `frontend/.env.local.example` | Create | Document the env var for developers |
| `frontend/next.config.ts` | Modify | Add `output: 'standalone'` for Docker build |
| `frontend/Dockerfile` | Create | Multi-stage Next.js build (deps→builder→runner) |
| `docker-compose.yml` | Modify | Add `frontend` service with build arg |
| `frontend/package.json` | Modify | Add `@playwright/test` dep + `test:e2e` scripts |
| `frontend/playwright.config.ts` | Create | Playwright: chromium + webServer (next dev) |
| `frontend/e2e/auth.spec.ts` | Create | Login + register page render tests |
| `frontend/e2e/dashboard.spec.ts` | Create | Protected route redirect tests |
| `README.md` | Modify | Add Quick Start section (Docker + manual dev) |
| `CLAUDE.md` | Modify | Mark S14 ✅ FAIT |

---

## Task 1: Polish — API base URL env var

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/.env.local.example`

The hardcoded `http://localhost:8000/api/v1` prevents Docker deployment. Replace with an env var that falls back to the same value.

- [ ] **Step 1: Read current `lib/api.ts`**

```bash
# From frontend/ directory
cat src/lib/api.ts
```

Note the line: `const API_BASE = "http://localhost:8000/api/v1";`

- [ ] **Step 2: Replace hardcoded URL with env var**

In `frontend/src/lib/api.ts`, change:

```typescript
const API_BASE = "http://localhost:8000/api/v1";
```

to:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
```

No other changes to this file.

- [ ] **Step 3: Create `frontend/.env.local.example`**

Create the file `frontend/.env.local.example`:

```bash
# Copy to .env.local to override the default API URL.
# Default (http://localhost:8000/api/v1) works for standard local dev.
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

- [ ] **Step 4: Verify build still passes**

```bash
cd frontend
npm run build
```

Expected: Build completes with 0 TypeScript errors, 0 ESLint warnings. Same 10 routes as before.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/.env.local.example
git commit -m "feat: use NEXT_PUBLIC_API_URL env var in api.ts (S14)"
```

---

## Task 2: Frontend Dockerfile + docker-compose + standalone config

**Files:**
- Modify: `frontend/next.config.ts`
- Create: `frontend/Dockerfile`
- Modify: `docker-compose.yml`

The `docker-compose.yml` already has `db` and `api` services. We add a `frontend` service using a multi-stage Next.js Docker build.

Next.js standalone mode (`output: 'standalone'`) copies only the minimal server files needed to run, making the image smaller. The runner stage starts `node server.js` (the auto-generated standalone server entry point).

**Important**: `NEXT_PUBLIC_*` env vars bake into the JS bundle at build time. The arg `http://localhost:8000/api/v1` is correct because the browser (on the host machine) reaches the API container via Docker's port mapping on localhost:8000.

- [ ] **Step 1: Add `output: 'standalone'` to `next.config.ts`**

File: `frontend/next.config.ts`

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

- [ ] **Step 2: Verify the standalone build works**

```bash
cd frontend
npm run build
```

Expected: Build succeeds. You should now see a `frontend/.next/standalone/` directory created. It contains `server.js`.

- [ ] **Step 3: Create `frontend/Dockerfile`**

Create the file `frontend/Dockerfile`:

```dockerfile
# ══════════════════════════════════════════════
# Stage 1 — deps: install node_modules
# ══════════════════════════════════════════════
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ══════════════════════════════════════════════
# Stage 2 — builder: compile Next.js
# ══════════════════════════════════════════════
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# ══════════════════════════════════════════════
# Stage 3 — runner: minimal production image
# ══════════════════════════════════════════════
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy standalone server + static assets
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
# public/ is empty in this project but copy it for completeness
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 4: Add `frontend` service to `docker-compose.yml`**

Read `docker-compose.yml` first. Then add the `frontend` service **after** the `api` service, before the `volumes:` section:

```yaml
  # ── Frontend Next.js ──────────────────────────
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1
    container_name: resilio_frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      - api
```

The final `docker-compose.yml` should have 3 services: `db`, `api`, `frontend`.

- [ ] **Step 5: Verify docker compose build succeeds**

```bash
cd /path/to/resilio-plus
docker compose build frontend
```

Expected: Build completes successfully. The output shows three stages (deps, builder, runner). No errors. Build may take 2–4 minutes on first run (downloads node:22-alpine, installs node_modules, builds Next.js).

If the build fails with "COPY public ./public: not found", create an empty `frontend/public/.gitkeep` file and add it.

- [ ] **Step 6: Commit**

```bash
git add frontend/next.config.ts frontend/Dockerfile docker-compose.yml
git commit -m "feat: add frontend Dockerfile + docker-compose service (S14)"
```

---

## Task 3: Install Playwright + config

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/playwright.config.ts`

Playwright is the industry standard for Next.js E2E testing. We install only the `@playwright/test` package (the test runner) and download only the Chromium browser (smallest, fastest). The `webServer` config in `playwright.config.ts` automatically starts `next dev` when running tests.

- [ ] **Step 1: Install `@playwright/test`**

```bash
cd frontend
npm install --save-dev @playwright/test
```

Expected: `package.json` devDependencies now includes `"@playwright/test": "^1.50.x"` (exact version may vary). `package-lock.json` updated.

- [ ] **Step 2: Add test scripts to `package.json`**

In `frontend/package.json`, add to the `"scripts"` section:

```json
"test:e2e": "playwright test",
"test:e2e:ui": "playwright test --ui"
```

The full scripts section should look like:

```json
"scripts": {
  "dev": "next dev --turbopack",
  "build": "next build --turbopack",
  "start": "next start",
  "lint": "eslint",
  "test:e2e": "playwright test",
  "test:e2e:ui": "playwright test --ui"
}
```

- [ ] **Step 3: Install Chromium browser (one-time)**

```bash
cd frontend
npx playwright install chromium
```

Expected: Playwright downloads Chromium browser to `~/.cache/ms-playwright/`. Takes ~30 seconds. Output ends with "Chromium X.X.X (playwright build XXXX) downloaded".

- [ ] **Step 4: Create `frontend/playwright.config.ts`**

```typescript
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
```

**Notes:**
- `reuseExistingServer: true` — if `next dev` is already running on port 3000, Playwright reuses it (useful during dev). If nothing is running, Playwright starts `npm run dev` automatically.
- `timeout: 120_000` — Turbopack dev server can take up to 60 seconds to compile on first run.
- `testDir: './e2e'` — we'll put all E2E tests in `frontend/e2e/`.

- [ ] **Step 5: Verify playwright config is valid**

```bash
cd frontend
npx playwright test --list
```

Expected: Output shows "No tests found" (we haven't written tests yet). No errors about config syntax.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/playwright.config.ts
git commit -m "feat: install Playwright + config for E2E tests (S14)"
```

---

## Task 4: E2E auth tests (login + register page render)

**Files:**
- Create: `frontend/e2e/auth.spec.ts`

These tests verify that the login and register pages render correctly. They don't require a running backend — the pages display their forms on mount without making any API calls.

Selectors used:
- `page.getByPlaceholder('simon@example.com')` → the email input on the login page
- `page.getByRole('button', { name: 'Se connecter' })` → the submit button on login page
- `page.getByText('Créer un compte')` → the link to register on login page
- `page.getByPlaceholder('Simon')` → the first_name input on register page
- `page.getByRole('button', { name: 'Créer mon compte' })` → submit button on register page
- `page.getByText('Se connecter')` → the link back to login on register page

- [ ] **Step 1: Create `frontend/e2e/` directory and `auth.spec.ts`**

Create `frontend/e2e/auth.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

test.describe("Login page", () => {
  test("renders login form with required fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByPlaceholder("simon@example.com")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Se connecter" })
    ).toBeVisible();
    await expect(page.getByText("Créer un compte")).toBeVisible();
  });
});

test.describe("Register page", () => {
  test("renders registration form with required fields", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByPlaceholder("Simon")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Créer mon compte" })
    ).toBeVisible();
    await expect(page.getByText("Se connecter")).toBeVisible();
  });
});
```

- [ ] **Step 2: Run the E2E tests**

```bash
cd frontend
npm run test:e2e
```

The first run starts `next dev` (Turbopack), waits up to 120 seconds for it to be ready, then runs the tests.

Expected output:
```
Running 2 tests using 1 worker

  ✓  [chromium] › auth.spec.ts:4:3 › Login page › renders login form... (Xs)
  ✓  [chromium] › auth.spec.ts:12:3 › Register page › renders registration form... (Xs)

  2 passed (Xs)
```

If a test fails:
- "Timeout waiting for element" → check the placeholder text matches exactly in `login/page.tsx` and `register/page.tsx`
- "net::ERR_CONNECTION_REFUSED" → the dev server didn't start; wait and retry, or increase `timeout` in `playwright.config.ts`

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/auth.spec.ts
git commit -m "test(e2e): add login + register page render tests (S14)"
```

---

## Task 5: E2E dashboard redirect tests

**Files:**
- Create: `frontend/e2e/dashboard.spec.ts`

These tests verify that protected routes redirect unauthenticated users to `/login`. The `dashboard/layout.tsx` uses `useEffect` + `router.push('/login')` when `localStorage.getItem('resilio_token')` is null. Playwright's `waitForURL` waits for the client-side redirect to complete.

The `beforeEach` clears localStorage by first navigating to `/login` (a public page) then calling `localStorage.clear()`. This ensures no leftover token from any previous test.

- [ ] **Step 1: Create `frontend/e2e/dashboard.spec.ts`**

```typescript
import { test, expect } from "@playwright/test";

test.describe("Protected routes — unauthenticated", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to a public page first (needed to execute JS on the domain)
    await page.goto("/login");
    // Clear any existing auth token
    await page.evaluate(() => localStorage.clear());
  });

  test("/dashboard redirects to /login when not authenticated", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await page.waitForURL("/login", { timeout: 5_000 });
    await expect(page).toHaveURL("/login");
  });

  test("/dashboard/calendar redirects to /login when not authenticated", async ({
    page,
  }) => {
    await page.goto("/dashboard/calendar");
    await page.waitForURL("/login", { timeout: 5_000 });
    await expect(page).toHaveURL("/login");
  });
});
```

- [ ] **Step 2: Run all E2E tests (auth + dashboard)**

```bash
cd frontend
npm run test:e2e
```

Expected output:
```
Running 4 tests using 1 worker

  ✓  [chromium] › auth.spec.ts:4:3 › Login page › renders login form... (Xs)
  ✓  [chromium] › auth.spec.ts:12:3 › Register page › renders registration form... (Xs)
  ✓  [chromium] › dashboard.spec.ts:11:3 › Protected routes › /dashboard redirects... (Xs)
  ✓  [chromium] › dashboard.spec.ts:19:3 › Protected routes › /dashboard/calendar redirects... (Xs)

  4 passed (Xs)
```

If the redirect tests fail with "Timeout":
- The `useEffect` redirect in `dashboard/layout.tsx` is async. Check that the layout uses `router.push('/login')` inside a `useEffect` — it does (as of S12). The 5-second timeout is generous.
- If Next.js dev server is slow to SSR, increase the `waitForURL` timeout to `8_000`.

- [ ] **Step 3: Verify backend tests still pass**

```bash
cd ..  # go back to project root
poetry run pytest --tb=short -q
```

Expected: All 157+ tests pass. No failures.

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e/dashboard.spec.ts
git commit -m "test(e2e): add protected route redirect tests (S14)"
```

---

## Task 6: README Quick Start + CLAUDE.md

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

Add a Quick Start section at the top of the README so a new developer can get the stack running in under 5 minutes. Then mark S14 done in CLAUDE.md.

- [ ] **Step 1: Read the current README.md**

```bash
head -20 README.md
```

Find the first `##` heading — the Quick Start section goes right after the intro paragraph (before the first `##` heading).

- [ ] **Step 2: Add Quick Start section to README.md**

Insert the following block right before the first `## 🧠 Architecture Multi-Agents` heading:

```markdown
## Quick Start

### With Docker (recommended)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
cp .env.example .env
# Edit .env: fill in ANTHROPIC_API_KEY (required for LLM agents)
docker compose up --build
```

- **API + OpenAPI docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

### Manual dev setup

```bash
# Backend
cp .env.example .env
poetry install
poetry run uvicorn api.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Run tests

```bash
# Backend unit tests (157+)
poetry run pytest

# Frontend E2E tests (requires Chromium — one-time install)
cd frontend
npx playwright install chromium
npm run test:e2e
```

---

```

- [ ] **Step 3: Update CLAUDE.md — mark S14 done**

In `CLAUDE.md`, find the session table row:

```
| **S14** | Intégration | Docker + tests E2E + polish | ⬜ À FAIRE |
```

Change it to:

```
| **S14** | Intégration | Docker + tests E2E + polish | ✅ FAIT |
```

Also update the repo structure section. Find:

```
├── frontend/                          ← ✅ S12 — Next.js 15 (TypeScript + Tailwind v4)
```

And update the tree to reflect S14 additions (after the `components/navbar.tsx` line):

```
├── frontend/                          ← ✅ S14 — Full-stack Docker + Playwright E2E
│   ├── Dockerfile                     ← ✅ S14 — Multi-stage (deps → builder → runner)
│   ├── playwright.config.ts           ← ✅ S14 — Playwright config (chromium + next dev)
│   ├── .env.local.example             ← ✅ S14 — NEXT_PUBLIC_API_URL doc
│   ├── e2e/
│   │   ├── auth.spec.ts               ← ✅ S14 — Login + register render tests
│   │   └── dashboard.spec.ts          ← ✅ S14 — Protected redirect tests
│   ├── package.json                   ← Next.js 15.5, React 19, Tailwind v4, Playwright
```

- [ ] **Step 4: Final verification — build + E2E + backend**

```bash
# 1. Frontend build (must still pass)
cd frontend && npm run build && cd ..

# 2. All E2E tests
cd frontend && npm run test:e2e && cd ..

# 3. Backend tests
poetry run pytest --tb=short -q
```

Expected: 
- `npm run build` — 0 errors, 10 routes
- `npm run test:e2e` — 4 passed
- `pytest` — 157+ passed, 0 failed

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: add Quick Start + mark S14 done in CLAUDE.md"
```

---

## Invariants post-S14

- `docker compose build` succeeds (db + api + frontend, ~4 min first run)
- `npm run test:e2e` — 4 tests pass (auth ×2, redirect ×2) in chromium
- `npm run build` — 0 TypeScript errors, 10 routes
- `npm run lint` — 0 ESLint warnings
- `poetry run pytest` — 157+ tests passing
- `NEXT_PUBLIC_API_URL` env var falls back to `http://localhost:8000/api/v1` when unset
