import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { Screen, Text, useTheme } from '@resilio/ui-mobile';

export default function MetricDetailScreen(): React.JSX.Element {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors: themeColors } = useTheme();
  return (
    <Screen>
      <View style={styles.container}>
        <Text variant="title" color={themeColors.foreground}>Détail métrique</Text>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
          {id} — à venir.
        </Text>
      </View>
    </Screen>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  sub: { marginTop: 8, textAlign: 'center' },
});
