import React, { ReactNode } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { colors } from '@resilio/design-tokens';

interface CardProps { children: ReactNode; style?: ViewStyle; }

export function Card({ children, style }: CardProps) {
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  return (
    <View style={[styles.card, { backgroundColor: themeColors.surface2, borderColor: themeColors.border }, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 16, borderWidth: 1, padding: 20 },
});
