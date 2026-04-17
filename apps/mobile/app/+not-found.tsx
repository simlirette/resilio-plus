import { View, Text, StyleSheet } from 'react-native';
import { Link, Stack } from 'expo-router';
import { useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

export default function NotFoundScreen() {
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  return (
    <>
      <Stack.Screen options={{ title: 'Page introuvable' }} />
      <View style={[styles.container, { backgroundColor: themeColors.background }]}>
        <Text style={[styles.title, { color: themeColors.foreground }]}>Page introuvable</Text>
        <Link href="/" style={[styles.link, { color: colors.primary }]}>
          Retour à l'accueil
        </Link>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  title: { fontSize: 20, fontWeight: '700', marginBottom: 16 },
  link: { fontSize: 15 },
});
