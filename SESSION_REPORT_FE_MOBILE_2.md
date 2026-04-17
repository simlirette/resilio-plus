# Session Report — FE-MOBILE-2
**Date:** 2026-04-17  
**Branch:** `session/fe-mobile-2-home-screen`  
**Type:** Feature — Mobile Home Screen  
**Duration:** ~6h (split across two contexts)

---

## Objectives vs Delivered

| Objective | Status | Notes |
|---|---|---|
| CognitiveLoadDial component | ✅ | SVG semi-arc, 3 states, 8 tests |
| SessionCard component | ✅ | 5 sport types, rest day, no session, 9 tests |
| MetricRow component | ✅ | 3 Circle metrics, 3 tests |
| ReadinessStatusBadge component | ✅ | 3 tiers, pill badge, 7 tests |
| `useHomeData` hook | ✅ | mock stub, pull-to-refresh 500ms, 3 scenarios |
| Home screen `index.tsx` | ✅ | Full layout, banner < 50, haptics on refresh |
| Home screen tests (9) | ✅ | All 9 passing after jest harness fix |
| jest.app.config.js | ✅ | jest-expo preset for apps/mobile RN tests |
| `test:mobile:app` script | ✅ | wired in root package.json |
| Regression tests | ✅ | 7/7 passing (unchanged) |
| ui-mobile tests | ✅ | 69/69 passing |
| TypeScript | ✅ | 0 errors |

**Total tests: 85** (69 ui-mobile + 7 regression + 9 Home screen)

---

## New Components (packages/ui-mobile)

### CognitiveLoadDial
- SVG semi-arc (180° sweep), progress fill via strokeDashoffset
- Props: `value` (0–100), `size`, `label`, `state` (normal/caution/critical)
- Colors: zoneGreen / zoneYellow / zoneRed from design tokens
- StyleSheet exception documented: `absoluteFill` for SVG overlay

### SessionCard
- 3 states: `session=null`, `is_rest_day=true`, normal session
- `SportIcon` wrapper uses `IconComponent` (not `Icon.*`) to avoid TS2786
- Sport labels: running / lifting / swimming / cycling / rest

### MetricRow
- Row of 3 `Circle` components (size=80) with nutrition/récup/sommeil labels
- `accessibilityLabel` on wrapper View (Circle has no prop for it)

### ReadinessStatusBadge
- Pill badge: ≥80 green, ≥60 yellow, <60 red
- Uses semantic background tokens (zoneGreenBg, zoneYellowBg, zoneRedBg)

---

## Home Screen (apps/mobile/app/(tabs)/index.tsx)

Layout:
- Greeting with time of day
- Readiness circle (Circle size=160) + ReadinessStatusBadge below
- Rest banner when readiness < 50 (accessibilityRole="alert", clinical: show session anyway)
- MetricRow (nutrition / récup / sommeil)
- Card with CognitiveLoadDial (charge allostatique)
- SessionCard
- Check-in CTA button
- Pull-to-refresh with expo-haptics NotificationFeedbackType.Success

Key patterns:
- `<Screen>` (no scrollProp) + manual `<ScrollView>` with `<RefreshControl>`
- StyleSheet for `contentContainerStyle` (NativeWind can't style ScrollView layout props)
- All colors from `useTheme()` and `colors` object

---

## jest Harness — Root Cause Analysis

**Problem:** `Invariant Violation: __fbBatchedBridgeConfig is not set`

**Root cause:** pnpm creates TWO react-native instances (different peer dep hashes):
- `apps/mobile` → `react-native@0.83.4_@babel+_0e81f392...`
- `packages/ui-mobile` → `react-native@0.83.4_@babel+_392dc7d...`

jest-expo's preset (via `react-native/jest/setup.js`) mocks `NativeModules` only in the `_0e81f392...` instance. When `@resilio/ui-mobile` imports react-native, it gets `_392dc7d...` — unmocked → crash.

**Fix:** `moduleNameMapper` in `jest.app.config.js`:
```js
'^react-native$': '<rootDir>/node_modules/react-native/index.js',
'^react-native/(.*)': '<rootDir>/node_modules/react-native/$1',
```
Forces all `react-native` imports to apps/mobile's instance → same one mocked by preset.

**Second error after fix:** `Cannot read properties of undefined (reading 'screen')` in `Dimensions.js`

**Root cause 2:** `setup.ts` had a `jest.mock('TurboModuleRegistry', ...)` that returned `{ getConstants: () => ({ window, screen }) }`. But `NativeDeviceInfo.js` (RN 0.83.x) calls `TurboModuleRegistry.getEnforcing('DeviceInfo')` and expects `{ getConstants: () => ({ Dimensions: { window, screen } }) }`. Our naive mock had the wrong shape.

**Fix 2:** Removed the `jest.mock` call from `setup.ts`. The preset already provides correct `NativeModules.DeviceInfo.getConstants()` → `{ Dimensions: {...} }` via `jest/mocks/NativeModules.js`.

**Rule going forward:** Do NOT mock TurboModuleRegistry manually in `setupFilesAfterEnv`. The preset handles it correctly.

---

## Files Created / Modified

### New Files
- `packages/ui-mobile/src/components/CognitiveLoadDial.tsx`
- `packages/ui-mobile/src/components/SessionCard.tsx`
- `packages/ui-mobile/src/components/MetricRow.tsx`
- `packages/ui-mobile/src/components/ReadinessStatusBadge.tsx`
- `packages/ui-mobile/src/__tests__/CognitiveLoadDial.test.tsx`
- `packages/ui-mobile/src/__tests__/SessionCard.test.tsx`
- `packages/ui-mobile/src/__tests__/MetricRow.test.tsx`
- `packages/ui-mobile/src/__tests__/ReadinessStatusBadge.test.tsx`
- `apps/mobile/src/mocks/athlete-home-stub.ts` (committed prev session)
- `apps/mobile/src/types/home.ts`
- `apps/mobile/src/hooks/useHomeData.ts` (committed prev session)
- `apps/mobile/app/(tabs)/__tests__/index.test.tsx`
- `apps/mobile/jest.app.config.js`
- `apps/mobile/src/__tests__/setup.ts`
- `apps/mobile/src/__tests__/mocks/nativewind.ts`
- `apps/mobile/src/__tests__/mocks/turbo-module-registry.ts` (kept for reference, not active)
- `docs/superpowers/brainstorms/2026-04-17-fe-mobile-2-components.md`

### Modified Files
- `packages/ui-mobile/src/index.ts` — exports 4 new components + types
- `packages/ui-mobile/src/components/MetricRow.tsx` — accessibility fix
- `packages/ui-mobile/src/components/SessionCard.tsx` — style merge fix
- `apps/mobile/app/(tabs)/index.tsx` — full home screen rewrite
- `apps/mobile/package.json` — added jest-expo, react-test-renderer, @testing-library/react-native
- `package.json` — added `test:mobile:app` root script
- `pnpm-lock.yaml`

---

## Known Issues / Deferred

| Item | Status | Notes |
|---|---|---|
| Check-in screen navigation | Deferred FE-MOBILE-3 | Button wired but screen not built |
| Real API data | Deferred FE-MOBILE-BACKEND-WIRING | useHomeData returns mock always |
| Real auth | Deferred FE-MOBILE-5 | useHomeData has no auth |
| Loading skeleton | N/A | Mock data = instant, no empty state |
| Web build | Pre-existing failure | Unrelated to mobile work |

---

## Health Check

```
pnpm test:mobile       → 69/69 ✅
pnpm test:mobile:regression → 7/7 ✅
pnpm test:mobile:app   → 9/9 ✅
pnpm typecheck:mobile  → 0 errors ✅
```

**Next session: FE-MOBILE-3** — Check-in screen (daily form, readiness input, mood, notes)
