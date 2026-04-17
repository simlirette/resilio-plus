import React from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Circle as SvgCircle } from 'react-native-svg';
import { Text } from './Text';
import { useTheme } from '../theme/ThemeProvider';

interface CircleProps {
  /** Value 0–100 */
  value: number;
  /** Diameter in dp (default: 80) */
  size?: number;
  /** Stroke color — use design token values */
  color: string;
  /** Optional label below the value */
  label?: string;
}

/**
 * SVG circle progress indicator. Base for Readiness + sub-metric circles.
 * value prop: 0–100 maps to circle fill percentage.
 */
export function Circle({ value, size = 80, color, label }: CircleProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  const clampedValue = Math.min(100, Math.max(0, value));
  const strokeWidth = size * 0.1;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - clampedValue / 100);

  return (
    <View style={styles.container}>
      <View style={{ width: size, height: size }}>
        <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Track */}
          <SvgCircle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={themeColors.border}
            strokeWidth={strokeWidth}
            fill="none"
          />
          {/* Progress */}
          <SvgCircle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            fill="none"
            strokeDasharray={`${circumference} ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            rotation="-90"
            origin={`${size / 2}, ${size / 2}`}
          />
        </Svg>
        {/* Centered value */}
        <View style={[StyleSheet.absoluteFill, styles.valueContainer]}>
          <Text variant="title" color={color} style={{ fontSize: size * 0.28, lineHeight: size * 0.34 }}>
            {clampedValue}
          </Text>
        </View>
      </View>
      {label ? (
        <Text variant="caption" color={themeColors.textSecondary} style={styles.label}>
          {label}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', gap: 6 },
  valueContainer: { alignItems: 'center', justifyContent: 'center' },
  label: { textAlign: 'center' },
});
