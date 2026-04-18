import React, { useState, useCallback } from 'react';
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
            loading={loading}
            disabled={loading}
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
