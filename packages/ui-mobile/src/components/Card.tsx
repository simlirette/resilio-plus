import React, { ReactNode } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

interface CardProps { children: ReactNode; style?: ViewStyle; }

/**
 * Surface card. radius=22, 0.5px hairline border, elevation shadow.
 * Design system v2 — warm palette (2026-04-17)
 */
export function Card({ children, style }: CardProps) {
  const { colorMode, colors: themeColors } = useTheme();
  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: themeColors.surface1,
          borderColor: themeColors.border,
          // Elevation shadow (Android) — iOS uses shadow* props
          elevation: colorMode === 'dark' ? 4 : 2,
          shadowColor: colorMode === 'dark' ? '#000000' : '#2B1C00',
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: colorMode === 'dark' ? 0.25 : 0.06,
          shadowRadius: 12,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 22,
    borderWidth: 0.5,
    padding: 0,
    overflow: 'hidden',
  },
});
