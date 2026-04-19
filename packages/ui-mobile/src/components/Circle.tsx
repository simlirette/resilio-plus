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
  /** Fixed stroke width override. Default: size * 0.1 */
  strokeWidth?: number;
  /** Optional label BELOW the circle */
  label?: string;
  /** Optional label rendered INSIDE the ring, above the value (e.g. "Readiness") */
  innerLabel?: string;
}

/**
 * SVG circle progress indicator. Base for Readiness + sub-metric circles.
 * value prop: 0–100 maps to circle fill percentage.
 *
 * Design v2 additions:
 * - strokeWidth prop: explicit override (design uses 10 for main ring, 5 for metrics)
 * - innerLabel prop: tertiary label inside ring above value
 */
export function Circle({ value, size = 80, color, strokeWidth: strokeWidthProp, label, innerLabel }: CircleProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  const clampedValue = Math.min(100, Math.max(0, value));
  const strokeWidth = strokeWidthProp ?? size * 0.1;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - clampedValue / 100);

  // Value font scale: weight 300 for large rings (size >= 150), 500 for small
  const isLarge = size >= 150;
  const valueFontSize = isLarge ? size * 0.33 : size * 0.28;
  const valueFontFamily = isLarge ? 'SpaceGrotesk_400Regular' : 'SpaceGrotesk_500Medium';

  return (
    <View style={styles.container}>
      <View style={{ width: size, height: size }}>
        <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Track */}
          <SvgCircle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={themeColors.track}
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
        {/* Center overlay: optional innerLabel + value */}
        <View style={[StyleSheet.absoluteFill, styles.valueContainer]}>
          {innerLabel ? (
            <Text
              variant="label"
              color={themeColors.textMuted}
              style={styles.innerLabel}
            >
              {innerLabel.toUpperCase()}
            </Text>
          ) : null}
          <Text
            variant="body"
            color={themeColors.foreground}
            style={{ fontFamily: valueFontFamily, fontSize: valueFontSize, lineHeight: valueFontSize * 1.1, letterSpacing: isLarge ? -2 : -0.5, fontVariant: ['tabular-nums'] }}
          >
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
  innerLabel: { marginBottom: 2 },
  label: { textAlign: 'center' },
});
