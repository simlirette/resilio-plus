# @resilio/ui-mobile — Component Reference

All components require `ThemeProvider` at the tree root (provided by `apps/mobile/app/_layout.tsx`).

---

## Icon / IconComponent

Sole authorized importer of `lucide-react-native`. Never import lucide directly in app screens.

**Props (IconComponent)**
```ts
interface IconComponentProps {
  name: IconName;       // key of Icon object (e.g. "Heart", "Activity", "Energy")
  size?: number;        // default 20
  color?: string;       // any CSS color string — use design token values
  strokeWidth?: number; // default: lucide default (1.5)
}
```

**Usage — object pattern (static)**
```tsx
import { Icon } from '@resilio/ui-mobile';
<Icon.Heart color={colors.zoneGreen} size={20} />
<Icon.Activity color={colors.primary} size={24} />
```

**Usage — name prop (dynamic)**
```tsx
import { IconComponent } from '@resilio/ui-mobile';
<IconComponent name="Heart" color={colors.zoneGreen} size={20} />
```

**Anti-pattern**
```tsx
// FORBIDDEN
import { Heart } from 'lucide-react-native';
```

---

## Screen

Safe-area wrapper. Always use instead of `SafeAreaView` or plain `View` for screen roots.

**Props**
```ts
interface ScreenProps {
  children: ReactNode;
  scroll?: boolean;   // wraps content in ScrollView (default: false)
  padded?: boolean;   // adds 24px horizontal + 16px vertical padding (default: false)
}
```

**Usage — basic**
```tsx
import { Screen } from '@resilio/ui-mobile';
<Screen>
  {/* screen content */}
</Screen>
```

**Usage — scrollable with padding**
```tsx
<Screen scroll padded>
  {/* long content */}
</Screen>
```

**Anti-pattern**
```tsx
// FORBIDDEN
import { SafeAreaView } from 'react-native-safe-area-context';
<SafeAreaView>...</SafeAreaView>
```

---

## Text

Typed typography component. Always use instead of React Native `Text` in screens.

**Props**
```ts
type TextVariant = 'display' | 'title' | 'body' | 'caption' | 'mono';

interface TextProps {
  children: ReactNode;
  variant?: TextVariant;  // default: 'body'
  color?: string;         // override theme foreground — use design token values
  style?: TextStyle;      // additional style overrides
  numberOfLines?: number; // truncate with ellipsis
}
```

**Variants**
| Variant | Font | Size | Use |
|---|---|---|---|
| `display` | SpaceGrotesk Bold | 36 | Hero numbers (score, value) |
| `title` | SpaceGrotesk Bold | 22 | Section headings |
| `body` | SpaceGrotesk Regular | 15 | Default text |
| `caption` | SpaceGrotesk Regular | 12 | Labels, metadata |
| `mono` | SpaceMono Regular | 13 | Time values, codes |

**Usage**
```tsx
import { Text } from '@resilio/ui-mobile';
<Text variant="display" color={colors.zoneGreen}>75</Text>
<Text variant="caption" color={colors.dark.textSecondary}>Forme du jour</Text>
<Text>Corps du texte par défaut</Text>
```

**Anti-pattern**
```tsx
// FORBIDDEN — never hardcode hex in color prop
<Text color="#10b981">Score</Text>
// CORRECT
<Text color={colors.zoneGreen}>Score</Text>
```

---

## Card

Surface container with themed background and border.

**Props**
```ts
interface CardProps {
  children: ReactNode;
  style?: ViewStyle;  // override card container style
}
```

**Usage**
```tsx
import { Card } from '@resilio/ui-mobile';
<Card>
  <Text variant="title">Forme du jour</Text>
  <Text>Score: 75</Text>
</Card>

// With spacing override
<Card style={{ marginBottom: 16 }}>
  {/* content */}
</Card>
```

**Notes**
- Background: `colors.dark.surface2` (`#14141f`)
- Border: `colors.dark.border` (`#22223a`), `borderRadius: 16`
- No gradient — flat surface only

---

## Circle

SVG progress ring indicator. Base component for Readiness score and sub-metric circles.

**Props**
```ts
interface CircleProps {
  value: number;      // 0–100, clamped at both ends
  color: string;      // stroke color — use design token values (zoneGreen, zoneYellow, zoneRed)
  size?: number;      // diameter in dp, default 80
  label?: string;     // optional text below the circle
}
```

**Usage — basic**
```tsx
import { Circle } from '@resilio/ui-mobile';
<Circle value={75} color={colors.zoneGreen} />
```

**Usage — with label and custom size**
```tsx
<Circle
  value={readinessScore}
  color={readinessScore >= 70 ? colors.zoneGreen : colors.zoneYellow}
  size={120}
  label="Forme"
/>
```

**Edge cases**
- `value < 0` → rendered as 0
- `value > 100` → rendered as 100
- `color` required — no default (must always pass a token)

**Notes**
- Requires `react-native-svg` peer dep
- Track ring uses `colors.dark.border` automatically via `useTheme()`

---

## Button

Primary action button with haptic feedback.

**Props**
```ts
type ButtonVariant = 'primary' | 'secondary' | 'ghost';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;  // default: 'primary'
  disabled?: boolean;       // default: false
  loading?: boolean;        // shows ActivityIndicator, hides title (default: false)
  style?: ViewStyle;        // override button container style
}
```

**Haptic mapping**
| Variant | Haptic |
|---|---|
| `primary` | `ImpactFeedbackStyle.Medium` |
| `secondary` | `ImpactFeedbackStyle.Light` |
| `ghost` | `ImpactFeedbackStyle.Light` |

**Usage**
```tsx
import { Button } from '@resilio/ui-mobile';

// Primary (default)
<Button title="Se connecter" onPress={handleLogin} />

// Secondary with loading
<Button
  title="Sauvegarder"
  onPress={handleSave}
  variant="secondary"
  loading={isSaving}
/>

// Ghost
<Button title="Annuler" onPress={handleCancel} variant="ghost" />

// Disabled
<Button title="Continuer" onPress={handleNext} disabled={!canProceed} />
```

---

## Input

Text input with optional label. Wraps React Native `TextInput`.

**Props**
```ts
interface InputProps extends TextInputProps {
  label?: string;    // renders above the input
  style?: ViewStyle; // override wrapper container style
  // All TextInputProps are also accepted (placeholder, value, onChangeText, etc.)
}
```

**Usage**
```tsx
import { Input } from '@resilio/ui-mobile';

<Input
  label="Email"
  value={email}
  onChangeText={setEmail}
  placeholder="athlete@exemple.com"
  keyboardType="email-address"
  autoCapitalize="none"
/>

<Input
  label="Mot de passe"
  value={password}
  onChangeText={setPassword}
  secureTextEntry
  style={{ marginTop: 16 }}
/>
```

---

## ThemeProvider / useTheme

Context provider for dark/light mode. Required at app root. `useTheme()` in any component.

**Usage**
```tsx
// In _layout.tsx (already configured)
import { ThemeProvider } from '@resilio/ui-mobile';
<ThemeProvider>{children}</ThemeProvider>

// In any component
import { useTheme } from '@resilio/ui-mobile';
const { colorMode, colors } = useTheme();
// colorMode: 'dark' | 'light'
// colors: typeof colors.dark | typeof colors.light (from @resilio/design-tokens)
```

**ThemeContextValue**
```ts
interface ThemeContextValue {
  colorMode: 'dark' | 'light';
  colors: typeof import('@resilio/design-tokens').colors.dark;
  // NB: same type for dark/light — both have same keys, different values
}
```

---

*Updated: Session FE-MOBILE-1B (2026-04-17). Maintained alongside `packages/ui-mobile/src/`.*
