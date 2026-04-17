import React from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { Text } from './Text';
import { useTheme } from '../theme/ThemeProvider';
import { colors } from '@resilio/design-tokens';

/**
 * Semi-arc dial indicator — 0 to 100.
 *
 * NAMING NOTE: Component is `CognitiveLoadDial` for file/API consistency with the
 * FE-MOBILE-2 brainstorm. In production UI, pass `label="Charge allostatique"` —
 * that is the correct clinical term aligned with `allostatic_score` in the backend.
 *
 * SVG geometry: upper semi-circle (180° arc) from left to right, sweeping upward.
 * - Path: M (left) A radius radius 0 0 1 (right)   [sweep-flag=1 = clockwise in SVG = upward visually]
 * - arcLength = π * radius
 * - strokeDashoffset = arcLength * (1 - value/100)
 *
 * StyleSheet exception: SVG absolute positioning for centered value overlay
 * (NativeWind cannot target children of <Svg>).
 */

export type DialState = 'green' | 'yellow' | 'red';

interface CognitiveLoadDialProps {
  /** Value 0–100 */
  value: number;
  /** Outer diameter in dp (default: 200) */
  size?: number;
  /** Optional label below the arc */
  label?: string;
  /** State drives stroke color */
  state: DialState;
}

function stateColor(state: DialState): string {
  switch (state) {
    case 'green':  return colors.zoneGreen;
    case 'yellow': return colors.zoneYellow;
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

  // SVG height: only the top half of the circle is visible
  const svgHeight = radius + strokeWidth;

  // Bottom-center of the SVG is the circle's center
  const cx = size / 2;
  const cy = svgHeight;

  // Arc endpoints on the horizontal diameter
  const startX = strokeWidth / 2;
  const endX = size - strokeWidth / 2;

  // sweep-flag=1 draws clockwise in SVG coordinates → visually goes UPWARD
  const trackPath = `M ${startX} ${cy} A ${radius} ${radius} 0 0 1 ${endX} ${cy}`;
  const fillDashoffset = arcLength * (1 - clampedValue / 100);

  const fillColor = stateColor(state);

  return (
    <View style={styles.container}>
      <View style={{ width: size, height: svgHeight }}>
        <Svg width={size} height={svgHeight} viewBox={`0 0 ${size} ${svgHeight}`}>
          {/* Track (background arc) */}
          <Path
            d={trackPath}
            stroke={themeColors.border}
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
          />
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

        {/* Value label — centered horizontally, positioned in lower half of the dial */}
        <View style={[StyleSheet.absoluteFill, styles.valueOverlay]}>
          <Text
            variant="title"
            color={fillColor}
            style={{ fontSize: size * 0.22, lineHeight: size * 0.28 }}
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
  container: { alignItems: 'center', gap: 8 },
  // Center value in the bottom 40% of the SVG (where the arc endpoints are)
  valueOverlay: { alignItems: 'center', justifyContent: 'flex-end', paddingBottom: 4 },
  label: { textAlign: 'center' },
});
