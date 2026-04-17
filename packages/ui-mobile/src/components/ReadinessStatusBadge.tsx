import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from './Text';
import { colors } from '@resilio/design-tokens';

interface ReadinessStatusBadgeProps {
  /** Readiness score 0–100 */
  value: number;
}

interface BadgeConfig {
  label: string;
  color: string;
  backgroundColor: string;
}

function badgeConfig(value: number): BadgeConfig {
  if (value >= 80) {
    return { label: 'Optimal', color: colors.zoneGreen, backgroundColor: colors.zoneGreenBg };
  }
  if (value >= 60) {
    return { label: 'Prudent', color: colors.zoneYellow, backgroundColor: colors.zoneYellowBg };
  }
  return { label: 'Repos recommandé', color: colors.zoneRed, backgroundColor: colors.zoneRedBg };
}

export function ReadinessStatusBadge({ value }: ReadinessStatusBadgeProps): React.JSX.Element {
  const config = badgeConfig(value);
  return (
    <View style={[styles.pill, { backgroundColor: config.backgroundColor }]}>
      <Text
        variant="caption"
        color={config.color}
        style={styles.text}
      >
        {config.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    alignSelf: 'center',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 999,
  },
  text: { fontWeight: '600' },
});
