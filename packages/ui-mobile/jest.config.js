/** @type {import('jest').Config} */
module.exports = {
  preset: 'jest-expo',
  setupFiles: ['./src/__tests__/setup-env.ts'],
  setupFilesAfterEnv: ['./src/__tests__/setup.ts'],
  testMatch: ['**/__tests__/**/*.test.{ts,tsx}'],
  moduleNameMapper: {
    // Mock all lucide-react-native icons as no-op components
    'lucide-react-native': '<rootDir>/src/__tests__/mocks/lucide-react-native.tsx',
    // Mock expo-haptics
    'expo-haptics': '<rootDir>/src/__tests__/mocks/expo-haptics.ts',
    // Mock react-native-svg
    'react-native-svg': '<rootDir>/src/__tests__/mocks/react-native-svg.tsx',
    // Mock safe-area-context
    'react-native-safe-area-context':
      '<rootDir>/src/__tests__/mocks/react-native-safe-area-context.ts',
    // Resolve workspace package
    '@resilio/design-tokens': '<rootDir>/../../packages/design-tokens/src/index.ts',
  },
  // pnpm stores packages at node_modules/.pnpm/<pkg>@<ver>/node_modules/<pkg>/
  // Two patterns are needed:
  // 1. Ignore .pnpm packages EXCEPT listed RN/Expo ones (matched by <pkg>@<ver> prefix)
  // 2. Ignore flat node_modules EXCEPT listed RN/Expo ones and .pnpm dir itself
  // pnpm stores packages at node_modules/.pnpm/<pkg>@<ver>/node_modules/<pkg>/
  // Scoped packages use + in pnpm paths: @react-native/js-polyfills → @react-native+js-polyfills
  // Two patterns:
  // 1. Ignore .pnpm packages EXCEPT listed ones (scoped use [@+] after package name)
  // 2. Ignore flat node_modules EXCEPT listed ones and the .pnpm dir itself
  transformIgnorePatterns: [
    'node_modules/\\.pnpm/(?!(react-native|@react-native|expo|@expo|nativewind|lucide-react-native|react-native-reanimated|react-native-safe-area-context|react-native-svg|@testing-library)[-@+])',
    'node_modules/(?!(\\.pnpm/|react-native|@react-native|expo|@expo|nativewind|lucide-react-native|react-native-reanimated|react-native-safe-area-context|react-native-svg|@testing-library))',
  ],
};
