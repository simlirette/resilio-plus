import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { useTheme } from '../theme/ThemeProvider';

interface HeroNumberProps {
  /** Main value — string to support "5:42", "78", "72 kg" */
  value: string | number;
  /** Optional unit shown smaller after the value (e.g. "/km", "kg") */
  unit?: string;
  /**
   * xl:  40px/700 — charge, reps (muscu hero metrics)
   * xxl: 72px/500 — readiness, large metrics
   * pace: 80px/700 — live pace (tracking -3)
   */
  size?: 'xl' | 'xxl' | 'pace';
  color?: string;
}

/**
 * Large tabular-nums display number. Space Grotesk only.
 * Spec: multiple SPEC.md (readiness, session, today's session)
 */
export function HeroNumber({ value, unit, size = 'xxl', color }: HeroNumberProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  const textColor = color ?? themeColors.foreground;

  const variant =
    size === 'xl'   ? 'heroLarge'
    : size === 'pace' ? 'heroPace'
    : 'heroNumber';

  return (
    <View style={styles.row}>
      <Text variant={variant} color={textColor}>
        {String(value)}
      </Text>
      {unit ? (
        <Text
          variant="metric"
          color={textColor}
          style={styles.unit}
        >
          {unit}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  unit: {
    marginBottom: 8,
    marginLeft: 4,
    opacity: 0.7,
  },
});
