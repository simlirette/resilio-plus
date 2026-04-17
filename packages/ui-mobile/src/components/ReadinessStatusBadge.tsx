import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from './Text';
import { useTheme } from '../theme/ThemeProvider';

interface ReadinessStatusBadgeProps {
  /** Readiness score 0–100 */
  value: number;
}

interface BadgeConfig {
  label: string;
  dotColor: string;
}

function badgeConfig(value: number, themeColors: { ok: string; caution: string }): BadgeConfig {
  if (value >= 80) {
    return { label: 'Optimal', dotColor: themeColors.ok };
  }
  if (value >= 60) {
    return { label: 'Prudent', dotColor: themeColors.caution };
  }
  return { label: 'Repos recommandé', dotColor: '#ef4444' };
}

/**
 * Readiness status pill.
 * Design v2: surface bg + hairline border + 7px dot + label.
 * Dot color: ok (green) / caution (amber) / red.
 */
export function ReadinessStatusBadge({ value }: ReadinessStatusBadgeProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  const config = badgeConfig(value, themeColors);

  return (
    <View
      style={[
        styles.pill,
        {
          backgroundColor: themeColors.surface1,
          borderColor: themeColors.border,
        },
      ]}
    >
      <View style={[styles.dot, { backgroundColor: config.dotColor }]} />
      <Text
        variant="body"
        color={themeColors.foreground}
        style={styles.text}
      >
        {config.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'center',
    gap: 8,
    paddingLeft: 12,
    paddingRight: 14,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 0.5,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 999,
  },
  text: {
    fontSize: 13,
    fontFamily: 'Inter_500Medium',
    letterSpacing: -0.1,
  },
});
