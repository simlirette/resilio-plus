import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { colors } from '@resilio/design-tokens';
import { Button, FloatingLabelInput, Text, useTheme } from '@resilio/ui-mobile';

export default function LoginScreen() {
  const router = useRouter();
  const { colorMode, colors: themeColors } = useTheme();
  const isDark = colorMode === 'dark';
  const accent = isDark ? colors.accentDark : colors.accent;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  async function handleLogin() {
    let valid = true;
    if (!email) { setEmailError('Email requis.'); valid = false; } else { setEmailError(''); }
    if (!password) { setPasswordError('Mot de passe requis.'); valid = false; } else { setPasswordError(''); }
    if (!valid) return;

    setLoading(true);
    // TODO: real auth call
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
    router.replace('/(tabs)');
  }

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: themeColors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <SafeAreaView style={styles.flex} edges={['top', 'bottom']}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Wordmark */}
          <View style={styles.wordmarkRow}>
            <Text variant="wordmark" color={themeColors.foreground}>Resilio</Text>
            <Text variant="wordmark" color={accent}>+</Text>
          </View>

          {/* Title */}
          <Text variant="pageTitle" style={styles.title}>Connexion</Text>

          {/* Inputs */}
          <View style={styles.inputs}>
            <FloatingLabelInput
              label="Email"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              autoFocus
              error={emailError}
            />
            <FloatingLabelInput
              label="Mot de passe"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              showToggle
              autoComplete="current-password"
              error={passwordError}
            />
          </View>

          {/* Forgot password link */}
          <Pressable
            style={styles.forgotRow}
            onPress={() => router.push('/(auth)/forgot-password')}
            hitSlop={8}
          >
            <Text variant="secondary" color={accent}>Mot de passe oublié</Text>
          </Pressable>

          {/* CTA */}
          <Button
            title="Se connecter"
            onPress={handleLogin}
            loading={loading}
            disabled={loading}
            style={styles.cta}
          />

          {/* Separator */}
          <View style={styles.separatorRow}>
            <View style={[styles.line, { backgroundColor: themeColors.border }]} />
            <Text variant="secondary" color={themeColors.textSecondary} style={styles.orText}>ou</Text>
            <View style={[styles.line, { backgroundColor: themeColors.border }]} />
          </View>

          {/* Apple Sign In */}
          <Button
            title="Continuer avec Apple"
            onPress={() => {/* TODO: expo-apple-authentication */}}
            variant="apple"
          />

          {/* Spacer pushes footer down */}
          <View style={styles.spacer} />

          {/* Footer */}
          <View style={styles.footer}>
            <Text variant="secondary" color={themeColors.textSecondary}>Pas de compte ? </Text>
            <Pressable onPress={() => router.push('/(auth)/signup')} hitSlop={8}>
              <Text variant="secondary" color={accent}>Créer un compte</Text>
            </Pressable>
          </View>
        </ScrollView>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 48,
    paddingBottom: 16,
  },
  wordmarkRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 40,
  },
  title: {
    marginBottom: 24,
  },
  inputs: {
    gap: 14,
    marginBottom: 10,
  },
  forgotRow: {
    alignSelf: 'flex-end',
    marginBottom: 20,
  },
  cta: {
    marginBottom: 20,
  },
  separatorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  line: {
    flex: 1,
    height: StyleSheet.hairlineWidth,
  },
  orText: {
    marginHorizontal: 12,
  },
  spacer: { flex: 1, minHeight: 32 },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 16,
  },
});
