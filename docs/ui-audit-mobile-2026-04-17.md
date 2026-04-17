# UI Mobile Audit — 2026-04-17

Session: FE-MOBILE-1B | Branch: session/fe-mobile-1b-consolidation

---

## 1. File Inventory

### apps/mobile/app/

| File | Lines | Role | Status |
|---|---|---|---|
| `_layout.tsx` | 38 | Root layout: fonts, splash, ThemeProvider, Stack navigator | production |
| `index.tsx` | 6 | Redirect → /(auth)/login | production |
| `+not-found.tsx` | 26 | 404 screen | production |
| `(auth)/login.tsx` | 107 | Login screen: email/pwd, mock auth 800ms, French copy | production |
| `(tabs)/_layout.tsx` | 60 | Tabs navigator: 4 tabs (Accueil/Check-in/Coach/Profil) | production |
| `(tabs)/index.tsx` | 105 | Home screen: readiness card, session card, check-in CTA | production |
| `(tabs)/check-in.tsx` | 103 | Step check-in: energy + sleep questions, 2 steps | production |
| `(tabs)/chat.tsx` | 20 | Coach chat placeholder | placeholder |
| `(tabs)/profile.tsx` | 20 | Athlete profile placeholder | placeholder |
| `app/login.tsx.backup` | — | Pre-migration flat login (English copy, old router path) | backup (gitignored) |
| `app/dashboard.tsx.backup` | — | Pre-migration flat dashboard | backup (gitignored) |
| `app/check-in.tsx.backup` | — | Pre-migration flat check-in (English copy) | backup (gitignored) |

### packages/ui-mobile/src/

| File | Lines | Role | Status |
|---|---|---|---|
| `Icon.tsx` | 53 | Sole lucide-react-native importer. Object + name-prop API | production |
| `icons.ts` | 6 | Deprecated re-export shim → Icon.tsx | legacy (keep until FE-MOBILE-2 cleanup) |
| `index.ts` | 15 | Barrel exports | production |
| `theme/ThemeProvider.tsx` | 30 | React context: colorMode + colors (dark/light) | production |
| `theme/useTheme.ts` | 2 | Re-export useTheme | production |
| `components/Button.tsx` | 75 | Button: primary/secondary/ghost, haptics, loading | production |
| `components/Card.tsx` | 20 | Surface card: border + bg tokens | production |
| `components/Circle.tsx` | 78 | SVG progress ring: value 0–100, label | production |
| `components/Input.tsx` | 26 | Text input with label | production |
| `components/Screen.tsx` | 58 | Screen wrapper: safe area via useSafeAreaInsets | production |
| `components/Text.tsx` | 68 | Typography: display/title/body/caption/mono variants | production |

---

## 2. Rule Conformance

### Rule 1 — No direct `lucide-react` import outside `@resilio/ui-web`
✅ 0 violations

### Rule 2 — No direct `lucide-react-native` import outside `@resilio/ui-mobile`
✅ 0 violations in apps/mobile/. Only `packages/ui-mobile/src/Icon.tsx` imports it (correct).

### Rule 3 — No hardcoded hex colors
⚠️ 4 violations found:

| File | Line | Value | Context |
|---|---|---|---|
| `apps/mobile/app/(tabs)/index.tsx` | 77 | `#fff` | `<Icon.Energy color="#fff" ...>` |
| `apps/mobile/app/(tabs)/index.tsx` | 104 | `#fff` | StyleSheet `checkinButtonText.color` |
| `packages/ui-mobile/src/components/Button.tsx` | 51 | `#ffffff` | Primary button text color |
| `packages/ui-mobile/src/components/Button.tsx` | 63 | `#ffffff` | ActivityIndicator primary color |

**Decision:** Skip in this session (design decision needed — use `colors.primaryForeground`). Fix in FE-MOBILE-2.

### Rule 4 — API calls via `@resilio/api-client`
✅ No direct fetch() or axios in screens. Auth mock uses `setTimeout` (placeholder — known).

### Rule 5 — Dark mode variants
✅ All screens use `useTheme()` / `colorMode` pattern. No un-themed colors.

### Rule 6 — Conventional commits
✅ All commits from FE-MOBILE-1 follow convention.

### Rule 7 — Tests for shared-logic and api-client
⚠️ `@resilio/ui-mobile` has NO test suite yet. Created in Step 4.

### Rule 8 — No business logic in UI components
✅ Components are pure presentational. Auth mock is temporary screen logic (not in a component).

### Rule 9 — Icons via `@resilio/ui-mobile`
✅ All screens use `Icon.*` pattern correctly.

### Rule 10 — StyleSheet.create in screens (prefer NativeWind)
⚠️ All 6 screen files use `StyleSheet.create`. This is a known migration item (FE-MOBILE-2).
- Acceptable in `packages/ui-mobile/src/components/*` (no NativeWind available in package context).

### Rule 11 — SafeAreaView direct use
❌ 1 violation: `apps/mobile/app/(tabs)/check-in.tsx:2` imports `SafeAreaView` from `react-native` and uses it as screen wrapper. **Fixed in Step 2.**

### Rule 12 — Haptics on primary actions
✅ Button component integrates haptics for all variants.

### Rule 13 — No emoji in UI copy
✅ 0 emoji found in source files.

### Rule 14 — French (tu) copy
✅ All visible text is French. Backups had English (pre-migration) — irrelevant.

### Rule 15 — react-native-reanimated (not Animated classic)
✅ 0 uses of `import { Animated } from 'react-native'` in screens.

### Rule 16 — Fonts via expo-font (no @import url)
✅ `apps/mobile/global.css` has no `@import url()`. Only NativeWind/Tailwind directives.

### Rule 17 — Dark/light mode
✅ All screens and components handle both modes.

### Rule 18 — Navigation via expo-router
✅ All navigation uses `useRouter`, `Redirect`, `Link` from expo-router. No React Navigation direct.

---

## 3. Technical Debt

### Backup files (gitignored — local only)
| File | Age | Differs from current? | Action |
|---|---|---|---|
| `app/login.tsx.backup` | >24h (Apr 16) | YES (English copy, old router) | Flag only — rule says don't delete if different |
| `app/dashboard.tsx.backup` | >24h (Apr 16) | N/A (current file is `(tabs)/index.tsx`) | Flag only |
| `app/check-in.tsx.backup` | >24h (Apr 16) | YES (English copy) | Flag only |

**Note:** Backups differ from current files because they are pre-migration versions. Content is superseded (committed in git). Simon-Olivier should manually delete once satisfied with FE-MOBILE-2 device test.

### Deprecated files
- `packages/ui-mobile/src/icons.ts` — re-export shim, marked `@deprecated`. Remove in FE-MOBILE-2 when screens no longer import from `icons.ts`.

### Unused packages
- `react-native-css: "^3.0.7"` — appears in `apps/mobile/package.json` but is NOT imported anywhere in the codebase. Likely installed accidentally during SDK upgrade. Flag for removal in FE-MOBILE-2.

### TODOs/FIXMEs
✅ 0 found in source files.

### console.log
✅ 0 found.

### TypeScript `any`
✅ 0 found.

### Unused imports / variables
No obvious unused imports detected in manual review. ESLint run in Step 2 will confirm.

---

## 4. Version Health Check

| Package | Version in package.json | Notes |
|---|---|---|
| `expo` | `~55.0.15` | SDK 55 ✅ |
| `react-native` | `0.83.4` | Aligned with SDK 55 ✅ |
| `react` | `19.2.4` | Aligned with SDK 55 ✅ |
| `expo-router` | `~55.0.12` | SDK-aligned naming ✅ |
| `expo-font` | `~55.0.6` | SDK-aligned ✅ |
| `expo-haptics` | `~55.0.14` | SDK-aligned ✅ |
| `expo-splash-screen` | `~55.0.18` | SDK-aligned ✅ |
| `expo-status-bar` | `~55.0.5` | SDK-aligned ✅ |
| `expo-secure-store` | `~55.0.13` | SDK-aligned ✅ |
| `expo-linking` | `~55.0.13` | SDK-aligned ✅ |
| `nativewind` | `5.0.0-preview.3` | ⚠️ Preview — API may change. Monitor release. |
| `tailwindcss` | `^4.2.2` | Required by NativeWind v5 ✅ |
| `react-native-reanimated` | `4.2.1` | Compatible with RN 0.83 ✅ |
| `react-native-safe-area-context` | `5.6.2` | Compatible ✅ |
| `react-native-svg` | `~15.15.3` | Compatible ✅ |
| `react-native-gesture-handler` | `~2.30.1` | Compatible ✅ |
| `react-native-screens` | `~4.23.0` | Compatible ✅ |
| `react-native-css` | `^3.0.7` | ⚠️ Not used anywhere — orphan dep |
| `typescript` | `~5.9.3` | Latest TypeScript 5.x ✅ |
| `@types/react` | `~19.2.14` | Aligned with React 19.2 ✅ |

**No major-minor version mismatches detected between Expo packages.**

---

## 5. Bundler Warnings & Errors

See Step 3 for bundler dry-run results.
