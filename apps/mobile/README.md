# @resilio/mobile — Expo SDK 55 + NativeWind v5

Application mobile iOS Resilio+ (Expo React Native).

**Statut :** Production-ready scaffold — Session FE-MOBILE-1 (2026-04-16)

---

## Stack

| Lib | Version | Rôle |
|---|---|---|
| Expo SDK | 55.x | Framework natif |
| React Native | 0.83.4 | Moteur RN |
| React | 19.2.4 | UI |
| Expo Router | 55.x | Navigation file-based |
| NativeWind | v5 preview | Tailwind v4 pour RN |
| expo-haptics | 55.x | Feedback haptique |
| expo-secure-store | 55.x | Stockage sécurisé (tokens) |
| react-native-reanimated | 4.x | Animations |
| react-native-gesture-handler | 2.x | Gestes |
| react-native-svg | 15.x | SVG (Circle composant) |

---

## Prérequis

1. **Compte Expo** (gratuit) — [expo.dev](https://expo.dev)
2. **Expo Go** sur iPhone — [App Store](https://apps.apple.com/app/expo-go/id982107779)
3. **EAS CLI** (pour builds cloud) :
   ```bash
   pnpm add -g eas-cli
   eas login
   ```

---

## Développement local (Windows + iPhone)

### Lancer l'app en dev

```bash
# Depuis la racine du monorepo
pnpm dev:mobile

# Ou directement
cd apps/mobile
pnpm dev
```

Metro démarre. Scanner le QR code avec Expo Go sur iPhone pour ouvrir l'app.

> **Note Windows :** Pas de simulateur iOS local. Dev via Expo Go uniquement.
> L'iPhone et l'ordinateur doivent être sur le même réseau Wi-Fi.

### TypeScript check

```bash
pnpm typecheck:mobile
# ou
cd apps/mobile && npx tsc --noEmit
```

---

## EAS Build (cloud macOS pour iOS)

### Preview (TestFlight interne)

```bash
pnpm build:mobile:ios:preview
# ou
cd apps/mobile && eas build --platform ios --profile preview
```

- Distribution : internal (invitations TestFlight)
- Build sur machines macOS EAS (cloud) — pas besoin de macOS local
- Auto-increment buildNumber

### Production (App Store)

```bash
pnpm build:mobile:ios:production
# ou
cd apps/mobile && eas build --platform ios --profile production
```

- Préreq : Apple Developer account ($99/an), App Store Connect configuré

### Profiles EAS disponibles

| Profile | Usage | Distribution |
|---|---|---|
| `development` | Dev client (remplace Expo Go) | internal |
| `preview` | TestFlight interne | internal |
| `production` | App Store | store |

---

## Structure

```
apps/mobile/
├── app/
│   ├── _layout.tsx           Root Stack + fonts + ThemeProvider
│   ├── index.tsx             Redirect → (auth)/login
│   ├── +not-found.tsx        404 screen
│   ├── (auth)/
│   │   └── login.tsx         Écran connexion
│   └── (tabs)/
│       ├── _layout.tsx       Tab navigator (4 onglets)
│       ├── index.tsx         Accueil (Readiness + prochaine séance)
│       ├── check-in.tsx      Check-in quotidien
│       ├── chat.tsx          Coach IA (placeholder FE-MOBILE-2)
│       └── profile.tsx       Profil athlète (placeholder FE-MOBILE-2)
├── ios-widget/               Scaffold expo-widgets (Session FE-MOBILE-WIDGET)
├── global.css                NativeWind v5 + Tailwind v4 directives
├── tailwind.config.js        Design tokens → classes Tailwind
├── metro.config.js           Metro + withNativewind + monorepo watchFolders
├── babel.config.js           babel-preset-expo (no jsxImportSource — v5)
├── postcss.config.mjs        @tailwindcss/postcss
├── eas.json                  EAS Build profiles
├── app.json                  Expo config (SDK 55, scheme resilio)
└── UI-RULES-MOBILE.md        Règles anti-drift pour sessions Claude Code
```

---

## Limitations connues

- **Pas de simulateur iOS sur Windows** — uniquement Expo Go via réseau local ou EAS Build
- **NativeWind v5 est en preview** — API peut changer avant release stable
- **expo-widgets en alpha** — widget iOS différé à Session FE-MOBILE-WIDGET
- **Auth non implémentée** — login fait un délai mock, redirige vers tabs
- **Pas testé sur device réel** — documenter les résultats après premier test

---

*Voir `UI-RULES-MOBILE.md` pour les règles de code. Voir `ios-widget/README.md` pour le widget.*
