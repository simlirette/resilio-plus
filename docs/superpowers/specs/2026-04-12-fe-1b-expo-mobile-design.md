# FE-1B: Expo Mobile Scaffold Design

**Date:** 2026-04-12
**Session:** fe-1b-expo-mobile
**Status:** Implemented

## Scope

Scaffold `apps/mobile/` (Expo SDK 52, iOS V1) and fill `packages/ui-mobile/` with
usable components. Files created manually (no create-expo-app) for monorepo control.

## Styling Decision: StyleSheet RN (not NativeWind)

**Chosen:** `StyleSheet.create()` from React Native.

**Why:**
- Zero extra Babel config — NativeWind v4 requires babel plugin that conflicts with monorepo hoisting
- Design tokens are JS objects; `colors.dark.surface2` maps directly to `StyleSheet`
- `StyleSheet.create()` is optimized (runs at startup, not per-render)

## Architecture

### apps/mobile/

```
app/
  _layout.tsx     — Stack + ThemeProvider root
  index.tsx       — Redirect → /login
  login.tsx       — Email/password + Resilio+ wordmark
  dashboard.tsx   — Readiness card (75) + Prochaine séance card (mocked)
  check-in.tsx    — 2-question wizard with progress bar
app.json          — name "Resilio+", slug "resilio-plus", bundleId "com.resilio.plus"
metro.config.js   — Monorepo-aware (watchFolders + nodeModulesPaths)
tsconfig.json     — Extends expo/tsconfig.base, paths for all @resilio/* packages
babel.config.js   — babel-preset-expo only
expo-env.d.ts     — Expo Router types reference
```

### packages/ui-mobile/

```
src/
  icons.ts               — lucide-react-native mappings (mirrors ui-web)
  theme/
    ThemeProvider.tsx    — Context + useTheme + dark/light via useColorScheme
    useTheme.ts          — Re-export
  components/
    Button.tsx           — primary/secondary variants, loading state
    Card.tsx             — surface2 + border, 16px radius
    Input.tsx            — labeled text input
  index.ts               — All exports
```

## Key Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| Styling | StyleSheet RN | Zero config, tokens map to JS values |
| Navigation | Expo Router v4 file-based | Ships with SDK 52, no extra setup |
| Theme | RN `useColorScheme` hook | Zero deps, auto dark/light |
| Types | `@types/react@~18.3.12` in ui-mobile devDeps | Prevents React 18/19 type conflict in monorepo |
| Forms | Controlled `useState` | 2 fields on login, no form library needed |

## Monorepo Integration

- `metro.config.js` adds `watchFolders: [workspaceRoot]` + `nodeModulesPaths` for pnpm
- `tsconfig.json` paths map all `@resilio/*` to source files
- `packages/ui-mobile/package.json` has `@types/react@~18.3.12` in devDeps to pin React 18 types locally

## Root Scripts Added

- `build:mobile:ios` → `pnpm --filter @resilio/mobile build:ios` → `eas build --platform ios`

## Invariants Verified

- `pnpm install` ✅
- `apps/mobile/ npx tsc --noEmit` ✅ clean
- `pnpm --filter @resilio/web build` ✅ no regression
