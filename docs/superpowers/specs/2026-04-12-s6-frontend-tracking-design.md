# S-6 Frontend Tracking Page — Design Spec

**Date:** 2026-04-12  
**Branch:** `session/s6-frontend-tracking`  
**Status:** Approved for implementation

---

## Overview

Add a "Tracking Only" mode frontend: two protected pages (`/tracking` and `/tracking/import`) visible only when `coaching_mode === "tracking_only"`, plus a mode badge in TopNav. The backend ExternalPlan CRUD (S-1) is live; the import endpoint (S-2) is stubbed.

---

## Architecture

### 1. `frontend/src/lib/api.ts` — new types + methods

**New types:**
```ts
interface AthleteProfile { id: string; name: string; coaching_mode: 'full' | 'tracking_only'; /* other fields */ }
interface ExternalPlanOut { id: string; athlete_id: string; title: string; source: string; status: string; start_date: string | null; end_date: string | null; created_at: string; sessions: ExternalSessionOut[] }
interface ExternalSessionOut { id: string; plan_id: string; athlete_id: string; session_date: string; sport: string; title: string; description: string | null; duration_min: number | null; status: string }
interface ExternalPlanCreate { title: string; start_date?: string; end_date?: string }
interface ExternalSessionCreate { session_date: string; sport: string; title: string; description?: string; duration_min?: number }
interface ExternalSessionUpdate { session_date?: string; sport?: string; title?: string; description?: string; duration_min?: number; status?: 'planned' | 'completed' | 'skipped' }
interface ExternalPlanDraft { title: string; sessions_parsed: number; sessions: ExternalSessionCreate[]; parse_warnings: string[] }  // S-2 stub
```

**New methods on `api`:**
- `getAthleteProfile(athleteId)` → `GET /athletes/{id}` → `AthleteProfile`
- `getExternalPlan(athleteId)` → `GET /athletes/{id}/external-plan` → `ExternalPlanOut`
- `createExternalPlan(athleteId, data)` → `POST /athletes/{id}/external-plan` → `ExternalPlanOut`
- `addExternalSession(athleteId, data)` → `POST /athletes/{id}/external-plan/sessions` → `ExternalSessionOut`
- `updateExternalSession(athleteId, sessionId, data)` → `PATCH /athletes/{id}/external-plan/sessions/{id}` → `ExternalSessionOut`
- `deleteExternalSession(athleteId, sessionId)` → `DELETE /athletes/{id}/external-plan/sessions/{id}` → void
- `importExternalPlan(athleteId, file)` → **STUB** (returns mock `ExternalPlanDraft` after 800ms delay)
- `confirmImportExternalPlan(athleteId, draft)` → **STUB** (returns mock `ExternalPlanOut` after 500ms delay)

---

### 2. `frontend/src/lib/auth.tsx` — add `coachingMode`

```ts
interface AuthState {
  token: string | null
  athleteId: string | null
  coachingMode: 'full' | 'tracking_only' | null  // NEW
}
```

- On `useEffect` load: after restoring `token` + `athleteId` from localStorage, fetch `GET /athletes/{id}` to get `coaching_mode`. Store in state.
- On `login()`: fetch `GET /athletes/{id}` immediately after setting token, set `coachingMode`.
- localStorage key: `coaching_mode` (string) for fast bootstrap.
- Expose `coachingMode` in context value.

---

### 3. `frontend/src/components/top-nav.tsx` — mode badge + conditional link

- Read `coachingMode` from `useAuth()`
- When `coachingMode === 'tracking_only'`:
  - Show badge `TRACKING` (yellow/amber) next to logo
  - Add "Tracking" nav link pointing to `/tracking`
- When `coachingMode === 'full'` or null: no badge, no tracking link

---

### 4. `frontend/src/app/tracking/page.tsx` — ExternalPlan viewer

**Protection:** `ProtectedRoute` wrapper + redirect to `/dashboard` if `coachingMode !== 'tracking_only'`.

**States:**
- Loading: pulse skeleton
- No plan (404): card with "Aucun plan actif" + "Créer un plan" form (title, start_date, end_date)
- Loaded: plan header + sessions list

**Plan header:** title, source badge, date range, session count

**Sessions list:** grouped by week, sorted by date. Each row:
- Date (formatted fr-FR), sport chip, title, duration badge, status badge (planned/completed/skipped)
- Actions: "✓ Terminé" button (PATCH status=completed), "— Sauté" button (PATCH status=skipped)
- Both disabled if already completed/skipped

**Add session form:** collapsible at bottom — date picker, sport select, title input, duration number, submit → `addExternalSession()`

**Import link:** button "Importer un plan" → `/tracking/import`

---

### 5. `frontend/src/app/tracking/import/page.tsx` — File import (S-2 stub)

**Protection:** same as tracking/page.

**3-step flow:**

**Step 1 — Upload:**
- Drag & drop zone or file input (accept: `.pdf,.txt,.csv,.ics`)
- "Analyser avec IA" button → calls `importExternalPlan()` (stub)
- Visible stub notice: "Import IA non disponible (S-2 en cours) — données de démonstration"

**Step 2 — Preview draft:**
- Shows `ExternalPlanDraft.sessions_parsed` count, warnings list
- Table of sessions: date, sport, title, duration
- "Confirmer l'import" button → calls `confirmImportExternalPlan()` (stub)
- "← Retour" link

**Step 3 — Confirmed:**
- Success message + "Voir mon plan →" link to `/tracking`

---

## Stubs (S-2 not yet implemented)

Both import endpoints are stubbed in `api.ts`. The stub behavior:
- `importExternalPlan`: returns a mock draft with 3 sample sessions after 800ms
- `confirmImportExternalPlan`: returns a mock `ExternalPlanOut` after 500ms
- Both stubs log `[STUB] S-2 not implemented` to console

SESSION_REPORT.md will document these stubs.

---

## Invariants

- `cd frontend && npx tsc --noEmit` → 0 errors
- `cd frontend && npm run build` → clean build
- No backend changes
- No new npm packages (use existing shadcn/ui + lucide-react)
