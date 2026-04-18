import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator, type ViewStyle } from 'react-native';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../theme/ThemeProvider';
import { colors } from '@resilio/design-tokens';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';

interface ButtonProps {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: ButtonVariant;
  style?: ViewStyle;
}

/**
 * Button component. Design v2: height=54, radius=16, accent color.
 * Primary: Amber #B8552E (light) / #D97A52 (dark), 6px shadow bloom.
 */
export function Button({ title, onPress, disabled = false, loading = false, variant = 'primary', style }: ButtonProps): React.JSX.Element {
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;

  function handlePress() {
    if (variant === 'primary') {
      void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    } else {
      void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    onPress();
  }

  const containerStyle = [
    styles.base,
    variant === 'primary' && {
      backgroundColor: disabled ? colors.accentDim : colors.accent,
      borderWidth: 0,
      // Shadow bloom
      shadowColor: colors.accent,
      shadowOffset: { width: 0, height: 6 },
      shadowOpacity: disabled ? 0 : 0.22,
      shadowRadius: 14,
      elevation: disabled ? 0 : 4,
    },
    variant === 'secondary' && {
      backgroundColor: themeColors.surface2,
      borderColor: themeColors.border,
      borderWidth: 0.5,
    },
    variant === 'ghost' && {
      backgroundColor: 'transparent',
      borderWidth: 0,
    },
    disabled && !loading && styles.disabled,
    style,
  ];

  const textColor =
    variant === 'primary' ? '#ffffff'
    : variant === 'ghost' ? colors.accent
    : themeColors.foreground;

  return (
    <TouchableOpacity
      onPress={handlePress}
      disabled={disabled || loading}
      activeOpacity={0.8}
      style={containerStyle}
    >
      {loading ? (
        <ActivityIndicator size="small" color={variant === 'primary' ? '#ffffff' : colors.accent} />
      ) : (
        <Text style={[styles.label, { color: textColor }]}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: { height: 54, borderRadius: 16, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 20 },
  label: { fontFamily: 'Inter_500Medium', fontSize: 16, letterSpacing: -0.1 },
  disabled: { opacity: 0.5 },
});
