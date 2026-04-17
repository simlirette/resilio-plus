/**
 * Resilio+ Design Tokens — Typography v2
 * Inter (sans) + Space Mono (mono for numeric displays)
 * Source: Claude Design handoff RbXZRFnMZI1nsG_v0vkzMw (2026-04-17)
 */

export const typography = {
  // Font families
  fontSans: "'Inter', -apple-system, system-ui, sans-serif",
  fontMono: "'Space Mono', 'Courier New', monospace",

  // Google Fonts import URL
  googleFontsUrl:
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',

  // Font sizes (rem)
  size: {
    xs: '0.75rem',    // 12px — metric labels, eyebrows
    sm: '0.8125rem',  // 13px — body secondary, badge text
    base: '1rem',     // 16px — button text
    lg: '1.0625rem',  // 17px — session title
    xl: '1.25rem',    // 20px — metric ring values
    '2xl': '1.625rem',// 26px — greeting
    '3xl': '2.375rem',// 38px — allostatic number
    '5xl': '4.5rem',  // 72px — readiness number
  },

  // Font weights
  weight: {
    light: '300',    // readiness/allostatic numbers
    normal: '400',   // body, dates
    medium: '500',   // labels, titles, buttons
    semibold: '600', // emphasized
    bold: '700',     // strong emphasis
  },

  // Line heights
  lineHeight: {
    none: '1',
    tight: '1.15',
    snug: '1.25',
    normal: '1.4',
    relaxed: '1.5',
  },

  // Letter spacing
  tracking: {
    tightest: '-2px',     // readiness number
    tighter: '-1.2px',    // allostatic number
    tight: '-0.6px',      // greeting
    snug: '-0.3px',       // session title
    nudge: '-0.1px',      // badge text
    normal: '0',
    wide: '0.1px',        // dates, metric labels
    wider: '0.6px',       // legend
    widest: '1.2px',      // section labels (CAPS)
    widestPlus: '1.6px',  // eyebrow
  },
} as const;
