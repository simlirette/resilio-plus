# Session 13 — Frontend: Weekly Review + Plan Detail Pages

## Goal

Add three new screens to the Resilio+ Next.js frontend:
1. **Weekly Review** — form to log completed workouts, calls POST /workflow/weekly-review, displays ACWR report
2. **Running Plan Detail** — full session breakdown (paces, distances, zones) from POST /plan/running
3. **Lifting Plan Detail** — full exercise prescription (Hevy-format) from POST /plan/lifting

Also update Navbar to surface the new Bilan link, and add deep-links from the calendar to the detail pages.

---

## Architecture

```
frontend/src/app/dashboard/
  weekly-review/page.tsx       ← form (add workouts) + submit → report card
  plan/running/page.tsx        ← full running plan detail
  plan/lifting/page.tsx        ← full lifting plan detail

frontend/src/components/navbar.tsx   ← +Bilan link
frontend/src/app/dashboard/calendar/page.tsx  ← +links to /plan/running + /plan/lifting
```

---

## Page 1: Weekly Review (`/dashboard/weekly-review`)

**Two panels:**

### Panel A — Workout logger

User builds a list of `ActualWorkout` objects:
- Select sport: `running` | `lifting`
- Select date: 7 date buttons (Mon–Sun of current week, ISO format)
- Completed toggle: yes/no
- If running + completed: `duration_min` (required), `distance_km` (optional), `avg_hr` (optional), `type` (easy/tempo/interval, optional)
- If lifting + completed: `session_type` (hypertrophy/strength/power, optional), `duration_min` (optional)
- "Ajouter" button → appends to workout list
- Workout list shows each entry as a chip with remove button

### Panel B — Submit + Report

"Soumettre le bilan" calls:
```
POST /workflow/weekly-review
{
  "athlete_state": <Simon demo state>,
  "actual_workouts": [ ...list from Panel A... ]
}
```

Response schema:
```typescript
interface WeeklyReport {
  agent: string;
  week_reviewed: number;
  completion_rate: number;       // 0.0–1.0
  sessions_completed: number;
  sessions_planned: number;
  trimp_total: number;
  acwr_before: number | null;
  acwr_after: number | null;
  adjustments: Adjustment[];
  next_week_notes: string;
}
interface Adjustment {
  type: "volume_reduction" | "rest_week" | "intensity_reduction" | "volume_increase";
  reason: string;
  pct?: number;
}
```

Report display:
- Completion rate: `X/Y séances` + coloured badge (green ≥0.8, yellow 0.6–0.8, red <0.6)
- TRIMP total
- ACWR: `before → after` with zone colour (green <1.3, yellow 1.3–1.5, red >1.5)
- Adjustments: labelled pills with icon (🔻 reduction, 🛑 rest, ⬆ increase)
- `next_week_notes`: italic coaching text block

---

## Page 2: Running Plan Detail (`/dashboard/plan/running`)

Calls POST /plan/running (Simon state) on mount. Displays:

**Header**: total weekly km, # sessions, phase/week

**Session cards** (one per session):
- Day + session type badge (Easy / Tempo / Interval / Long Run / Repetition)
- Distance + duration + target pace
- Full description text
- Zone badge (Z1 / Z2 / Z3)

**Coaching notes** section at bottom (array of strings from plan response)

**Back link** → `/dashboard/calendar`

---

## Page 3: Lifting Plan Detail (`/dashboard/plan/lifting`)

Calls POST /plan/lifting (Simon state) on mount. Displays:

**Header**: # sessions, split type, phase/week

**Session cards** (one per session):
- Day + session type badge (Upper Hypertrophy / Lower Strength / etc.)
- Exercise table: `Exercise | Sets × Reps | Weight | RPE | Rest`
- The exercises come from `session.hevy_workout.exercises` (Hevy format)
- If `hevy_workout` not present, fall back to `session.exercises` or show "Details unavailable"

**Coaching notes** at bottom

**Back link** → `/dashboard/calendar`

---

## Navbar update

Add "Bilan" link between "Calendrier" and "Chat" pointing to `/dashboard/weekly-review`.

Active state: `pathname.startsWith("/dashboard/weekly-review")`.

---

## Calendar page update

Add two buttons below the weekly grid (after plan is loaded):
- "Détail course →" → links to `/dashboard/plan/running`
- "Détail musculation →" → links to `/dashboard/plan/lifting`

---

## Files Summary

| File | Action |
|------|--------|
| `src/app/dashboard/weekly-review/page.tsx` | Create |
| `src/app/dashboard/plan/running/page.tsx` | Create |
| `src/app/dashboard/plan/lifting/page.tsx` | Create |
| `src/components/navbar.tsx` | Modify — add Bilan link |
| `src/app/dashboard/calendar/page.tsx` | Modify — add detail links |
| `CLAUDE.md` | Modify — S13 ✅ FAIT |

---

## Invariants post-S13

- `npm run build` in `frontend/` succeeds with 0 TypeScript errors
- `npm run lint` clean
- Weekly review form can submit with 0 workouts (empty list — still valid API call)
- ACWR zone colours: green = acwr < 1.3, yellow = 1.3–1.5, red > 1.5
- Plan detail pages load independently (no dependency on calendar state)
