import React, { type ReactNode } from 'react';
import { Text as RNText, StyleSheet, type TextStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type TextVariant =
  | 'heroNumber'   // 72px/500 — readiness, large physio metric
  | 'heroPace'     // 80px/700 — live pace Mode B
  | 'heroLarge'    // 40px/700 — charge/reps Mode B muscu
  | 'pageTitle'    // 28px/700 — page titles, session titles
  | 'stepTitle'    // 26px/700 — onboarding step titles
  | 'sectionTitle' // 22px/700 — card section headers
  | 'wordmark'     // 17px/600 — "Resilio+"
  | 'navBar'       // 17px/600 — navigation bar
  | 'metric'       // 17px/500 — metric values (tabular)
  | 'body'         // 15px/400 — body text
  | 'bodyBold'     // 15px/600 — emphasized body
  | 'secondary'    // 14px/400 — secondary body, coach justification
  | 'caption'      // 13px/400 — details, timestamps, delta values
  | 'label'        // 11px/500 — small-caps section labels (uppercase enforced)
  | 'smallCaps';   // 11px/500 — alias of label, explicit small-caps intent

type TextVariantAlias = TextVariant | 'display' | 'headline' | 'title' | 'mono'; // back-compat

interface TextProps {
  children: ReactNode;
  variant?: TextVariantAlias;
  color?: string;
  style?: TextStyle;
  numberOfLines?: number;
  tabular?: boolean; // force tabular-nums even on non-numeric variants
}

// Space Grotesk variants — UI-RULES.md + docs/design/*/SPEC.md
const variantStyles: Record<TextVariantAlias, TextStyle> = {
  // ── Hero numbers ─────────────────────────────────────────────────────────
  heroNumber: {
    fontFamily: 'SpaceGrotesk_500Medium',
    fontSize: 72,
    lineHeight: 72,
    letterSpacing: -2,
    fontVariant: ['tabular-nums'],
  },
  heroPace: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 80,
    lineHeight: 80,
    letterSpacing: -3,
    fontVariant: ['tabular-nums'],
  },
  heroLarge: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 40,
    lineHeight: 44,
    letterSpacing: -1,
    fontVariant: ['tabular-nums'],
  },
  // ── Titles ────────────────────────────────────────────────────────────────
  pageTitle: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 28,
    lineHeight: 32,
    letterSpacing: -0.5,
  },
  stepTitle: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 26,
    lineHeight: 30,
    letterSpacing: -0.5,
  },
  sectionTitle: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 22,
    lineHeight: 26,
    letterSpacing: -0.3,
  },
  // ── Navigation / chrome ───────────────────────────────────────────────────
  wordmark: {
    fontFamily: 'SpaceGrotesk_600SemiBold',
    fontSize: 17,
    letterSpacing: -0.3,
  },
  navBar: {
    fontFamily: 'SpaceGrotesk_600SemiBold',
    fontSize: 17,
    letterSpacing: -0.1,
  },
  metric: {
    fontFamily: 'SpaceGrotesk_500Medium',
    fontSize: 17,
    lineHeight: 20,
    fontVariant: ['tabular-nums'],
  },
  // ── Body ─────────────────────────────────────────────────────────────────
  body: {
    fontFamily: 'SpaceGrotesk_400Regular',
    fontSize: 15,
    lineHeight: 21,
  },
  bodyBold: {
    fontFamily: 'SpaceGrotesk_600SemiBold',
    fontSize: 15,
    lineHeight: 21,
  },
  secondary: {
    fontFamily: 'SpaceGrotesk_400Regular',
    fontSize: 14,
    lineHeight: 20,
  },
  caption: {
    fontFamily: 'SpaceGrotesk_400Regular',
    fontSize: 13,
    lineHeight: 18,
    fontVariant: ['tabular-nums'],
  },
  // ── Labels ────────────────────────────────────────────────────────────────
  label: {
    fontFamily: 'SpaceGrotesk_500Medium',
    fontSize: 11,
    lineHeight: 14,
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
  smallCaps: {
    fontFamily: 'SpaceGrotesk_500Medium',
    fontSize: 11,
    lineHeight: 14,
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
  // ── Back-compat aliases ───────────────────────────────────────────────────
  display: {
    fontFamily: 'SpaceGrotesk_500Medium',
    fontSize: 72,
    lineHeight: 72,
    letterSpacing: -2,
    fontVariant: ['tabular-nums'],
  },
  headline: {
    fontFamily: 'SpaceGrotesk_500Medium',
    fontSize: 38,
    lineHeight: 38,
    letterSpacing: -1.2,
    fontVariant: ['tabular-nums'],
  },
  title: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 28,
    lineHeight: 32,
    letterSpacing: -0.5,
  },
  mono: {
    fontFamily: 'SpaceGrotesk_400Regular',
    fontSize: 13,
    lineHeight: 20,
    fontVariant: ['tabular-nums'],
  },
};

/**
 * Typed typography component — Space Grotesk only.
 * Always use <Text> instead of RN Text directly.
 * Never hardcode hex colors — use the color prop with design tokens.
 */
export function Text({
  children,
  variant = 'body',
  color,
  style,
  numberOfLines,
  tabular,
}: TextProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <RNText
      style={[
        { color: color ?? themeColors.foreground },
        variantStyles[variant],
        tabular ? styles.tabular : undefined,
        style,
      ]}
      numberOfLines={numberOfLines}
    >
      {children}
    </RNText>
  );
}

const styles = StyleSheet.create({
  tabular: { fontVariant: ['tabular-nums'] },
});
