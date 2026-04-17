# UI Rules Mobile — Resilio+ (apps/mobile)

Anti-drift reference for all Claude Code sessions working on the Resilio+ mobile app.
**Design system v2** — Warm minimalist, Apple Health / Whoop 5.0 inspired.
Source: Claude Design handoff `RbXZRFnMZI1nsG_v0vkzMw` (2026-04-17)

---

## Règles héritées de CLAUDE.md (1–8)

| # | Règle |
|---|---|
| 1 | Jamais d'import direct de `lucide-react` hors `@resilio/ui-web` |
| 2 | **Jamais d'import direct de `lucide-react-native`** hors `@resilio/ui-mobile` |
| 3 | Jamais de valeur de couleur hardcodée hors `@resilio/design-tokens` |
| 4 | Toujours passer par `@resilio/api-client` pour les appels backend |
| 5 | Light + dark mode obligatoires sur tout nouveau composant |
| 6 | Commits conventionnels (`feat(mobile):`, `fix(mobile):`, `chore(mobile):`, etc.) |
| 7 | Tests non négociables pour `shared-logic` et `api-client` |
| 8 | Pas de logique métier dans les composants UI |

---

## Design System v2 — Palette

### Accent
**Un seul accent coloré visible simultanément.**
Default: **Clinical Blue `#3B74C9`** (`colors.accent`).
Autres options: Emerald `#2F7D5B`, Indigo `#5B5BAF` — via `colors.accent` seulement.

### Light mode
| Token | Hex | Usage |
|-------|-----|-------|
| background | `#F7F4EE` | Screen bg |
| surface1 | `#FDFBF7` | Card bg |
| surface2 | `#F3EFE8` | Badge bg, inner metric |
| foreground | `#2B2824` | Primary text |
| textSecondary | `rgba(43,40,36,0.62)` | Secondary text |
| textMuted | `rgba(43,40,36,0.38)` | Tertiary / labels |
| border | `rgba(43,40,36,0.08)` | Hairline borders |
| warn | `#B8863A` | Metric state: yellow |
| ok | `#6B9259` | Metric state: green |
| okStrong | `#5C8250` | Reserved (not used in MetricRow) |
| caution | `#A6762E` | Prudent state |

### Dark mode
| Token | Hex | Usage |
|-------|-----|-------|
| background | `#131210` | Screen bg |
| surface1 | `#1C1B18` | Card bg |
| surface2 | `#232120` | Badge bg, inner metric |
| foreground | `#EDE9E2` | Primary text |
| textSecondary | `rgba(237,233,226,0.62)` | Secondary text |
| textMuted | `rgba(237,233,226,0.38)` | Tertiary / labels |
| border | `rgba(237,233,226,0.08)` | Hairline borders |
| warn | `#D6A24A` | Metric state: yellow |
| ok | `#7DA66A` | Metric state: green |
| okStrong | `#6B9259` | Reserved (not used in MetricRow) |
| caution | `#C79140` | Prudent state |

---

## Typographie

**Font: Inter** (via `@expo-google-fonts/inter`).
Migration: Space Grotesk → Inter (v2, 2026-04-17). ❌ Ne pas réintroduire Space Grotesk.

| Variant | Size | Weight | Usage |
|---------|------|--------|-------|
| `display` | 72px | 300 | Readiness number |
| `headline` | 38px | 300 | Allostatic dial number |
| `title` | 26px | 500 | Greeting name |
| `body` | 15px | 400 | Body text |
| `secondary` | 13px | 400 | Dates, details (tabular-nums) |
| `caption` | 12px | 400 | Metric labels |
| `label` | 11px | 500 | Section labels (CAPS) |
| `mono` | 13px | — | Tabular numeric (SpaceMono) |

**Tabular nums obligatoires** sur tous les chiffres visibles (`fontVariant: ['tabular-nums']`).

---

## Règles spécifiques mobile (9–18)

### 9 — Icônes

```tsx
// ❌ INTERDIT — jamais dans apps/mobile/ ni aucun package hors @resilio/ui-mobile
import { Heart } from 'lucide-react-native';

// ✅ CORRECT — objet pattern
import { Icon } from '@resilio/ui-mobile';
<Icon.Heart color={colors.accent} size={20} />

// ✅ CORRECT — name prop pattern (icône dynamique)
import { IconComponent } from '@resilio/ui-mobile';
<IconComponent name="Heart" color={colors.accent} size={20} />
```

**Exception SF Symbols — tab bar uniquement :**
La tab bar principale (`app/(tabs)/_layout.tsx`) utilise SF Symbols via `NativeTabs.Trigger.Icon` pour l'intégration native iOS liquid glass. Sur web/Android, l'icône SF est ignorée (labels seuls). Tous les autres icônes dans l'app utilisent Lucide via `@resilio/ui-mobile/Icon`.

```tsx
// ✅ CORRECT — tab bar uniquement
import { NativeTabs } from 'expo-router/unstable-native-tabs';
<NativeTabs.Trigger.Icon sf={{ default: 'house', selected: 'house.fill' }} />
```

### 10 — Styles

StyleSheet est autorisé (v2 adopte StyleSheet pour tous les composants de base).
❌ Hex hardcodés dans les styles — toujours via `colors.*` ou `useTheme()`.

```tsx
// ❌ INTERDIT — hex hardcodé
<View style={{ backgroundColor: '#131210' }} />

// ✅ CORRECT — design tokens
const { colors: themeColors } = useTheme();
<View style={{ backgroundColor: themeColors.background }} />

// ✅ CORRECT — tokens globaux
import { colors } from '@resilio/design-tokens';
<View style={{ borderColor: colors.accent }} />
```

**Exception StyleSheet:** `contentContainerStyle` sur ScrollView (NativeWind ne peut pas cibler cette prop). Documenter dans le commit.

### 11 — Safe Area

```tsx
// ❌ INTERDIT
import { SafeAreaView } from 'react-native-safe-area-context';

// ✅ CORRECT — wrapper Screen de @resilio/ui-mobile
import { Screen } from '@resilio/ui-mobile';
<Screen>...</Screen>
```

### 12 — Haptics

- `Button` primary → `ImpactFeedbackStyle.Medium` (intégré dans Button.tsx)
- `Button` secondary/ghost → `ImpactFeedbackStyle.Light`
- Confirmations → `NotificationFeedbackType.Success`

### 13 — Pas d'emoji ni de copy célébratoire

```tsx
// ❌ INTERDIT
<Text>Bravo ! 🎉 Tu as terminé ta séance !</Text>

// ✅ CORRECT — ton clinique neutre
<Text>Séance terminée. Score de récupération : 78.</Text>
```

### 14 — Copy en français (tu)

Tout le texte affiché est en français, tutoiement.

**Termes techniques conservés en anglais :** les termes de sport science consacrés restent en anglais — Strain, Readiness, VO₂max, RPE, HRV, ACWR, EWMA. Les termes généraux sont en français : Sommeil, Nutrition, Repos, Séance.

### 15 — Animations

```tsx
// ✅ CORRECT — react-native-reanimated
import Animated, { useSharedValue, withSpring } from 'react-native-reanimated';
```

### 16 — Fonts

```tsx
// ✅ CORRECT — expo-font via useFonts dans _layout.tsx
import { useFonts, Inter_400Regular } from '@expo-google-fonts/inter';
```

### 17 — Dark / Light mode

**Tout composant testé en light ET dark avant merge.**

```tsx
const { colorMode, colors } = useTheme();
// colorMode: 'light' | 'dark' — suit la préférence système iOS
```

### 18 — Navigation

```tsx
// ✅ CORRECT — expo-router
import { useRouter } from 'expo-router';
router.push('/(tabs)/check-in');
```

---

## Composant sizing (design handoff)

| Composant | Valeur | Notes |
|-----------|--------|-------|
| Card radius | 22px | borderRadius: 22 |
| Card border | 0.5px | hairline |
| Button height | 54px | |
| Button radius | 16px | |
| Readiness ring | 216px diam, stroke 10px | innerLabel="Readiness" |
| Metric rings | 68px diam, stroke 5px | Circle strokeWidth=5 |
| Tab bar radius | 33px | |
| State badge | pill 999 + 7px dot | |

---

## Anti-patterns formels

| Anti-pattern | Raison |
|---|---|
| Photos paysages en background (Bevel-style) | ❌ Aesthetic incompatible |
| Serif display typography | ❌ Aesthetic incompatible |
| Palettes pastel surchargées | ❌ Aesthetic incompatible |
| Accents multiples dans un écran | ❌ Règle d'unité |
| Gradients agressifs | ❌ Aesthetic incompatible |
| L'ancien `#08080e` dark clinical | ❌ Deprecated — remplacé par `#131210` |
| Space Grotesk font | ❌ Deprecated — remplacé par Inter |
| `colors.primary = '#5b5fef'` | ❌ Deprecated — remplacé par `#3B74C9` |
| Import direct de `lucide-react-native` | ❌ Règle 2 |
| Hex hardcodé hors design-tokens | ❌ Règle 3 |

---

## MetricRow — Couleurs state-based

Les cercles `MetricRow` changent de couleur selon la **valeur** (état), pas selon le **type de métrique**.

| State | Token | Description |
|-------|-------|-------------|
| `'green'` | `themeColors.ok` | Optimal |
| `'yellow'` | `themeColors.warn` | Caution |
| `'red'` | `colors.zoneRed` (#ef4444) | Alert |

---

*Mis à jour : Session FE-HOME-POLISH-NATIVETABS (2026-04-17). Voir `CLAUDE.md` pour les règles globales.*
