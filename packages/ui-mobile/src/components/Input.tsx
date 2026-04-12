import React from 'react';
import { View, Text, TextInput, StyleSheet, TextInputProps, ViewStyle } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { colors } from '@resilio/design-tokens';

interface InputProps extends TextInputProps { label?: string; style?: ViewStyle; }

export function Input({ label, style, ...props }: InputProps) {
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  return (
    <View style={style}>
      {label ? <Text style={[styles.label, { color: themeColors.textSecondary }]}>{label}</Text> : null}
      <TextInput
        style={[styles.input, { backgroundColor: themeColors.surface1, borderColor: themeColors.border, color: themeColors.foreground }]}
        placeholderTextColor={themeColors.textMuted}
        {...props}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  label: { fontSize: 13, fontWeight: '500', marginBottom: 6 },
  input: { height: 48, borderRadius: 10, borderWidth: 1, paddingHorizontal: 14, fontSize: 15 },
});
