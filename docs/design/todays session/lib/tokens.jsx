// tokens.jsx — Resilio+ design tokens (light + dark)
// Neutrals are warm (a touch of yellow in the grey).
// Accent: single electric lime, reserved for primary actions + brand marks.
// Physio semantics: green / yellow / red only for Readiness, Strain, HRV, Sleep.

const ACCENTS = {
  electric: { base: '#C8FF4D', ink: '#0E1200' },  // warm lime
  amber:    { base: '#FFB347', ink: '#1A0E00' },
  ice:      { base: '#8ECDEB', ink: '#001018' },
};

function makeTheme(dark, accentKey = 'electric') {
  const a = ACCENTS[accentKey] || ACCENTS.electric;
  if (dark) {
    return {
      dark: true,
      accent: a.base,
      accentInk: a.ink,
      bg:       '#141311',        // warm charcoal, NOT clinical #08080e
      bgElev:   '#1C1B18',        // card
      bgElev2:  '#242320',        // inset / pressed
      hairline: 'rgba(255,248,230,0.08)',
      hairlineStrong: 'rgba(255,248,230,0.14)',
      ink:      '#F3EFE6',        // warm white
      inkMuted: 'rgba(243,239,230,0.62)',
      inkDim:   'rgba(243,239,230,0.38)',
      inkFaint: 'rgba(243,239,230,0.22)',
      // physio semantics — muted, warm
      green:    '#8FCB82',
      yellow:   '#E8C86A',
      red:      '#E27A6F',
    };
  }
  return {
    dark: false,
    accent: a.base,
    accentInk: a.ink,
    bg:       '#F5F3EE',          // off-white, warm
    bgElev:   '#FFFFFF',
    bgElev2:  '#EDEAE2',
    hairline: 'rgba(26,22,16,0.08)',
    hairlineStrong: 'rgba(26,22,16,0.16)',
    ink:      '#181613',          // warm near-black
    inkMuted: 'rgba(24,22,19,0.62)',
    inkDim:   'rgba(24,22,19,0.42)',
    inkFaint: 'rgba(24,22,19,0.22)',
    green:    '#3F8A4A',
    yellow:   '#B88A16',
    red:      '#B64536',
  };
}

// Type scale — Space Grotesk, tabular where relevant
const T = {
  font: "'Space Grotesk', system-ui, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, monospace",
  // helpers
  tabular: { fontVariantNumeric: 'tabular-nums', fontFeatureSettings: '"tnum" 1, "zero" 1' },
  smallcaps: { textTransform: 'uppercase', letterSpacing: '0.14em', fontSize: 11, fontWeight: 500 },
};

Object.assign(window, { makeTheme, T, ACCENTS });
