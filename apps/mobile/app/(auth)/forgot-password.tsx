import React, { useState, useCallback } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Text, Button, Input, Card, useTheme } from '@resilio/ui-mobile';

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
