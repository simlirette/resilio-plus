import React, { type ReactNode } from 'react';
import { ScrollView, View, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../theme/ThemeProvider';

interface ScreenProps {
  children: ReactNode;
  /** Wraps content in ScrollView when true */
  scroll?: boolean;
  /** Adds horizontal/vertical padding (24px) when true */
  padded?: boolean;
}

/**
 * Screen wrapper providing safe area + background token.
 * Always use <Screen> instead of SafeAreaView directly.
 * Uses useSafeAreaInsets (React 19 compatible) instead of SafeAreaView component.
 */
export function Screen({ children, scroll = false, padded = false }: ScreenProps): React.JSX.Element {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  const safeStyle = {
    paddingTop: insets.top,
    paddingBottom: insets.bottom,
    paddingLeft: insets.left,
    paddingRight: insets.right,
    backgroundColor: colors.background,
  };

  const innerStyle = padded ? styles.padded : styles.flex;

  if (scroll) {
    return (
      <View style={[styles.flex, safeStyle]}>
        <ScrollView
          style={styles.flex}
          contentContainerStyle={padded ? styles.scrollPadded : undefined}
          keyboardShouldPersistTaps="handled"
        >
          {children}
        </ScrollView>
      </View>
    );
  }

  return (
    <View style={[styles.flex, safeStyle]}>
      <View style={innerStyle}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  padded: { flex: 1, paddingHorizontal: 24, paddingVertical: 16 },
  scrollPadded: { paddingHorizontal: 24, paddingVertical: 16 },
});
