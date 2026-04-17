/**
 * Jest config for apps/mobile component tests (React Native environment).
 * Different from jest.regression.config.js (pure Node) — this uses jest-expo preset.
 *
 * Run: cd apps/mobile && npx jest --config jest.app.config.js
 *      or: pnpm test:mobile:app (root script)
 */
/** @type {import('jest').Config} */
module.exports = {
  preset: 'jest-expo',
  setupFilesAfterFramework: [],
  setupFilesAfterEnv: ['<rootDir>/src/__tests__/setup.ts'],
  testMatch: [
    '**/app/**/__tests__/**/*.test.{ts,tsx}',
    '**/src/**/__tests__/**/*.test.{ts,tsx}',
  ],
  moduleNameMapper: {
    // pnpm creates two react-native instances (different peer-dep hashes).
    // Jest setup only mocks ONE instance (apps/mobile's). When @resilio/ui-mobile
    // loads the OTHER instance, NativeModules is unmocked → __fbBatchedBridgeConfig crash.
    // Fix: redirect ALL react-native imports to apps/mobile's instance (already mocked).
    '^react-native$': '<rootDir>/node_modules/react-native/index.js',
    '^react-native/(.*)': '<rootDir>/node_modules/react-native/$1',
    // Mocks for packages without React Native test support
    'lucide-react-native': '<rootDir>/../../packages/ui-mobile/src/__tests__/mocks/lucide-react-native.tsx',
    'expo-haptics': '<rootDir>/../../packages/ui-mobile/src/__tests__/mocks/expo-haptics.ts',
    'react-native-svg': '<rootDir>/../../packages/ui-mobile/src/__tests__/mocks/react-native-svg.tsx',
    'react-native-safe-area-context': '<rootDir>/../../packages/ui-mobile/src/__tests__/mocks/react-native-safe-area-context.ts',
    // NativeWind no-op mock — patches react-native components at import time in prod,
    // which requires native module access unavailable in jest environment
    '^nativewind$': '<rootDir>/src/__tests__/mocks/nativewind.ts',
    // Workspace package resolutions
    '@resilio/design-tokens': '<rootDir>/../../packages/design-tokens/src/index.ts',
    '@resilio/ui-mobile': '<rootDir>/../../packages/ui-mobile/src/index.ts',
  },
  // pnpm: scoped pkgs use + separator, variants use - (see packages/ui-mobile/jest.config.js)
  transformIgnorePatterns: [
    'node_modules/\\.pnpm/(?!(react-native|@react-native|expo|@expo|nativewind|lucide-react-native|react-native-reanimated|react-native-safe-area-context|react-native-svg|@testing-library)[-@+])',
    'node_modules/(?!(\\.pnpm/|react-native|@react-native|expo|@expo|nativewind|lucide-react-native|react-native-reanimated|react-native-safe-area-context|react-native-svg|@testing-library))',
  ],
};
