/** @type {import('tailwindcss').Config} */
module.exports = {
  presets: [require('nativewind/preset')],
  content: [
    './app/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
    '../../packages/ui-mobile/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Source: @resilio/design-tokens/src/colors.ts
        primary: '#5b5fef',
        'primary-dim': 'rgba(91, 95, 239, 0.15)',
        'zone-green': '#10b981',
        'zone-yellow': '#f59e0b',
        'zone-red': '#ef4444',
        'zone-critical': '#dc2626',
        // Dark surfaces (default — Resilio+ is dark-first)
        background: '#08080e',
        'surface-1': '#0f0f18',
        'surface-2': '#14141f',
        'surface-3': '#1a1a28',
        'border-col': '#22223a',
        foreground: '#eeeef4',
        'text-muted': '#5c5c7a',
        'text-secondary': '#8888a8',
      },
      fontFamily: {
        // Source: @resilio/design-tokens/src/typography.ts
        sans: ['SpaceGrotesk_400Regular', 'system-ui', 'sans-serif'],
        mono: ['SpaceMono_400Regular', 'monospace'],
      },
      borderRadius: {
        // Source: @resilio/design-tokens/src/radius.ts
        sm: 4,
        md: 8,
        lg: 12,
        xl: 16,
        '2xl': 24,
      },
      spacing: {
        // Source: @resilio/design-tokens/src/spacing.ts (4px scale)
        1: 4,
        2: 8,
        3: 12,
        4: 16,
        6: 24,
        8: 32,
        12: 48,
        16: 64,
      },
    },
  },
};
