'use client';
/**
 * @resilio/ui-web — ThemeProvider
 * Wraps next-themes ThemeProvider with Resilio+ defaults.
 * - Default theme: dark
 * - Persists to localStorage under key 'resilio-theme'
 * - Respects prefers-color-scheme on first load
 */
import React from 'react';
import { ThemeProvider as NextThemesProvider } from 'next-themes';

interface ThemeProviderProps {
  children: React.ReactNode;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      storageKey="resilio-theme"
      enableSystem
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  );
}
