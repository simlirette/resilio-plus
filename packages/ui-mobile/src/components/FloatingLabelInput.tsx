import React, { useCallback, useRef, useState } from 'react';
import {
  Animated,
  Pressable,
  StyleSheet,
  TextInput,
  type TextInputProps,
  View,
} from 'react-native';
import { colors } from '@resilio/design-tokens';
import { useTheme } from '../theme/ThemeProvider';
import { Text } from './Text';

interface FloatingLabelInputProps extends Omit<TextInputProps, 'style'> {
  label: string;
  error?: string;
  /** Show/hide toggle — use when secureTextEntry is true */
  showToggle?: boolean;
}

const ANIM_DURATION = 150;

/**
 * Input with animated floating label (translateY + scale via RN Animated).
 * Spec: docs/design/flow auth/SPEC.md
 *
 * - Border: 1px neutral → 1.5px accent on focus (margin -0.5px compensates layout shift)
 * - Label floats when value present or focused: translateY -22, scale 0.78
 * - Error: inline text below input (physio.red color)
 * - Password toggle: text "Voir" / "Masquer" (no icon dep)
 */
export function FloatingLabelInput({
  label,
  value,
  error,
  showToggle,
  secureTextEntry,
  onFocus,
  onBlur,
  ...rest
}: FloatingLabelInputProps): React.JSX.Element {
  const { colorMode, colors: themeColors } = useTheme();
  const isDark = colorMode === 'dark';

  const [focused, setFocused] = useState(false);
  const [hidden, setHidden] = useState(secureTextEntry ?? false);
  const inputRef = useRef<TextInput>(null);

  const isFloated = Boolean(value) || focused;
  const floatAnim = useRef(new Animated.Value(isFloated ? 1 : 0)).current;

  const animateTo = useCallback(
    (toValue: number) => {
      Animated.timing(floatAnim, {
        toValue,
        duration: ANIM_DURATION,
        useNativeDriver: true,
      }).start();
    },
    [floatAnim],
  );

  const handleFocus = useCallback(
    (e: Parameters<NonNullable<TextInputProps['onFocus']>>[0]) => {
      setFocused(true);
      animateTo(1);
      onFocus?.(e);
    },
    [animateTo, onFocus],
  );

  const handleBlur = useCallback(
    (e: Parameters<NonNullable<TextInputProps['onBlur']>>[0]) => {
      setFocused(false);
      if (!value) animateTo(0);
      onBlur?.(e);
    },
    [animateTo, onBlur, value],
  );

  // Sync animation when value changes programmatically
  React.useEffect(() => {
    animateTo(value || focused ? 1 : 0);
  }, [value, focused, animateTo]);

  const labelTranslateY = floatAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -18],
  });
  const labelScale = floatAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 0.76],
  });

  const accent = isDark ? colors.accentDark : colors.accent;
  const errorColor = isDark ? colors.physio.red.dark : colors.physio.red.light;
  const borderColor = error ? errorColor : focused ? accent : themeColors.border;
  const borderWidth = focused ? 1.5 : 1;
  const marginCompensation = focused ? -0.5 : 0;
  const labelColor = focused ? accent : themeColors.textMuted;

  return (
    <View style={styles.wrapper}>
      <Pressable
        onPress={() => inputRef.current?.focus()}
        accessible={false}
        style={[
          styles.container,
          {
            borderColor,
            borderWidth,
            margin: marginCompensation,
          },
        ]}
      >
        {/* Floating label */}
        <Animated.View
          pointerEvents="none"
          style={[
            styles.labelContainer,
            {
              transform: [
                { translateY: labelTranslateY },
                { scale: labelScale },
              ],
            },
          ]}
        >
          <Animated.Text
            style={[
              styles.labelText,
              {
                color: labelColor,
                fontFamily: 'SpaceGrotesk_500Medium',
              },
            ]}
          >
            {label}
          </Animated.Text>
        </Animated.View>

        {/* Text input — shifts up when floated */}
        <TextInput
          ref={inputRef}
          style={[
            styles.input,
            {
              color: themeColors.foreground,
              fontFamily: 'SpaceGrotesk_400Regular',
              paddingTop: isFloated ? 14 : 0,
            },
          ]}
          value={value}
          secureTextEntry={hidden}
          placeholderTextColor={themeColors.textMuted}
          onFocus={handleFocus}
          onBlur={handleBlur}
          {...rest}
        />

        {/* Password toggle */}
        {showToggle ? (
          <Pressable
            onPress={() => setHidden((h) => !h)}
            style={styles.toggleButton}
            hitSlop={8}
            accessibilityLabel={hidden ? 'Afficher le mot de passe' : 'Masquer le mot de passe'}
          >
            <Text variant="caption" color={themeColors.textMuted}>
              {hidden ? 'Voir' : 'Masquer'}
            </Text>
          </Pressable>
        ) : null}
      </Pressable>

      {/* Inline error */}
      {error ? (
        <Text variant="caption" color={errorColor} style={styles.error}>
          {error}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    gap: 4,
  },
  container: {
    height: 56,
    borderRadius: 10,
    borderWidth: 1,
    paddingHorizontal: 14,
    justifyContent: 'center',
    overflow: 'hidden',
  },
  labelContainer: {
    position: 'absolute',
    left: 14,
    right: 50,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
  },
  labelText: {
    fontSize: 15,
  },
  input: {
    fontSize: 15,
    height: '100%',
    paddingTop: 0,
    paddingBottom: 0,
    includeFontPadding: false,
  },
  toggleButton: {
    position: 'absolute',
    right: 14,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
  },
  error: {
    paddingHorizontal: 2,
  },
});
