/**
 * Resilio+ Design Tokens — Typography
 * Space Grotesk (sans) + Space Mono (mono)
 */

export const typography = {
  // Font families
  fontSans: "'Space Grotesk', system-ui, sans-serif",
  fontMono: "'Space Mono', 'Courier New', monospace",

  // Google Fonts import URL
  googleFontsUrl:
    'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap',

  // Font sizes (rem)
  size: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '1.875rem',// 30px
    '4xl': '2.25rem', // 36px
    '6xl': '3.75rem', // 60px
  },

  // Font weights
  weight: {
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },

  // Line heights
  lineHeight: {
    tight: '1.2',
    snug: '1.375',
    normal: '1.5',
    relaxed: '1.625',
  },

  // Letter spacing
  tracking: {
    tight: '-0.02em',
    normal: '0',
    wide: '0.025em',
    widest: '0.1em',
  },
} as const;
