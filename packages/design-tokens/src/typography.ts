/**
 * Resilio+ Design Tokens — Typography v3
 * Space Grotesk (400/500/600/700) — only font family.
 * Source: UI-RULES.md + Claude Design handoff (2026-04-18)
 */

export const typography = {
  // Font families — web
  fontSans: "'Space Grotesk', -apple-system, system-ui, sans-serif",

  // Font family names — React Native (useFonts key names)
  fontFamily: {
    regular:  'SpaceGrotesk_400Regular',
    medium:   'SpaceGrotesk_500Medium',
    semibold: 'SpaceGrotesk_600SemiBold',
    bold:     'SpaceGrotesk_700Bold',
  },

  // Font sizes (rem — web)
  size: {
    xs:   '0.75rem',    // 12px — caption, timestamps
    sm:   '0.8125rem',  // 13px — body secondary, badge text
    base: '1rem',       // 16px — button text, input value
    lg:   '1.0625rem',  // 17px — nav bar, metric values
    xl:   '1.25rem',    // 20px — metric values large
    '2xl':'1.625rem',   // 26px — step title onboarding
    '3xl':'1.75rem',    // 28px — page title, session title
    '4xl':'2.5rem',     // 40px — hero charge/reps
    '5xl':'4.5rem',     // 72px — readiness number
    '6xl':'5rem',       // 80px — hero pace
  },

  // Font weights
  weight: {
    normal:   '400',
    medium:   '500',
    semibold: '600',
    bold:     '700',
  },

  // Line heights
  lineHeight: {
    none:    '1',
    tight:   '1.15',
    snug:    '1.25',
    normal:  '1.4',
    relaxed: '1.5',
  },

  // Letter spacing
  tracking: {
    tightest:   -3,      // hero pace
    tighter:    -2,      // readiness number
    tight:      -0.5,    // page titles, step titles
    snug:       -0.3,    // session title, wordmark
    normal:     0,
    wide:       0.5,     // dates
    wider:      1,       // small-caps labels (approximate)
    widest:     2,       // small-caps labels (11px @0.14em)
  },
} as const;
