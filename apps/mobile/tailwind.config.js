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
        // Source: @resilio/design-tokens/src/colors.ts v2
        // Accent
        accent: '#3B74C9',
        primary: '#3B74C9',
        'primary-dim': 'rgba(59,116,201,0.15)',
        // Semantic zone (training logic — not UI chrome)
        'zone-green': '#6B9259',
        'zone-yellow': '#B8863A',
        'zone-red': '#ef4444',
        'zone-critical': '#dc2626',
        // Light mode
        'bg-light': '#F7F4EE',
        'surface-light': '#FDFBF7',
        'surface2-light': '#F3EFE8',
        // Dark mode
        'bg-dark': '#131210',
        'surface-dark': '#1C1B18',
        'surface2-dark': '#232120',
      },
      fontFamily: {
        // Source: @resilio/design-tokens/src/typography.ts v2
        sans: ['Inter_400Regular', 'system-ui', 'sans-serif'],
        mono: ['SpaceMono_400Regular', 'monospace'],
      },
      borderRadius: {
        // Source: @resilio/design-tokens/src/radius.ts
        sm: 4,
        md: 8,
        lg: 12,
        xl: 16,
        '2xl': 22,
        '3xl': 33,
      },
      spacing: {
        // Source: @resilio/design-tokens/src/spacing.ts (4px scale)
        1: 4,
        2: 8,
        3: 12,
        4: 16,
        5: 20,
        6: 24,
        8: 32,
        12: 48,
        16: 64,
      },
    },
  },
};
