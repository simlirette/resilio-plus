# S-5 Design Spec — Frontend Check-in + Energy Card

**Date:** 2026-04-12
**Branch:** session/s5-frontend-energy
**Status:** Implemented ✅

---

## Scope

Frontend-only session. Backend endpoints (V3-C) existed and were not modified.

### Pages Modified

| File | Change |
|---|---|
| `frontend/src/lib/api.ts` | Added 3 types + 3 API methods |
| `frontend/src/app/check-in/page.tsx` | Completed to 5 questions + real API call |
| `frontend/src/app/dashboard/page.tsx` | Added EnergyCard component |
| `frontend/src/app/energy/page.tsx` | Replaced mock-data with real API |
| `frontend/src/app/energy/cycle/page.tsx` | Replaced mock-data with static constants |
| `frontend/src/app/login/page.tsx` | Removed mock-data import |

---

## API Contract Used

```
POST /athletes/{id}/checkin   → ReadinessResponse (201)
GET  /athletes/{id}/readiness → ReadinessResponse
GET  /athletes/{id}/energy/history?days=N → EnergySnapshotSummary[]
```

### CheckInRequest (5 required fields + 2 optional)
```typescript
{
  work_intensity: 'light' | 'normal' | 'heavy' | 'exhausting'
  stress_level: 'none' | 'mild' | 'significant'
  legs_feeling: 'fresh' | 'normal' | 'heavy' | 'dead'
  energy_global: 'great' | 'ok' | 'low' | 'exhausted'
  cycle_phase?: 'menstrual' | 'follicular' | 'ovulation' | 'luteal' | null
  comment?: string | null   // max 140 chars
}
```

### ReadinessResponse
```typescript
{
  date: string
  objective_score: number     // 0–100
  subjective_score: number    // 0–100
  final_readiness: number     // 0–100
  divergence: number
  divergence_flag: 'none' | 'moderate' | 'high'
  traffic_light: 'green' | 'yellow' | 'red'
  allostatic_score: number    // 0–100
  energy_availability: number // kcal/kg FFM
  intensity_cap: number       // 0–1.0
  insights: string[]
}
```

---

## Decisions

### check-in/page.tsx
- Progressive disclosure: each question card becomes active only after the previous one is answered
- ProgressDots shows 4 segments (Q1–Q4 required, Q5 comment optional)
- Confirmation screen shows real ReadinessResponse: traffic_light dot, final_readiness score, insights, intensity cap
- cycle_phase question omitted from UI (optional backend field) — not exposed since there's no sex detection

### dashboard/page.tsx EnergyCard
- Loads `getReadiness()` in parallel with `getWeekStatus()`
- Three states: loading, no-checkin (404 → link to /check-in), loaded (shows score + insights)
- Shows up to 2 insights to keep card compact

### energy/page.tsx
- Uses `Promise.allSettled()` to load readiness + 7-day history independently
- 404 on readiness → "no check-in today" CTA
- History chart only shows allostatic_score (no HRV — not in EnergySnapshotSummary)
- Removed HRV/sleep stat cards (no data source); replaced with readiness + intensity_cap stats

### energy/cycle/page.tsx
- Mock data replaced with static CYCLE_PHASES + PHASE_DESCRIPTIONS constants
- Shows demo notice (J18 lutéale) — real cycle data requires hormonal profile API (GET not implemented)

---

## Invariants Verified
- `npx tsc --noEmit` → no errors
- `npm run build` → clean (17 static pages)
