# frontend-master-v1.md — Resilio+ Frontend Architecture

**Version:** 1.0 — Session 0 (2026-04-12)  
**Auteur:** Session frontend-s0-monorepo-setup  
**Référence principale pour tout le code frontend.**

---

## 1. Architecture Monorepo

### Structure cible (Session 0 complétée)

```
resilio-plus/
├── apps/
│   ├── web/            — Next.js 16 (React 19) — @resilio/web
│   ├── desktop/        — Tauri wrapper (scaffold Vague 1)
│   └── mobile/         — Expo React Native iOS (scaffold Vague 1)
├── packages/
│   ├── design-tokens/  — Tokens bruts (couleurs, typo, spacing, ...) — @resilio/design-tokens
│   ├── ui-web/         — Composants React + abstractions icônes — @resilio/ui-web
│   ├── ui-mobile/      — Composants React Native (skeleton) — @resilio/ui-mobile
│   ├── api-client/     — Client TypeScript généré depuis OpenAPI — @resilio/api-client
│   ├── shared-logic/   — Logique métier pure (zéro UI) — @resilio/shared-logic
│   └── brand/          — Logo, BRAND.md, identité — @resilio/brand
├── pnpm-workspace.yaml
├── package.json        — Scripts monorepo root
├── frontend-master-v1.md  ← CE FICHIER
├── FRONTEND_AUDIT.md   — Audit Session 0 (référence)
└── CLAUDE.md
```

### Gestionnaire de paquets

- **pnpm 10.33.0** — workspace hoisting, fast install, strict peer deps
- `pnpm install` à la racine — installe tous les workspaces
- `pnpm --filter @resilio/web <script>` — exécute un script dans un workspace spécifique

---

## 2. Design System

### Tokens (`@resilio/design-tokens`)

| Module | Contenu |
|---|---|
| `colors.ts` | Palette dark + light, accent, zones (green/yellow/red), phases cycle |
| `typography.ts` | Space Grotesk + Space Mono, tailles, poids, line-heights |
| `spacing.ts` | Échelle 4/8/12/16/24/32/48/64 px |
| `radius.ts` | 4/8/12/16/full px |
| `shadows.ts` | 4 niveaux d'élévation (dark + light) |
| `animation.ts` | Durées fast/normal/slow, courbes easing |

### Règle absolue #1 — Jamais d'import direct de `lucide-react`
```ts
// ❌ INTERDIT
import { Trash2 } from 'lucide-react';

// ✅ CORRECT
import { Icon } from '@resilio/ui-web';
const DeleteIcon = Icon.Delete;
```

### Règle absolue #2 — Jamais d'import direct de `lucide-react-native`
```ts
// ❌ INTERDIT
import { Trash2 } from 'lucide-react-native';

// ✅ CORRECT
import { Icon } from '@resilio/ui-mobile';
```

### Règle absolue #3 — Jamais de valeur de couleur hardcodée hors `@resilio/design-tokens`
```ts
// ❌ INTERDIT
style={{ background: '#14141f', color: '#eeeef4' }}

// ✅ CORRECT — CSS variables (auto-switch dark/light)
style={{ background: 'var(--card)', color: 'var(--foreground)' }}

// ✅ CORRECT — depuis design-tokens
import { colors } from '@resilio/design-tokens';
style={{ background: colors.dark.surface2 }}
```

**Exception autorisée :** Les couleurs de zone statique (green/yellow/red) qui ne varient pas entre dark/light peuvent rester hardcodées ou utiliser les tokens de zone.

### Dark Mode

- Implémentation : `next-themes` avec `attribute="class"`, `storageKey="resilio-theme"`
- Défaut : dark
- Respects `prefers-color-scheme` au premier chargement
- CSS vars définies dans `apps/web/src/app/globals.css` :
  - `:root` — dark mode (valeurs par défaut)
  - `.light` — overrides pour light mode
- Toggle : `TopNav` — icône Moon (mode clair) / Sun (mode sombre)

---

## 3. Plateformes cibles

| Plateforme | App | Technologie | Statut |
|---|---|---|---|
| **Web** | `apps/web` | Next.js 16 + React 19 + Tailwind v4 | ✅ Session 0 |
| **Desktop** | `apps/desktop` | Tauri v2 (wrap de apps/web) | 🔲 Vague 1 Session T |
| **iOS** | `apps/mobile` | Expo + React Native | 🔲 Vague 1 Session M |

---

## 4. Partage de code

### Ce qui est partagé (packages/)

| Package | Partagé avec |
|---|---|
| `@resilio/design-tokens` | web + desktop + mobile |
| `@resilio/shared-logic` | web + desktop + mobile |
| `@resilio/api-client` | web + desktop + mobile |
| `@resilio/brand` | web + desktop (React), mobile (React Native via logo-mobile.tsx) |
| `@resilio/ui-web` | web + desktop (même moteur Chromium/WebKit) |
| `@resilio/ui-mobile` | mobile uniquement |

### Ce qui n'est PAS partagé

- Composants UI web (shadcn/ui, Radix) — React DOM uniquement
- Composants UI mobile (React Native Text, View, etc.)
- Logique de navigation (Next.js Router vs Expo Router)
- Config build (next.config.ts vs metro.config.js vs tauri.conf.json)

---

## 5. API Client (`@resilio/api-client`)

### Outil : `openapi-typescript`

Choix justifié : génère des types TypeScript natifs (pas de runtime) depuis le schéma OpenAPI de FastAPI. Compatible avec n'importe quel fetch wrapper. Léger, sans dépendances runtime.

### Génération

```bash
# Nécessite le backend running sur localhost:8000
pnpm --filter @resilio/api-client generate
```

Le client généré est dans `packages/api-client/src/generated/api.ts` (ignoré du git via `.gitkeep`).

### Utilisation actuelle (apps/web)

`apps/web/src/lib/api.ts` — client API custom en attendant la migration vers `@resilio/api-client`.  
**Migration : Vague 1**

---

## 6. Conventions de code

### Langue

- **UI text (labels, boutons, messages) :** français
- **Code (variables, fonctions, classes, types) :** anglais
- **Commits :** conventional commits avec scope

### Commits conventionnels

```
feat(web): add weekly plan comparison view
feat(desktop): scaffold Tauri app
feat(mobile): scaffold Expo app
fix(web): fix ThemeProvider hydration mismatch
chore(tokens): add missing shadow tokens
chore(api-client): regenerate from OpenAPI spec
test(shared-logic): add formatter unit tests
docs(frontend): update frontend-master-v1
```

### Qualité code

- TypeScript strict mode dans tous les packages
- `pnpm typecheck` doit passer avant tout commit
- `eslint` + `prettier` (à configurer en Vague 1)

---

## 7. Règles absolues frontend (8)

| # | Règle |
|---|---|
| 1 | Jamais d'import direct de `lucide-react` en dehors de `@resilio/ui-web` |
| 2 | Jamais d'import direct de `lucide-react-native` en dehors de `@resilio/ui-mobile` |
| 3 | Jamais de valeur de couleur hardcodée en dehors de `@resilio/design-tokens` |
| 4 | Toujours passer par `@resilio/api-client` pour les appels backend (migration Vague 1) |
| 5 | Tailwind `darkMode: 'class'` + CSS variables obligatoires sur toute nouvelle classe colorée |
| 6 | Commits conventionnels obligatoires (`feat(web)`, `feat(desktop)`, `feat(mobile)`, `chore(tokens)`, etc.) |
| 7 | Tests non négociables pour `shared-logic` et `api-client` |
| 8 | Pas de logique métier dans les composants UI — toujours dans `shared-logic` ou dans l'app |

---

## 8. État d'implémentation

### Session 0 ✅ (2026-04-12)

- [x] Monorepo pnpm configuré
- [x] `frontend/` migré vers `apps/web/` (git mv, historique préservé)
- [x] 6 packages créés (design-tokens, ui-web, ui-mobile, api-client, shared-logic, brand)
- [x] Design tokens extraits et codifiés
- [x] Dark/light mode infrastructure (CSS vars light mode, ThemeProvider config)
- [x] Pass dark mode sur 5 écrans critiques (dashboard, check-in, energy, tracking, top-nav)
- [x] Scaffolds desktop/mobile (placeholders)
- [x] FRONTEND_AUDIT.md
- [x] CLAUDE.md mis à jour (8 règles absolues, workspace structure)

### Vague 1 ✅ (2026-04-12) — livrée via 2 merges consolidés, voir FRONTEND_VAGUE1_POSTMORTEM.md

| Session | Statut | Livrable | Branche effective |
|---|---|---|---|
| FE-1A | ✅ | Tauri desktop scaffold (`apps/desktop/`) | via fe-1d |
| FE-1B | ✅ | Expo mobile scaffold + composants `@resilio/ui-mobile` | fe-1b |
| FE-1C | ✅ | ESLint rules + migration hex → CSS vars (check-in, energy) | via fe-1d |
| FE-1D | ✅ | Génération `@resilio/api-client` + migration `apps/web/src/lib/api.ts` | fe-1d |

---

## 8b. Dette technique Vague 1

| Item | Sévérité | Description |
|---|---|---|
| 37 warnings ESLint dans `energy/cycle/page.tsx` | ⚠️ Moyen | 26 warnings — composants cycle menstruel démo avec variables non utilisées. À nettoyer avant Vague 2. |
| 1 warning ESLint dans `allostatic-gauge.tsx` | ℹ️ Faible | Gauge SVG — variable inutilisée mineure. |
| Désynchro peer deps React dans `apps/mobile` | ⚠️ Moyen | À corriger avant le premier `expo start`. Expo SDK 52 attend React 18 ; workspace hoiste React 19. |
| 2 branches abandonnées sur remote | ℹ️ Info | `session/fe-1a` et `session/fe-1c` conservées pour traçabilité, non mergées. Le travail est dans main via fe-1d. |

---

## 9. Backlog Vague 1 Frontend

Sessions à planifier dans la prochaine vague :

### Session F1 — Migration `api.ts` → `@resilio/api-client`
Migrer `apps/web/src/lib/api.ts` vers le package `@resilio/api-client`.
Régénérer le client depuis `http://localhost:8000/openapi.json`.
Préreq : backend running.

### Session F2 — Tests `shared-logic` + `api-client`
Écrire tests vitest pour tous les formatters et validators de `@resilio/shared-logic`.
Écrire tests pour `@resilio/api-client` helpers.

### Session F3 — ESLint + Prettier monorepo
Configurer eslint-config partagé pour tous les packages.
Ajouter règles custom : no-direct-lucide, no-hardcoded-colors.
CI: `pnpm lint` dans la pipeline.

### Session F4 — Conversion inline styles → CSS variables (reste des écrans)
Compléter la migration des styles inline hardcodés vers CSS vars sur tous les écrans
non couverts en Session 0 : plan, review, history, analytics, session/[id], energy/cycle, etc.

### Session F5 — Dark mode complet + tests visuels
Vérifier rendu light mode sur tous les écrans.
Ajouter Storybook ou Playwright visual regression si pertinent.

### Session T — Tauri Desktop Scaffold
`npm create tauri-app` dans `apps/desktop/`.
Configurer le wrapper Next.js statique.
Build + distribution macOS/Windows.

### Session M — Expo Mobile Scaffold
`npx create-expo-app` dans `apps/mobile/`.
Implémenter `@resilio/ui-mobile` (icons + composants de base).
Premiers écrans : Dashboard, Check-in, Energy.

### Session F6 — PWA (Progressive Web App)
Ajouter `next-pwa` pour offline + installation sur mobile.
Manifest, service worker, icônes.

### Session FE-MOBILE-2 — Home Screen complet
Implémentation production-ready de l'écran d'accueil mobile :
Circle Readiness large + 3 petits cercles (HRV, Sommeil, Strain), carte prochaine séance,
bouton check-in. Utiliser les nouveaux composants Circle, Screen, Text de `@resilio/ui-mobile`.

### Session FE-MOBILE-WIDGET — Readiness iOS Widget
Implémenter le widget iOS home screen Readiness via `expo-widgets` + `@expo/ui`.
Préreq : iOS 17+, Xcode 26+ via EAS Build cloud, expo-widgets stable (post-alpha).
Voir `apps/mobile/ios-widget/README.md` pour architecture cible et contraintes.

---

## 10. Dette technique frontend

| Item | Sévérité | Description |
|---|---|---|
| Styles inline hardcodés (écrans restants) | ⚠️ Moyen | plan, review, history, analytics, etc. utilisent encore des hex hardcodés. À migrer vers CSS vars en Session F4. |
| `apps/web/src/lib/api.ts` custom | ⚠️ Moyen | Devrait être migré vers `@resilio/api-client`. Fonctionnel en l'état. |
| Pas de linting règles custom | ℹ️ Faible | Règles 1-3 (lucide, couleurs) ne sont pas encore enforced par ESLint. |
| `ui-mobile` skeleton vide | ℹ️ Faible | Attendu — sera rempli en Session M. |
| `api-client/src/generated/` vide | ℹ️ Faible | Attendu — générer avec backend running. |
| `next-themes enableSystem` | ℹ️ Faible | `prefers-color-scheme` activé — les utilisateurs avec dark OS verront dark. OK. |

---

*Référence principale pour tout le travail frontend Resilio+. Voir `resilio-master-v3.md` pour le backend.*
