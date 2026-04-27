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
import { Button, FloatingLabelInput, IconComponent, Text, useTheme } from '@resilio/ui-mobile';

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const { colorMode, colors: themeColors } = useTheme();
  const isDark = colorMode === 'dark';
  const accent = isDark ? colors.accentDark : colors.accent;

  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [emailError, setEmailError] = useState('');

  async function handleSubmit() {
    if (!email) { setEmailError('Email requis.'); return; }
    setEmailError('');
    setLoading(true);
    // TODO: real password reset call
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
    setSent(true);
  }

  async function handleResend() {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
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
          <Text variant="pageTitle" style={styles.title}>
            {'Réinitialiser\nle mot de passe'}
          </Text>

          {!sent ? (
            <>
              {/* Subtitle */}
              <Text variant="body" color={themeColors.textSecondary} style={styles.subtitle}>
                Saisis ton email et on t'envoie un lien de réinitialisation.
              </Text>

              {/* Email input */}
              <View style={{ marginBottom: 20 }}>
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
              </View>

              {/* CTA */}
              <Button
                title="Envoyer le lien"
                onPress={handleSubmit}
                loading={loading}
                disabled={loading}
              />
            </>
          ) : (
            <>
              {/* Confirmation block */}
              <View
                style={[
                  styles.confirmation,
                  {
                    backgroundColor: themeColors.surface2,
                    borderColor: themeColors.border,
                  },
                ]}
              >
                <IconComponent name="Mail" color={accent} size={24} />
                <View style={styles.confirmationText}>
                  <Text variant="bodyBold" color={themeColors.foreground}>
                    Email envoyé
                  </Text>
                  <Text variant="secondary" color={themeColors.textSecondary}>
                    Expire dans 30 minutes.
                  </Text>
                </View>
              </View>

              {/* Resend */}
              <Button
                title="Renvoyer"
                onPress={handleResend}
                loading={loading}
                variant="ghost"
                style={styles.resendBtn}
              />
            </>
          )}

          {/* Spacer */}
          <View style={styles.spacer} />

          {/* Footer */}
          <View style={styles.footer}>
            <Pressable onPress={() => router.back()} hitSlop={8}>
              <Text variant="secondary" color={accent}>← Revenir à la connexion</Text>
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
    marginBottom: 16,
  },
  subtitle: {
    marginBottom: 24,
    lineHeight: 22,
  },
  confirmation: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 16,
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    marginBottom: 16,
  },
  confirmationText: {
    flex: 1,
    gap: 2,
  },
  resendBtn: {
    marginTop: 4,
  },
  spacer: { flex: 1, minHeight: 32 },
  footer: {
    alignItems: 'center',
    paddingTop: 16,
  },
});
