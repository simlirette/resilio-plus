import { View, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { Button, Card, Screen, Text, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';
import { useAuth } from '../../src/auth/AuthProvider';

export default function ProfileScreen() {
  const router = useRouter();
  const { user, session, apiBaseUrl, logout } = useAuth();
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;

  async function handleLogout() {
    await logout();
    router.replace('/(auth)/login');
  }

  return (
    <Screen padded>
      <View style={styles.header}>
        <Text variant="title" color={themeColors.foreground}>Profil</Text>
        <Text variant="secondary" color={themeColors.textSecondary}>
          Compte et session mobile
        </Text>
      </View>

      <Card style={styles.card}>
        <Text variant="label" color={themeColors.textMuted}>EMAIL</Text>
        <Text variant="body" color={themeColors.foreground} style={styles.value}>
          {user?.email ?? 'Session active'}
        </Text>

        <Text variant="label" color={themeColors.textMuted} style={styles.label}>ATHLETE ID</Text>
        <Text variant="body" color={themeColors.foreground} style={styles.value}>
          {session?.athleteId ?? 'Indisponible'}
        </Text>

        <Text variant="label" color={themeColors.textMuted} style={styles.label}>API</Text>
        <Text variant="body" color={themeColors.foreground} style={styles.value}>
          {apiBaseUrl}
        </Text>
      </Card>

      <Button title="Se deconnecter" onPress={handleLogout} variant="secondary" style={styles.logout} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { marginBottom: 20 },
  card: { width: '100%' },
  label: { marginTop: 18 },
  value: { marginTop: 6 },
  logout: { marginTop: 20 },
});
