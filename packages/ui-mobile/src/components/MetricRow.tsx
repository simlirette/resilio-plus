import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Circle } from './Circle';
import { Text } from './Text';
import { useTheme } from '../theme/ThemeProvider';

export type MetricState = 'green' | 'yellow' | 'red';

interface Metric {
  value: number;
  state: MetricState;
}

interface MetricRowProps {
  nutrition: Metric;
  strain: Metric;
  sleep: Metric;
}

/**
 * Row of 3 metric circles: Nutrition, Strain (Récup.), Sommeil.
 * Design v2: 68px circles, fixed stroke=5, semantic colors per metric type,
 * hairline dividers between columns. Wrap in <Card> at call site.
 *
 * Colors sourced from theme tokens: warn (nutrition), ok (strain), okStrong (sleep).
 */
export function MetricRow({ nutrition, strain, sleep }: MetricRowProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();

  const metrics: Array<{ key: string; label: string; data: Metric; color: string }> = [
    { key: 'nutrition', label: 'Nutrition', data: nutrition, color: themeColors.warn },
    { key: 'strain',    label: 'Récup.',    data: strain,    color: themeColors.ok },
    { key: 'sleep',     label: 'Sommeil',   data: sleep,     color: themeColors.okStrong },
  ];

  return (
    <View style={styles.row}>
      {metrics.map(({ key, label, data, color }, idx) => (
        <React.Fragment key={key}>
          {idx > 0 && (
            <View
              style={[styles.divider, { backgroundColor: themeColors.border }]}
            />
          )}
          <View
            style={styles.col}
            accessible={true}
            accessibilityLabel={`${label} : ${data.value} sur 100`}
          >
            <Circle
              value={data.value}
              size={68}
              strokeWidth={5}
              color={color}
            />
            <Text
              variant="caption"
              color={themeColors.textSecondary}
              style={styles.label}
            >
              {label}
            </Text>
          </View>
        </React.Fragment>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'stretch' },
  col: { flex: 1, alignItems: 'center', gap: 10, paddingVertical: 16, paddingHorizontal: 4 },
  divider: { width: 0.5, marginVertical: 14 },
  label: { textAlign: 'center' },
});
