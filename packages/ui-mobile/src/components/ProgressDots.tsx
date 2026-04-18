import React from 'react';
import { View, StyleSheet } from 'react-native';
import { colors } from '@resilio/design-tokens';
import { useTheme } from '../theme/ThemeProvider';

interface ProgressDotsProps {
  /** 0-indexed current step. Segments 0..step are filled. */
  step: number;
  total?: number;
}

export function ProgressDots({ step, total = 5 }: ProgressDotsProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <View style={styles.row}>
      {Array.from({ length: total }).map((_, i) => (
        <View
          key={i}
          testID="progress-dot"
          style={[
            styles.dot,
            { backgroundColor: i <= step ? colors.accent : themeColors.border },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 6, alignItems: 'center' },
  dot: { height: 3, width: 28, borderRadius: 2 },
});
