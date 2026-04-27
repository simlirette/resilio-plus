import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@resilio/design-tokens';
import { useTheme } from '../theme/ThemeProvider';

interface ProgressSegmentsProps {
  /** Total number of segments */
  total: number;
  /** Current step (1-based) */
  current: number;
}

/**
 * Onboarding progress bar — thin segments, no dots.
 * Spec: docs/design/onboarding/SPEC.md
 *
 * Completed + active: accent color. Future: neutral border.
 * Swap is instantaneous — no transition animation per spec.
 */
export function ProgressSegments({ total, current }: ProgressSegmentsProps): React.JSX.Element {
  const { colorMode, colors: themeColors } = useTheme();
  const isDark = colorMode === 'dark';
  const accent = isDark ? colors.accentDark : colors.accent;

  return (
    <View style={styles.row}>
      {Array.from({ length: total }, (_, i) => {
        const filled = i < current;
        return (
          <View
            key={i}
            style={[
              styles.segment,
              { backgroundColor: filled ? accent : themeColors.border },
              i < total - 1 && styles.gap,
            ]}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    height: 3,
  },
  segment: {
    flex: 1,
    borderRadius: 2,
  },
  gap: {
    marginRight: 6,
  },
});
