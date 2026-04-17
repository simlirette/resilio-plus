import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

export default function ProfileScreen() {
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  return (
    <View style={[styles.container, { backgroundColor: themeColors.background }]}>
      <Text style={[styles.placeholder, { color: themeColors.textSecondary }]}>
        Profil athlète — Session FE-MOBILE-2
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  placeholder: { fontSize: 14 },
});
