# SESSION PLAN — S-5 Frontend Check-in + Energy Card

**Date:** 2026-04-12
**Branch:** session/s5-frontend-energy
**Invariant:** `npx tsc --noEmit` passes, `npm run build` succeeds

---

## Context

Backend endpoints already exist (V3-C):
- `POST /athletes/{id}/checkin` → ReadinessResponse (201)
- `GET /athletes/{id}/readiness` → ReadinessResponse
- `GET /athletes/{id}/energy/history` → list[EnergySnapshotSummary]

TopNav already has `/energy` and `/check-in` links.
`energy/page.tsx` currently imports from non-existent `mock-data/simon` — must fix.
`check-in/page.tsx` exists with 2 questions, no API call — must complete to 5 questions + wire API.

---

## Tasks

### Task 1: api.ts — Add types + 3 functions
- `CheckInRequest` interface (5 fields + optional cycle_phase + comment)
- `ReadinessResponse` interface
- `EnergySnapshotSummary` interface
- `api.submitCheckin(athleteId, data)` → POST /athletes/{id}/checkin
- `api.getReadiness(athleteId)` → GET /athletes/{id}/readiness
- `api.getEnergyHistory(athleteId, days?)` → GET /athletes/{id}/energy/history

### Task 2: check-in/page.tsx — Complete 5-question form + API wire
Current state: 2 questions (work_intensity, stress_level), no API call.
Add:
- Q3: legs_feeling (fresh/normal/heavy/dead)
- Q4: energy_global (great/ok/low/exhausted)
- Q5: comment (optional text, max 140 chars)
- useAuth() for athleteId
- Call api.submitCheckin() on submit
- Show real ReadinessResponse on confirmation (traffic_light, final_readiness, insights)
- Handle loading/error states

### Task 3: dashboard/page.tsx — Add EnergyCard
- Load readiness via api.getReadiness(athleteId) alongside week-status
- EnergyCard component: traffic_light dot, final_readiness score, insights list
- Graceful 404 → show "No check-in today" with link to /check-in
- 401 → logout + redirect

### Task 4: energy/page.tsx — Replace mock-data with real API
- Remove import from non-existent mock-data/simon
- Load via api.getReadiness() + api.getEnergyHistory(28 days)
- Map ReadinessResponse fields to existing UI structure
- Loading/error/empty states
- energy/cycle/page.tsx may also need fix

### Task 5: tsc verification + npm run build

---

## Data Mapping

ReadinessResponse → energy/page.tsx UI:
- `allostatic_score` → AllostaticGauge
- `energy_availability` → EnergyAvailabilityCard
- `traffic_light` → VetoStatus banner (green/yellow/red)
- `intensity_cap` → VetoStatus intensity cap
- `insights` → bullet list
- `final_readiness` → stat card

EnergySnapshotSummary[] → 7-day chart:
- `date` → XAxis label (last 2 chars or dd/MM)
- `allostatic_score` → allostatic chart line
- No HRV data in history endpoint → show single chart or hide HRV

---

## Notes
- cycle_phase question only shown if user is female (we don't have that context easily) → make it optional/hidden by default, show as collapsible "optional" section
- If athleteId is null (not logged in) on check-in page → redirect to /login
- energy/page.tsx uses ProtectedRoute pattern — check if it uses it; it doesn't currently, energy page has no ProtectedRoute wrapper. Keep consistent with dashboard (add ProtectedRoute or use useAuth redirect).
