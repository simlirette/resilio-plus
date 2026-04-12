import React, { createContext, useContext, ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { colors } from '@resilio/design-tokens';

export type ColorMode = 'dark' | 'light';

export interface ThemeContextValue {
  colorMode: ColorMode;
  colors: typeof colors.dark | typeof colors.light;
}

export const ThemeContext = createContext<ThemeContextValue>({
  colorMode: 'dark',
  colors: colors.dark,
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const scheme = useColorScheme();
  const colorMode: ColorMode = scheme === 'light' ? 'light' : 'dark';
  const themeColors = colorMode === 'light' ? colors.light : colors.dark;
  return (
    <ThemeContext.Provider value={{ colorMode, colors: themeColors }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
