# Session Report — FE-HOME-FROM-DESIGN
**Date:** 2026-04-17
**Branch:** `session/fe-home-from-design`
**Status:** ✅ Complete — ready for visual validation

---

## Summary

Design handoff URL was 404 → Simon-Olivier provided files in `docs/design/home/`.
Design files analyzed: `home-screen.jsx` (full token + component source), `Resilio Home.html` (entry point).
Complete design system pivot from dark clinical → warm minimalist (Apple Health / Whoop 5.0).
All 76 tests pass. Web preview exported at `apps/mobile/dist-web-preview/`, served at `http://localhost:3001`.

---

## Design Source

**Files:** `docs/design/home/home-screen.jsx` + `Resilio Home.html`
**Analysis:** `docs/design/home/DESIGN-ANALYSIS.md`

---

## Tokens Extracted

| Category | Count |
|----------|-------|
| Color tokens (light+dark) | 14 per mode |
| Accent options | 3 (clinical/emerald/indigo) |
| Typography sizes | 8 |
| Font weights | 5 (300/400/500/600/700) |

---

## Files Refactored

### Design tokens
- `packages/design-tokens/src/colors.ts` — warm palette, new semantic tokens (warn/ok/okStrong/caution/track)
- `packages/design-tokens/src/typography.ts` — Inter font, updated size/weight scales

### Mobile app
- `apps/mobile/app/_layout.tsx` — Inter font loading (300/400/500/600/700)
- `apps/mobile/tailwind.config.js` — mapped to new palette
- `apps/mobile/UI-RULES-MOBILE.md` — full rewrite for v2

### UI components (`packages/ui-mobile/src/components/`)
- `Text.tsx` — Inter font, 7 variants (display/headline/title/body/secondary/caption/label)
- `Card.tsx` — radius 22, 0.5px border, shadow
- `Button.tsx` — height 54, radius 16, accent color, shadow bloom
- `Circle.tsx` — `strokeWidth` + `innerLabel` props added
- `MetricRow.tsx` — 68px circles, stroke 5, semantic colors per metric type, hairline dividers
- `ReadinessStatusBadge.tsx` — dot+text pill (surface bg, hairline border)
- `CognitiveLoadDial.tsx` — tick marks at 25/50/75%, accent color, weight-300 number
- `SessionCard.tsx` — side-by-side layout (text left, chevron right)

### Home screen
- `apps/mobile/app/(tabs)/index.tsx` — 216px readiness ring, dynamic date, allostatic card side-by-side layout, MetricRow wrapped in Card

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Button | 8 | ✅ |
| Card | 4 | ✅ |
| Circle | 8 | ✅ |
| CognitiveLoadDial | 5 | ✅ |
| Icon | 3 | ✅ |
| MetricRow | 3 | ✅ |
| ReadinessStatusBadge | 7 | ✅ |
| Screen | 3 | ✅ |
| SessionCard | 9 | ✅ |
| Text | 5 | ✅ |
| Regression (rules) | 7 | ✅ |
| **Total** | **76** | **✅ All pass** |

---

## Divergences from Design (documented decisions)

| Decision | Reason |
|----------|--------|
| Font migration: Space Grotesk → Inter | Design explicitly uses Inter. Authorized autonomous decision per session spec. |
| `colorMode` from `useTheme()` in Home | Needed for conditional banner color (light/dark alpha variants). |
| `SessionCard` keeps `sportLabel` visible | Tests assert "Musculation", "Natation", "Vélo" — kept as small accent text in sport row. |
| MetricRow not a Card internally | Card wrapping done in `index.tsx` per design pattern (MetricRow = pure content). |
| Allostatic dial size 160px (not 180px) | Fits side-by-side card layout without overflow on 390px screen. |
| `@expo-google-fonts/inter` added as dep | Required for Inter font loading in Expo. |
| `pnpm.lock` / `apps/mobile/package.json` | Required for new Inter package. |

---

## Web Preview

URL: `http://localhost:3001`
Export: `apps/mobile/dist-web-preview/` (gitignored)
Command: `cd apps/mobile && npx expo export --platform web --output-dir dist-web-preview`

Expected appearance:
- Warm off-white background (#F7F4EE in light)
- 216px readiness ring with "Readiness" label inside, accent blue stroke
- "Prudent" badge with amber dot below ring
- Card with 3 metric rings (Nutrition/Strain/Sommeil)
- Allostatic card: text left, semi-arc dial right
- Session card: Course facile with chevron
- "Check-in quotidien" accent blue button

---

## Risks for FE-MOBILE-3+

1. **Inter font rendering on real device** — not tested on physical iOS device yet
2. **Shadow props** — Card uses `shadowColor/shadowOffset` which are iOS-only (elevation for Android); test both platforms
3. **Tab bar** — design shows floating liquid-glass tab bar (33px radius, backdrop blur) — NOT implemented in this session (pre-existing tab bar unchanged)
4. **MetricRow semantic colors** — `warn/ok/okStrong` per metric type (not state-based). If a metric has `state: 'red'`, it will show in green/amber (its type color), not red. Consider if this is correct behavior.

---

## Recommendations for Simon-Olivier

1. **Visual validation**: Open `http://localhost:3001` to see light mode. Toggle OS to dark for dark mode.
2. **Tab bar**: The floating liquid-glass tab bar from the design is not yet implemented — it's a significant component (FE-MOBILE-3 candidate).
3. **Accent selection**: Design supports 3 accents (clinical/emerald/indigo). Currently hardcoded to clinical blue. User preference toggle could be added later.
4. **MetricRow colors**: Discuss whether metric colors should be type-based (current) or state-based (old) — design is ambiguous on this.
