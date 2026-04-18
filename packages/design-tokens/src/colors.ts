/**
 * Resilio+ Design Tokens — Color palette v2
 * Warm off-white + warm near-black. Apple Health / Whoop 5.0 inspired.
 * Source: Claude Design handoff RbXZRFnMZI1nsG_v0vkzMw (2026-04-17)
 * NEVER hardcode these values in components — always import from here.
 */

export const colors = {
  // ── Accent (Amber/Terracotta — canonical) ───────────────────────────────
  accent: '#B8552E',        // light mode
  accentDark: '#D97A52',    // dark mode
  accentDim: 'rgba(184,85,46,0.20)',

  // Legacy alias — keep so existing imports of colors.primary still compile
  primary: '#B8552E',
  primaryForeground: '#ffffff',
  primaryDim: 'rgba(184,85,46,0.15)',

  // ── Physiological semantic (Readiness / Strain / Sleep ONLY) ────────────
  // Never use these on UI chrome (buttons, cards, labels unrelated to physio)
  physio: {
    green:  { light: '#3F8A4A', dark: '#8FCB82' },
    yellow: { light: '#B8863A', dark: '#E8C86A' },  // light = amber reused
    red:    { light: '#B64536', dark: '#E27A6F' },
  },

  // ── Semantic status ──────────────────────────────────────────────────────
  // Zone colors (legacy aliases for training-zone logic — not for UI chrome)
  zoneGreen: '#6B9259',
  zoneGreenBg: 'rgba(107,146,89,0.12)',
  zoneYellow: '#B8863A',
  zoneYellowBg: 'rgba(184,134,58,0.12)',
  zoneRed: '#B64536',               // terracotta warm (was #ef4444 cold red)
  zoneRedBg: 'rgba(182,69,54,0.10)',
  zoneCritical: '#9C3020',

  // RGB channels for alpha variants
  primaryRgb: '184, 85, 46',
  zoneGreenRgb: '107, 146, 89',
  zoneYellowRgb: '184, 134, 58',
  zoneRedRgb: '182, 69, 54',
  zoneCriticalRgb: '156, 48, 32',
  phaseLutealRgb: '129, 140, 248',

  // ── Cycle phase colors ───────────────────────────────────────────────────
  phaseMenstrual: '#ef4444',
  phaseFollicular: '#6B9259',
  phaseOvulation: '#B8863A',
  phaseLuteal: '#818cf8',

  // ── Dark mode surfaces ───────────────────────────────────────────────────
  dark: {
    background: '#131210',       // warm near-black
    surface1: '#1C1B18',         // card surface
    surface2: '#232120',         // inner metric / badge bg
    surface3: '#1C1B18',         // compat alias for surface1
    border: 'rgba(237,233,226,0.08)',
    borderSubtle: 'rgba(237,233,226,0.05)',
    foreground: '#EDE9E2',       // warm off-white text
    textMuted: 'rgba(237,233,226,0.38)',
    textSecondary: 'rgba(237,233,226,0.62)',
    track: 'rgba(237,233,226,0.08)',  // SVG arc track
    warn: '#D6A24A',             // nutrition / caution
    ok: '#7DA66A',               // strain / positive
    okStrong: '#6B9259',         // sleep / strong positive
    caution: '#C79140',          // prudent state dot
  },

  // ── Light mode surfaces ──────────────────────────────────────────────────
  light: {
    background: '#F7F4EE',       // warm off-white
    surface1: '#FDFBF7',         // card surface
    surface2: '#F3EFE8',         // inner metric / badge bg
    surface3: '#FDFBF7',         // compat alias for surface1
    border: 'rgba(43,40,36,0.08)',
    borderSubtle: 'rgba(43,40,36,0.05)',
    foreground: '#2B2824',       // warm charcoal text
    textMuted: 'rgba(43,40,36,0.38)',
    textSecondary: 'rgba(43,40,36,0.62)',
    track: 'rgba(43,40,36,0.08)',     // SVG arc track
    warn: '#B8863A',             // nutrition / caution
    ok: '#6B9259',               // strain / positive
    okStrong: '#5C8250',         // sleep / strong positive
    caution: '#A6762E',          // prudent state dot
  },

  // ── Shadcn semantic (web) ────────────────────────────────────────────────
  shadcn: {
    dark: {
      background: '#131210',
      foreground: '#EDE9E2',
      card: '#1C1B18',
      cardForeground: '#EDE9E2',
      muted: '#232120',
      mutedForeground: 'rgba(237,233,226,0.38)',
      border: 'rgba(237,233,226,0.08)',
      primary: '#D97A52',
      primaryForeground: '#ffffff',
      secondary: '#232120',
      secondaryForeground: 'rgba(237,233,226,0.62)',
      destructive: '#ef4444',
      destructiveForeground: '#ffffff',
      input: '#232120',
      ring: '#D97A52',
    },
    light: {
      background: '#F7F4EE',
      foreground: '#2B2824',
      card: '#FDFBF7',
      cardForeground: '#2B2824',
      muted: '#F3EFE8',
      mutedForeground: 'rgba(43,40,36,0.38)',
      border: 'rgba(43,40,36,0.08)',
      primary: '#B8552E',
      primaryForeground: '#ffffff',
      secondary: '#F3EFE8',
      secondaryForeground: 'rgba(43,40,36,0.62)',
      destructive: '#ef4444',
      destructiveForeground: '#ffffff',
      input: '#F3EFE8',
      ring: '#B8552E',
    },
  },
} as const;

export type ColorMode = 'dark' | 'light';
