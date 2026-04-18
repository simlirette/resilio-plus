# UI Integration Brainstorm v1
**Date :** 2026-04-18  
**Objectif :** Port partiel des 6 exports Claude Design → apps/mobile  
**Scope :** Brainstorm étape 1 — stop avant write-plan

---

## 1. INVENTAIRE RÉEL

### Contenu de `docs/design/`

| Dossier | Fichiers clés | Page Resilio+ |
|---------|---------------|---------------|
| `flow auth/` | `auth-screens.jsx`, `design-canvas.jsx`, `ios-frame.jsx` | Login + Signup + Forgot Password |
| `homedashboard/` | `dashboard.jsx`, `design-canvas.jsx`, `ios-frame.jsx`, `uploads/` | Home / Dashboard |
| `onboarding/onboarding/` | `steps.jsx`, `tokens.js` | Onboarding 5 steps |
| `todays session/` | `app.jsx`, `lib/prescription.jsx`, `lib/execution.jsx`, `lib/icons.jsx`, `tokens.jsx` | Session du jour (2 modes) |
| `training historycalendar/lib/` | `screen.jsx`, `components.jsx`, `views.jsx`, `data.js`, `theme.js` | Training History / Calendar |
| `coach chat/` | `coach-chat.jsx`, `hitl-sheet.jsx`, `ios-frame.jsx` | Coach Chat |
| **`test home/`** | — | ❌ ARCHIVE — ignorée, jamais touchée |

**`test home/` confirmé ignoré.** La source de la home est `homedashboard/`. `test home/` reste en place.

**Dossiers ambigus :** Aucun — tous les 7 dossiers sont clairs. `test home` n'a pas d'équivalent fonctionnel actif.

---

## 2. MAPPING VERS apps/mobile

### Structure cible vs état actuel

| Export | Route cible | État actuel |
|--------|-------------|-------------|
| `flow auth/` → login | `app/(auth)/login.tsx` | ✅ Existe — mais **outdated** (SpaceGrotesk, RN Text brut) |
| `flow auth/` → signup | `app/(auth)/signup.tsx` | ❌ Absent |
| `flow auth/` → forgot password | `app/(auth)/forgot-password.tsx` | ❌ Absent |
| `onboarding/` | `app/(onboarding)/index.tsx` (5 steps dans 1 fichier) | ❌ Absent |
| `homedashboard/` | `app/(tabs)/index.tsx` | ✅ **DÉJÀ PORTÉ** — complet, production-quality, **AUCUNE ACTION** |
| `todays session/` prescription | `app/session/today.tsx` | ❌ Absent |
| `todays session/` execution | `app/session/live.tsx` | ❌ Absent |
| `training historycalendar/` | `app/(tabs)/training.tsx` | ❌ Absent (tab non existante) |
| `coach chat/` | `app/(tabs)/coach.tsx` | Existe en tant que `chat.tsx` — placeholder vide |

### Justifications d'écart

- **Onboarding → 1 fichier** (`index.tsx`) plutôt que 5 fichiers séparés : les 5 steps sont dans `steps.jsx` comme une seule machine à états (`useState`). Port direct en 1 composant. L'URL n'affichera pas le step — acceptable pour v1.
- **`chat.tsx` → `coach.tsx`** : le fichier doit être renommé pour correspondre au trigger NativeTabs `name="coach"`. Renommer = changement de route — décision à trancher (voir §8).
- **Session `today.tsx`** et `live.tsx` : hors (tabs), accessibles via router.push depuis la home ou depuis training.

---

## 3. AUDIT DES EXPORTS

### 3a. Primitives web → React Native

| Primitif web | Équivalent RN |
|---|---|
| `div` | `View` |
| `button` | `Pressable` ou `Button` (@resilio/ui-mobile) |
| `input` | `TextInput` ou `Input` (@resilio/ui-mobile) |
| `span` | `Text` (inline via `<Text>` avec `style`) |
| `svg` / `path` | `react-native-svg` (déjà en place) |
| `h1`, `p` | `Text` avec variant (via @resilio/ui-mobile Text) |
| `scrollview` / overflow | `ScrollView` |
| `position: fixed` | `position: 'absolute'` ou `Modal` RN |
| Bottom sheet | `@gorhom/bottom-sheet` ou sheet Modal |
| `transition` CSS | `Animated` / `Reanimated` |
| `onClick` | `onPress` |
| `onChange` | `onChangeText` |

### 3b. Système de style détecté + stratégie

Tous les exports utilisent **inline styles web** avec CSS-in-JS pur. Stratégie de port :
- **StyleSheet.create()** pour les styles statiques (conforme UI-RULES §10)
- **`useTheme()`** pour les couleurs dynamiques light/dark
- **Zéro NativeWind** : non utilisé dans le projet mobile (`nativewind-env.d.ts` présent mais les composants existants n'utilisent pas de className)
- **Exception documentée** : `contentContainerStyle` sur ScrollView reste StyleSheet inline

### 3c. Assets à convertir

| Asset | Type | Action |
|-------|------|--------|
| SVG icônes inline (coach chat, session) | `<svg>` JSX | Convertir en `react-native-svg` + extraire dans `packages/ui-mobile/src/icons.ts` OU utiliser `Icon` existant |
| PNG uploads (session, home) | Screenshots design | Ne pas porter — décoration uniquement |
| `lib/icons.jsx` (todays session) | SVG custom icons | Mapper vers `Icon` (@resilio/ui-mobile) si équivalent, sinon `react-native-svg` inline |

### 3d. Anti-patterns détectés dans les exports

| Export | Anti-pattern | Correction à appliquer |
|--------|-------------|----------------------|
| **TOUS** | Font `'Space Grotesk'` | → `Inter` via `Text` component — **déjà géré par Text.tsx** |
| `flow auth/` | Accent `oklch(0.62 0.14 35)` (amber chaud) | → `colors.accent` (#3B74C9 clinical blue) |
| `flow auth/` | Palette `bg: '#F5F5F2'` divergente | → `colors.light.background` (#F7F4EE) |
| `homedashboard/` | Accent `oklch(0.62 0.14 55)` (amber) | N/A — home déjà porté avec les bons tokens |
| `coach chat/` | Accent `#B8552E` (sienna chaud) | → `colors.accent` (#3B74C9) |
| `onboarding/` | `JetBrains Mono` font | → `SpaceMono_400Regular` (déjà chargé dans `_layout.tsx`) |
| `todays session/` | SVG icônes custom (sport) | → `Icon` (@resilio/ui-mobile) si disponible |
| `flow auth/` | `oklch()` couleurs non supportées nativement en RN | → hex/rgba via tokens |
| `coach chat/` | Bottom sheet avec `position: fixed` | → `Modal` RN ou `@gorhom/bottom-sheet` |
| `flow auth/` | `Apple Sign In` button | → `expo-apple-authentication` (ou placeholder texte pour v1) |

---

## 4. COMPOSANTS PARTAGÉS À EXTRAIRE

### Déjà dans packages/ui-mobile

Button, Card, Circle, CognitiveLoadDial, Input, MetricRow, ReadinessStatusBadge, Screen, SessionCard, Text, Icon, ThemeProvider, useTheme

### À créer dans packages/ui-mobile

| Composant | Source design | Justification extraction |
|-----------|--------------|--------------------------|
| `ProgressDots` | `onboarding/steps.jsx` → `ProgressDots` | Réutilisable dans tout flux multi-step |
| `CoachBubble` | `coach-chat.jsx` → coach message | Spécifique coach chat — **inline dans coach.tsx pour v1**, extraction v2 |
| `UserBubble` | `coach-chat.jsx` → user message | Idem |
| `HITLSheet` | `hitl-sheet.jsx` | HITL est un pattern central (coach + onboarding) — extraire |
| `DisciplineIcon` | `todays session/lib/icons.jsx` | Run/Lift/Swim/Bike — variante d'Icon.tsx |
| `SessionSummaryCard` | `training historycalendar/lib/components.jsx` | Réutilisé en training + potentiellement home future |
| `CalendarStrip` | `training historycalendar/lib/views.jsx` | Spécifique training — **inline pour v1** |

### Décision proposée

- **Extraire maintenant** : `ProgressDots`, `HITLSheet`, `DisciplineIcon`
- **Inline pour v1** : `CoachBubble`, `UserBubble`, `CalendarStrip`, `SessionSummaryCard`
- La liste `OptionCard` (mentionnée dans le brief) est couverte par `HITLSheet`

---

## 5. TOKENS DANS packages/design-tokens

### État actuel

| Catégorie | Fichier | État |
|-----------|---------|------|
| Couleurs light/dark | `colors.ts` | ✅ Complet — tous les tokens v2 présents |
| Typography | `typography.ts` | ✅ Présent (valeurs web rem) — RN utilise `Text.tsx` avec px natifs |
| Spacing | `spacing.ts` | ✅ |
| Radius | `radius.ts` | ✅ |
| Shadows | `shadows.ts` | ✅ |
| Animation | `animation.ts` | ✅ |

### Gaps identifiés

| Gap | Impact | Action |
|-----|--------|--------|
| `colors.accent` existe mais les exports utilisent amber/sienna | Corrige en portant | Aucun ajout token nécessaire — correction au port |
| Pas de token `zoneRed` dans la palette principale | `zoneRed: '#ef4444'` existe dans `colors` root — OK | ✅ |
| Pas de token pour coaching bubble backgrounds | Utiliser `surface1`/`surface2` | Pas d'ajout nécessaire |

**Conclusion :** Aucun token manquant. Tout est disponible.

---

## 6. ROUTING ET NAVIGATION

### Structure Expo Router existante

```
app/
  _layout.tsx          ✅ Root — ThemeProvider, Inter fonts, Stack
  index.tsx            ✅ Redirect → /(auth)/login
  +not-found.tsx       ✅
  (auth)/
    login.tsx          ✅ Existe — à mettre à jour (SpaceGrotesk, RN Text)
  (tabs)/
    _layout.tsx        ✅ NativeTabs (4 tabs: index, check-in, chat, profile)
    index.tsx          ✅ Home — COMPLET, aucune action
    check-in.tsx       ✅ Minimal 2-step check-in
    chat.tsx           ✅ Placeholder vide
    profile.tsx        ✅ Placeholder vide
```

### Structure cible v1

```
app/
  _layout.tsx          (inchangé)
  index.tsx            (inchangé)
  +not-found.tsx       (inchangé)
  (auth)/
    _layout.tsx        (à créer — Stack sans header)
    login.tsx          (réécrire)
    signup.tsx         (créer)
    forgot-password.tsx (créer)
  (onboarding)/
    _layout.tsx        (à créer)
    index.tsx          (créer — machine à 5 états)
  (tabs)/
    _layout.tsx        (modifier — ajouter training, renommer chat→coach)
    index.tsx          (INCHANGÉ — ne pas toucher)
    check-in.tsx       (INCHANGÉ — voir §8 décision)
    coach.tsx          (renommer depuis chat.tsx + implémenter)
    training.tsx       (créer)
    profile.tsx        (placeholder minimal)
  session/
    today.tsx          (créer)
    live.tsx           (créer)
```

### Décision à trancher — structure tab bar (voir §8)

Le tab `check-in` existe actuellement. La structure proposée ne l'inclut pas dans les 4-5 tabs de la v1. Deux options :
- **A** : check-in reste tab (cœur) → 5 tabs : index, check-in, training, coach, profile
- **B** : check-in devient modal/sheet depuis home button → 4 tabs : index, training, coach, profile

---

## 7. PLACEHOLDERS POUR PAGES NON EXPORTÉES

Les 4 pages non exportées reçoivent un **placeholder minimal** identique au pattern `profile.tsx` actuel :

| Page | Route | Placeholder |
|------|-------|-------------|
| Metric Detail | `app/metric/[id].tsx` | "Détail métrique — à venir." |
| Nutrition Log | `app/(tabs)/nutrition.tsx` | "Journal nutrition — à venir." |
| Profile/Settings | `app/(tabs)/profile.tsx` | "Profil — à venir." (déjà en place) |
| Integrations/Connectors | `app/settings/integrations.tsx` | "Intégrations — à venir." |

---

## 8. RISQUES ET DÉCISIONS À TRANCHER

### 8.1 ❓ Tab bar : garder `check-in` ou le convertir en modal ?

**Option A — garder check-in comme tab (5 tabs)**  
- Tab bar : index · check-in · training · coach · profile
- SF Symbols à ajouter : training → `calendar` / `dumbbell` (non disponible) → `chart.bar.fill`
- NativeTabs supporte 5 tabs sans problème  
- ✅ Pas de refactor du flow existant

**Option B — check-in devient modal depuis home (4 tabs)**  
- Tab bar : index · training · coach · profile
- Le bouton "Check-in quotidien" sur la home route vers un modal Stack au lieu de `/(tabs)/check-in`
- `check-in.tsx` peut rester mais sort des tabs
- ⚠️ Casse le routing actuel — il faudra mettre à jour `home/index.tsx` qui fait `router.push('/(tabs)/check-in')`

**Recommandation :** Option A — 5 tabs. Plus simple, zéro refactor home. On peut always reduce plus tard.

### 8.2 ❓ Renommage `chat.tsx` → `coach.tsx`

Renommer le fichier + mettre à jour le trigger NativeTabs `name="chat"` → `name="coach"`.  
Changement minimal. SF Symbol : garder `bolt`/`bolt.fill`.

**Recommandation :** Renommer. Nom `coach` est plus précis et correspond au design export.

### 8.3 ❓ Onboarding : 1 fichier ou 5 fichiers ?

Le design export a tous les steps dans `steps.jsx` (machine à états). 1 fichier → `(onboarding)/index.tsx`.  
Alternative : 5 fichiers séparés `step-1.tsx` ... `step-5.tsx` avec URL step visible.

**Recommandation :** 1 fichier avec `useState(step)`. URL step non nécessaire pour v1 — simplifie le port direct.

### 8.4 ❓ HITLSheet — @gorhom/bottom-sheet ou Modal RN ?

- `@gorhom/bottom-sheet` : riche, gestures, mais dépendance supplémentaire
- `Modal` RN natif : intégré, suffisant pour v1 sans gestures avancées

**Recommandation :** `Modal` RN pour v1. `@gorhom/bottom-sheet` en v2 si le coach chat devient prioritaire.

### 8.5 ❓ Auth : Apple Sign In pour v1 ?

Le design export inclut "Continuer avec Apple". Nécessite `expo-apple-authentication` + config EAS.

**Recommandation :** Placeholder textuel `"Continuer avec Apple — bientôt disponible"` pour v1. Ne pas ajouter la dépendance EAS maintenant.

### 8.6 ❓ Auth — `(auth)/_layout.tsx` existant ?

Il n'existe pas actuellement — le `_layout.tsx` racine a `<Stack.Screen name="(auth)" />` mais pas de layout dans le groupe. En Expo Router, un groupe sans `_layout.tsx` utilise le Stack parent — ça fonctionne. Créer un `_layout.tsx` dans `(auth)/` pour control fin du Stack (sans header) est recommandé.

### 8.7 ⚠️ Home déjà porté

`app/(tabs)/index.tsx` est **complet et production-ready**. Ne pas le toucher. Le design export `homedashboard/dashboard.jsx` est sa source — il a déjà été intégré lors d'une session précédente.

### 8.8 ⚠️ `Resilio Sync` reverts files in ~30s

Règle critique : écrire et committer immédiatement. Chaque fichier créé doit être committé avant d'écrire le suivant.

---

## SYNTHÈSE — Ce qui reste à faire

| Priorité | Tâche | Complexité |
|----------|-------|------------|
| 1 | Vérifier tokens + ThemeProvider (déjà OK) | ✅ RAS |
| 2 | `ProgressDots`, `HITLSheet`, `DisciplineIcon` → ui-mobile | Moyen |
| 3 | Auth group : login (rewrite) + signup + forgot-password | Moyen |
| 4 | Onboarding : `(onboarding)/index.tsx` 5 steps | Moyen |
| 5 | Home : **SKIP** — déjà porté | ✅ RAS |
| 6 | Today's Session : `session/today.tsx` + `live.tsx` | Moyen |
| 7 | Training History : `(tabs)/training.tsx` | Moyen |
| 8 | Coach Chat : `(tabs)/coach.tsx` (depuis chat.tsx) | Élevé |
| 9 | 4 placeholders pages non exportées | Simple |
| 10 | Tab bar + navigation câblée | Simple |

**Pages à porter effectivement : 5** (auth ×3, onboarding, session ×2, training, coach chat)  
**Home : 0 action** (déjà fait)
