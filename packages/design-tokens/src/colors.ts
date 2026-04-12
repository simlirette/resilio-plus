/**
 * Resilio+ Design Tokens — Color palette
 * Source of truth for all color values across web, desktop, and mobile.
 * NEVER hardcode these values in components — always import from here.
 */

export const colors = {
  // ── Surface hierarchy ────────────────────────────────────────────────────
  dark: {
    background: '#08080e',
    surface1: '#0f0f18',
    surface2: '#14141f',
    surface3: '#1a1a28',
    border: '#22223a',
    borderSubtle: '#191928',
    foreground: '#eeeef4',
    textMuted: '#5c5c7a',
    textSecondary: '#8888a8',
  },

  light: {
    background: '#f8f8fc',
    surface1: '#f0f0f8',
    surface2: '#ffffff',
    surface3: '#f4f4fb',
    border: '#e2e2ee',
    borderSubtle: '#ebebf5',
    foreground: '#0f0f18',
    textMuted: '#6b6b88',
    textSecondary: '#888899',
  },

  // ── Brand accent ─────────────────────────────────────────────────────────
  primary: '#5b5fef',
  primaryForeground: '#ffffff',
  primaryDim: 'rgba(91, 95, 239, 0.15)',

  // ── Status / training zones ──────────────────────────────────────────────
  zoneGreen: '#10b981',
  zoneGreenBg: 'rgba(16, 185, 129, 0.10)',
  zoneYellow: '#f59e0b',
  zoneYellowBg: 'rgba(245, 158, 11, 0.10)',
  zoneRed: '#ef4444',
  zoneRedBg: 'rgba(239, 68, 68, 0.10)',
  zoneCritical: '#dc2626',

  // ── RGB channels for alpha variants ─────────────────────────────────────
  primaryRgb: '91, 95, 239',
  zoneGreenRgb: '16, 185, 129',
  zoneYellowRgb: '245, 158, 11',
  zoneRedRgb: '239, 68, 68',
  zoneCriticalRgb: '220, 38, 38',
  phaseLutealRgb: '129, 140, 248',

  // ── Cycle phase colors ───────────────────────────────────────────────────
  phaseMenstrual: '#ef4444',
  phaseFollicular: '#10b981',
  phaseOvulation: '#f59e0b',
  phaseLuteal: '#818cf8',

  // ── Shadcn semantic (dark) ───────────────────────────────────────────────
  shadcn: {
    dark: {
      background: '#08080e',
      foreground: '#eeeef4',
      card: '#14141f',
      cardForeground: '#eeeef4',
      muted: '#1a1a28',
      mutedForeground: '#5c5c7a',
      border: '#22223a',
      primary: '#5b5fef',
      primaryForeground: '#ffffff',
      secondary: '#1a1a28',
      secondaryForeground: '#8888a8',
      destructive: '#ef4444',
      destructiveForeground: '#ffffff',
      input: '#1a1a28',
      ring: '#5b5fef',
    },
    light: {
      background: '#f8f8fc',
      foreground: '#0f0f18',
      card: '#ffffff',
      cardForeground: '#0f0f18',
      muted: '#f0f0f8',
      mutedForeground: '#6b6b88',
      border: '#e2e2ee',
      primary: '#5b5fef',
      primaryForeground: '#ffffff',
      secondary: '#f0f0f8',
      secondaryForeground: '#6b6b88',
      destructive: '#ef4444',
      destructiveForeground: '#ffffff',
      input: '#f0f0f8',
      ring: '#5b5fef',
    },
  },
} as const;

export type ColorMode = 'dark' | 'light';
