# Web Preview — Resilio+ Mobile

## Pourquoi

Simon-Olivier développe sur Windows sans Apple Developer account. Le web preview permet de voir le rendu de l'app mobile dans un navigateur comme validation visuelle rapide avant le dev build iOS (qui prend ~70min de cycle EAS).

## Commande one-liner

```bash
# Depuis la racine du monorepo
pnpm preview:mobile-web
```

Ou directement dans `apps/mobile` :
```bash
pnpm preview-web
```

Puis ouvrir **http://localhost:3001** dans Chrome.

> La première fois prend ~15-20s (Metro bundling). Re-runs sont plus rapides grâce au cache Metro.

## Limitations connues du preview web

| Feature | Web preview | Dev build iOS |
|---|---|---|
| Layout / couleurs / typo | ✅ Fidèle | ✅ |
| Rendu SVG (CognitiveLoadDial, Circle) | ✅ react-native-svg v15 | ✅ |
| NativeWind className | ✅ | ✅ |
| Haptics (expo-haptics) | ⚠️ No-op | ✅ |
| Safe area iPhone notch | ⚠️ Absent | ✅ |
| Fonts Google Fonts | ⚠️ Peut différer | ✅ |
| Gestures tactiles | ⚠️ Simulés clic/drag | ✅ Native |
| expo-secure-store | ⚠️ Fallback localStorage | ✅ Keychain |
| Performance native | ⚠️ JS/DOM | ✅ JSI |

**Utilise le preview web pour :** layout, couleurs, proportions, hiérarchie typo, rendu SVG, logique conditionnelle (banners, états).

**Utilise le dev build iOS pour :** haptics, safe area, perf native, gestures.

## Changer de scenario mock

Pour voir les différents états du Home screen :

1. Éditer `apps/mobile/src/hooks/useHomeData.ts`
2. Changer l'import de la donnée mock :
   - `mockHomeDataGreen` → score forme ≥ 80 (état Optimal)
   - `mockHomeDataYellow` → score forme 60-79 (état Prudent)
   - `mockHomeDataRestDay` → jour de repos
3. Re-run `pnpm preview:mobile-web`
4. Refresh Chrome (Ctrl+R)

## Routes disponibles

Après export, les routes générées dans `dist-web-preview/` :
- `/` → Home screen (index.tsx)
- `/check-in` → Check-in screen
- `/profile` → Profil
- `/chat` → Chat
- `/login` → Login
- `/(tabs)/...` → idem via tab navigation

## Historique du fix (2026-04-17)

**Cause racine :** `react-native-web` et `react-dom` absents du monorepo.

Expo SDK 55 nécessite `react-native-web ~0.21.0` pour l'export web. Metro utilise ce package pour aliaser les imports `react-native` vers leurs équivalents web. Le SSR (`@expo/router-server`) en a aussi besoin en contexte Node.js.

**Fix appliqué :**
1. `apps/mobile/package.json` → ajout `react-native-web ~0.21.0` + `react-dom 19.2.4` en dépendances
2. `.npmrc` racine → `public-hoist-pattern[]=react-native-web` + `public-hoist-pattern[]=react-dom` pour hoisting pnpm (accessibilité depuis le chemin SSR Node.js)
3. `pnpm install --no-frozen-lockfile`

**Non-régression confirmée :** 85 tests verts, typecheck 0 erreur, builds iOS/Android non impactés.
