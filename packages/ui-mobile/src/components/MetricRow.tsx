import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Circle } from './Circle';
import { Text } from './Text';
import { useTheme } from '../theme/ThemeProvider';
import { colors } from '@resilio/design-tokens';

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

function colorForState(state: MetricState): string {
  switch (state) {
    case 'green':  return colors.zoneGreen;
    case 'yellow': return colors.zoneYellow;
    case 'red':    return colors.zoneRed;
  }
}

export function MetricRow({ nutrition, strain, sleep }: MetricRowProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();

  const metrics: Array<{ key: string; label: string; data: Metric }> = [
    { key: 'nutrition', label: 'Nutrition',  data: nutrition },
    { key: 'strain',    label: 'Récup.',     data: strain },
    { key: 'sleep',     label: 'Sommeil',    data: sleep },
  ];

  return (
    <View style={styles.row}>
      {metrics.map(({ key, label, data }) => (
        <View key={key} style={styles.col}>
          <Circle
            value={data.value}
            size={80}
            color={colorForState(data.state)}
            accessibilityLabel={`${label} : ${data.value} sur 100`}
          />
          <Text
            variant="caption"
            color={themeColors.textSecondary}
            style={styles.label}
          >
            {label}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  col: { flex: 1, alignItems: 'center', gap: 6 },
  label: { textAlign: 'center' },
});
