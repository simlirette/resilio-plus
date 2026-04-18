import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Screen, Text, useTheme } from '@resilio/ui-mobile';

export default function ProfileScreen(): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <Screen>
      <View style={styles.container}>
        <Text variant="title" color={themeColors.foreground}>Profil</Text>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
          Profil athlète et réglages — à venir.
        </Text>
      </View>
    </Screen>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  sub: { marginTop: 8, textAlign: 'center' },
});
