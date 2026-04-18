# UI Integration v1 — Mobile Design Exports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:subagent-driven-development (recommended) or superpowers-optimized:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter 6 exports Claude Design dans apps/mobile (partiel — passe de test Expo Go avant v2).

**Architecture:** Composants partagés dans `packages/ui-mobile`, écrans dans `apps/mobile/app`. Navigation Expo Router câblée bout-en-bout (auth → onboarding → tabs → session). ThemeProvider light/dark déjà opérationnel — aucune modification. Home (`(tabs)/index.tsx`) déjà porté — ne pas toucher.

**Tech Stack:** Expo SDK 54, Expo Router 6, React Native, TypeScript strict, StyleSheet (no NativeWind), @resilio/ui-mobile, @resilio/design-tokens, react-native-svg

**Assumptions:**
- Home (`app/(tabs)/index.tsx`) est complet — exclut toute modification de ce fichier
- `packages/ui-mobile` jest tests passent avant de commencer — confirmer avec `pnpm --filter @resilio/ui-mobile test`
- Résilio Sync actif : chaque fichier doit être committé dans les 30 s après création
- Pas de @gorhom/bottom-sheet — HITLSheet utilise Modal RN natif
- Apple Sign In non implémenté en v1 — placeholder texte uniquement
- `SportType` = `'running' | 'lifting' | 'swimming' | 'cycling' | 'rest'` (identique à SessionCard)

---

## File Structure

### Nouveaux fichiers — packages/ui-mobile

| Fichier | Responsabilité |
|---------|---------------|
| `src/components/ProgressDots.tsx` | 5 segments de progression (onboarding) |
| `src/components/HITLSheet.tsx` | Bottom sheet Modal RN pour options HITL |
| `src/components/DisciplineIcon.tsx` | Icône sport (run/lift/swim/bike/rest) |
| `src/__tests__/ProgressDots.test.tsx` | Tests ProgressDots |
| `src/__tests__/HITLSheet.test.tsx` | Tests HITLSheet |
| `src/__tests__/DisciplineIcon.test.tsx` | Tests DisciplineIcon |

### Fichiers modifiés — packages/ui-mobile

| Fichier | Modification |
|---------|-------------|
| `src/index.ts` | Export ProgressDots, HITLSheet, DisciplineIcon |

### Nouveaux fichiers — apps/mobile

| Fichier | Responsabilité |
|---------|---------------|
| `app/(auth)/_layout.tsx` | Stack sans header pour groupe auth |
| `app/(auth)/signup.tsx` | Inscription email + mot de passe |
| `app/(auth)/forgot-password.tsx` | Demande de réinitialisation mot de passe |
| `app/(onboarding)/_layout.tsx` | Stack sans header pour groupe onboarding |
| `app/(onboarding)/index.tsx` | Machine à 5 états (profil athlète) |
| `app/session/today.tsx` | Prescription séance (mode A) |
| `app/session/live.tsx` | Exécution séance (mode B) |
| `app/(tabs)/training.tsx` | Historique + calendrier entraînements |
| `app/(tabs)/coach.tsx` | Coach Chat (depuis chat.tsx) |
| `app/(tabs)/nutrition.tsx` | Placeholder nutrition |
| `app/metric/[id].tsx` | Placeholder détail métrique |
| `app/settings/integrations.tsx` | Placeholder intégrations |

### Fichiers modifiés — apps/mobile

| Fichier | Modification |
|---------|-------------|
| `app/(auth)/login.tsx` | Réécriture — supprimer SpaceGrotesk, utiliser ui-mobile Text |
| `app/(tabs)/_layout.tsx` | Ajouter training tab, renommer chat→coach, garder check-in |
| `app/_layout.tsx` | Ajouter routes onboarding, session, settings, metric |
| `app/(tabs)/chat.tsx` | Supprimer après création de coach.tsx |

---

## Corrections loggées (anti-patterns)

Toute correction d'anti-pattern doit être loggée dans `docs/ui-integration-corrections-v1.md`.
Format d'entrée :
```
- [Task N] <Fichier> : <anti-pattern> → <correction appliquée>
```

---

## Task 1: ProgressDots — ui-mobile

**Files:**
- Create: `packages/ui-mobile/src/components/ProgressDots.tsx`
- Create: `packages/ui-mobile/src/__tests__/ProgressDots.test.tsx`

**Does NOT cover:** animations de transition entre steps (Reanimated) — v2 uniquement.

- [ ] **Step 1: Write failing test**

```tsx
// packages/ui-mobile/src/__tests__/ProgressDots.test.tsx
import React from 'react';
import { renderWithTheme } from './helpers';
import { ProgressDots } from '../components/ProgressDots';

describe('ProgressDots', () => {
  it('renders correct number of segments', () => {
    const { getAllByTestId } = renderWithTheme(
      <ProgressDots step={0} total={5} />
    );
    expect(getAllByTestId('progress-dot')).toHaveLength(5);
  });

  it('renders with default total=5', () => {
    const { getAllByTestId } = renderWithTheme(
      <ProgressDots step={2} />
    );
    expect(getAllByTestId('progress-dot')).toHaveLength(5);
  });

  it('renders custom total', () => {
    const { getAllByTestId } = renderWithTheme(
      <ProgressDots step={1} total={3} />
    );
    expect(getAllByTestId('progress-dot')).toHaveLength(3);
  });

  it('renders without crash at step 0', () => {
    expect(() => renderWithTheme(<ProgressDots step={0} />)).not.toThrow();
  });

  it('renders without crash at last step', () => {
    expect(() => renderWithTheme(<ProgressDots step={4} total={5} />)).not.toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --filter @resilio/ui-mobile test -- --testPathPattern=ProgressDots`
Expected: FAIL — "Cannot find module '../components/ProgressDots'"

- [ ] **Step 3: Implement**

```tsx
// packages/ui-mobile/src/components/ProgressDots.tsx
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { colors } from '@resilio/design-tokens';
import { useTheme } from '../theme/ThemeProvider';

interface ProgressDotsProps {
  /** 0-indexed current step. Segments 0..step are filled. */
  step: number;
  total?: number;
}

export function ProgressDots({ step, total = 5 }: ProgressDotsProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <View style={styles.row}>
      {Array.from({ length: total }).map((_, i) => (
        <View
          key={i}
          testID="progress-dot"
          style={[
            styles.dot,
            { backgroundColor: i <= step ? colors.accent : themeColors.border },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 6, alignItems: 'center' },
  dot: { height: 3, width: 28, borderRadius: 2 },
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --filter @resilio/ui-mobile test -- --testPathPattern=ProgressDots`
Expected: PASS — 5 tests

- [ ] **Step 5: Commit**

```bash
git add packages/ui-mobile/src/components/ProgressDots.tsx packages/ui-mobile/src/__tests__/ProgressDots.test.tsx
git commit -m "feat(ui-mobile): add ProgressDots component"
```

---

## Task 2: HITLSheet — ui-mobile

**Files:**
- Create: `packages/ui-mobile/src/components/HITLSheet.tsx`
- Create: `packages/ui-mobile/src/__tests__/HITLSheet.test.tsx`

**Does NOT cover:** gesture swipe-to-dismiss (nécessiterait @gorhom/bottom-sheet — v2). Ne couvre pas les options avec icônes.

- [ ] **Step 1: Write failing test**

```tsx
// packages/ui-mobile/src/__tests__/HITLSheet.test.tsx
import React from 'react';
import { fireEvent } from '@testing-library/react-native';
import { renderWithTheme } from './helpers';
import { HITLSheet } from '../components/HITLSheet';

const OPTIONS = [
  { id: 'a', label: 'Option A', description: 'Desc A' },
  { id: 'b', label: 'Option B' },
];

describe('HITLSheet', () => {
  it('renders title when visible', () => {
    const { getByText } = renderWithTheme(
      <HITLSheet visible title="Choisir" options={OPTIONS} onSelect={() => {}} onDismiss={() => {}} />
    );
    expect(getByText('Choisir')).toBeTruthy();
  });

  it('renders all option labels', () => {
    const { getByText } = renderWithTheme(
      <HITLSheet visible title="T" options={OPTIONS} onSelect={() => {}} onDismiss={() => {}} />
    );
    expect(getByText('Option A')).toBeTruthy();
    expect(getByText('Option B')).toBeTruthy();
  });

  it('calls onSelect with option id when pressed', () => {
    const onSelect = jest.fn();
    const onDismiss = jest.fn();
    const { getByText } = renderWithTheme(
      <HITLSheet visible title="T" options={OPTIONS} onSelect={onSelect} onDismiss={onDismiss} />
    );
    fireEvent.press(getByText('Option A'));
    expect(onSelect).toHaveBeenCalledWith('a');
    expect(onDismiss).toHaveBeenCalled();
  });

  it('calls onDismiss when Annuler pressed', () => {
    const onDismiss = jest.fn();
    const { getByText } = renderWithTheme(
      <HITLSheet visible title="T" options={OPTIONS} onSelect={() => {}} onDismiss={onDismiss} />
    );
    fireEvent.press(getByText('Annuler'));
    expect(onDismiss).toHaveBeenCalled();
  });

  it('renders without crash when not visible', () => {
    expect(() =>
      renderWithTheme(
        <HITLSheet visible={false} title="T" options={OPTIONS} onSelect={() => {}} onDismiss={() => {}} />
      )
    ).not.toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --filter @resilio/ui-mobile test -- --testPathPattern=HITLSheet`
Expected: FAIL — "Cannot find module '../components/HITLSheet'"

- [ ] **Step 3: Implement**

```tsx
// packages/ui-mobile/src/components/HITLSheet.tsx
import React from 'react';
import { View, Modal, Pressable, StyleSheet, ScrollView } from 'react-native';
import { Text } from './Text';
import { Button } from './Button';
import { useTheme } from '../theme/ThemeProvider';

export interface HITLOption {
  id: string;
  label: string;
  description?: string;
}

interface HITLSheetProps {
  visible: boolean;
  title: string;
  options: HITLOption[];
  onSelect: (id: string) => void;
  onDismiss: () => void;
}

export function HITLSheet({
  visible, title, options, onSelect, onDismiss,
}: HITLSheetProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onDismiss}
    >
      <Pressable
        style={styles.overlay}
        onPress={onDismiss}
        accessibilityLabel="Fermer"
      />
      <View
        style={[
          styles.sheet,
          {
            backgroundColor: themeColors.surface1,
            borderColor: themeColors.border,
          },
        ]}
      >
        <View style={[styles.handle, { backgroundColor: themeColors.border }]} />
        <Text variant="body" color={themeColors.foreground} style={styles.title}>
          {title}
        </Text>
        <ScrollView style={styles.scroll} bounces={false}>
          {options.map((opt) => (
            <Pressable
              key={opt.id}
              style={[styles.option, { borderColor: themeColors.border }]}
              onPress={() => { onSelect(opt.id); onDismiss(); }}
            >
              <Text variant="body" color={themeColors.foreground}>{opt.label}</Text>
              {opt.description !== undefined && (
                <Text variant="secondary" color={themeColors.textSecondary}>
                  {opt.description}
                </Text>
              )}
            </Pressable>
          ))}
        </ScrollView>
        <Button variant="ghost" title="Annuler" onPress={onDismiss} style={styles.cancel} />
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' },
  sheet: {
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    borderWidth: 0.5,
    paddingTop: 12,
    paddingHorizontal: 20,
    paddingBottom: 40,
    maxHeight: '80%',
  },
  handle: {
    width: 36, height: 4, borderRadius: 2,
    alignSelf: 'center', marginBottom: 20,
  },
  title: { fontWeight: '600', marginBottom: 16 } as const,
  scroll: { flexGrow: 0 },
  option: {
    paddingVertical: 14,
    borderBottomWidth: 0.5,
    gap: 4,
  },
  cancel: { marginTop: 12 },
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --filter @resilio/ui-mobile test -- --testPathPattern=HITLSheet`
Expected: PASS — 5 tests

- [ ] **Step 5: Commit**

```bash
git add packages/ui-mobile/src/components/HITLSheet.tsx packages/ui-mobile/src/__tests__/HITLSheet.test.tsx
git commit -m "feat(ui-mobile): add HITLSheet component (Modal RN)"
```

---

## Task 3: DisciplineIcon — ui-mobile

**Files:**
- Create: `packages/ui-mobile/src/components/DisciplineIcon.tsx`
- Create: `packages/ui-mobile/src/__tests__/DisciplineIcon.test.tsx`
- Modify: `packages/ui-mobile/src/index.ts`

**Does NOT cover:** tailles autres que `size` prop — pas de variantes prédéfinies (sm/md/lg).

- [ ] **Step 1: Write failing test**

```tsx
// packages/ui-mobile/src/__tests__/DisciplineIcon.test.tsx
import React from 'react';
import { renderWithTheme } from './helpers';
import { DisciplineIcon } from '../components/DisciplineIcon';
import type { SportType } from './SessionCard';

describe('DisciplineIcon', () => {
  const sports: Array<import('../components/SessionCard').SportType> = [
    'running', 'lifting', 'swimming', 'cycling', 'rest',
  ];

  sports.forEach((sport) => {
    it(`renders without crash for sport=${sport}`, () => {
      expect(() =>
        renderWithTheme(<DisciplineIcon sport={sport} />)
      ).not.toThrow();
    });
  });

  it('accepts custom size', () => {
    expect(() =>
      renderWithTheme(<DisciplineIcon sport="running" size={24} />)
    ).not.toThrow();
  });

  it('accepts custom color', () => {
    expect(() =>
      renderWithTheme(<DisciplineIcon sport="lifting" color="#ff0000" />)
    ).not.toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --filter @resilio/ui-mobile test -- --testPathPattern=DisciplineIcon`
Expected: FAIL — "Cannot find module '../components/DisciplineIcon'"

- [ ] **Step 3: Implement**

```tsx
// packages/ui-mobile/src/components/DisciplineIcon.tsx
import React from 'react';
import { IconComponent } from '../Icon';
import type { IconName } from '../Icon';
import type { SportType } from './SessionCard';

interface DisciplineIconProps {
  sport: SportType;
  size?: number;
  color?: string;
}

const SPORT_ICON: Record<SportType, IconName> = {
  running:  'Activity',
  lifting:  'Lifting',
  swimming: 'Swimming',
  cycling:  'Biking',
  rest:     'DarkMode',
};

export function DisciplineIcon({ sport, size = 18, color }: DisciplineIconProps): React.JSX.Element {
  return (
    <IconComponent
      name={SPORT_ICON[sport] ?? 'Activity'}
      size={size}
      color={color}
    />
  );
}
```

Ajouter les exports dans `packages/ui-mobile/src/index.ts` :

```tsx
// Ajouter après les exports existants :
export { ProgressDots } from './components/ProgressDots';
export { HITLSheet } from './components/HITLSheet';
export type { HITLOption } from './components/HITLSheet';
export { DisciplineIcon } from './components/DisciplineIcon';
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --filter @resilio/ui-mobile test -- --testPathPattern=DisciplineIcon`
Expected: PASS — 7 tests

- [ ] **Step 5: Run full ui-mobile test suite**

Run: `pnpm --filter @resilio/ui-mobile test`
Expected: tous les tests passent (aucune régression)

- [ ] **Step 6: Commit**

```bash
git add packages/ui-mobile/src/components/DisciplineIcon.tsx packages/ui-mobile/src/__tests__/DisciplineIcon.test.tsx packages/ui-mobile/src/index.ts
git commit -m "feat(ui-mobile): add DisciplineIcon + export ProgressDots/HITLSheet/DisciplineIcon"
```

---

## Task 4: (auth) group — layout + login rewrite

**Files:**
- Create: `apps/mobile/app/(auth)/_layout.tsx`
- Modify: `apps/mobile/app/(auth)/login.tsx` (backup avant modification)

**Does NOT cover:** Apple Sign In (placeholder texte). Ne couvre pas la persistance token JWT (mock seulement en v1).

> **Correction loggée :** login.tsx — SpaceGrotesk → Inter (Text ui-mobile), RN Text brut → Text ui-mobile, hex hardcodés → themeColors.*

- [ ] **Step 1: Créer le backup de login.tsx**

```bash
cp apps/mobile/app/\(auth\)/login.tsx apps/mobile/app/\(auth\)/login.tsx.v1-backup
git add apps/mobile/app/\(auth\)/login.tsx.v1-backup
git commit -m "chore(mobile): backup login.tsx before v1 rewrite"
```

- [ ] **Step 2: Créer (auth)/_layout.tsx**

```tsx
// apps/mobile/app/(auth)/_layout.tsx
import { Stack } from 'expo-router';

export default function AuthLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
```

- [ ] **Step 3: Réécrire login.tsx**

```tsx
// apps/mobile/app/(auth)/login.tsx
import { useState, useCallback } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Text, Button, Input, Card, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

export default function LoginScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = useCallback(async () => {
    if (!email || !password) {
      setError('Email et mot de passe requis.');
      return;
    }
    setError('');
    setLoading(true);
    await new Promise<void>((r) => setTimeout(r, 800));
    setLoading(false);
    router.replace('/(tabs)');
  }, [email, password, router]);

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: themeColors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        {/* Wordmark */}
        <View style={styles.wordmarkRow}>
          <Text variant="title" color={themeColors.foreground}>Resilio</Text>
          <Text variant="title" color={colors.accent}>+</Text>
        </View>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.subtitle}>
          Ta plateforme de coaching hybride
        </Text>

        {/* Form */}
        <Card style={styles.card}>
          <Input
            label="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
          />
          <Input
            label="Mot de passe"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="current-password"
            style={styles.inputGap}
          />
          {error !== '' && (
            <Text variant="secondary" color={colors.zoneRed} style={styles.error}>
              {error}
            </Text>
          )}
          <Button
            title={loading ? 'Connexion…' : 'Se connecter'}
            onPress={handleLogin}
            disabled={loading}
            loading={loading}
            style={styles.loginBtn}
          />
        </Card>

        {/* Apple Sign In placeholder */}
        <Text variant="secondary" color={themeColors.textMuted} style={styles.applePlaceholder}>
          Connexion Apple — bientôt disponible
        </Text>

        {/* Footer links */}
        <View style={styles.footer}>
          <Pressable onPress={() => router.push('/(auth)/forgot-password')}>
            <Text variant="secondary" color={themeColors.textSecondary}>
              Mot de passe oublié
            </Text>
          </Pressable>
          <Text variant="secondary" color={themeColors.textMuted}>·</Text>
          <Pressable onPress={() => router.push('/(auth)/signup')}>
            <Text variant="secondary" color={colors.accent}>
              Créer un compte
            </Text>
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
    paddingVertical: 48,
  },
  wordmarkRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 0,
    marginBottom: 8,
  },
  subtitle: { textAlign: 'center', marginBottom: 32 },
  card: { width: '100%' },
  inputGap: { marginTop: 16 },
  error: { marginTop: 8 },
  loginBtn: { marginTop: 24 },
  applePlaceholder: { textAlign: 'center', marginTop: 20 },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    marginTop: 24,
  },
});
```

- [ ] **Step 4: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 5: Logger les corrections**

Créer `docs/ui-integration-corrections-v1.md` avec :
```markdown
# UI Integration v1 — Corrections d'anti-patterns

- [Task 4] app/(auth)/login.tsx : SpaceGrotesk → Inter (via Text ui-mobile)
- [Task 4] app/(auth)/login.tsx : `Text` RN brut → `Text` de @resilio/ui-mobile
- [Task 4] app/(auth)/login.tsx : hex hardcodés → themeColors.* via useTheme()
- [Task 4] app/(auth)/login.tsx : `colors.primary` (ancien) → `colors.accent`
```

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/app/\(auth\)/_layout.tsx apps/mobile/app/\(auth\)/login.tsx docs/ui-integration-corrections-v1.md
git commit -m "feat(ui): integrate auth layout + rewrite login (Inter, design tokens)"
```

---

## Task 5: signup.tsx

**Files:**
- Create: `apps/mobile/app/(auth)/signup.tsx`

**Does NOT cover:** validation robuste email/mot de passe (format, longueur) — mock seulement.

- [ ] **Step 1: Créer signup.tsx**

```tsx
// apps/mobile/app/(auth)/signup.tsx
import { useState, useCallback } from 'react';
import React from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Text, Button, Input, Card, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

export default function SignupScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSignup = useCallback(async () => {
    if (!email || !password) {
      setError('Email et mot de passe requis.');
      return;
    }
    if (password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.');
      return;
    }
    setError('');
    setLoading(true);
    await new Promise<void>((r) => setTimeout(r, 800));
    setLoading(false);
    // Post-signup → onboarding
    router.replace('/(onboarding)');
  }, [email, password, router]);

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: themeColors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} style={styles.back}>
            <Text variant="secondary" color={themeColors.textSecondary}>← Retour</Text>
          </Pressable>
          <Text variant="title" color={themeColors.foreground}>Créer un compte</Text>
          <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
            Quelques secondes pour commencer.
          </Text>
        </View>

        <Card style={styles.card}>
          <Input
            label="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
          />
          <Input
            label="Mot de passe"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="new-password"
            style={styles.inputGap}
          />
          {error !== '' && (
            <Text variant="secondary" color={colors.zoneRed} style={styles.error}>
              {error}
            </Text>
          )}
          <Button
            title={loading ? 'Création…' : 'Créer mon compte'}
            onPress={handleSignup}
            disabled={loading}
            loading={loading}
            style={styles.btn}
          />
        </Card>

        <View style={styles.footer}>
          <Text variant="secondary" color={themeColors.textMuted}>Déjà un compte ?</Text>
          <Pressable onPress={() => router.replace('/(auth)/login')}>
            <Text variant="secondary" color={colors.accent}> Se connecter</Text>
          </Pressable>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24, paddingVertical: 48 },
  header: { marginBottom: 32 },
  back: { marginBottom: 24 },
  sub: { marginTop: 8 },
  card: { width: '100%' },
  inputGap: { marginTop: 16 },
  error: { marginTop: 8 },
  btn: { marginTop: 24 },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: 24 },
});
```

- [ ] **Step 2: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 3: Logger correction**

Ajouter dans `docs/ui-integration-corrections-v1.md` :
```
- [Task 5] app/(auth)/signup.tsx : accent oklch(0.62 0.14 35) → colors.accent (#3B74C9)
- [Task 5] app/(auth)/signup.tsx : Space Grotesk → Inter via Text ui-mobile
```

- [ ] **Step 4: Commit**

```bash
git add apps/mobile/app/\(auth\)/signup.tsx docs/ui-integration-corrections-v1.md
git commit -m "feat(ui): integrate signup screen"
```

---

## Task 6: forgot-password.tsx

**Files:**
- Create: `apps/mobile/app/(auth)/forgot-password.tsx`

**Does NOT cover:** envoi réel d'email — mock seulement.

- [ ] **Step 1: Créer forgot-password.tsx**

```tsx
// apps/mobile/app/(auth)/forgot-password.tsx
import React, { useState, useCallback } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Text, Button, Input, Card, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

export default function ForgotPasswordScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();

  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSend = useCallback(async () => {
    if (!email) return;
    setLoading(true);
    await new Promise<void>((r) => setTimeout(r, 800));
    setLoading(false);
    setSent(true);
  }, [email]);

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: themeColors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Pressable onPress={() => router.back()} style={styles.back}>
            <Text variant="secondary" color={themeColors.textSecondary}>← Retour</Text>
          </Pressable>
          <Text variant="title" color={themeColors.foreground}>Mot de passe oublié</Text>
          <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
            Indique ton adresse email. Tu recevras un lien de réinitialisation.
          </Text>
        </View>

        {sent ? (
          <Card style={styles.card}>
            <Text variant="body" color={themeColors.foreground}>
              Lien envoyé. Vérifie ta boîte de réception.
            </Text>
            <Button
              title="Retour à la connexion"
              variant="secondary"
              onPress={() => router.replace('/(auth)/login')}
              style={styles.btn}
            />
          </Card>
        ) : (
          <Card style={styles.card}>
            <Input
              label="Email"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
            />
            <Button
              title={loading ? 'Envoi…' : 'Envoyer le lien'}
              onPress={handleSend}
              disabled={loading || !email}
              loading={loading}
              style={styles.btn}
            />
          </Card>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24, paddingVertical: 48 },
  header: { marginBottom: 32 },
  back: { marginBottom: 24 },
  sub: { marginTop: 8 },
  card: { width: '100%' },
  btn: { marginTop: 24 },
});
```

- [ ] **Step 2: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 3: Commit**

```bash
git add apps/mobile/app/\(auth\)/forgot-password.tsx
git commit -m "feat(ui): integrate forgot-password screen"
```

---

## Task 7: Onboarding — layout + 5 steps

**Files:**
- Create: `apps/mobile/app/(onboarding)/_layout.tsx`
- Create: `apps/mobile/app/(onboarding)/index.tsx`

**Does NOT cover:** persistance des réponses (pas d'API call). Ne couvre pas la navigation skip vers tabs sans compléter le flow.

> **Correction loggée :** Space Grotesk → Inter, JetBrains Mono → SpaceMono, bg hardcodé → themeColors.background

- [ ] **Step 1: Créer (onboarding)/_layout.tsx**

```tsx
// apps/mobile/app/(onboarding)/_layout.tsx
import { Stack } from 'expo-router';

export default function OnboardingLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
```

- [ ] **Step 2: Créer (onboarding)/index.tsx**

```tsx
// apps/mobile/app/(onboarding)/index.tsx
import React, { useState, useCallback } from 'react';
import { View, StyleSheet, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Text, Button, Card, ProgressDots, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

type Step = 0 | 1 | 2 | 3 | 4;
const TOTAL = 5;

interface StepConfig {
  label: string;
  title: string;
  sub: string;
  options: string[];
}

const STEPS: Record<Step, StepConfig> = {
  0: {
    label: 'ÉTAPE 1 / 5',
    title: 'Quels sports pratiques-tu ?',
    sub: 'Sélectionne tout ce qui s\'applique.',
    options: ['Course à pied', 'Musculation', 'Natation', 'Cyclisme'],
  },
  1: {
    label: 'ÉTAPE 2 / 5',
    title: 'Quel est ton objectif principal ?',
    sub: 'Un seul objectif pour commencer.',
    options: ['Perdre du poids', 'Gagner en endurance', 'Améliorer ma force', 'Compétition'],
  },
  2: {
    label: 'ÉTAPE 3 / 5',
    title: 'Combien d\'heures par semaine ?',
    sub: 'Volume d\'entraînement hebdomadaire visé.',
    options: ['Moins de 3 h', '3–5 h', '6–8 h', 'Plus de 8 h'],
  },
  3: {
    label: 'ÉTAPE 4 / 5',
    title: 'Quel est ton niveau ?',
    sub: 'Auto-évaluation honnête.',
    options: ['Débutant', 'Intermédiaire', 'Avancé', 'Compétiteur'],
  },
  4: {
    label: 'ÉTAPE 5 / 5',
    title: 'Connecte tes applis',
    sub: 'Optionnel — tu peux le faire plus tard dans les réglages.',
    options: ['Strava', 'Hevy', 'Apple Santé', 'Passer cette étape'],
  },
};

export default function OnboardingScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();

  const [step, setStep] = useState<Step>(0);
  const [answers, setAnswers] = useState<Partial<Record<Step, string>>>({});

  const config = STEPS[step];
  const canContinue = answers[step] !== undefined;
  const isLast = step === TOTAL - 1;

  const handleSelect = useCallback((option: string) => {
    setAnswers((prev) => ({ ...prev, [step]: option }));
  }, [step]);

  const handleNext = useCallback(() => {
    if (isLast) {
      router.replace('/(tabs)');
    } else {
      setStep((s) => (s + 1) as Step);
    }
  }, [isLast, router]);

  const handleBack = useCallback(() => {
    if (step === 0) {
      router.back();
    } else {
      setStep((s) => (s - 1) as Step);
    }
  }, [step, router]);

  return (
    <Screen>
      {/* Top bar */}
      <View style={[styles.topBar, { borderBottomColor: themeColors.border }]}>
        <Pressable onPress={handleBack} style={styles.backBtn}>
          <Text variant="secondary" color={step === 0 ? themeColors.textMuted : themeColors.textSecondary}>
            ← Retour
          </Text>
        </Pressable>
        <ProgressDots step={step} total={TOTAL} />
        <Pressable onPress={() => router.replace('/(tabs)')} style={styles.skipBtn}>
          <Text variant="secondary" color={themeColors.textMuted}>Passer</Text>
        </Pressable>
      </View>

      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        {/* Step label */}
        <Text
          variant="label"
          color={themeColors.textMuted}
          style={styles.stepLabel}
        >
          {config.label}
        </Text>

        {/* Title */}
        <Text variant="title" color={themeColors.foreground} style={styles.title}>
          {config.title}
        </Text>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
          {config.sub}
        </Text>

        {/* Options */}
        <View style={styles.options}>
          {config.options.map((option) => {
            const selected = answers[step] === option;
            return (
              <Pressable
                key={option}
                onPress={() => handleSelect(option)}
                style={[
                  styles.optionCard,
                  {
                    backgroundColor: selected ? colors.accentDim : themeColors.surface1,
                    borderColor: selected ? colors.accent : themeColors.border,
                  },
                ]}
              >
                <Text
                  variant="body"
                  color={selected ? colors.accent : themeColors.foreground}
                >
                  {option}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </ScrollView>

      {/* CTA */}
      <View style={[styles.cta, { borderTopColor: themeColors.border }]}>
        <Button
          title={isLast ? 'Commencer' : 'Continuer'}
          onPress={handleNext}
          disabled={!canContinue}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 0.5,
  },
  backBtn: { padding: 4, minWidth: 60 },
  skipBtn: { padding: 4, minWidth: 60, alignItems: 'flex-end' },
  content: { paddingHorizontal: 24, paddingTop: 28, paddingBottom: 24 },
  stepLabel: {
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 14,
  },
  title: { marginBottom: 10 },
  sub: { marginBottom: 28 },
  options: { gap: 10 },
  optionCard: {
    borderRadius: 16,
    borderWidth: 0.5,
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  cta: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 32,
    borderTopWidth: 0.5,
  },
});
```

- [ ] **Step 3: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 4: Logger corrections**

Ajouter dans `docs/ui-integration-corrections-v1.md` :
```
- [Task 7] app/(onboarding)/index.tsx : Space Grotesk → Inter via Text ui-mobile
- [Task 7] app/(onboarding)/index.tsx : JetBrains Mono → SpaceMono (via Text variant="mono")
- [Task 7] app/(onboarding)/index.tsx : accent oklch → colors.accent + accentDim pour sélection
```

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/app/\(onboarding\)/_layout.tsx apps/mobile/app/\(onboarding\)/index.tsx docs/ui-integration-corrections-v1.md
git commit -m "feat(ui): integrate onboarding 5-step screen"
```

---

## Task 8: session/today.tsx — Prescription séance

**Files:**
- Create: `apps/mobile/app/session/today.tsx`

**Does NOT cover:** données réelles API (mock statique). Ne couvre pas le lancement effectif de la séance (bouton navigue vers live.tsx).

> **Correction loggée :** font Space Grotesk → Inter, div → View, bg hardcodé → themeColors.*

- [ ] **Step 1: Créer session/today.tsx**

```tsx
// apps/mobile/app/session/today.tsx
import React from 'react';
import { View, StyleSheet, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Text, Button, Card, DisciplineIcon, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

interface Block {
  label: string;
  reps?: string;
  duration?: string;
  rest?: string;
  note?: string;
}

const MOCK_SESSION = {
  sport: 'running' as const,
  category: 'Séance course · Z2',
  title: 'Endurance fondamentale',
  duration: '52 min',
  load: 'Modérée',
  zone: 'Zone 2 — 65–75 % FCmax',
  why: 'Cette séance développe ta base aérobie. Le volume Z2 est le fondement de l\'endurance à long terme — tu dois pouvoir tenir une conversation sans effort.',
  blocks: [
    { label: 'Échauffement', duration: '10 min', note: 'Allure très facile' },
    { label: 'Bloc principal', duration: '34 min', note: 'Z2 — allure conversationnelle' },
    { label: 'Retour au calme', duration: '8 min', note: 'Décompression progressive' },
  ] as Block[],
};

export default function TodaySessionScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();

  return (
    <Screen>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: themeColors.border }]}>
        <Pressable onPress={() => router.back()} style={styles.backBtn}>
          <Text variant="secondary" color={themeColors.textSecondary}>← Retour</Text>
        </Pressable>
        <View style={styles.headerCenter}>
          <Text variant="label" color={themeColors.textMuted} style={styles.headerSub}>
            {MOCK_SESSION.category.toUpperCase()}
          </Text>
          <Text variant="body" color={themeColors.foreground} style={styles.headerTitle}>
            {MOCK_SESSION.title}
          </Text>
        </View>
        <View style={styles.headerRight} />
      </View>

      <ScrollView style={styles.flex} contentContainerStyle={styles.content}>
        {/* Sport + titre */}
        <View style={styles.titleRow}>
          <DisciplineIcon sport={MOCK_SESSION.sport} size={20} color={themeColors.textMuted} />
          <Text variant="title" color={themeColors.foreground} style={styles.titleText}>
            {MOCK_SESSION.title}
          </Text>
        </View>

        {/* Meta row */}
        <View style={[styles.metaRow, { borderColor: themeColors.border }]}>
          <MetaCell label="Durée" value={MOCK_SESSION.duration} themeColors={themeColors} />
          <View style={[styles.metaSep, { backgroundColor: themeColors.border }]} />
          <MetaCell label="Charge" value={MOCK_SESSION.load} themeColors={themeColors} />
          <View style={[styles.metaSep, { backgroundColor: themeColors.border }]} />
          <MetaCell label="Intensité" value="Z2" themeColors={themeColors} />
        </View>

        {/* Pourquoi */}
        <Card style={styles.whyCard}>
          <Text variant="label" color={themeColors.textMuted} style={styles.whyLabel}>
            POURQUOI CETTE SÉANCE
          </Text>
          <Text variant="body" color={themeColors.textSecondary} style={styles.whyText}>
            {MOCK_SESSION.why}
          </Text>
        </Card>

        {/* Prescription */}
        <Text variant="label" color={themeColors.textMuted} style={styles.sectionLabel}>
          DÉROULÉ
        </Text>
        {MOCK_SESSION.blocks.map((block, i) => (
          <Card key={i} style={styles.blockCard}>
            <View style={styles.blockHeader}>
              <Text variant="body" color={themeColors.foreground}>{block.label}</Text>
              {block.duration !== undefined && (
                <Text variant="secondary" color={themeColors.textMuted} style={{ fontVariant: ['tabular-nums'] }}>
                  {block.duration}
                </Text>
              )}
            </View>
            {block.note !== undefined && (
              <Text variant="secondary" color={themeColors.textSecondary} style={styles.blockNote}>
                {block.note}
              </Text>
            )}
          </Card>
        ))}
      </ScrollView>

      {/* CTA fixe bas */}
      <View style={[styles.cta, { borderTopColor: themeColors.border, backgroundColor: themeColors.background }]}>
        <Button
          title="Démarrer la séance"
          onPress={() => router.push('/session/live')}
        />
      </View>
    </Screen>
  );
}

function MetaCell({ label, value, themeColors }: { label: string; value: string; themeColors: ReturnType<typeof useTheme>['colors'] }) {
  return (
    <View style={styles.metaCell}>
      <Text variant="label" color={themeColors.textMuted} style={styles.metaCellLabel}>
        {label.toUpperCase()}
      </Text>
      <Text variant="body" color={themeColors.foreground} style={{ fontVariant: ['tabular-nums'] }}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 0.5,
  },
  backBtn: { width: 36, padding: 4 },
  headerCenter: { flex: 1, alignItems: 'center' },
  headerSub: { textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 2 },
  headerTitle: { fontWeight: '500' } as const,
  headerRight: { width: 36 },
  content: { paddingHorizontal: 20, paddingBottom: 32, paddingTop: 20 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 16 },
  titleText: { flex: 1 },
  metaRow: {
    flexDirection: 'row',
    borderRadius: 14,
    borderWidth: 0.5,
    overflow: 'hidden',
    marginBottom: 16,
  },
  metaCell: { flex: 1, alignItems: 'center', paddingVertical: 12 },
  metaCellLabel: { textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 4 },
  metaSep: { width: 0.5 },
  whyCard: { marginBottom: 20 },
  whyLabel: { textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8 },
  whyText: { lineHeight: 20 },
  sectionLabel: { textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 12 },
  blockCard: { marginBottom: 8 },
  blockHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  blockNote: { marginTop: 4 },
  cta: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 32,
    borderTopWidth: 0.5,
  },
});
```

- [ ] **Step 2: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 3: Logger corrections**

Ajouter dans `docs/ui-integration-corrections-v1.md` :
```
- [Task 8] app/session/today.tsx : Space Grotesk → Inter via Text ui-mobile
- [Task 8] app/session/today.tsx : div → View/ScrollView, button → Pressable
- [Task 8] app/session/today.tsx : bg hardcodé → themeColors.*
```

- [ ] **Step 4: Commit**

```bash
git add apps/mobile/app/session/today.tsx docs/ui-integration-corrections-v1.md
git commit -m "feat(ui): integrate session prescription screen (today.tsx)"
```

---

## Task 9: session/live.tsx — Exécution séance

**Files:**
- Create: `apps/mobile/app/session/live.tsx`

**Does NOT cover:** chronomètre réel (mock elapsed statique). Ne couvre pas l'enregistrement des données en temps réel.

> **Correction loggée :** polices, couleurs identiques à Task 8.

- [ ] **Step 1: Créer session/live.tsx**

```tsx
// apps/mobile/app/session/live.tsx
import React, { useState, useCallback } from 'react';
import { View, StyleSheet, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Text, Button, Card, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';
import * as Haptics from 'expo-haptics';

export default function LiveSessionScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();
  const [paused, setPaused] = useState(false);

  const handlePause = useCallback(async () => {
    setPaused((p) => !p);
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
  }, []);

  const handleEnd = useCallback(async () => {
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    router.replace('/(tabs)');
  }, [router]);

  return (
    <Screen>
      {/* Header en cours */}
      <View style={[styles.header, { borderBottomColor: themeColors.border }]}>
        <View style={styles.headerInfo}>
          <Text variant="label" color={themeColors.textMuted} style={styles.enCours}>
            EN COURS
          </Text>
          <Text variant="body" color={themeColors.foreground} style={styles.sessionTitle}>
            Endurance fondamentale Z2
          </Text>
          <Text variant="secondary" color={themeColors.textMuted} style={{ fontVariant: ['tabular-nums'] }}>
            12:34 / 52:00
          </Text>
        </View>
        <Pressable
          onPress={handlePause}
          style={[styles.pauseBtn, { borderColor: themeColors.border }]}
          accessibilityLabel={paused ? 'Reprendre' : 'Pause'}
        >
          <Text variant="secondary" color={themeColors.foreground}>
            {paused ? '▶' : '⏸'}
          </Text>
        </Pressable>
      </View>

      <ScrollView style={styles.flex} contentContainerStyle={styles.content}>
        {/* Phase chip */}
        <View style={styles.phaseRow}>
          <View style={[styles.phaseDot, { backgroundColor: colors.accent }]} />
          <Text variant="label" color={themeColors.textMuted} style={styles.phaseLabel}>
            BLOC PRINCIPAL · Z2 · 2/3
          </Text>
        </View>

        {/* Cible principale */}
        <Card style={styles.targetCard}>
          <Text variant="label" color={themeColors.textMuted} style={styles.targetLabel}>
            ALLURE CIBLE
          </Text>
          <Text
            variant="display"
            color={themeColors.foreground}
            style={styles.targetValue}
          >
            5:20
          </Text>
          <Text variant="secondary" color={themeColors.textMuted}>
            min/km
          </Text>
        </Card>

        {/* Stats secondaires */}
        <View style={styles.statsRow}>
          <StatCard label="FC CIBLE" value="145–155" unit="bpm" themeColors={themeColors} />
          <StatCard label="RPE CIBLE" value="5–6" unit="/ 10" themeColors={themeColors} />
        </View>

        {/* Zone cible */}
        <Card style={styles.zoneCard}>
          <View style={[styles.zoneBadge, { backgroundColor: colors.accentDim }]}>
            <Text variant="secondary" color={colors.accent}>Zone 2 — Fondamental</Text>
          </View>
          <Text variant="secondary" color={themeColors.textSecondary} style={styles.zoneDesc}>
            Maintiens une allure conversationnelle. Si tu ne peux pas parler, ralentis.
          </Text>
        </Card>
      </ScrollView>

      {/* CTA terminer */}
      <View style={[styles.cta, { borderTopColor: themeColors.border, backgroundColor: themeColors.background }]}>
        <Button
          title="Terminer la séance"
          variant="secondary"
          onPress={handleEnd}
        />
      </View>
    </Screen>
  );
}

function StatCard({ label, value, unit, themeColors }: {
  label: string; value: string; unit: string;
  themeColors: ReturnType<typeof useTheme>['colors'];
}) {
  return (
    <Card style={styles.statCard}>
      <Text variant="label" color={themeColors.textMuted} style={styles.statLabel}>
        {label}
      </Text>
      <Text variant="headline" color={themeColors.foreground} style={{ fontVariant: ['tabular-nums'] }}>
        {value}
      </Text>
      <Text variant="secondary" color={themeColors.textMuted}>{unit}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 0.5,
  },
  headerInfo: { flex: 1 },
  enCours: { textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 2 },
  sessionTitle: { fontWeight: '500', marginBottom: 2 } as const,
  pauseBtn: {
    width: 40, height: 40, borderRadius: 20,
    borderWidth: 1, alignItems: 'center', justifyContent: 'center',
  },
  content: { paddingHorizontal: 20, paddingBottom: 32, paddingTop: 16 },
  phaseRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 16 },
  phaseDot: { width: 8, height: 8, borderRadius: 4 },
  phaseLabel: { textTransform: 'uppercase', letterSpacing: 0.5 },
  targetCard: { alignItems: 'center', paddingVertical: 24, marginBottom: 12 },
  targetLabel: { textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8 },
  targetValue: { fontSize: 72, fontWeight: '300', letterSpacing: -2, lineHeight: 72 },
  statsRow: { flexDirection: 'row', gap: 10, marginBottom: 12 },
  statCard: { flex: 1, alignItems: 'center', paddingVertical: 16 },
  statLabel: { textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 6 },
  zoneCard: { marginBottom: 8 },
  zoneBadge: { borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6, alignSelf: 'flex-start', marginBottom: 8 },
  zoneDesc: { lineHeight: 20 },
  cta: { paddingHorizontal: 20, paddingTop: 12, paddingBottom: 32, borderTopWidth: 0.5 },
});
```

- [ ] **Step 2: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 3: Logger corrections**

Ajouter dans `docs/ui-integration-corrections-v1.md` :
```
- [Task 9] app/session/live.tsx : font Space Grotesk → Inter via Text ui-mobile
- [Task 9] app/session/live.tsx : fontSize 88px → variant="display" (72px, conforme design tokens)
```

- [ ] **Step 4: Commit**

```bash
git add apps/mobile/app/session/live.tsx docs/ui-integration-corrections-v1.md
git commit -m "feat(ui): integrate session live execution screen"
```

---

## Task 10: training.tsx — Historique entraînements

**Files:**
- Create: `apps/mobile/app/(tabs)/training.tsx`

**Does NOT cover:** calendrier interactif avec sélection de date (vue Liste seulement en v1). Ne couvre pas les données API réelles.

> **Correction loggée :** Space Grotesk → Inter, bg hardcodés → themeColors.*

- [ ] **Step 1: Créer training.tsx**

```tsx
// apps/mobile/app/(tabs)/training.tsx
import React, { useState, useCallback } from 'react';
import { View, StyleSheet, ScrollView, Pressable, FlatList } from 'react-native';
import { Screen, Text, Card, DisciplineIcon, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';
import type { SportType } from '@resilio/ui-mobile';

interface SessionRecord {
  id: string;
  date: string;
  sport: SportType;
  title: string;
  duration_min: number;
  load: 'Légère' | 'Modérée' | 'Élevée';
  completed: boolean;
}

const MOCK_SESSIONS: SessionRecord[] = [
  { id: '1', date: 'Ven 18 avr', sport: 'running', title: 'Endurance fondamentale', duration_min: 52, load: 'Modérée', completed: true },
  { id: '2', date: 'Mer 16 avr', sport: 'lifting', title: 'Musculation haut du corps', duration_min: 65, load: 'Élevée', completed: true },
  { id: '3', date: 'Lun 14 avr', sport: 'running', title: 'Récupération active', duration_min: 35, load: 'Légère', completed: true },
  { id: '4', date: 'Sam 12 avr', sport: 'cycling', title: 'Endurance vélo Z2', duration_min: 90, load: 'Modérée', completed: true },
  { id: '5', date: 'Ven 11 avr', sport: 'lifting', title: 'Musculation bas du corps', duration_min: 60, load: 'Élevée', completed: false },
];

type ViewMode = 'list' | 'cal';

export default function TrainingScreen(): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  const [view, setView] = useState<ViewMode>('list');

  return (
    <Screen>
      <ScrollView style={styles.flex} contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Text variant="title" color={themeColors.foreground}>Entraînement</Text>
        </View>

        {/* Segmented control */}
        <View style={[styles.segmented, { backgroundColor: themeColors.surface2, borderColor: themeColors.border }]}>
          {(['list', 'cal'] as ViewMode[]).map((mode) => {
            const active = view === mode;
            return (
              <Pressable
                key={mode}
                style={[
                  styles.segmentBtn,
                  active && { backgroundColor: themeColors.surface1 },
                ]}
                onPress={() => setView(mode)}
              >
                <Text
                  variant="secondary"
                  color={active ? themeColors.foreground : themeColors.textSecondary}
                  style={active ? styles.segmentActive : undefined}
                >
                  {mode === 'list' ? 'Liste' : 'Calendrier'}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {view === 'cal' ? (
          <Card style={styles.calPlaceholder}>
            <Text variant="secondary" color={themeColors.textSecondary}>
              Vue calendrier — disponible prochainement.
            </Text>
          </Card>
        ) : (
          <View style={styles.list}>
            {MOCK_SESSIONS.map((session) => (
              <SessionRow key={session.id} session={session} themeColors={themeColors} />
            ))}
          </View>
        )}
      </ScrollView>
    </Screen>
  );
}

function SessionRow({ session, themeColors }: { session: SessionRecord; themeColors: ReturnType<typeof useTheme>['colors'] }) {
  const loadColor = session.load === 'Élevée' ? colors.zoneRed : session.load === 'Modérée' ? colors.zoneYellow : colors.zoneGreen;

  return (
    <Card style={styles.sessionRow}>
      <View style={styles.sessionLeft}>
        <Text variant="label" color={themeColors.textMuted} style={styles.sessionDate}>
          {session.date.toUpperCase()}
        </Text>
        <View style={styles.sessionTitleRow}>
          <DisciplineIcon sport={session.sport} size={14} color={themeColors.textMuted} />
          <Text variant="body" color={themeColors.foreground} style={styles.sessionTitle}>
            {session.title}
          </Text>
        </View>
        <Text variant="secondary" color={themeColors.textSecondary} style={{ fontVariant: ['tabular-nums'] }}>
          {session.duration_min} min · {session.load}
        </Text>
      </View>
      <View style={[styles.statusDot, { backgroundColor: session.completed ? colors.zoneGreen : themeColors.textMuted }]} />
    </Card>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingBottom: 48 },
  header: { paddingHorizontal: 24, paddingTop: 14, paddingBottom: 20 },
  segmented: {
    flexDirection: 'row',
    marginHorizontal: 20,
    borderRadius: 12,
    borderWidth: 0.5,
    padding: 3,
    marginBottom: 20,
  },
  segmentBtn: { flex: 1, alignItems: 'center', paddingVertical: 8, borderRadius: 10 },
  segmentActive: { fontWeight: '500' } as const,
  calPlaceholder: { marginHorizontal: 20, alignItems: 'center', paddingVertical: 40 },
  list: { paddingHorizontal: 20, gap: 8 },
  sessionRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sessionLeft: { flex: 1, gap: 3 },
  sessionDate: { textTransform: 'uppercase', letterSpacing: 0.6 },
  sessionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  sessionTitle: { flex: 1 },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginLeft: 12 },
});
```

- [ ] **Step 2: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 3: Logger corrections**

Ajouter dans `docs/ui-integration-corrections-v1.md` :
```
- [Task 10] app/(tabs)/training.tsx : Space Grotesk → Inter via Text ui-mobile
- [Task 10] app/(tabs)/training.tsx : bg hardcodés → themeColors.*
- [Task 10] app/(tabs)/training.tsx : SVG filtre inline → pas de SVG (card avec dot statut)
- [Task 10] app/(tabs)/training.tsx : vue calendrier → placeholder (hors scope v1)
```

- [ ] **Step 4: Commit**

```bash
git add apps/mobile/app/\(tabs\)/training.tsx docs/ui-integration-corrections-v1.md
git commit -m "feat(ui): integrate training history screen (liste)"
```

---

## Task 11: coach.tsx — Coach Chat

**Files:**
- Create: `apps/mobile/app/(tabs)/coach.tsx`
- Delete: `apps/mobile/app/(tabs)/chat.tsx` (après création de coach.tsx)

**Does NOT cover:** appel API réel (mock messages). Ne couvre pas la persistance de l'historique des conversations.

> **Correction loggée :** accent #B8552E (sienna) → colors.accent (#3B74C9), Space Grotesk → Inter, SVG icônes → Icon ui-mobile

- [ ] **Step 1: Créer coach.tsx**

```tsx
// apps/mobile/app/(tabs)/coach.tsx
import React, { useState, useCallback, useRef } from 'react';
import {
  View, StyleSheet, ScrollView, TextInput, Pressable,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import { Screen, Text, Icon, HITLSheet, useTheme } from '@resilio/ui-mobile';
import type { HITLOption } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

interface Message {
  id: string;
  role: 'coach' | 'user';
  content: string;
  timestamp: string;
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: '1',
    role: 'coach',
    content: 'Bonjour. J\'ai analysé ta semaine. Tu as 3 séances prévues. Veux-tu que je t\'explique la logique du plan ?',
    timestamp: '09:41',
  },
];

const HITL_OPTIONS: HITLOption[] = [
  { id: 'explain', label: 'Explique la logique du plan', description: 'Détail des choix d\'intensité et volume' },
  { id: 'adjust', label: 'Ajuste le plan cette semaine', description: 'Je suis disponible / indisponible certains jours' },
  { id: 'question', label: 'J\'ai une question spécifique', description: 'Nutrition, récupération, blessure...' },
];

export default function CoachScreen(): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [hitlVisible, setHitlVisible] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text) return;
    const userMsg: Message = {
      id: String(Date.now()),
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    // Simulate coach response
    setTimeout(() => {
      const coachMsg: Message = {
        id: String(Date.now() + 1),
        role: 'coach',
        content: 'Je note. Je prends en compte ta disponibilité pour ajuster la charge de la semaine.',
        timestamp: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, coachMsg]);
    }, 800);
  }, [input]);

  const handleHITLSelect = useCallback((id: string) => {
    const option = HITL_OPTIONS.find((o) => o.id === id);
    if (!option) return;
    const userMsg: Message = {
      id: String(Date.now()),
      role: 'user',
      content: option.label,
      timestamp: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
  }, []);

  return (
    <Screen>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={88}
      >
        {/* Header */}
        <View style={[styles.header, { borderBottomColor: themeColors.border }]}>
          <View style={styles.coachInfo}>
            <View style={[styles.onlineDot, { backgroundColor: colors.zoneGreen }]} />
            <Text variant="body" color={themeColors.foreground} style={styles.coachName}>
              Head Coach
            </Text>
          </View>
          <Pressable
            onPress={() => setHitlVisible(true)}
            style={[styles.hitlBtn, { borderColor: themeColors.border }]}
            accessibilityLabel="Options"
          >
            <Icon.Analytics size={16} color={themeColors.textSecondary} />
          </Pressable>
        </View>

        {/* Messages */}
        <ScrollView
          ref={scrollRef}
          style={styles.flex}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map((msg) => (
            <View
              key={msg.id}
              style={[
                styles.bubble,
                msg.role === 'user' ? styles.bubbleUser : styles.bubbleCoach,
                {
                  backgroundColor: msg.role === 'user'
                    ? themeColors.surface2
                    : themeColors.surface1,
                  borderColor: themeColors.border,
                },
              ]}
            >
              <Text variant="body" color={themeColors.foreground}>{msg.content}</Text>
              <Text variant="label" color={themeColors.textMuted} style={styles.timestamp}>
                {msg.timestamp}
              </Text>
            </View>
          ))}
        </ScrollView>

        {/* Input */}
        <View style={[styles.inputRow, { borderTopColor: themeColors.border, backgroundColor: themeColors.background }]}>
          <Pressable
            onPress={() => setHitlVisible(true)}
            style={[styles.optionsBtn, { borderColor: themeColors.border }]}
            accessibilityLabel="Suggestions"
          >
            <Icon.Add size={18} color={themeColors.textSecondary} />
          </Pressable>
          <View style={[styles.inputWrap, { backgroundColor: themeColors.surface1, borderColor: themeColors.border }]}>
            <TextInput
              style={[styles.textInput, { color: themeColors.foreground }]}
              placeholder="Message…"
              placeholderTextColor={themeColors.textMuted}
              value={input}
              onChangeText={setInput}
              multiline
              returnKeyType="send"
              onSubmitEditing={handleSend}
            />
          </View>
          <Pressable
            onPress={handleSend}
            disabled={!input.trim()}
            style={[
              styles.sendBtn,
              { backgroundColor: input.trim() ? colors.accent : themeColors.surface2 },
            ]}
            accessibilityLabel="Envoyer"
          >
            <Icon.ChevronUp size={16} color={input.trim() ? '#fff' : themeColors.textMuted} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>

      <HITLSheet
        visible={hitlVisible}
        title="Que veux-tu faire ?"
        options={HITL_OPTIONS}
        onSelect={handleHITLSelect}
        onDismiss={() => setHitlVisible(false)}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 0.5,
  },
  coachInfo: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  onlineDot: { width: 8, height: 8, borderRadius: 4 },
  coachName: { fontWeight: '500' } as const,
  hitlBtn: {
    width: 34, height: 34, borderRadius: 10,
    borderWidth: 0.5, alignItems: 'center', justifyContent: 'center',
  },
  messagesContent: { paddingHorizontal: 16, paddingVertical: 16, gap: 10 },
  bubble: {
    maxWidth: '85%',
    borderRadius: 16,
    borderWidth: 0.5,
    padding: 14,
    gap: 6,
  },
  bubbleCoach: { alignSelf: 'flex-start' },
  bubbleUser: { alignSelf: 'flex-end' },
  timestamp: { alignSelf: 'flex-end', letterSpacing: 0 },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 24,
    borderTopWidth: 0.5,
  },
  optionsBtn: {
    width: 36, height: 36, borderRadius: 18,
    borderWidth: 0.5, alignItems: 'center', justifyContent: 'center',
  },
  inputWrap: {
    flex: 1,
    borderRadius: 18,
    borderWidth: 0.5,
    paddingHorizontal: 14,
    paddingVertical: 8,
    minHeight: 36,
  },
  textInput: { fontSize: 15, lineHeight: 20, maxHeight: 100 },
  sendBtn: {
    width: 36, height: 36, borderRadius: 18,
    alignItems: 'center', justifyContent: 'center',
  },
});
```

- [ ] **Step 2: Supprimer chat.tsx**

```bash
rm apps/mobile/app/\(tabs\)/chat.tsx
```

- [ ] **Step 3: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 4: Logger corrections**

Ajouter dans `docs/ui-integration-corrections-v1.md` :
```
- [Task 11] app/(tabs)/coach.tsx : accent #B8552E (sienna) → colors.accent (#3B74C9)
- [Task 11] app/(tabs)/coach.tsx : Space Grotesk → Inter via Text ui-mobile
- [Task 11] app/(tabs)/coach.tsx : SVG icônes custom (Back, More, Send) → Icon.* ui-mobile
- [Task 11] app/(tabs)/coach.tsx : userBubble 'rgba(184,85,46,0.10)' → themeColors.surface2
```

- [ ] **Step 5: Commit**

```bash
git add apps/mobile/app/\(tabs\)/coach.tsx docs/ui-integration-corrections-v1.md
git commit -m "feat(ui): integrate coach chat screen + HITLSheet integration"
```

---

## Task 12: Placeholders — 3 pages non exportées

**Files:**
- Create: `apps/mobile/app/(tabs)/nutrition.tsx`
- Create: `apps/mobile/app/metric/[id].tsx`
- Create: `apps/mobile/app/settings/integrations.tsx`
- Update: `apps/mobile/app/(tabs)/profile.tsx` (mise à jour placeholder)

**Does NOT cover:** toute UI fonctionnelle — placeholders uniquement.

- [ ] **Step 1: Créer nutrition.tsx**

```tsx
// apps/mobile/app/(tabs)/nutrition.tsx
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Screen, Text, useTheme } from '@resilio/ui-mobile';

export default function NutritionScreen(): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <Screen>
      <View style={styles.container}>
        <Text variant="title" color={themeColors.foreground}>Nutrition</Text>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
          Journal nutrition — à venir.
        </Text>
      </View>
    </Screen>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  sub: { marginTop: 8, textAlign: 'center' },
});
```

- [ ] **Step 2: Créer metric/[id].tsx**

```tsx
// apps/mobile/app/metric/[id].tsx
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { Screen, Text, useTheme } from '@resilio/ui-mobile';

export default function MetricDetailScreen(): React.JSX.Element {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors: themeColors } = useTheme();
  return (
    <Screen>
      <View style={styles.container}>
        <Text variant="title" color={themeColors.foreground}>Détail métrique</Text>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
          {id} — à venir.
        </Text>
      </View>
    </Screen>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  sub: { marginTop: 8, textAlign: 'center' },
});
```

- [ ] **Step 3: Créer settings/integrations.tsx**

```tsx
// apps/mobile/app/settings/integrations.tsx
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Screen, Text, useTheme } from '@resilio/ui-mobile';

export default function IntegrationsScreen(): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <Screen>
      <View style={styles.container}>
        <Text variant="title" color={themeColors.foreground}>Intégrations</Text>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
          Connexion Strava, Hevy, Apple Santé — à venir.
        </Text>
      </View>
    </Screen>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  sub: { marginTop: 8, textAlign: 'center' },
});
```

- [ ] **Step 4: Mettre à jour profile.tsx** (supprimer le placeholder "Session FE-MOBILE-2")

```tsx
// apps/mobile/app/(tabs)/profile.tsx
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Screen, Text, useTheme } from '@resilio/ui-mobile';

export default function ProfileScreen(): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <Screen>
      <View style={styles.container}>
        <Text variant="title" color={themeColors.foreground}>Profil</Text>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
          Profil athlète et réglages — à venir.
        </Text>
      </View>
    </Screen>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  sub: { marginTop: 8, textAlign: 'center' },
});
```

- [ ] **Step 5: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/app/\(tabs\)/nutrition.tsx apps/mobile/app/metric/\[id\].tsx apps/mobile/app/settings/integrations.tsx apps/mobile/app/\(tabs\)/profile.tsx
git commit -m "feat(ui): add placeholder screens (nutrition, metric, integrations, profile)"
```

---

## Task 13: Navigation — tab bar + root layout

**Files:**
- Modify: `apps/mobile/app/(tabs)/_layout.tsx`
- Modify: `apps/mobile/app/_layout.tsx`

**Does NOT cover:** deep linking. Ne couvre pas la logique d'auth guard (redirection automatique si non authentifié).

- [ ] **Step 1: Mettre à jour (tabs)/_layout.tsx**

Backup :
```bash
cp apps/mobile/app/\(tabs\)/_layout.tsx apps/mobile/app/\(tabs\)/_layout.tsx.backup
```

Nouveau contenu :
```tsx
// apps/mobile/app/(tabs)/_layout.tsx
import { NativeTabs } from 'expo-router/unstable-native-tabs';
import { colors } from '@resilio/design-tokens';

/**
 * Tab bar — 5 tabs : Accueil · Check-in · Entraînement · Coach · Profil
 *
 * iOS: UITabBarController liquid glass (systemChromeMaterial).
 * SF Symbols: tab bar uniquement (exception règle Lucide — UI-RULES §9).
 */
export default function TabsLayout() {
  return (
    <NativeTabs
      tintColor={colors.accent}
      blurEffect="systemChromeMaterial"
    >
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.Label>Accueil</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'house', selected: 'house.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="check-in">
        <NativeTabs.Trigger.Label>Check-in</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'heart', selected: 'heart.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="training">
        <NativeTabs.Trigger.Label>Entraînement</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'chart.bar', selected: 'chart.bar.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="coach">
        <NativeTabs.Trigger.Label>Coach</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'bolt', selected: 'bolt.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="profile">
        <NativeTabs.Trigger.Label>Profil</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'person', selected: 'person.fill' }}
        />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
```

- [ ] **Step 2: Mettre à jour _layout.tsx (root)**

Ajouter les nouvelles routes dans le Stack :
```tsx
// apps/mobile/app/_layout.tsx
import '../global.css';
import { useEffect } from 'react';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import {
  useFonts,
  Inter_300Light,
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
} from '@expo-google-fonts/inter';
import { SpaceMono_400Regular } from '@expo-google-fonts/space-mono';
import { ThemeProvider } from '@resilio/ui-mobile';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Inter_300Light,
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    SpaceMono_400Regular,
  });

  useEffect(() => {
    if (fontsLoaded) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded]);

  if (!fontsLoaded) {
    return null;
  }

  return (
    <ThemeProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(onboarding)" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="session" />
        <Stack.Screen name="metric" />
        <Stack.Screen name="settings" />
        <Stack.Screen name="+not-found" />
      </Stack>
    </ThemeProvider>
  );
}
```

- [ ] **Step 3: Vérifier TypeScript**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 4: Commit**

```bash
git add apps/mobile/app/\(tabs\)/_layout.tsx apps/mobile/app/_layout.tsx apps/mobile/app/\(tabs\)/_layout.tsx.backup
git commit -m "feat(mobile): wire navigation — 5 tabs + onboarding + session + metric routes"
```

---

## Task 14: Vérification finale

- [ ] **Step 1: TypeScript clean**

Run: `pnpm --filter @resilio/mobile typecheck`
Expected: 0 erreurs

- [ ] **Step 2: ui-mobile tests**

Run: `pnpm --filter @resilio/ui-mobile test`
Expected: tous les tests passent (incluant ProgressDots, HITLSheet, DisciplineIcon)

- [ ] **Step 3: Vérifier que home est intact**

```bash
git diff HEAD~20 apps/mobile/app/\(tabs\)/index.tsx
```
Expected: aucune ligne modifiée dans index.tsx (ou diff vide)

- [ ] **Step 4: Vérifier que test home n'a pas été touchée**

```bash
ls "docs/design/test home/"
```
Expected: fichiers présents, inchangés

- [ ] **Step 5: Confirmer docs/ui-integration-corrections-v1.md complet**

Vérifier que toutes les corrections loggées dans les tasks précédentes sont présentes.

- [ ] **Step 6: Commit final si nécessaire**

```bash
git status
# Si fichiers non commités :
git add <fichiers>
git commit -m "chore(mobile): finalize UI integration v1"
```

---

## Checklist par page

| Page | Compile | Light | Dark | Tokens only | Navigation | No anti-pattern |
|------|---------|-------|------|-------------|------------|-----------------|
| login | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| signup | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| forgot-password | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| onboarding | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| session/today | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| session/live | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| training | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| coach | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| placeholders (×3) | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| home (inchangée) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
