/**
 * Training History — placeholder.
 * Implémentation pixel-perfect en Phase 2 (Wave 2–3 + P4).
 * Voir docs/design/training historycalendar/SPEC.md
 */
import { View, StyleSheet } from 'react-native';
import { Screen, Text, useTheme } from '@resilio/ui-mobile';

export default function TrainingScreen() {
  const { colors: themeColors } = useTheme();
  return (
    <Screen>
      <View style={styles.center}>
        <Text variant="label" color={themeColors.textMuted}>ENTRAÎNEMENT</Text>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
          Calendrier et historique — à venir
        </Text>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 8 },
  sub: { textAlign: 'center' },
});
