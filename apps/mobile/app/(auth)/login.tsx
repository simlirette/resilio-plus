// apps/mobile/app/(auth)/login.tsx
import React, { useState, useCallback } from 'react';
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
        <View style={styles.wordmarkRow}>
          <Text variant="title" color={themeColors.foreground}>Resilio</Text>
          <Text variant="title" color={colors.accent}>+</Text>
        </View>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.subtitle}>
          Ta plateforme de coaching hybride
        </Text>

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

        <Text variant="secondary" color={themeColors.textMuted} style={styles.applePlaceholder}>
          Connexion Apple — bientôt disponible
        </Text>

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
