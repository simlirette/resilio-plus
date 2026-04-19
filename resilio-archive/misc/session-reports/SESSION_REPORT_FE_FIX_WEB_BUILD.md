# Session Report — FE-FIX-WEB-BUILD
**Date:** 2026-04-17  
**Branch:** `session/fe-fix-web-build`  
**Type:** Bug fix — Web export for mobile preview  
**Duration:** ~30 min  
**Base:** `main` @ `f3c1303` (FE-MOBILE-2 merged)

---

## Status : ✅ COMPLETE

---

## Cause racine identifiée

**Hypothèse A confirmée.** `react-native-web` et `react-dom` étaient **complètement absents** du monorepo (ni dans aucun `package.json`, ni dans le pnpm store).

Expo SDK 55 nécessite `react-native-web ~0.21.0` (via `expo/bundledNativeModules.json`) pour deux chemins :

1. **Metro bundler** (client JS) : aliase `import from 'react-native'` → équivalents `react-native-web` lors de l'export `--platform web`
2. **Node.js SSR** (`@expo/router-server`) : `expo-modules-core/Platform.ts` tente d'importer `react-native-web/dist/exports/Platform` depuis un processus Node.js (pas Metro) — nécessite le package hoisted dans `node_modules/`

---

## Fix appliqué

### Changements

**`apps/mobile/package.json`** — ajout deps :
```json
"react-dom": "19.2.4",
"react-native-web": "~0.21.0",
```

**`.npmrc`** (nouveau à la racine) :
```
public-hoist-pattern[]=react-native-web
public-hoist-pattern[]=react-dom
```
Nécessaire pour le chemin SSR Node.js : `@expo/router-server` est dans `node_modules/.pnpm/` (pnpm virtual store) et cherche `react-native-web` via résolution Node.js standard. Sans hoisting, il ne le trouve pas depuis son emplacement dans le virtual store.

**`apps/mobile/package.json`** — nouveau script :
```json
"preview-web": "npx expo export --platform web --output-dir dist-web-preview && npx serve dist-web-preview -l 3001"
```

**`package.json` racine** — nouveau script :
```json
"preview:mobile-web": "pnpm --filter @resilio/mobile preview-web"
```

**`apps/mobile/.gitignore`** — ajout `dist-web-preview/`

**`apps/mobile/WEB-PREVIEW.md`** — guide d'utilisation complet

---

## Validation

### Export web
```
npx expo export --platform web → ✅ 12 routes statiques générées
dist-web-preview/index.html → ✅ HTML valide avec react-native-web styles
Bundle JS : 3MB (entry-152999cb...)
CSS : 6.1KB (global-9af99b41...)
```

### Non-régression
```
pnpm typecheck:mobile     → ✅ 0 erreurs
pnpm test:mobile          → ✅ 69/69
pnpm test:mobile:regression → ✅ 7/7
pnpm test:mobile:app       → ✅ 9/9
Total                      → ✅ 85/85
```

### react-native-web version installée
`react-native-web@0.21.2` (résolution de `~0.21.0` = compatible React 19.2.4)

---

## Fichiers créés / modifiés

| Fichier | Changement |
|---|---|
| `apps/mobile/package.json` | +react-dom 19.2.4, +react-native-web ~0.21.0, +preview-web script |
| `.npmrc` | Nouveau — hoisting pnpm pour react-native-web et react-dom |
| `package.json` | +preview:mobile-web root script |
| `apps/mobile/.gitignore` | +dist-web-preview/ |
| `apps/mobile/WEB-PREVIEW.md` | Nouveau — guide complet |
| `pnpm-lock.yaml` | Mis à jour |

---

## Limitations du preview web (documentées dans WEB-PREVIEW.md)

- Haptics : no-op (expo-haptics)
- Safe area iPhone notch : absente
- Fonts : peuvent légèrement différer selon browser
- expo-secure-store : fallback localStorage
- Performance : JS/DOM vs JSI natif

---

## Commandes pour Simon-Olivier en arrivant

```bash
# Preview web (rebuil + serve)
pnpm preview:mobile-web
# Puis ouvrir http://localhost:3001

# Ou si bundle déjà généré (cache Metro)
cd apps/mobile/dist-web-preview && npx serve -l 3001
```

Pour changer de scenario mock :
1. Éditer `apps/mobile/src/hooks/useHomeData.ts`
2. Changer `mockHomeDataGreen` → `mockHomeDataYellow` ou `mockHomeDataRestDay`
3. Re-run `pnpm preview:mobile-web`

---

## Dette technique créée

Aucune. Le fix est propre et suit les pratiques recommandées Expo + pnpm.

**Note :** `pnpm-lock.yaml` a été mis à jour avec `--no-frozen-lockfile`. Normal lors d'ajout de nouvelles dépendances.

---

**Prochaine session :** Review visuelle du web preview, puis FE-MOBILE-3 (Check-in screen)
