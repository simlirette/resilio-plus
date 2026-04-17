import React from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Path, Line } from 'react-native-svg';
import { Text } from './Text';
import { useTheme } from '../theme/ThemeProvider';
import { colors } from '@resilio/design-tokens';

/**
 * Semi-arc dial indicator — 0 to 100.
 *
 * NAMING NOTE: Component is `CognitiveLoadDial` for file/API consistency.
 * In production UI, pass `label="Charge allostatique"` — that is the correct
 * clinical term aligned with `allostatic_score` in the backend.
 *
 * SVG geometry: upper semi-circle (180° arc) from left to right, sweeping upward.
 * Design v2: tick marks at 0.25/0.5/0.75, accent fill color, weight-300 value.
 *
 * StyleSheet exception: SVG absolute positioning for centered value overlay.
 */

export type DialState = 'green' | 'yellow' | 'red';

interface CognitiveLoadDialProps {
  /** Value 0–100 */
  value: number;
  /** Outer diameter in dp (default: 200) */
  size?: number;
  /** Optional label below the arc */
  label?: string;
  /** State drives fallback color if accent not suitable */
  state: DialState;
}

function stateColor(state: DialState): string {
  switch (state) {
    case 'green':  return colors.accent;
    case 'yellow': return colors.accent;
    case 'red':    return colors.zoneRed;
  }
}

export function CognitiveLoadDial({
  value,
  size = 200,
  label,
  state,
}: CognitiveLoadDialProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();

  const clampedValue = Math.min(100, Math.max(0, value));
  const strokeWidth = size * 0.08;
  const radius = (size - strokeWidth) / 2;
  const arcLength = Math.PI * radius;

  const svgHeight = radius + strokeWidth;
  const cx = size / 2;
  const cy = svgHeight;

  const startX = strokeWidth / 2;
  const endX = size - strokeWidth / 2;

  const trackPath = `M ${startX} ${cy} A ${radius} ${radius} 0 0 1 ${endX} ${cy}`;
  const fillDashoffset = arcLength * (1 - clampedValue / 100);
  const fillColor = stateColor(state);

  // Tick marks at 25%, 50%, 75% of arc
  const tickPositions = [0.25, 0.5, 0.75];
  const ticks = tickPositions.map((p) => {
    const angle = Math.PI - p * Math.PI;
    const inner = radius - strokeWidth / 2 - 2;
    const outer = radius + strokeWidth / 2 + 2;
    return {
      key: p,
      x1: cx + inner * Math.cos(angle),
      y1: cy - inner * Math.sin(angle),
      x2: cx + outer * Math.cos(angle),
      y2: cy - outer * Math.sin(angle),
    };
  });

  return (
    <View style={styles.container}>
      <View style={{ width: size, height: svgHeight }}>
        <Svg width={size} height={svgHeight} viewBox={`0 0 ${size} ${svgHeight}`}>
          {/* Track */}
          <Path
            d={trackPath}
            stroke={themeColors.track}
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
          />
          {/* Tick marks */}
          {ticks.map((t) => (
            <Line
              key={t.key}
              x1={t.x1} y1={t.y1}
              x2={t.x2} y2={t.y2}
              stroke={themeColors.border}
              strokeWidth={1}
            />
          ))}
          {/* Value arc */}
          <Path
            d={trackPath}
            stroke={fillColor}
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${arcLength} ${arcLength}`}
            strokeDashoffset={fillDashoffset}
          />
        </Svg>

        {/* Value label — centered at bottom of arc */}
        <View style={[StyleSheet.absoluteFill, styles.valueOverlay]}>
          <Text
            variant="headline"
            color={themeColors.foreground}
            style={{ fontSize: size * 0.19, lineHeight: size * 0.22, letterSpacing: -1.2 }}
          >
            {clampedValue}
          </Text>
          <Text
            variant="label"
            color={themeColors.textMuted}
            style={{ marginTop: 2 }}
          >
            / 100
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
  container: { alignItems: 'center', gap: 8 },
  valueOverlay: { alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 4 },
  label: { textAlign: 'center' },
});
