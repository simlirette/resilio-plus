# UI Rules Mobile — Resilio+ (apps/mobile)

Anti-drift reference for all Claude Code sessions working on the Resilio+ mobile app.

---

## Règles héritées de CLAUDE.md (1–8)

| # | Règle |
|---|---|
| 1 | Jamais d'import direct de `lucide-react` hors `@resilio/ui-web` |
| 2 | **Jamais d'import direct de `lucide-react-native`** hors `@resilio/ui-mobile` |
| 3 | Jamais de valeur de couleur hardcodée hors `@resilio/design-tokens` |
| 4 | Toujours passer par `@resilio/api-client` pour les appels backend |
| 5 | Dark mode `dark:` variants obligatoires + CSS variables pour inline styles |
| 6 | Commits conventionnels (`feat(mobile):`, `fix(mobile):`, `chore(mobile):`, etc.) |
| 7 | Tests non négociables pour `shared-logic` et `api-client` |
| 8 | Pas de logique métier dans les composants UI |

---

## Règles spécifiques mobile (9–18)

### 9 — Icônes

```tsx
// ❌ INTERDIT — jamais dans apps/mobile/ ni aucun package hors @resilio/ui-mobile
import { Heart } from 'lucide-react-native';

// ✅ CORRECT — objet pattern
import { Icon } from '@resilio/ui-mobile';
<Icon.Heart color={colors.zoneGreen} size={20} />

// ✅ CORRECT — name prop pattern (icône dynamique)
import { IconComponent } from '@resilio/ui-mobile';
<IconComponent name="Heart" color={colors.zoneGreen} size={20} />
```

### 10 — Styles

```tsx
// ❌ INTERDIT — StyleSheet dans les écrans (sauf exception documentée)
const styles = StyleSheet.create({ container: { backgroundColor: '#08080e' } });

// ✅ CORRECT — className NativeWind (préféré pour nouveaux composants)
<View className="flex-1 bg-background px-6 pt-4" />

// ✅ CORRECT — tokens via useTheme() pour valeurs dynamiques
const { colors } = useTheme();
<View style={{ backgroundColor: colors.background }} />
```

**Exception StyleSheet acceptée :** uniquement si NativeWind ne supporte pas la propriété CSS cible (ex: `shadowOffset`, `transform` complexes). Documenter l'exception dans le commit message.

### 11 — Safe Area

```tsx
// ❌ INTERDIT
import { SafeAreaView } from 'react-native-safe-area-context';
<SafeAreaView>...</SafeAreaView>

// ✅ CORRECT — wrapper Screen de @resilio/ui-mobile
import { Screen } from '@resilio/ui-mobile';
<Screen padded>...</Screen>
<Screen scroll padded>...</Screen>
```

### 12 — Haptics

Toutes les actions primaires déclenchent un retour haptique :
- `Button` primary → `ImpactFeedbackStyle.Medium` (déjà intégré dans Button.tsx)
- `Button` secondary/ghost → `ImpactFeedbackStyle.Light`
- Confirmations critiques → `NotificationFeedbackType.Success`

```tsx
import * as Haptics from 'expo-haptics';
await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
```

### 13 — Pas d'emoji ni de copy célébratoire

```tsx
// ❌ INTERDIT — copie célébratoire (règle clinique Resilio+)
<Text>Bravo ! 🎉 Tu as terminé ta séance !</Text>

// ✅ CORRECT — ton clinique neutre
<Text>Séance terminée. Score de récupération : 78.</Text>
```

### 14 — Copy en français (tu)

Tout le texte affiché à l'utilisateur est en français, tutoiement :
- Boutons : "Se connecter", "Continuer", "Terminer"
- Labels : "Forme du jour", "Prochaine séance"
- Erreurs : "Email et mot de passe requis."

### 15 — Animations

```tsx
// ❌ INTERDIT — API Animated classique
import { Animated } from 'react-native';

// ✅ CORRECT — react-native-reanimated
import Animated, { useSharedValue, withSpring } from 'react-native-reanimated';
```

### 16 — Fonts

```tsx
// ❌ INTERDIT — import URL Google Fonts
// @import url('https://fonts.googleapis.com/...')

// ✅ CORRECT — expo-font via useFonts dans _layout.tsx
import { useFonts, SpaceGrotesk_400Regular } from '@expo-google-fonts/space-grotesk';
const [fontsLoaded] = useFonts({ SpaceGrotesk_400Regular });
```

### 17 — Dark / Light mode

Tous les composants doivent fonctionner en dark ET light mode.
- Défaut : dark (Resilio+ est dark-first)
- Utiliser `useTheme()` pour les couleurs dynamiques
- `className` NativeWind utilise automatiquement les tokens dark/light du `tailwind.config.js`

```tsx
const { colorMode, colors } = useTheme();
// colors.background, colors.foreground, etc. — auto dark/light
```

### 18 — Navigation

```tsx
// ❌ INTERDIT — SafeAreaView pour navigation guard
// ❌ INTERDIT — React Navigation direct

// ✅ CORRECT — expo-router
import { useRouter, Redirect } from 'expo-router';
const router = useRouter();
router.push('/(tabs)/check-in');
router.replace('/(tabs)/');
```

---

## Design Tokens Rappel (mobile)

Tokens disponibles depuis `@resilio/design-tokens` et mappés dans `tailwind.config.js` :

| Token NW class | Valeur (dark) | Usage |
|---|---|---|
| `bg-background` | `#08080e` | Fond écran principal |
| `bg-surface-1` | `#0f0f18` | Tab bar, header |
| `bg-surface-2` | `#14141f` | Cards, inputs |
| `bg-surface-3` | `#1a1a28` | Éléments imbriqués |
| `text-foreground` | `#eeeef4` | Texte principal |
| `text-text-muted` | `#5c5c7a` | Texte désactivé |
| `text-text-secondary` | `#8888a8` | Labels secondaires |
| `bg-primary` | `#5b5fef` | Boutons primaires, accent |
| `text-zone-green` | `#10b981` | Readiness ≥ 70 |
| `text-zone-yellow` | `#f59e0b` | Readiness 50–69 |
| `text-zone-red` | `#ef4444` | Readiness < 50 |

Via `useTheme()` :
```tsx
const { colors } = useTheme();
colors.background  // '#08080e' en dark
colors.primary     // '#5b5fef'
colors.zoneGreen   // '#10b981'
```

---

## Anti-patterns à éviter

| Anti-pattern | Raison | Alternative |
|---|---|---|
| `import { X } from 'lucide-react-native'` | Violation règle 2 | `Icon.X` from `@resilio/ui-mobile` |
| Hex hardcodé dans composant | Violation règle 3 | `colors.*` from `@resilio/design-tokens` ou `useTheme()` |
| `StyleSheet.create` dans écrans | NativeWind préféré | `className` NativeWind |
| `<SafeAreaView>` direct | Type instable React 19 | `<Screen>` from `@resilio/ui-mobile` |
| `Animated` API RN classique | Non compatible Fabric/RN 0.83 | `react-native-reanimated` |
| `@import url()` Google Fonts | Pas d'optimisation build | `expo-font` + `useFonts` |
| Emoji dans UI | Règle clinique Resilio+ | Texte neutre |
| Copy anglais | Convention Resilio+ mobile | Français, tutoiement |
| Logique métier dans composant UI | Règle 8 | `@resilio/shared-logic` |
| `fetch()` direct dans composant | Règle 4 | `@resilio/api-client` |

---

*Mis à jour : Session FE-MOBILE-1 (2026-04-16). Voir `CLAUDE.md` pour les règles globales.*
