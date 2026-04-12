import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator, ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { colors } from '@resilio/design-tokens';

interface ButtonProps {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary';
  style?: ViewStyle;
}

export function Button({ title, onPress, disabled = false, loading = false, variant = 'primary', style }: ButtonProps) {
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  const isPrimary = variant === 'primary';
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.8}
      style={[
        styles.base,
        {
          backgroundColor: isPrimary ? (disabled ? colors.primaryDim : colors.primary) : themeColors.surface2,
          borderColor: isPrimary ? 'transparent' : themeColors.border,
          borderWidth: isPrimary ? 0 : 1,
          opacity: disabled && !loading ? 0.5 : 1,
        },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator size="small" color={isPrimary ? '#fff' : colors.primary} />
      ) : (
        <Text style={[styles.label, { color: isPrimary ? '#fff' : themeColors.foreground }]}>
          {title}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: { height: 48, borderRadius: 12, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 20 },
  label: { fontSize: 15, fontWeight: '600' },
});
