import React, { type ReactNode } from 'react';
import { Text as RNText, StyleSheet, type TextStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type TextVariant = 'display' | 'headline' | 'title' | 'body' | 'secondary' | 'caption' | 'label' | 'mono';

interface TextProps {
  children: ReactNode;
  variant?: TextVariant;
  color?: string;
  style?: TextStyle;
  numberOfLines?: number;
}

// Inter font variants — design system v2 (Claude Design handoff 2026-04-17)
const variantStyles: Record<TextVariant, TextStyle> = {
  // 72px weight-300 — readiness number (override size via style prop)
  display: {
    fontFamily: 'Inter_300Light',
    fontSize: 72,
    lineHeight: 72,
    letterSpacing: -2,
    fontVariant: ['tabular-nums'],
  },
  // 38px weight-300 — allostatic dial number
  headline: {
    fontFamily: 'Inter_300Light',
    fontSize: 38,
    lineHeight: 38,
    letterSpacing: -1.2,
    fontVariant: ['tabular-nums'],
  },
  // 26px weight-500 — greeting name, section headers
  title: {
    fontFamily: 'Inter_500Medium',
    fontSize: 26,
    lineHeight: 30,
    letterSpacing: -0.6,
  },
  // 15px weight-400 — body text, descriptions
  body: {
    fontFamily: 'Inter_400Regular',
    fontSize: 15,
    lineHeight: 21,
    letterSpacing: -0.1,
  },
  // 13px weight-400 — dates, details, secondary info
  secondary: {
    fontFamily: 'Inter_400Regular',
    fontSize: 13,
    lineHeight: 18,
    letterSpacing: 0.1,
    fontVariant: ['tabular-nums'],
  },
  // 12px weight-400 — metric labels, small text
  caption: {
    fontFamily: 'Inter_400Regular',
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.1,
  },
  // 11px weight-500 uppercase — section labels (SÉANCE DU JOUR, etc.)
  label: {
    fontFamily: 'Inter_500Medium',
    fontSize: 11,
    lineHeight: 14,
    letterSpacing: 1.2,
  },
  // Mono — tabular numeric data
  mono: {
    fontFamily: 'SpaceMono_400Regular',
    fontSize: 13,
    lineHeight: 20,
  },
};

/**
 * Typed typography component. Always use <Text> instead of RN Text directly.
 * Never hardcode hex colors — use the color prop with design tokens.
 *
 * Font migration: Space Grotesk → Inter (v2, 2026-04-17)
 */
export function Text({ children, variant = 'body', color, style, numberOfLines }: TextProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <RNText
      style={[
        styles.base,
        { color: color ?? themeColors.foreground },
        variantStyles[variant],
        style,
      ]}
      numberOfLines={numberOfLines}
    >
      {children}
    </RNText>
  );
}

const styles = StyleSheet.create({
  base: {},
});
