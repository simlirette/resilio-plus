# @resilio/mobile - Expo SDK 55

Application mobile iOS Resilio+ (Expo React Native).

**Statut actuel : boucle mobile quotidienne partiellement fonctionnelle.**
Les assets Expo, le tooling, la session mobile, l'accueil backend et le check-in
quotidien sont branches. Les parcours nutrition journalisee, detail de seance,
connecteurs et coach doivent encore etre completes dans les phases suivantes.

## Stack

| Lib | Version cible | Role |
|---|---:|---|
| Expo SDK | 55.x | Framework natif |
| React Native | 0.83.4 | Moteur RN |
| React | 19.2.4 | UI |
| Expo Router | 55.x | Navigation file-based |
| NativeWind | 5.0.0 preview | Styling RN |
| expo-secure-store | 55.x | Stockage securise des tokens |

La source de verite des versions est `apps/mobile/package.json` avec
`pnpm-lock.yaml`. Si `node_modules` diverge, relancer l'installation depuis la
racine du monorepo.

## Commandes officielles

Depuis la racine du monorepo:

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm dev:mobile
corepack pnpm typecheck:mobile
corepack pnpm test:mobile:app
corepack pnpm test:mobile:regression
```

Sur Windows PowerShell, si les scripts `.ps1` sont bloques, utiliser les
executables `.cmd`:

```powershell
corepack.cmd pnpm install --frozen-lockfile
corepack.cmd pnpm dev:mobile
npx.cmd tsc --noEmit
npx.cmd jest --config jest.app.config.js --runInBand
```

## EAS Build

Preview/TestFlight interne:

```bash
corepack pnpm build:mobile:ios:preview
```

Production App Store:

```bash
corepack pnpm build:mobile:ios:production
```

Profiles disponibles dans `eas.json`:

| Profile | Usage | Distribution |
|---|---|---|
| `development` | Dev client | internal |
| `preview` | TestFlight interne | internal |
| `production` | App Store | store |

## Structure

```text
apps/mobile/
  app/
    _layout.tsx
    index.tsx
    (auth)/login.tsx
    (tabs)/index.tsx
    (tabs)/check-in.tsx
    (tabs)/chat.tsx
    (tabs)/profile.tsx
  assets/
    icon.png
    splash.png
    adaptive-icon.png
  src/
    hooks/useHomeData.ts
    mocks/athlete-home-stub.ts
    types/home.ts
```

## Realite produit au 2026-04-26

- Auth mobile: branchee a `/auth/login`, `/auth/refresh`, `/auth/logout` et `/auth/me`.
- Session: tokens stockes dans SecureStore, refresh au bootstrap, guards sur les routes privees.
- Home mobile: branchee a `GET /mobile/home`, avec etats vides quand une mesure manque.
- Check-in mobile: soumet le schema backend `CheckInInput`.
- Profil: vue session minimale avec logout.
- Chat: placeholder.
- Assets Expo: presents depuis la Phase 0.
- Test device reel: a valider apres premier build TestFlight.

La source de verite MVP est `docs/MOBILE_TESTFLIGHT_MVP.md`.
