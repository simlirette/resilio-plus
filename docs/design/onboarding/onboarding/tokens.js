// Design tokens for Resilio+ onboarding
const TOKENS = {
  light: {
    bg: '#F5F5F2',
    surface: '#FFFFFF',
    surfaceAlt: '#FAFAF7',
    text: '#1A1A18',
    textSub: 'oklch(0.42 0.006 80)',
    textMuted: 'oklch(0.56 0.006 80)',
    border: 'oklch(0.88 0.004 80)',
    borderStrong: 'oklch(0.80 0.006 80)',
    accent: 'oklch(0.64 0.14 45)',
    accentText: '#FFFFFF',
    accentSoft: 'oklch(0.94 0.03 45)',
    overlay: 'rgba(0,0,0,0.04)',
    statusBar: '#000',
  },
  dark: {
    bg: '#17161A',
    surface: '#201E23',
    surfaceAlt: '#26232A',
    text: '#F0EEEA',
    textSub: 'oklch(0.76 0.008 80)',
    textMuted: 'oklch(0.58 0.008 80)',
    border: 'oklch(0.28 0.005 60)',
    borderStrong: 'oklch(0.36 0.006 60)',
    accent: 'oklch(0.72 0.14 45)',
    accentText: '#17161A',
    accentSoft: 'oklch(0.30 0.06 45)',
    overlay: 'rgba(255,255,255,0.04)',
    statusBar: '#fff',
  },
};

window.TOKENS = TOKENS;
