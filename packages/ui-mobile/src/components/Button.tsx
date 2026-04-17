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
      backgroundColor: disabled ? colors.primaryDim : colors.primary,
      borderWidth: 0,
    },
    variant === 'secondary' && {
      backgroundColor: themeColors.surface2,
      borderColor: themeColors.border,
      borderWidth: 1,
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
    : variant === 'ghost' ? colors.primary
    : themeColors.foreground;

  return (
    <TouchableOpacity
      onPress={handlePress}
      disabled={disabled || loading}
      activeOpacity={0.8}
      style={containerStyle}
    >
      {loading ? (
        <ActivityIndicator size="small" color={variant === 'primary' ? '#ffffff' : colors.primary} />
      ) : (
        <Text style={[styles.label, { color: textColor }]}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: { height: 48, borderRadius: 12, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 20 },
  label: { fontSize: 15, fontWeight: '600' },
  disabled: { opacity: 0.5 },
});
