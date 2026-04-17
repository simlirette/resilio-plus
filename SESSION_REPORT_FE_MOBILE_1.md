# Session Report — FE-MOBILE-1
**Date :** 2026-04-16  
**Branche :** `session/fe-mobile-1-upgrade-setup`  
**Auteur :** Claude Sonnet 4.6 (autonome)

---

## Status

**✅ Done** — tous les objectifs atteints, sauf une note sur la validation device réel.

---

## Résumé

Upgrade complet d'`apps/mobile` de Expo SDK 52 à SDK 55 (React Native 0.83.4, React 19.2.4) via 3 sauts incrémentaux avec commits intermédiaires. NativeWind v5 installé et configuré (Tailwind v4, postcss, tailwind.config, metro withNativeWind). L'app directory a été restructuré en groupes `(auth)/` et `(tabs)/` avec 4 onglets (Accueil, Check-in, Coach, Profil). Six nouveaux composants ui-mobile créés (Icon, Screen, Text, Card, Circle, Button+haptics). Scaffold `ios-widget/`, `eas.json`, `UI-RULES-MOBILE.md` et scripts root ajoutés.

---

## Versions avant / après

| Lib | Avant | Après |
|---|---|---|
| Expo SDK | ~52.0.0 | ~55.0.27 |
| React Native | 0.76.5 | 0.83.4 |
| React | 18.3.1 | 19.2.4 |
| expo-router | ~4.0.0 | ~55.0.12 |
| NativeWind | non installé | v5 (5.0.0-preview.3) |
| Tailwind CSS | non installé | v4 (4.2.x) |
| react-native-reanimated | non installé | 4.2.1 |
| expo-haptics | non installé | ~55.0.14 |
| expo-secure-store | non installé | ~55.0.13 |
| react-native-gesture-handler | non installé | ~2.30.1 |
| @expo-google-fonts/space-grotesk | non installé | ^0.4.1 |
| TypeScript | ~5.3.3 | ~5.9.3 |

---

## Breaking Changes par saut de SDK

### SDK 52 → 53 (expo 53.0.27)
- React 18.3.1 → **React 19.0.0** — peer deps lucide-react-native stale (avertissement seul, runtime OK)
- react-native 0.76.5 → **0.79.6**
- expo-router 4.0 → **5.1** — API tabs inchangée
- `@types/react-native` **déprécié** — supprimé (built-in types depuis RN 0.73)

### SDK 53 → 54 (expo 54.0.33)
- react-native 0.79.6 → **0.81.5**
- expo-router 5.1 → **6.0** (puis 55.x)
- expo-font 13.x → **14.x** (puis 55.x)
- expo-splash-screen 0.30 → **31.x** (rebranded, même API)

### SDK 54 → 55 (expo 55.0.15)
- react-native 0.81.5 → **0.83.4**
- React 19.1 → **19.2.4**
- expo-router renuméroté → **~55.0.12** (aligned with SDK number)
- expo-font → **~55.0.6**, expo-splash-screen → **~55.0.18** (same pattern)
- expo-linking ajouté explicitement → **~55.0.0** (requis par expo-router 55)
- `SafeAreaView` de react-native-safe-area-context incompatible React 19 JSX types → remplacé par `useSafeAreaInsets` dans Screen.tsx

---

## Décisions autonomes prises

| Décision | Justification |
|---|---|
| NativeWind v5 babel sans `jsxImportSource` | Docs v5 officiels : l'option jsxImportSource est un pattern v4, **retiré en v5** (task instructions basées sur version plus ancienne) |
| Metro `withNativeWind(config)` sans `{ input: "./global.css" }` | Docs v5 : option `input` n'existe pas dans withNativeWind v5 (seuls `globalClassNamePolyfill` et `typescriptEnvPath`) |
| `useSafeAreaInsets` au lieu de `SafeAreaView` dans Screen.tsx | SafeAreaView de react-native-safe-area-context a une incompatibilité de types avec React 19 (ReactPortal.children manquant). useSafeAreaInsets est la méthode moderne recommandée |
| `@expo-google-fonts/space-grotesk` + `space-mono` | Fonts Space Grotesk/Mono bundlées localement via expo-font (règle 16 — pas de `@import url()` Google Fonts CDN) |
| `IconComponent` export distinct de `Icon` objet | Rétrocompatibilité avec écrans existants qui utilisent `Icon.Heart`. La nouvelle API `<IconComponent name="Heart">` est additionnelle, pas un remplacement |
| `icons.ts` gardé (re-export deprecated) | Backward compat — sera nettoyé en Session FE-MOBILE-2 |
| Copy French dans nouveaux écrans | Règle 14 mobile. L'ancien check-in.tsx avait de l'anglais (corrigé dans (tabs)/check-in.tsx) |
| No emoji dans (tabs)/index.tsx | Dashboard original avait "Good morning 👋" — supprimé (règle 13) |

---

## Dette technique créée

| Item | Sévérité | Description |
|---|---|---|
| `app/login.tsx.backup`, `app/dashboard.tsx.backup`, `app/check-in.tsx.backup` | ℹ️ | Backups des fichiers plats originaux. À supprimer après confirmation boot sur device. |
| `icons.ts` re-export deprecated | ℹ️ | Maintenu pour backward compat. Supprimer en Session FE-MOBILE-2 en migrant les écrans vers `Icon.tsx`. |
| Auth mock (800ms delay) | ⚠️ | Login ne se connecte pas au backend. À implémenter avec `@resilio/api-client` + `expo-secure-store`. |
| NativeWind v5 preview | ⚠️ | Version 5.0.0-preview.3 — API peut changer. Tester à chaque mise à jour NativeWind. |
| Web build failure (pre-existing) | ⚠️ | `@ts-expect-error ReactNode mismatch` dans ThemeProvider web. **Présent sur main avant cette session**, pas une régression. À corriger en Session F5. |
| `pnpm approve-builds` requis | ℹ️ | sharp@0.34.5 nécessite un approve builds. Résolu en session mais à ajouter en CI. |
| Chat/Profile placeholders | ℹ️ | Les onglets Coach et Profil sont des placeholders. À implémenter en Session FE-MOBILE-2. |

---

## Prochaines étapes recommandées (ordre de priorité)

### Session FE-MOBILE-2 — Home Screen complet

1. Implémenter l'écran Accueil avec `<Circle>` pour Readiness + 3 sous-métriques (HRV, Sommeil, Strain)
2. Connecter à `/api/v1/athletes/{id}/readiness/current` via `@resilio/api-client`
3. Implémenter l'auth réelle (JWT → expo-secure-store, refresh tokens)
4. Migrer les écrans existants de `StyleSheet` vers `className` NativeWind
5. Supprimer `icons.ts` deprecated, `*.backup` files
6. Implémenter les onglets Chat et Profil

### Session FE-MOBILE-3 — Tests + ESLint

1. Tests render basiques pour tous les composants `@resilio/ui-mobile`
2. ESLint rules mobile (no-direct-lucide-react-native, no-hardcoded-colors)
3. Nettoyer la web ThemeProvider `@ts-expect-error` (Session F5)

---

## Comment tester (Simon-Olivier, Windows + iPhone)

### Prérequis

1. Node.js installé, pnpm 10.x installé
2. Expo Go sur iPhone (App Store)
3. PC et iPhone sur le même réseau Wi-Fi

### Lancer l'app

```bash
# À la racine du repo
pnpm dev:mobile
```

Metro démarre. Un QR code s'affiche dans le terminal.

**Scanner le QR code** avec l'app appareil photo iOS (ou Expo Go directement).

L'app s'ouvre dans Expo Go. Tu devrais voir :
- Écran de connexion RESILIO+ avec champs email/mot de passe
- Après saisie + "Se connecter" → redirection vers les 4 onglets (Accueil, Check-in, Coach, Profil)
- Onglet Accueil : score Readiness 75 + prochaine séance
- Onglet Check-in : questions énergie + sommeil avec progression

### TypeScript check

```bash
pnpm typecheck:mobile
# Expected output: rien (zero error)
```

### Commande complète de validation

```bash
pnpm install && pnpm typecheck:mobile && pnpm lint
```

---

## Fichiers modifiés par cette session

**apps/mobile/**
- `package.json` — SDK upgrades + NativeWind + core libs
- `app.json` — expo-secure-store plugin ajouté par expo install
- `metro.config.js` — withNativewind wrapper
- `babel.config.js` — commentaire NativeWind v5
- `tsconfig.json` — include nativewind-env.d.ts
- `global.css` — NativeWind/Tailwind v4 directives (nouveau)
- `postcss.config.mjs` — @tailwindcss/postcss (nouveau)
- `tailwind.config.js` — design tokens mappés (nouveau)
- `eas.json` — 3 profils EAS Build (nouveau)
- `README.md` — documentation complète
- `UI-RULES-MOBILE.md` — règles anti-drift (nouveau)
- `app/_layout.tsx` — useFonts SpaceGrotesk/Mono + SplashScreen
- `app/index.tsx` — redirect → /(auth)/login
- `app/+not-found.tsx` — 404 screen (nouveau)
- `app/(auth)/login.tsx` — login migré, copy française
- `app/(tabs)/_layout.tsx` — Tabs navigator 4 onglets (nouveau)
- `app/(tabs)/index.tsx` — Home screen (ex-dashboard)
- `app/(tabs)/check-in.tsx` — Check-in migré, copy française
- `app/(tabs)/chat.tsx` — placeholder (nouveau)
- `app/(tabs)/profile.tsx` — placeholder (nouveau)
- `ios-widget/README.md` — scaffold Widget (nouveau)

**packages/ui-mobile/**
- `package.json` — peer deps React 19 + RN 0.83
- `src/Icon.tsx` — abstraction lucide-react-native (nouveau)
- `src/icons.ts` — deprecated re-export
- `src/index.ts` — barrel exports mis à jour
- `src/components/Button.tsx` — ghost variant + expo-haptics
- `src/components/Screen.tsx` — useSafeAreaInsets (nouveau)
- `src/components/Text.tsx` — variants display/title/body/caption/mono (nouveau)
- `src/components/Circle.tsx` — SVG progress ring (nouveau)

**Racine**
- `package.json` — scripts mobile ajoutés
- `frontend-master-v1.md` — Sessions FE-MOBILE-2 + FE-MOBILE-WIDGET ajoutées au backlog
- `pnpm-lock.yaml` — mis à jour
