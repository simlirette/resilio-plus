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

export default function SignupScreen() {
  const router = useRouter();
  const { colorMode, colors: themeColors } = useTheme();
  const isDark = colorMode === 'dark';
  const accent = isDark ? colors.accentDark : colors.accent;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [confirmError, setConfirmError] = useState('');

  async function handleSignup() {
    let valid = true;
    if (!email) { setEmailError('Email requis.'); valid = false; } else { setEmailError(''); }
    if (!password) { setPasswordError('Mot de passe requis.'); valid = false; } else { setPasswordError(''); }
    if (!confirm) {
      setConfirmError('Confirmation requise.'); valid = false;
    } else if (confirm !== password) {
      setConfirmError('Les mots de passe ne correspondent pas.'); valid = false;
    } else {
      setConfirmError('');
    }
    if (!valid) return;

    setLoading(true);
    // TODO: real signup call
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
          <Text variant="pageTitle" style={styles.title}>Créer un compte</Text>

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
              autoComplete="new-password"
              error={passwordError}
            />
            <FloatingLabelInput
              label="Confirmer le mot de passe"
              value={confirm}
              onChangeText={setConfirm}
              secureTextEntry
              showToggle
              autoComplete="new-password"
              error={confirmError}
            />
          </View>

          {/* CTA */}
          <Button
            title="Créer mon compte"
            onPress={handleSignup}
            loading={loading}
            disabled={loading}
            style={styles.cta}
          />

          {/* Legal */}
          <Text
            variant="caption"
            color={themeColors.textMuted}
            style={styles.legal}
          >
            En créant un compte, tu acceptes nos{' '}
            <Text variant="caption" color={accent}>Conditions d'utilisation</Text>
            {' '}et notre{' '}
            <Text variant="caption" color={accent}>Politique de confidentialité</Text>.
          </Text>

          {/* Spacer */}
          <View style={styles.spacer} />

          {/* Footer */}
          <View style={styles.footer}>
            <Text variant="secondary" color={themeColors.textSecondary}>Déjà un compte ? </Text>
            <Pressable onPress={() => router.back()} hitSlop={8}>
              <Text variant="secondary" color={accent}>Se connecter</Text>
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
    marginBottom: 20,
  },
  cta: {
    marginBottom: 12,
  },
  legal: {
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 8,
  },
  spacer: { flex: 1, minHeight: 32 },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 16,
  },
});
