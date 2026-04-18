# SDK 55 → 54 Downgrade Plan
_2026-04-18 — branch: chore/downgrade-sdk54_

## Context

Expo Go sur device physique iOS bloqué à SDK 54 (impossible de mettre à jour).
Objectif: faire tourner l'app dans Expo Go SDK 54 pour valider Wave 1.

**Backups existants** (créés en Phase 0):
- `apps/mobile/package.json.backup-sdk55`
- `apps/mobile/app.json.backup-sdk55`
- `pnpm-lock.yaml.backup-sdk55`
- `packages/ui-mobile/package.json.backup-sdk55`

---

## 1. Table de correspondance versions 55 → 54

### Packages Expo (auto-résolus par `expo install --fix`)

| Package | SDK 55 (actuel) | SDK 54 (cible estimée) | Méthode |
|---|---|---|---|
| `expo` | `~55.0.15` | `~54.0.0` | Manuel → pin |
| `expo-router` | `~55.0.12` | `~4.0.0` | `expo install --fix` |
| `expo-font` | `~55.0.6` | `~14.0.0` | `expo install --fix` |
| `expo-haptics` | `~55.0.14` | `~14.0.0` | `expo install --fix` |
| `expo-linking` | `~55.0.13` | `~7.0.0` | `expo install --fix` |
| `expo-secure-store` | `~55.0.13` | `~14.0.0` | `expo install --fix` |
| `expo-splash-screen` | `~55.0.18` | `~0.29.0` | `expo install --fix` |
| `expo-status-bar` | `~55.0.5` | `~2.0.0` | `expo install --fix` |
| `expo-apple-authentication` | `^55.0.13` | `~7.2.0` | `expo install --fix` |
| `expo-blur` | `^55.0.14` | `~14.0.0` | `expo install --fix` |
| `jest-expo` (devDep) | `~55.0.16` | `~54.0.0` | `expo install --fix` |

> ⚠️ Les versions SDK 54 ci-dessus sont des **estimations**. `expo install --fix` écrira les versions exactes.

### React / React Native

| Package | SDK 55 | SDK 54 | Risque |
|---|---|---|---|
| `react` | `19.2.4` | À déterminer par `expo install` | ⚠️ Possible downgrade vers 18.3.x |
| `react-dom` | `19.2.4` | Aligné sur `react` | ⚠️ |
| `react-test-renderer` | `19.2.4` | Aligné sur `react` | ⚠️ |
| `react-native` | `0.83.4` | ~`0.76.x`–`0.79.x` | 🔴 Majeur — pilote tout le reste |

> **Note React 18 vs 19**: Si SDK 54 requiert React 18, les types `@types/react` et le style JSX seront différents. Impact probable sur les composants ui-mobile qui utilisent `React.JSX.Element` (React 19 style). À évaluer après `expo install --fix`.

### Packages non-Expo dépendant de React Native

Ces packages ne sont **pas** gérés par `expo install --fix` — à ajuster manuellement selon la version RN choisie:

| Package | SDK 55 | SDK 54 (cible) | Raison |
|---|---|---|---|
| `react-native-reanimated` | `4.2.1` | `~3.16.x` ou `~3.19.x` | v4 requiert RN ≥ 0.82. SDK 54 utilise RN 0.76–0.79 → v3 obligatoire |
| `react-native-gesture-handler` | `~2.30.1` | ~`2.20.x` | Version liée à RN version |
| `react-native-safe-area-context` | `5.6.2` | ~`4.12.x` | Même raison |
| `react-native-screens` | `~4.23.0` | ~`4.4.x` | Même raison |
| `react-native-svg` | `~15.15.3` | ~`15.8.x` | Compatible mais version exacte à vérifier |
| `nativewind` | `5.0.0-preview.3` | `5.0.0-preview.3` ou antérieur | Preview — peut être incompatible avec RN 0.76 |
| `@gorhom/bottom-sheet` | `^5.2.9` | `^5.2.9` ou antérieur | Dépend de gesture-handler + reanimated |
| `react-native-draggable-flatlist` | `^4.0.3` | `^4.0.3` | Dépend de gesture-handler |

---

## 2. Plan d'exécution en commits atomiques

### Commit A — Pin expo + expo install --fix
```bash
# Dans apps/mobile/
# 1. Modifier package.json: "expo": "~54.0.0"
# 2. Lancer expo install --fix (depuis apps/mobile/)
npx expo install --fix
# Cela réécrira automatiquement toutes les versions expo-* dans package.json
# Lire le diff pour confirmer les versions choisies
# 3. Alignement react/react-dom/react-test-renderer si expo install les a touchés
# Commit:
git add apps/mobile/package.json
git commit -m "chore(mobile): pin expo SDK 54, expo install --fix"
```

### Commit B — Downgrade reanimated + RN ecosystem
```bash
# Selon la version RN déterminée par Commit A:
# - react-native-reanimated: ~3.19.x (dernier 3.x stable)
# - react-native-gesture-handler, safe-area-context, screens, svg: versions compatibles RN cible
# pnpm install (depuis racine monorepo)
git add apps/mobile/package.json pnpm-lock.yaml
git commit -m "chore(mobile): downgrade reanimated 4→3, align RN ecosystem deps"
```

### Commit C — Vérification nativewind / gorhom
```bash
# Tester si nativewind 5.0.0-preview.3 fonctionne avec RN cible
# Si erreur: downgrader ou patcher
# Tester si @gorhom/bottom-sheet s'installe sans conflits
# Commit si changement nécessaire:
git commit -m "chore(mobile): fix nativewind/gorhom compat SDK 54"
```

### Commit D — app.json sdkVersion (si nécessaire)
```bash
# SDK 54 peut requérir sdkVersion explicite dans app.json
# "sdkVersion": "54.0.0" dans expo{}
# Commit:
git commit -m "chore(mobile): set sdkVersion 54 in app.json"
```

### Commit E — Régénération lockfile propre
```bash
# Depuis racine monorepo:
pnpm install
# Vérifier: pas de conflits de résolution
git add pnpm-lock.yaml
git commit -m "chore: regenerate pnpm-lock for SDK 54"
```

---

## 3. Risques identifiés

### 🔴 Critique

| Risque | Impact | Mitigation |
|---|---|---|
| **React 18 vs 19** | Si SDK 54 requiert React 18: les types JSX diffèrent (`React.FC` vs nouvelles signatures), `React.JSX.Element` peut ne pas exister en 18. Tous les composants ui-mobile seraient à retyper. | Vérifier via `expo install --fix` output. Si React 18 requis: évaluer si c'est bloquant ou patchable rapidement. |
| **reanimated v3 API compat** | FloatingLabelInput utilise `Animated` built-in (pas reanimated) → OK. ReadinessRing Wave 2 prévu avec reanimated → v3 OK mais API légèrement différente de v4. | Pas de risque Wave 1. Wave 2 à adapter si API change. |

### 🟡 Modéré

| Risque | Impact | Mitigation |
|---|---|---|
| **nativewind preview incompatible** | `5.0.0-preview.3` peut ne pas supporter le RN cible. Crash au runtime ou erreurs build. | Si échec: downgrader à la preview compatible SDK 54 (ex: `5.0.0-alpha.X`), ou désactiver nativewind temporairement (pas utilisé dans Wave 1). |
| **@gorhom/bottom-sheet v5** | v5 dépend de reanimated + gesture-handler. Après downgrade, peut y avoir conflit de peerDeps. | `pnpm install` signalera les conflits. Ajustement de version si nécessaire. |
| **expo-router v4 vs v55** | expo-router v4 a des différences d'API vs v55 (Stack, navigation types). | L'app utilise des patterns basiques (Stack + Tabs). Peu probable que ça casse. |

### 🟢 Faible

| Risque | Impact | Mitigation |
|---|---|---|
| **Lockfile conflicts** | pnpm peut avoir du mal avec les résolutions croisées monorepo. | Supprimer node_modules + lockfile et réinstaller depuis zéro si bloqué. |
| **TypeScript strict mode** | Downgrade de types peut créer des erreurs TS. | `typecheck` en étape de vérification après chaque commit. |

---

## 4. Vérifications post-downgrade

```bash
# 1. Metro démarre sans erreur
cd apps/mobile && npx expo start

# 2. Typecheck propre
pnpm --filter @resilio/mobile typecheck
pnpm --filter @resilio/ui-mobile typecheck

# 3. Expo Go scan QR → app charge
# Test /_debug/text-showcase → Space Grotesk render
# Test /_debug/inputs-showcase → float label animation

# 4. Régression test
pnpm --filter @resilio/mobile test:regression
```

---

## 5. Rollback

Si downgrade échoue ou produit trop de casse:
```bash
# Restaurer depuis backups
cp apps/mobile/package.json.backup-sdk55 apps/mobile/package.json
cp apps/mobile/app.json.backup-sdk55 apps/mobile/app.json
cp pnpm-lock.yaml.backup-sdk55 pnpm-lock.yaml
cp packages/ui-mobile/package.json.backup-sdk55 packages/ui-mobile/package.json
pnpm install
git checkout main  # ou rester sur la branche + git reset --hard
```

---

**STOP — Attends validation avant exécution des commits A–E.**
