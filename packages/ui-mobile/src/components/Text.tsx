import React, { type ReactNode } from 'react';
import { Text as RNText, StyleSheet, type TextStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

type TextVariant = 'display' | 'title' | 'body' | 'caption' | 'mono';

interface TextProps {
  children: ReactNode;
  variant?: TextVariant;
  color?: string;
  style?: TextStyle;
  numberOfLines?: number;
}

const variantStyles: Record<TextVariant, TextStyle> = {
  display: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 36,
    lineHeight: 44,
    letterSpacing: -0.5,
  },
  title: {
    fontFamily: 'SpaceGrotesk_700Bold',
    fontSize: 22,
    lineHeight: 28,
  },
  body: {
    fontFamily: 'SpaceGrotesk_400Regular',
    fontSize: 15,
    lineHeight: 22,
  },
  caption: {
    fontFamily: 'SpaceGrotesk_400Regular',
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.25,
  },
  mono: {
    fontFamily: 'SpaceMono_400Regular',
    fontSize: 13,
    lineHeight: 20,
  },
};

/**
 * Typed typography component. Always use <Text> instead of RN Text directly.
 * Never hardcode hex colors — use the color prop with design tokens.
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
