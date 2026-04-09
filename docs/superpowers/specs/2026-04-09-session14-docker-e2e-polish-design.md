# Session 14 — Docker Full-Stack + E2E Tests + Polish

## Goal

Make the full Resilio+ stack runnable with a single `docker compose up`, add Playwright E2E smoke tests for the Next.js frontend, and polish the API base URL configuration.

---

## Architecture

```
resilio-plus/
  docker-compose.yml        ← add frontend service
  frontend/
    Dockerfile              ← CREATE: multi-stage Next.js build
    playwright.config.ts    ← CREATE: webServer + chromium config
    .env.local.example      ← CREATE: document NEXT_PUBLIC_API_URL
    package.json            ← MODIFY: add @playwright/test + test:e2e script
    e2e/
      auth.spec.ts          ← CREATE: login + register page render tests
      dashboard.spec.ts     ← CREATE: protected redirect tests
    src/lib/api.ts          ← MODIFY: use NEXT_PUBLIC_API_URL env var
  README.md                 ← MODIFY: add Quick Start section
  CLAUDE.md                 ← MODIFY: S14 ✅ FAIT
```

---

## Part 1: Docker Full-Stack

### `frontend/Dockerfile` (multi-stage)

```dockerfile
# Stage 1 — deps
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# Stage 2 — builder
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# Stage 3 — runner
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

**Note on `standalone` output**: Requires `output: 'standalone'` in `next.config.ts`. This copies only the minimal server files.

### `next.config.ts` update

```typescript
const nextConfig: NextConfig = {
  output: 'standalone',
};
```

### `docker-compose.yml` — add frontend service

```yaml
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

**Why `http://localhost:8000/api/v1`**: The NEXT_PUBLIC_API_URL is embedded in the browser-side JS bundle. When a user opens the app in their browser (on the host machine), `localhost:8000` resolves to the API container via Docker's port mapping. This is correct for local dev.

---

## Part 2: E2E Tests (Playwright)

### Dependencies

Add to `frontend/package.json` devDependencies:
```json
"@playwright/test": "^1.50.0"
```

Add to scripts:
```json
"test:e2e": "playwright test",
"test:e2e:ui": "playwright test --ui"
```

Install chromium browser (one-time, not in Dockerfile):
```bash
npx playwright install chromium
```

### `frontend/playwright.config.ts`

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
```

**webServer uses `npm run dev`** (Turbopack) so no pre-build is required. `reuseExistingServer: true` means if port 3000 is already running, Playwright reuses it (useful during local dev).

### `frontend/e2e/auth.spec.ts`

Tests login and register pages render correctly without any API call:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Login page', () => {
  test('renders login form with required fields', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByPlaceholder('simon@example.com')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Se connecter' })).toBeVisible();
    await expect(page.getByText('Créer un compte')).toBeVisible();
  });
});

test.describe('Register page', () => {
  test('renders registration form with required fields', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByPlaceholder('Simon')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Créer mon compte' })).toBeVisible();
    await expect(page.getByText('Se connecter')).toBeVisible();
  });
});
```

### `frontend/e2e/dashboard.spec.ts`

Tests that protected routes redirect to `/login` when no token is in localStorage:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Protected routes — unauthenticated', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure localStorage is empty (no JWT token)
    await page.goto('/login');
    await page.evaluate(() => localStorage.clear());
  });

  test('/dashboard redirects to /login', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForURL('/login', { timeout: 5_000 });
    await expect(page).toHaveURL('/login');
  });

  test('/dashboard/calendar redirects to /login', async ({ page }) => {
    await page.goto('/dashboard/calendar');
    await page.waitForURL('/login', { timeout: 5_000 });
    await expect(page).toHaveURL('/login');
  });
});
```

---

## Part 3: Polish

### `frontend/src/lib/api.ts` — env var for API base

Replace hardcoded URL:
```typescript
// Before
const API_BASE = "http://localhost:8000/api/v1";

// After
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
```

### `frontend/.env.local.example`

```bash
# Copy to .env.local for local development overrides
# Default: http://localhost:8000/api/v1 (no override needed for standard local dev)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### `README.md` — Quick Start section

Add at the top (after the title block), before the Architecture section:

```markdown
## Quick Start

### With Docker (recommended)

Prerequisites: Docker Desktop

\```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY in .env
docker compose up --build
\```

- API: http://localhost:8000/docs (OpenAPI)
- Frontend: http://localhost:3000

### Manual dev setup

\```bash
# Backend
cp .env.example .env
poetry install
poetry run uvicorn api.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
\```

### Run tests

\```bash
# Backend unit tests (157+)
poetry run pytest

# Frontend E2E tests (Playwright)
cd frontend
npx playwright install chromium   # one-time
npm run test:e2e
\```
```

---

## Invariants post-S14

- `docker compose build` succeeds (all 3 services: db, api, frontend)
- `npm run test:e2e` passes — 4 tests (auth ×2, redirect ×2)
- `npm run build` still passes — 0 TypeScript errors
- `npm run lint` clean
- `poetry run pytest` still 157+ tests passing
- `NEXT_PUBLIC_API_URL` falls back to `http://localhost:8000/api/v1` if not set

---

## Files Summary

| File | Action |
|------|--------|
| `frontend/Dockerfile` | Create — multi-stage Next.js (deps → builder → runner) |
| `frontend/next.config.ts` | Modify — add `output: 'standalone'` |
| `docker-compose.yml` | Modify — add frontend service with build arg |
| `frontend/playwright.config.ts` | Create — chromium + webServer dev |
| `frontend/e2e/auth.spec.ts` | Create — login + register render tests |
| `frontend/e2e/dashboard.spec.ts` | Create — protected redirect tests |
| `frontend/package.json` | Modify — @playwright/test + test:e2e scripts |
| `frontend/src/lib/api.ts` | Modify — NEXT_PUBLIC_API_URL env var |
| `frontend/.env.local.example` | Create — document env var |
| `README.md` | Modify — Quick Start section |
| `CLAUDE.md` | Modify — S14 ✅ FAIT |
