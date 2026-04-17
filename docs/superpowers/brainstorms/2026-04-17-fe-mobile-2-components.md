# Brainstorm — FE-MOBILE-2 Component Specs

**Date:** 2026-04-17
**Session:** FE-MOBILE-2
**Author:** Claude Sonnet 4.6

---

## CognitiveLoadDial.tsx

**API:** `{ value: number, size?: number (default: 200), label?: string, state: 'green'|'yellow'|'red' }`

**SVG math:**
- Semi-arc = 180° arc from left endpoint to right endpoint, sweeping UPWARD (clockwise in SVG coords)
- Path: `M (strokeWidth/2, cy) A r r 0 0 1 (size-strokeWidth/2, cy)` where cy = radius + strokeWidth
- strokeDasharray = π * r; strokeDashoffset = π * r * (1 - value/100)
- SVG height = radius + strokeWidth (only upper half visible)
- Value displayed centered below arc apex, font size relative to size

**Color mapping:** green → zoneGreen, yellow → zoneYellow, red → zoneRed (from design-tokens)

**Naming note:** Component is `CognitiveLoadDial`, but UI label passed via `label` prop. Home screen passes `label="Charge allostatique"`.

**StyleSheet exception:** SVG wrapper requires StyleSheet.absoluteFill for centered value overlay.

**Edge cases:** value clamped to [0, 100]. Size < 60 may render poorly — min recommended = 120.

**Tests needed:** render value 0 / 50 / 100, each state color, label present/absent.

---

## SessionCard.tsx

**API:** `{ session: WorkoutSlotStub | null }`

**3 render states:**
1. `session === null` → "Repos programmé — aucune séance aujourd'hui" with `Icon.DarkMode`
2. `session.is_rest_day === true` → "Repos actif — récupération" with `Icon.Heart` (different from #1 — prescribed rest)
3. Normal session → sport icon + title + duration + zone badge

**Sport icon mapping:**
- `running` → `Icon.Activity` (no dedicated Running in lucide-react-native)
- `lifting` → `Icon.Lifting`
- `swimming` → `Icon.Swimming`
- `cycling` → `Icon.Biking`
- `rest` → `Icon.DarkMode`
- fallback → `Icon.Target`

**Composite of Card + Text + Icon — no new primitives.**

**Edge cases:** unknown sport type → fallback icon. Very long title → Text numberOfLines={2}.

**Tests:** null session, is_rest_day, each sport type (at least running + lifting), normal session with full data.

---

## MetricRow.tsx

**API:** `{ nutrition: { value: number, state: MetricState }, strain: { value: number, state: MetricState }, sleep: { value: number, state: MetricState } }`

**Layout:** `flexDirection: 'row'`, each column `flex: 1`, `alignItems: 'center'`

**Each column:** `<Circle size={80} value={m.value} color={stateColor(m.state)} />` + `<Text variant="caption">` label

**Color fn:** `(state: MetricState) => state === 'green' ? colors.zoneGreen : state === 'yellow' ? colors.zoneYellow : colors.zoneRed`

**Labels:** "Nutrition" / "Récupération musculaire" (abbreviated "Strain" in code, "Récup." in UI) / "Sommeil"

**Tests:** render with mixed states, each circle visible.

---

## ReadinessStatusBadge.tsx

**API:** `{ value: number }`

**Thresholds:**
- value >= 80 → "Optimal" + zoneGreen bg
- value >= 60 → "Prudent" + zoneYellow bg
- value < 60 → "Repos recommandé" + zoneRed bg

**Pill shape:** paddingHorizontal=12, paddingVertical=4, borderRadius=999

**Tests:** values 59 (red), 60 (yellow), 79 (yellow), 80 (green), edge cases.

---

## Home Screen layout (ASCII)

```
┌────────────────────────────────────┐
│ [Bannière "Repos recommandé"]      │  ← conditionnelle si readiness < 50
│  accessibilityRole="alert"         │
├────────────────────────────────────┤
│ Bonjour,                           │  ← greeting (mock name placeholder)
│ Résumé de coaching du jour         │
├────────────────────────────────────┤
│         ╭───────────╮              │
│        │  Readiness  │             │  ← Circle size=160
│        │     82      │             │
│         ╰───────────╯              │
│          [Optimal]                 │  ← ReadinessStatusBadge
├────────────────────────────────────┤
│  (●)       (●)       (●)           │  ← MetricRow (3x Circle size=80)
│ Nutrition Récup.  Sommeil          │
├────────────────────────────────────┤
│  ╭──────────────────────────────╮  │
│  │ Charge allostatique          │  │  ← CognitiveLoadDial in Card
│  │    [semi-arc SVG]            │  │    label="Charge allostatique"
│  │         28                   │  │
│  ╰──────────────────────────────╯  │
├────────────────────────────────────┤
│  ╭──────────────────────────────╮  │
│  │ Séance du jour               │  │  ← SessionCard
│  │ 🏃 Easy Run Z1 — 45 min     │  │
│  │ Zone 1 (60–74% FCmax)        │  │
│  ╰──────────────────────────────╯  │
├────────────────────────────────────┤
│     [ Check-in quotidien ]         │  ← Button primary
└────────────────────────────────────┘
```

*Bannière absente sur scenarios green (82) et yellow (61, rest day — readiness >= 50).*

---

*Implémenté en FE-MOBILE-2. Brainstorm préparatoire FE-MOBILE-1B: `2026-04-17-home-screen.md`.*
