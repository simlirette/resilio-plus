import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, type ViewStyle } from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors } from '@resilio/design-tokens';
import { useTheme } from '../theme/ThemeProvider';
import { Text } from './Text';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'apple';

interface ButtonProps {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: ButtonVariant;
  style?: ViewStyle;
  /** Use Heavy haptic — for primary session actions (Démarrer, Set terminé) */
  heavyHaptic?: boolean;
}

/**
 * Button — Space Grotesk, amber accent. Spec: docs/design/<page>/SPEC.md
 *
 * Variants:
 * - primary: amber background, white text — all CTAs
 * - secondary: surfaceAlt background, border
 * - ghost: transparent, accent text + border
 * - apple: black/white depending on mode — Apple Sign In container
 *
 * Height: 54px, radius: 12px. disabled: opacity 0.4.
 */
export function Button({
  title,
  onPress,
  disabled = false,
  loading = false,
  variant = 'primary',
  style,
  heavyHaptic = false,
}: ButtonProps): React.JSX.Element {
  const { colorMode, colors: themeColors } = useTheme();
  const isDark = colorMode === 'dark';
  const accent = isDark ? colors.accentDark : colors.accent;

  function handlePress() {
    if (disabled || loading) return;
    if (variant === 'primary' || variant === 'apple') {
      void Haptics.impactAsync(
        heavyHaptic
          ? Haptics.ImpactFeedbackStyle.Heavy
          : Haptics.ImpactFeedbackStyle.Medium,
      );
    } else {
      void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    onPress();
  }

  const bgColor =
    variant === 'primary' ? accent
    : variant === 'apple'  ? (isDark ? '#FFFFFF' : '#000000')
    : variant === 'secondary' ? themeColors.surface2
    : 'transparent';

  const textColor =
    variant === 'primary' ? (isDark ? '#131210' : '#FFFFFF')
    : variant === 'apple'  ? (isDark ? '#000000' : '#FFFFFF')
    : variant === 'ghost'  ? accent
    : themeColors.foreground;

  const borderColor =
    variant === 'ghost' ? accent
    : variant === 'secondary' ? themeColors.border
    : 'transparent';

  return (
    <Pressable
      onPress={handlePress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.base,
        { backgroundColor: bgColor, borderColor, opacity: pressed ? 0.85 : 1 },
        variant === 'secondary' && styles.secondaryBorder,
        variant === 'ghost' && styles.ghostBorder,
        (disabled && !loading) && styles.disabled,
        style,
      ]}
      accessibilityRole="button"
      accessibilityState={{ disabled, busy: loading }}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === 'primary' ? (isDark ? '#131210' : '#FFFFFF') : accent}
        />
      ) : (
        <Text variant="bodyBold" color={textColor} style={styles.label}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 54,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
    borderWidth: 0,
  },
  secondaryBorder: {
    borderWidth: StyleSheet.hairlineWidth,
  },
  ghostBorder: {
    borderWidth: 1,
  },
  disabled: {
    opacity: 0.4,
  },
  label: {
    fontSize: 16,
  },
});
