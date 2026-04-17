import React from 'react';
import { View, StyleSheet } from 'react-native';
import { colors as globalColors } from '@resilio/design-tokens';
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
 * Row of 3 metric circles: Nutrition, Strain, Sommeil.
 * Design v2: 68px circles, fixed stroke=5, state-based colors (green/yellow/red).
 * Hairline dividers between columns. Wrap in <Card> at call site.
 *
 * Colors: state='green' → ok, 'yellow' → warn, 'red' → zoneRed.
 */
function stateColor(state: MetricState, themeColors: { ok: string; warn: string }): string {
  switch (state) {
    case 'green': return themeColors.ok;
    case 'yellow': return themeColors.warn;
    case 'red': return globalColors.zoneRed;
  }
}

export function MetricRow({ nutrition, strain, sleep }: MetricRowProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();

  const metrics: Array<{ key: string; label: string; data: Metric; color: string }> = [
    { key: 'nutrition', label: 'Nutrition', data: nutrition, color: stateColor(nutrition.state, themeColors) },
    { key: 'strain',    label: 'Strain',    data: strain,    color: stateColor(strain.state, themeColors) },
    { key: 'sleep',     label: 'Sommeil',   data: sleep,     color: stateColor(sleep.state, themeColors) },
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
