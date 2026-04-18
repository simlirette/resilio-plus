# docs/design — Source de vérité UI Resilio+

## Objet

Ce dossier contient les exports Claude Design qui servent de référence absolue pour l'implémentation du UI de l'app mobile Resilio+.

## Structure par page

Chaque sous-dossier = une page. Structure standard:

```
<page>/
├── SPEC.md           Spec d'implémentation et comportements interactifs
├── screenshots/      Contrat visuel (light + dark, multi-états)
├── source/           Code source Claude Design (.jsx, .html, .css)
└── REFERENCES/       Optionnel, inspiration externe
```

## Hiérarchie d'autorité

Quand plusieurs sources se contredisent, cet ordre tranche:

1. **Screenshots** = contrat visuel absolu
2. **SPEC.md** = comportements, animations, edge cases
3. **Code source** = référence d'implémentation logique
4. **REFERENCES** = inspiration structurelle uniquement, ignorer le contenu
5. **Anciennes specs ou memories** = à ignorer si en conflit avec ce qui précède

## Cible de port

React Native / Expo SDK 52. Monorepo pnpm.

Correspondances web → RN standard:

| Web | React Native |
|---|---|
| `div` / `span` / `button` | `View` / `Text` / `Pressable` |
| Styles inline / Tailwind | `StyleSheet` + `packages/design-tokens` |
| CSS transitions | `react-native-reanimated` v3 |
| `backdrop-filter` | `expo-blur` `BlurView` |
| `position: fixed` | `KeyboardAvoidingView` + `SafeAreaView` |
| HTML drag | `react-native-draggable-flatlist` |
| Modals / drawers | `@gorhom/bottom-sheet` |
| Haptic iOS | `expo-haptics` |

## Pages présentes

| Dossier | Contenu | Complétude |
|---|---|---|
| `flow auth/` | 4 screenshots, 4 .jsx source | Complet — login, signup, forgot password |
| `onboarding/` | 2 screenshots, 1 .html, 1 .jsx source + tokens.js | Complet — 5 étapes |
| `homedashboard/` | 2 screenshots, 3 .jsx source, uploads | Complet — 3 états Readiness × 2 modes |
| `todays session/` | 2 screenshots, 1 .jsx + lib/ complet | Complet — Mode A prescription + Mode B exécution |
| `training historycalendar/` | 2 screenshots, 1 .html + lib/ | Complet — calendrier + liste + détail jour |
| `coach chat/` | 4 screenshots, 4 .jsx source, uploads (références HITL) | Complet — conversation + 3 types de questions HITL |

## Exclusions

- `ui archive/home/` = archive historique (ancienne v0), **ne jamais porter**. Voir `ui archive/home/DESIGN-ANALYSIS.md` pour contexte.
- 4 pages pas encore exportées (**Metric Detail, Nutrition, Profile, Connectors**) = placeholders, à compléter dans un cycle futur.

## Convention screenshots

Nommage recommandé:
- `<page>-light.png`
- `<page>-dark.png`
- `<page>-<état>.png` (ex: `home-light-scrolled.png`, `coach-chat-multiselect.png`)

Résolution cible: iPhone 390×844 natif minimum, idéalement @2x ou @3x.

## Note sur la couleur d'accent

Les anciennes specs mentionnent `#5b5fef` (violet) ou `#3B74C9` (bleu). Les screenshots et le code source montrent sans ambiguïté un **amber/terracotta chaud** (~`#B8552E` en light, ~`#D97A52` en dark). Les screenshots gagnent. Voir `frontend/UI-RULES.md` pour la palette canonique.
