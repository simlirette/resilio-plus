import { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Button, Card, Input, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

export default function LoginScreen() {
  const router = useRouter();
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleLogin() {
    if (!email || !password) {
      setError('Email et mot de passe requis.');
      return;
    }
    setError('');
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setLoading(false);
    router.replace('/(tabs)/');
  }

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: themeColors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={[styles.wordmark, { color: colors.primary }]}>
          RESILIO+
        </Text>
        <Text style={[styles.subtitle, { color: themeColors.textSecondary }]}>
          Ta plateforme de coaching hybride
        </Text>
        <Card style={styles.card}>
          <Input
            label="Email"
            value={email}
            onChangeText={setEmail}
            placeholder="athlete@exemple.com"
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
          />
          <Input
            label="Mot de passe"
            value={password}
            onChangeText={setPassword}
            placeholder="••••••••"
            secureTextEntry
            autoComplete="current-password"
            style={{ marginTop: 16 }}
          />
          {error ? (
            <Text style={[styles.error, { color: colors.zoneRed }]}>{error}</Text>
          ) : null}
          <Button
            title={loading ? 'Connexion…' : 'Se connecter'}
            onPress={handleLogin}
            disabled={loading}
            style={{ marginTop: 24 }}
          />
        </Card>
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
  wordmark: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 32,
    letterSpacing: 4,
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 32,
  },
  card: { width: '100%' },
  error: { fontSize: 13, marginTop: 8 },
});
